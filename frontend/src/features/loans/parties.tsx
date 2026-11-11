import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Pencil, Plus, ShieldAlert } from "lucide-react";
import { get, patch, post } from "@/api/client";
import { useAuth, useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, Textarea } from "@/components/ui/input";
import { Switch } from "@/components/ui/misc";
import { ConfirmDialog, Field } from "@/components/data/feedback";
import { EmptyState, ErrorState, InlineError, TableSkeleton } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { formatDate } from "@/lib/utils";

export interface Guarantor { id: string; full_name: string; relationship_to_borrower: string | null; mobile: string | null; email: string | null; agreement_ref: string;
  agreement_executed_on: string | null; guarantee_scope: string | null; guarantee_status: string; verification: string; communication_permitted: boolean;
  communication_basis: string | null; approval_status: string; pending_change: { action?: string; reason?: string; changes?: Record<string, unknown> } | null; pending_by: string | null; source: string }
export interface Witness { id: string; full_name: string; document_ref: string; witnessed_on: string | null; address_city: string | null; verification: string; notes: string | null; liability: string; source: string }

type GForm = { full_name: string; relationship_to_borrower: string; mobile: string; email: string; agreement_ref: string; agreement_executed_on: string; guarantee_scope: string; communication_permitted: boolean; communication_basis: string; reason: string };
const emptyG: GForm = { full_name: "", relationship_to_borrower: "", mobile: "", email: "", agreement_ref: "", agreement_executed_on: "", guarantee_scope: "", communication_permitted: false, communication_basis: "", reason: "" };
const clean = (o: Record<string, unknown>) => Object.fromEntries(Object.entries(o).filter(([, v]) => v !== "" && v !== undefined));

function GuarantorDialog({ loanId, editing, open, onOpenChange }: { loanId: string; editing: Guarantor | null; open: boolean; onOpenChange: (o: boolean) => void }) {
  const qc = useQueryClient();
  const [f, setF] = React.useState<GForm>(emptyG);
  const [touched, setTouched] = React.useState(false);
  React.useEffect(() => {
    if (!open) return;
    setTouched(false);
    setF(editing ? { ...emptyG, full_name: editing.full_name, relationship_to_borrower: editing.relationship_to_borrower ?? "", agreement_ref: editing.agreement_ref,
      agreement_executed_on: editing.agreement_executed_on ?? "", guarantee_scope: editing.guarantee_scope ?? "", communication_permitted: editing.communication_permitted,
      communication_basis: editing.communication_basis ?? "" } : emptyG);
  }, [open, editing]);
  const set = (k: keyof GForm) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => setF((s) => ({ ...s, [k]: e.target.value }));
  const err = { full_name: f.full_name.trim().length < 2 ? "Enter the guarantor name" : undefined, agreement_ref: f.agreement_ref.trim().length < 2 ? "Agreement reference is required (FR-GUA-01)" : undefined,
    basis: f.communication_permitted && f.communication_basis.trim().length < 5 ? "State the lawful basis from the executed agreement" : undefined,
    reason: editing && f.reason.trim().length < 5 ? "Give a reason for the change" : undefined };
  const ok = !Object.values(err).some(Boolean);
  const m = useMutation({
    mutationFn: () => {
      const body = clean({ ...f, reason: undefined, mobile: editing ? undefined : f.mobile, email: editing ? undefined : f.email });
      return editing ? patch(`/guarantors/${editing.id}`, { ...body, reason: f.reason }) : post(`/loans/${loanId}/guarantors`, body);
    },
    onSuccess: () => { toast.success(editing ? "Change submitted for second-user approval" : "Guarantor recorded"); qc.invalidateQueries({ queryKey: ["guarantors", loanId] }); onOpenChange(false); },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent wide>
        <DialogHeader title={editing ? "Change guarantor record" : "Add guarantor"} description="Guarantor details must come from the executed guarantee agreement. Changes are audited and may need a second approver." />
        <DialogBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name" htmlFor="g-name" required error={touched ? err.full_name : undefined}><Input id="g-name" value={f.full_name} onChange={set("full_name")} /></Field>
          <Field label="Relationship to borrower" htmlFor="g-rel"><Input id="g-rel" value={f.relationship_to_borrower} onChange={set("relationship_to_borrower")} /></Field>
          {!editing && <Field label="Mobile" htmlFor="g-mob" hint="Digits with country code, e.g. +919876543210"><Input id="g-mob" value={f.mobile} onChange={set("mobile")} /></Field>}
          {!editing && <Field label="Email" htmlFor="g-mail"><Input id="g-mail" type="email" value={f.email} onChange={set("email")} /></Field>}
          <Field label="Guarantee agreement reference" htmlFor="g-ref" required error={touched ? err.agreement_ref : undefined}><Input id="g-ref" className="font-mono" value={f.agreement_ref} onChange={set("agreement_ref")} /></Field>
          <Field label="Agreement executed on" htmlFor="g-date"><Input id="g-date" type="date" value={f.agreement_executed_on} onChange={set("agreement_executed_on")} /></Field>
          <div className="sm:col-span-2"><Field label="Scope of guarantee (as supplied by the bank)" htmlFor="g-scope"><Input id="g-scope" value={f.guarantee_scope} onChange={set("guarantee_scope")} /></Field></div>
          <div className="flex items-start gap-3 rounded-md border p-3 sm:col-span-2">
            <Switch id="g-comm" checked={f.communication_permitted} onCheckedChange={(v) => setF((s) => ({ ...s, communication_permitted: v }))} />
            <div className="flex-1 space-y-2"><label htmlFor="g-comm" className="text-sm font-medium">Communication permitted by the executed agreement</label>
              <p className="text-[11px] text-muted-foreground">Guarantors are contacted only with an approved lawful basis and template (BR-13).</p>
              {f.communication_permitted && <Field label="Lawful basis" htmlFor="g-basis" required error={touched ? err.basis : undefined}><Input id="g-basis" value={f.communication_basis} onChange={set("communication_basis")} placeholder="e.g. Clause 14 of executed guarantee agreement" /></Field>}</div>
          </div>
          {editing && <div className="sm:col-span-2"><Field label="Reason for change" htmlFor="g-reason" required error={touched ? err.reason : undefined}><Textarea id="g-reason" value={f.reason} onChange={set("reason")} /></Field></div>}
          <div className="sm:col-span-2"><InlineError error={m.error} /></div>
        </DialogBody>
        <DialogFooter><Button variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button loading={m.isPending} onClick={() => { setTouched(true); if (ok) m.mutate(); }}>{editing ? "Submit change" : "Add guarantor"}</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function GuarantorsTab({ loanId }: { loanId: string }) {
  const can = useCan();
  const me = useAuth((s) => s.me);
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["guarantors", loanId], queryFn: () => get<Guarantor[]>(`/loans/${loanId}/guarantors`) });
  const [open, setOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Guarantor | null>(null);
  const [decide, setDecide] = React.useState<{ g: Guarantor; action: "approve" | "reject" } | null>(null);
  const dm = useMutation({
    mutationFn: (notes: string) => post(`/guarantors/${decide!.g.id}/${decide!.action}`, { notes }),
    onSuccess: () => { toast.success(decide?.action === "approve" ? "Change approved" : "Change rejected"); setDecide(null); qc.invalidateQueries({ queryKey: ["guarantors", loanId] }); },
  });
  if (q.isLoading) return <TableSkeleton rows={3} />;
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">Guarantor liability derives only from the executed agreement and applicable law (BR-07).</p>
        {can("guarantor:write") && <Button size="sm" onClick={() => { setEditing(null); setOpen(true); }}><Plus />Add guarantor</Button>}
      </div>
      {!q.data?.length ? <EmptyState title="No guarantor recorded for this loan" /> : (
        <ul className="grid gap-3 md:grid-cols-2">
          {q.data.map((g) => (
            <li key={g.id} className="rounded-lg border bg-surface p-4">
              <div className="flex items-start justify-between gap-2">
                <div><p className="font-semibold">{g.full_name}</p><p className="text-xs text-muted-foreground">{g.relationship_to_borrower ?? "Relationship not recorded"}</p></div>
                <div className="flex flex-wrap justify-end gap-1"><StatusBadge status={g.guarantee_status} /><StatusBadge status={g.verification} />
                  {g.approval_status !== "APPROVED" && <StatusBadge status="PENDING_APPROVAL" />}</div>
              </div>
              <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                <div><dt className="text-muted-foreground">Agreement</dt><dd className="font-mono">{g.agreement_ref}</dd></div>
                <div><dt className="text-muted-foreground">Executed</dt><dd>{formatDate(g.agreement_executed_on)}</dd></div>
                <div><dt className="text-muted-foreground">Contact</dt><dd>{g.mobile ?? "-"}</dd></div>
                <div><dt className="text-muted-foreground">Communication</dt><dd>{g.communication_permitted ? <Badge tone="success">Permitted</Badge> : <Badge tone="neutral">Not permitted</Badge>}</dd></div>
              </dl>
              {g.guarantee_scope && <p className="mt-2 text-xs text-muted-foreground">{g.guarantee_scope}</p>}
              {g.pending_change && g.approval_status !== "APPROVED" && (
                <div className="mt-3 rounded-md bg-warning-soft p-2 text-xs">
                  <p className="font-medium">Pending {g.pending_change.action?.toLowerCase()} awaiting a second approver</p>
                  {g.pending_change.reason && <p className="text-muted-foreground">Reason: {g.pending_change.reason}</p>}
                  {g.pending_change.changes && <p className="text-muted-foreground">Fields: {Object.keys(g.pending_change.changes).join(", ")}</p>}
                </div>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                {can("guarantor:write") && g.approval_status === "APPROVED" && <Button size="sm" variant="secondary" onClick={() => { setEditing(g); setOpen(true); }}><Pencil />Change</Button>}
                {can("guarantor:approve") && g.approval_status !== "APPROVED" && (g.pending_by === me?.id
                  ? <p className="text-[11px] text-muted-foreground">You submitted this change; another approver must decide (maker-checker).</p>
                  : <><Button size="sm" variant="success" onClick={() => setDecide({ g, action: "approve" })}>Approve</Button>
                    <Button size="sm" variant="secondary" onClick={() => setDecide({ g, action: "reject" })}>Reject</Button></>)}
              </div>
            </li>
          ))}
        </ul>
      )}
      <GuarantorDialog loanId={loanId} editing={editing} open={open} onOpenChange={setOpen} />
      <ConfirmDialog open={!!decide} onOpenChange={(o) => !o && setDecide(null)} title={decide?.action === "approve" ? "Approve guarantor change" : "Reject guarantor change"}
        rationale rationaleLabel="Decision notes" minLength={3} loading={dm.isPending} error={dm.error} tone={decide?.action === "reject" ? "danger" : "default"}
        confirmLabel={decide?.action === "approve" ? "Approve" : "Reject"} onConfirm={(n) => dm.mutate(n ?? "")} />
    </div>
  );
}

type WForm = { full_name: string; document_ref: string; witnessed_on: string; address_city: string; notes: string; verification: string };

export function WitnessesTab({ loanId }: { loanId: string }) {
  const can = useCan();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["witnesses", loanId], queryFn: () => get<Witness[]>(`/loans/${loanId}/witnesses`) });
  const [open, setOpen] = React.useState(false);
  const [editing, setEditing] = React.useState<Witness | null>(null);
  const [f, setF] = React.useState<WForm>({ full_name: "", document_ref: "", witnessed_on: "", address_city: "", notes: "", verification: "" });
  const [touched, setTouched] = React.useState(false);
  const start = (w: Witness | null) => {
    setEditing(w); setTouched(false);
    setF(w ? { full_name: w.full_name, document_ref: w.document_ref, witnessed_on: w.witnessed_on ?? "", address_city: w.address_city ?? "", notes: w.notes ?? "", verification: w.verification }
      : { full_name: "", document_ref: "", witnessed_on: "", address_city: "", notes: "", verification: "" });
    setOpen(true);
  };
  const m = useMutation({
    mutationFn: () => editing ? patch(`/witnesses/${editing.id}`, clean({ ...f })) : post(`/loans/${loanId}/witnesses`, clean({ ...f, verification: undefined })),
    onSuccess: () => { toast.success(editing ? "Witness updated" : "Witness recorded"); setOpen(false); qc.invalidateQueries({ queryKey: ["witnesses", loanId] }); },
  });
  const err = { full_name: f.full_name.trim().length < 2 ? "Enter the witness name" : undefined, document_ref: f.document_ref.trim().length < 2 ? "Enter the witnessed document reference" : undefined };
  const set = (k: keyof WForm) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => setF((s) => ({ ...s, [k]: e.target.value }));
  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2 rounded-md border border-teal/30 bg-teal-soft px-3 py-2 text-xs text-teal">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />
        <span>A witness is not a guarantor and has no repayment liability (BR-07). Witness records carry no guarantee or communication fields and are never used for follow-up.</span>
      </div>
      {can("witness:write") && <div className="flex justify-end"><Button size="sm" onClick={() => start(null)}><Plus />Add witness</Button></div>}
      {q.isLoading ? <TableSkeleton rows={2} /> : q.error ? <ErrorState error={q.error} /> : !q.data?.length ? <EmptyState title="No witnesses recorded" /> : (
        <ul className="divide-y rounded-lg border bg-surface">
          {q.data.map((w) => (
            <li key={w.id} className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1"><p className="font-medium">{w.full_name}</p>
                <p className="text-xs text-muted-foreground">Witnessed <span className="font-mono">{w.document_ref}</span> on {formatDate(w.witnessed_on)}{w.address_city ? ` - ${w.address_city}` : ""}</p></div>
              <Badge tone="neutral">Liability: none</Badge><StatusBadge status={w.verification} />
              {can("witness:write") && <Button size="sm" variant="ghost" onClick={() => start(w)}><Pencil />Edit</Button>}
            </li>
          ))}
        </ul>
      )}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader title={editing ? "Edit witness" : "Add witness"} description="Record who witnessed the loan document. This creates no obligation." />
          <DialogBody>
            <Field label="Full name" htmlFor="w-name" required error={touched ? err.full_name : undefined}><Input id="w-name" value={f.full_name} onChange={set("full_name")} /></Field>
            <Field label="Witnessed document reference" htmlFor="w-doc" required error={touched ? err.document_ref : undefined}><Input id="w-doc" className="font-mono" value={f.document_ref} onChange={set("document_ref")} /></Field>
            <Field label="Witnessed on" htmlFor="w-date"><Input id="w-date" type="date" value={f.witnessed_on} onChange={set("witnessed_on")} /></Field>
            <Field label="City" htmlFor="w-city"><Input id="w-city" value={f.address_city} onChange={set("address_city")} /></Field>
            {editing && <Field label="Verification" htmlFor="w-ver"><select id="w-ver" className="h-9 w-full rounded-md border border-input bg-surface px-2 text-sm" value={f.verification} onChange={set("verification")}>
              <option value="UNVERIFIED">Unverified</option><option value="VERIFIED">Verified</option><option value="FAILED">Failed</option></select></Field>}
            <Field label="Notes" htmlFor="w-notes"><Textarea id="w-notes" value={f.notes} onChange={set("notes")} /></Field>
            <InlineError error={m.error} />
          </DialogBody>
          <DialogFooter><Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button loading={m.isPending} onClick={() => { setTouched(true); if (!err.full_name && !err.document_ref) m.mutate(); }}>Save witness</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
