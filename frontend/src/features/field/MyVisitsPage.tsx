import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { CalendarClock, MapPin, Phone, PlayCircle, ShieldOff } from "lucide-react";
import { get, post } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { EmptyState, QueryBoundary } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { cn, formatDate, formatDateTime } from "@/lib/utils";
import type { MyCase, Visit } from "./types";

export default function MyVisitsPage() {
  const nav = useNavigate();
  const q = useQuery({ queryKey: ["my-cases"], queryFn: () => get<{ items: MyCase[]; settings: { location_capture_note: string } }>("/field/my-cases") });
  const start = useMutation({
    mutationFn: (c: MyCase) => post<Visit>(`/cases/${c.case_id}/visits`, { purpose: c.next_action || "Follow-up visit for assigned case", draft: true, client_draft_id: crypto.randomUUID() }),
    onSuccess: (v) => nav(`/field/visits/${v.id}`),
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="My field visits" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Field visits" }]}
        description="Only cases assigned to you are shown (FR-FLD-01)." />
      <div className="mb-4 flex items-start gap-2 rounded-md border bg-surface px-3 py-2 text-xs text-muted-foreground">
        <ShieldOff className="mt-0.5 h-4 w-4 shrink-0 text-teal" />Location is not captured. Check-in and check-out record time only (OD-14). Stay safe: report any incident in the visit form.
      </div>
      <QueryBoundary query={q} isEmpty={(d) => d.items.length === 0}
        empty={<EmptyState icon={CalendarClock} title="No assigned cases" description="Your manager assigns cases. They appear here with the borrower address and next action." />}>
        {(d) => (
          <ul className="space-y-3">
            {d.items.map((c) => (
              <li key={c.case_id}>
                <Card className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="truncate text-base font-semibold">{c.student.name}</p>
                      <p className="font-mono text-[11px] text-muted-foreground">{c.case_ref} - {c.student.dapro_ref}</p>
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-1"><StatusBadge status={c.priority} /><StatusBadge status={c.status} /></div>
                  </div>
                  <div className="mt-3 space-y-1.5 text-sm">
                    <p className="flex items-start gap-2"><MapPin className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />{c.address ? c.address.text : <span className="text-muted-foreground">No current address on record</span>}</p>
                    <p className="flex items-center gap-2"><Phone className="h-4 w-4 text-muted-foreground" />{c.student.mobile ?? "No mobile on record"}</p>
                    {c.loan && <p className="flex flex-wrap items-center gap-1.5 text-xs"><span className="font-mono">{c.loan.bank_loan_ref}</span><StatusBadge status={c.loan.repayment_status} />{c.loan.dpd ? <Badge tone="danger">{c.loan.dpd} DPD</Badge> : null}</p>}
                    <p className="text-xs"><span className="text-muted-foreground">Next action:</span> {c.next_action ?? "-"}</p>
                    <p className={cn("text-xs", c.overdue && "font-semibold text-danger")}>Due {formatDate(c.due_on)}{c.overdue ? " (overdue)" : ""}</p>
                  </div>
                  <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                    {c.next_visit ? (
                      <Button className="w-full sm:w-auto" onClick={() => nav(`/field/visits/${c.next_visit!.id}`)}>
                        <CalendarClock />Open {c.next_visit.status === "DRAFT" ? "draft visit" : `visit ${c.next_visit.scheduled_for ? formatDateTime(c.next_visit.scheduled_for) : ""}`}
                      </Button>
                    ) : (
                      <Button className="w-full sm:w-auto" loading={start.isPending && start.variables?.case_id === c.case_id} onClick={() => start.mutate(c)}><PlayCircle />Start visit</Button>
                    )}
                    <Button variant="secondary" className="w-full sm:w-auto" onClick={() => nav(`/cases/${c.case_id}`)}>Case details</Button>
                  </div>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </QueryBoundary>
    </div>
  );
}
