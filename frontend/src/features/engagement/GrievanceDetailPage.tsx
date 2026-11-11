import * as React from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { EyeOff, MessageCircle, RefreshCcw, UserPlus } from "lucide-react";
import { get } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { EmptyState, ErrorState } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { Timeline, type TimelineItem } from "@/components/data/timeline";
import { PageFallback } from "@/components/layout/AppShell";
import { cn, formatDate, formatDateTime } from "@/lib/utils";
import { AssignGrievanceDialog, GrievanceTransitionDialog, RespondForm } from "./GrievanceDialogs";
import type { Grievance, GrievanceEvent } from "./types";

const OPEN = ["SUBMITTED", "ACKNOWLEDGED", "UNDER_REVIEW", "AWAITING_INFORMATION"];

function toTimeline(events: GrievanceEvent[]): TimelineItem[] {
  return [...events].reverse().map((e) => ({
    id: e.id, at: e.at, actor: e.actor_name,
    icon: e.visibility === "INTERNAL" ? EyeOff : e.type === "STATUS_CHANGED" ? RefreshCcw : MessageCircle,
    tone: e.visibility === "INTERNAL" ? "default" : e.to === "RESOLVED" || e.to === "CLOSED" ? "success" : e.to === "REJECTED" ? "danger" : "info",
    title: <span className="flex flex-wrap items-center gap-1.5">{labelFor(e.type)}{e.to && <StatusBadge status={e.to} />}{e.visibility === "INTERNAL" && <Badge tone="outline">Internal</Badge>}</span>,
    body: <p className="whitespace-pre-wrap text-foreground/80">{e.message}</p>,
  }));
}

export default function GrievanceDetailPage() {
  const { id } = useParams();
  const can = useCan();
  const q = useQuery({ queryKey: ["grievance", id], queryFn: () => get<Grievance>(`/grievances/${id}`) });
  const [assign, setAssign] = React.useState(false);
  const [to, setTo] = React.useState<string | null>(null);
  if (q.isLoading) return <PageFallback />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const g = q.data;
  const manage = can("grievance:manage");
  const open = OPEN.includes(g.status);
  return (
    <div className="space-y-6">
      <PageHeader title={<span className="flex flex-wrap items-center gap-3"><span className="font-mono">{g.ref}</span><span className="text-base font-normal text-muted-foreground">{g.subject}</span></span>}
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Grievances", to: "/grievances" }, { label: g.ref }]}
        meta={<><StatusBadge status={g.status} /><StatusBadge status={g.priority} /><Badge tone="outline">{labelFor(g.category)}</Badge>
          <span className="text-xs text-muted-foreground">Received via {labelFor(g.channel).toLowerCase()} {formatDateTime(g.created_at)}</span></>}
        actions={manage && open && <Button variant="secondary" onClick={() => setAssign(true)}><UserPlus />{g.owner_id ? "Reassign" : "Assign"}</Button>} />

      <Card>
        <CardContent className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <KeyValue cols={2} items={[
              { label: "Borrower", value: <Link to={`/students/${g.student_id}`} className="font-medium text-primary hover:underline">{g.student_name}</Link>, hint: g.dapro_ref },
              { label: "Owner", value: g.owner_name ?? <span className="text-warning">Unassigned</span> },
              { label: "Response due", value: <span className={cn(g.overdue && "font-semibold text-danger")}>{formatDate(g.due_on)}{g.overdue ? " (overdue)" : ""}</span>, hint: "Service-level target from the GRIEVANCE_SLA policy" },
              { label: "About staff member", value: g.subject_user_name ?? "Not applicable", hint: g.subject_user_name ? "This person cannot handle the grievance (FR-GRV-03)" : undefined },
            ]} />
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Description</p>
              <p className="whitespace-pre-wrap rounded-md bg-muted/40 p-3 text-sm">{g.description}</p>
            </div>
            {g.correction_field && (
              <div className="rounded-md border border-primary/20 bg-primary-soft/40 p-3 text-sm">
                <p className="font-medium">Correction requested</p>
                <p className="mt-1 text-xs text-muted-foreground">{labelFor(g.correction_field)} should be <span className="font-mono text-foreground">{g.correction_requested_value}</span>. The record changes only if a reviewer approves it on resolution.</p>
              </div>
            )}
            {g.resolution && <p className="rounded-md border bg-success-soft/50 p-3 text-sm"><span className="font-medium">Outcome:</span> {g.resolution}</p>}
          </div>
          <div className="space-y-3 rounded-lg border bg-muted/30 p-4 text-sm">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Linked records</p>
            {g.case_id ? <div><Link to={`/cases/${g.case_id}`} className="font-mono font-medium text-primary hover:underline">{g.case_ref}</Link>
              <div className="mt-1 flex flex-wrap items-center gap-1.5"><StatusBadge status={g.case_status} />{g.case_status === "DISPUTED" && <span className="text-[11px] text-muted-foreground">paused until resolved</span>}</div></div>
              : <p className="text-muted-foreground">No linked case</p>}
            {g.loan_id ? <Link to={`/loans/${g.loan_id}`} className="block text-primary hover:underline">View linked loan</Link> : <p className="text-muted-foreground">No linked loan</p>}
          </div>
        </CardContent>
        {manage && (g.allowed_transitions?.length ?? 0) > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t px-5 py-3">
            <span className="mr-1 text-xs font-medium text-muted-foreground">Next step:</span>
            {g.allowed_transitions!.map((t) => (
              <Button key={t} size="sm" variant={t === "REJECTED" ? "danger" : t === "RESOLVED" || t === "CLOSED" ? "success" : "secondary"} onClick={() => setTo(t)}>{labelFor(t)}</Button>
            ))}
          </div>
        )}
      </Card>

      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Activity</CardTitle></CardHeader>
          <CardContent>{g.events?.length ? <Timeline items={toTimeline(g.events)} /> : <EmptyState title="No activity yet" />}</CardContent>
        </Card>
        {manage && open && <Card><CardHeader><CardTitle>Respond</CardTitle></CardHeader><CardContent><RespondForm g={g} /></CardContent></Card>}
      </div>

      {assign && <AssignGrievanceDialog g={g} onClose={() => setAssign(false)} />}
      {to && <GrievanceTransitionDialog g={g} to={to} onClose={() => setTo(null)} />}
    </div>
  );
}
