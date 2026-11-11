import * as React from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Dialog, SheetContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { NativeSelect, Textarea } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { EntitySelect, studentOptions } from "@/components/data/entity";
import { KeyValue } from "@/components/data/layout";
import { InlineError } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { post } from "@/api/client";
import { useCan } from "@/auth/store";
import { formatDateTime } from "@/lib/utils";

export interface ReconItem { id: string; kind: string; severity: string; summary: string; details: Record<string, unknown>; status: string; resolution: string | null;
  loan_id: string | null; student_id: string | null; batch_id: string | null; resolved_at: string | null; created_at: string;
  bank_loan_ref: string | null; student_name: string | null; dapro_ref: string | null }

const ACTIONS: Record<string, { value: string; label: string }[]> = {
  AMBIGUOUS_LINK: [{ value: "CONFIRM_LINK", label: "Confirm link (identity verified by a person)" }, { value: "REJECT_LINK", label: "Reject link" }],
  UNMATCHED_LOAN: [{ value: "LINK_TO_STUDENT", label: "Link to a student (validated with bank)" }, { value: "DISMISS", label: "Dismiss" }],
};
const DEFAULT_ACTIONS = [{ value: "RESOLVE", label: "Resolve (documented)" }, { value: "DISMISS", label: "Dismiss" }];

export function ReconDrawer({ item, onClose }: { item: ReconItem | null; onClose: () => void }) {
  const can = useCan();
  const qc = useQueryClient();
  const actions = item ? ACTIONS[item.kind] ?? DEFAULT_ACTIONS : DEFAULT_ACTIONS;
  const [action, setAction] = React.useState("");
  const [resolution, setResolution] = React.useState("");
  const [studentId, setStudentId] = React.useState<string | null>(null);
  const [touched, setTouched] = React.useState(false);
  React.useEffect(() => { setAction(""); setResolution(""); setStudentId(null); setTouched(false); }, [item?.id]);
  const m = useMutation({
    mutationFn: () => post(`/reconciliation/${item!.id}/resolve`, { action, resolution: resolution.trim(), student_id: action === "LINK_TO_STUDENT" ? studentId : undefined }),
    onSuccess: () => { toast.success("Reconciliation item closed and audited"); qc.invalidateQueries({ queryKey: ["recon"] }); onClose(); },
  });
  const err = { action: !action ? "Choose an action" : undefined, resolution: resolution.trim().length < 5 ? "Record the evidence or reason (min 5 characters)" : undefined,
    student: action === "LINK_TO_STUDENT" && !studentId ? "Select the student" : undefined };
  const ok = !err.action && !err.resolution && !err.student;
  const details = Object.entries(item?.details ?? {}).map(([k, v]) => ({ label: k.replace(/_/g, " "), value: typeof v === "object" ? JSON.stringify(v) : String(v) }));
  return (
    <Dialog open={!!item} onOpenChange={(o) => !o && onClose()}>
      {item && (
        <SheetContent title={labelFor(item.kind)} description={item.summary}>
          <div className="space-y-5 p-5">
            <div className="flex flex-wrap gap-2"><StatusBadge status={item.severity} /><StatusBadge status={item.status} /></div>
            <KeyValue items={[{ label: "Borrower", value: item.student_id ? <Link className="text-primary hover:underline" to={`/students/${item.student_id}`}>{item.student_name} ({item.dapro_ref})</Link> : "-" },
              { label: "Loan", value: item.loan_id ? <Link className="font-mono text-primary hover:underline" to={`/loans/${item.loan_id}`}>{item.bank_loan_ref}</Link> : (item.details?.bank_loan_ref as string) ?? "-" },
              { label: "Raised", value: formatDateTime(item.created_at) }, { label: "Batch", value: item.batch_id ? <Link className="text-primary hover:underline" to={`/imports/${item.batch_id}`}>Open batch</Link> : "-" }]} />
            <div><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Details from source</p>
              {details.length ? <KeyValue items={details} /> : <p className="text-sm text-muted-foreground">No further details.</p>}</div>
            {item.status !== "OPEN" ? (
              <div className="rounded-md bg-muted p-3 text-sm"><p className="font-medium">Resolved {formatDateTime(item.resolved_at)}</p><p className="text-muted-foreground">{item.resolution}</p></div>
            ) : can("loan:reconcile") && (
              <div className="space-y-3 rounded-md border p-4">
                <p className="text-sm font-semibold">Resolve this item</p>
                <p className="text-[11px] text-muted-foreground">DAPRO never decides a link or allocation itself. Your decision and rationale are recorded in the audit trail.</p>
                <Field label="Action" htmlFor="rc-action" required error={touched ? err.action : undefined}>
                  <NativeSelect id="rc-action" value={action} onChange={(e) => setAction(e.target.value)}>
                    <option value="">Choose an action</option>{actions.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
                  </NativeSelect>
                </Field>
                {action === "LINK_TO_STUDENT" && <Field label="Student" htmlFor="rc-student" required error={touched ? err.student : undefined}>
                  <EntitySelect id="rc-student" queryKey="students" value={studentId} onChange={(v) => setStudentId(v)} fetchOptions={studentOptions} /></Field>}
                <Field label="Resolution and evidence" htmlFor="rc-res" required error={touched ? err.resolution : undefined} hint="For example: identity confirmed against the signed loan agreement page 2.">
                  <Textarea id="rc-res" value={resolution} onChange={(e) => setResolution(e.target.value)} />
                </Field>
                <InlineError error={m.error} />
                <Button loading={m.isPending} onClick={() => { setTouched(true); if (ok) m.mutate(); }}>Record decision</Button>
              </div>
            )}
          </div>
        </SheetContent>
      )}
    </Dialog>
  );
}
