import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ClipboardCheck, ShieldAlert } from "lucide-react";
import { get } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { EmptyState, QueryBoundary } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { formatDateTime } from "@/lib/utils";
import { ReviewPanel } from "./ReviewPanel";
import type { Visit } from "./types";

export default function VisitReviewPage() {
  const q = useQuery({ queryKey: ["review-queue"], queryFn: () => get<{ items: Visit[] }>("/field/review-queue") });
  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title="Field visit review" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Visit review" }]}
        description="Reports with safety incidents, escalated or disputed cases need supervisor review (FR-FLD-05)." />
      <QueryBoundary query={q} isEmpty={(d) => d.items.length === 0}
        empty={<EmptyState icon={ClipboardCheck} title="No reports awaiting review" />}>
        {(d) => (
          <ul className="space-y-4">
            {d.items.map((v) => (
              <li key={v.id}>
                <Card className="p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold">{v.student_name} <span className="font-mono text-xs font-normal text-muted-foreground">{v.case_ref}</span></p>
                      <p className="text-xs text-muted-foreground">{v.officer?.name} - visited {formatDateTime(v.visited_at)} - outcome {labelFor(v.outcome)}</p>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {v.safety_incident && <Badge tone="danger"><ShieldAlert className="h-3 w-3" />Safety incident</Badge>}
                      <StatusBadge status={v.case_status} /><StatusBadge status={v.case_priority} />
                    </div>
                  </div>
                  <p className="mt-3 text-sm">{v.notes}</p>
                  {v.incident_notes && <p className="mt-2 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger">Incident: {v.incident_notes}</p>}
                  <p className="mt-2 text-xs"><Link className="text-primary hover:underline" to={`/field/visits/${v.id}`}>Open full report</Link> - <Link className="text-primary hover:underline" to={`/cases/${v.case_id}`}>Open case</Link></p>
                  <div className="mt-4 border-t pt-4"><ReviewPanel visit={v} compact /></div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </QueryBoundary>
    </div>
  );
}
