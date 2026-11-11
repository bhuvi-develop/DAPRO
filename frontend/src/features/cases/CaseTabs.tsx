import * as React from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CalendarPlus, Download, FileCheck2, HandCoins, PhoneCall, ShieldAlert } from "lucide-react";
import { download, post, upload } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { FileDrop } from "@/components/data/entity";
import { Field } from "@/components/data/feedback";
import { EmptyState, InlineError } from "@/components/data/states";
import { Money, StatusBadge, labelFor } from "@/components/data/status";
import { Timeline } from "@/components/data/timeline";
import { formatDate, formatDateTime } from "@/lib/utils";
import type { CaseDetail, CaseMeta } from "./types";

function useRefresh(id: string) {
  const qc = useQueryClient();
  return () => { qc.invalidateQueries({ queryKey: ["case", id] }); qc.invalidateQueries({ queryKey: ["cases"] }); };
}

const nowLocal = () => new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16);

export function FollowUpsTab({ c, meta }: { c: CaseDetail; meta?: CaseMeta }) {
  const refresh = useRefresh(c.id);
  const outcomes = [...(meta?.outcomes.no_contact ?? []), ...(meta?.outcomes.contact ?? [])];
  const [channel, setChannel] = React.useState("PHONE");
  const [outcome, setOutcome] = React.useState("NO_ANSWER");
  const [notes, setNotes] = React.useState("");
  const [at, setAt] = React.useState(nowLocal());
  const [next, setNext] = React.useState("");
  const m = useMutation({
    mutationFn: () => post(`/cases/${c.id}/follow-ups`, { channel, outcome, notes, contacted_at: new Date(at).toISOString(), next_follow_up_on: next || undefined }),
    onSuccess: () => { toast.success("Follow-up recorded"); setNotes(""); setNext(""); refresh(); },
  });
  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="lg:col-span-3">
        {c.follow_ups.length ? (
          <Timeline items={c.follow_ups.map((f) => ({
            id: f.id, at: f.contacted_at, actor: f.actor?.name, icon: PhoneCall,
            tone: (meta?.outcomes.contact ?? []).includes(f.outcome) ? "success" : "warning",
            title: <span>{labelFor(f.channel)} - {labelFor(f.outcome)}</span>,
            body: <span>{f.notes}{f.next_follow_up_on ? ` Next follow-up: ${formatDate(f.next_follow_up_on)}.` : ""}</span>,
          }))} />
        ) : <EmptyState title="No follow-ups yet" description="Record each compliant contact attempt. Failed contact is never evidence of absconding (BR-05)." />}
      </div>
      {c.can.follow_up && (
        <div className="space-y-3 rounded-lg border p-4 lg:col-span-2">
          <p className="text-sm font-semibold">Record follow-up</p>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Channel" htmlFor="fu-ch"><NativeSelect id="fu-ch" value={channel} onChange={(e) => setChannel(e.target.value)}>{(meta?.channels ?? ["PHONE"]).map((x) => <option key={x} value={x}>{labelFor(x)}</option>)}</NativeSelect></Field>
            <Field label="Outcome" htmlFor="fu-out"><NativeSelect id="fu-out" value={outcome} onChange={(e) => setOutcome(e.target.value)}>{outcomes.map((x) => <option key={x} value={x}>{labelFor(x)}</option>)}</NativeSelect></Field>
          </div>
          <Field label="Contacted at" htmlFor="fu-at"><Input id="fu-at" type="datetime-local" value={at} onChange={(e) => setAt(e.target.value)} /></Field>
          <Field label="Notes" htmlFor="fu-notes" required hint="Factual record of what happened."><Textarea id="fu-notes" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
          <Field label="Next follow-up" htmlFor="fu-next"><Input id="fu-next" type="date" value={next} onChange={(e) => setNext(e.target.value)} /></Field>
          <InlineError error={m.error} />
          <Button className="w-full" loading={m.isPending} disabled={notes.trim().length < 3} onClick={() => m.mutate()}>Save follow-up</Button>
        </div>
      )}
    </div>
  );
}

export function EvidenceTab({ c }: { c: CaseDetail }) {
  const refresh = useRefresh(c.id);
  const [file, setFile] = React.useState<File | null>(null);
  const [title, setTitle] = React.useState("");
  const [kind, setKind] = React.useState("DOCUMENT");
  const m = useMutation({
    mutationFn: () => { const f = new FormData(); f.append("file", file!); f.append("title", title); f.append("kind", kind); return upload(`/cases/${c.id}/evidence`, f); },
    onSuccess: () => { toast.success("Evidence uploaded and hashed"); setFile(null); setTitle(""); refresh(); },
  });
  return (
    <div className="grid gap-6 lg:grid-cols-5">
      <div className="lg:col-span-3">
        {c.evidence.length ? (
          <ul className="divide-y rounded-md border">
            {c.evidence.map((e) => (
              <li key={e.id} className="flex items-center gap-3 px-3 py-2.5">
                <FileCheck2 className="h-4 w-4 text-teal" aria-hidden />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{e.title}</p>
                  <p className="truncate text-[11px] text-muted-foreground">{labelFor(e.kind)} - {e.file_name} - sha256 {e.sha256?.slice(0, 12)} - {labelFor(e.evidence_quality)} - {e.uploaded_by?.name}, {formatDateTime(e.created_at)}</p>
                </div>
                <Button size="icon-sm" variant="ghost" aria-label={`Download ${e.title}`} onClick={() => download(`/evidence/${e.id}/download`, e.file_name ?? "evidence").catch((x: Error) => toast.error(x.message))}><Download /></Button>
              </li>
            ))}
          </ul>
        ) : <EmptyState title="No evidence attached" description="Documents and photos are stored with a SHA-256 hash and every download is audited." />}
      </div>
      {c.can.update && (
        <div className="space-y-3 rounded-lg border p-4 lg:col-span-2">
          <p className="text-sm font-semibold">Attach evidence</p>
          <Field label="Title" htmlFor="ev-title" required><Input id="ev-title" value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
          <Field label="Kind" htmlFor="ev-kind"><NativeSelect id="ev-kind" value={kind} onChange={(e) => setKind(e.target.value)}>{["DOCUMENT", "PHOTO", "BANK_CONFIRMATION", "NOTE"].map((k) => <option key={k} value={k}>{labelFor(k)}</option>)}</NativeSelect></Field>
          <FileDrop accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" file={file} onFile={setFile} hint="PDF, PNG or JPEG. Max 10 MB. Type is verified on the server." />
          <InlineError error={m.error} />
          <Button className="w-full" loading={m.isPending} disabled={!file || title.trim().length < 3} onClick={() => m.mutate()}>Upload</Button>
        </div>
      )}
    </div>
  );
}

export function CommitmentsTab({ c }: { c: CaseDetail }) {
  const refresh = useRefresh(c.id);
  const can = useCan();
  const [amount, setAmount] = React.useState("");
  const [date, setDate] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [confirming, setConfirming] = React.useState<string | null>(null);
  const [txn, setTxn] = React.useState("");
  const add = useMutation({
    mutationFn: () => post(`/cases/${c.id}/commitments`, { amount, promised_date: date, notes: notes || undefined }),
    onSuccess: () => { toast.success("Commitment recorded as borrower-reported (not a payment)"); setAmount(""); setDate(""); setNotes(""); refresh(); },
  });
  const confirm = useMutation({
    mutationFn: () => post(`/commitments/${confirming}/confirm`, { bank_txn_ref: txn.trim() }),
    onSuccess: () => { toast.success("Commitment matched to a bank-confirmed transaction"); setConfirming(null); setTxn(""); refresh(); },
  });
  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning-soft px-3 py-2 text-xs text-[hsl(32_95%_30%)]">
        <HandCoins className="mt-0.5 h-4 w-4 shrink-0" />A payment commitment is a borrower-reported promise. It is never shown or counted as a payment until the bank confirms a transaction (BR-08, AC-12).
      </div>
      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          {c.commitments.length ? (
            <ul className="divide-y rounded-md border">
              {c.commitments.map((p) => (
                <li key={p.id} className="flex flex-wrap items-center gap-3 px-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm"><Money value={p.amount} className="font-semibold" /> promised for {formatDate(p.promised_date)}</p>
                    <p className="text-[11px] text-muted-foreground">Recorded by {p.recorded_by?.name} {formatDateTime(p.created_at)}{p.notes ? ` - ${p.notes}` : ""}{p.bank_txn_ref ? ` - bank txn ${p.bank_txn_ref}` : ""}</p>
                  </div>
                  <Badge tone="warning">Borrower-reported - not a payment</Badge>
                  <StatusBadge status={p.status} />
                  {p.status === "OPEN" && can("case:close") && <Button size="sm" variant="secondary" onClick={() => setConfirming(p.id)}>Match bank transaction</Button>}
                </li>
              ))}
            </ul>
          ) : <EmptyState title="No commitments recorded" />}
        </div>
        {c.can.update && (
          <div className="space-y-3 rounded-lg border p-4 lg:col-span-2">
            <p className="text-sm font-semibold">Record borrower commitment</p>
            <Field label="Amount (INR)" htmlFor="pc-amt" required><Input id="pc-amt" inputMode="decimal" value={amount} onChange={(e) => setAmount(e.target.value.replace(/[^\d.]/g, ""))} /></Field>
            <Field label="Promised date" htmlFor="pc-date" required><Input id="pc-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} /></Field>
            <Field label="Notes" htmlFor="pc-notes"><Textarea id="pc-notes" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
            <InlineError error={add.error} />
            <Button className="w-full" loading={add.isPending} disabled={!Number(amount) || !date} onClick={() => add.mutate()}>Record commitment</Button>
          </div>
        )}
      </div>
      <Dialog open={!!confirming} onOpenChange={(o) => !o && setConfirming(null)}>
        <DialogContent>
          <DialogHeader title="Match to bank transaction" description="Enter the bank transaction reference. It must exist in the bank-confirmed transactions for this loan." />
          <DialogBody>
            <Field label="Bank transaction reference" htmlFor="cf-txn" required><Input id="cf-txn" className="font-mono" value={txn} onChange={(e) => setTxn(e.target.value)} /></Field>
            <InlineError error={confirm.error} />
          </DialogBody>
          <DialogFooter><Button variant="secondary" onClick={() => setConfirming(null)}>Cancel</Button><Button loading={confirm.isPending} disabled={txn.trim().length < 3} onClick={() => confirm.mutate()}>Confirm</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export function VisitsTab({ c }: { c: CaseDetail }) {
  const refresh = useRefresh(c.id);
  const [open, setOpen] = React.useState(false);
  const [purpose, setPurpose] = React.useState("Confirm current address and contact details");
  const [when, setWhen] = React.useState(nowLocal());
  const m = useMutation({
    mutationFn: () => post(`/cases/${c.id}/visits`, { purpose, scheduled_for: new Date(when).toISOString() }),
    onSuccess: () => { toast.success("Visit scheduled"); setOpen(false); refresh(); },
  });
  return (
    <div className="space-y-4">
      {c.can.record_visit && <Button variant="secondary" onClick={() => setOpen(true)}><CalendarPlus />Schedule visit</Button>}
      {c.visits.length ? (
        <ul className="divide-y rounded-md border">
          {c.visits.map((v) => (
            <li key={v.id}>
              <Link to={`/field/visits/${v.id}`} className="flex flex-wrap items-center gap-3 px-3 py-2.5 hover:bg-muted/50">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{v.purpose}</p>
                  <p className="text-[11px] text-muted-foreground">{v.officer?.name} - {v.visited_at ? `visited ${formatDateTime(v.visited_at)}` : `scheduled ${formatDateTime(v.scheduled_for)}`}{v.outcome ? ` - ${labelFor(v.outcome)}` : ""}</p>
                </div>
                {v.safety_incident && <Badge tone="danger"><ShieldAlert className="h-3 w-3" />Safety incident</Badge>}
                <StatusBadge status={v.status} />
                {v.review_status !== "NOT_REQUIRED" && <StatusBadge status={v.review_status} />}
              </Link>
            </li>
          ))}
        </ul>
      ) : <EmptyState title="No field visits" description="Visits are recorded only by the assigned officer, for an authorised purpose (FR-FLD-01)." />}
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader title="Schedule field visit" description="Field visits must be proportionate, safe and limited to the case purpose." />
          <DialogBody>
            <Field label="Purpose" htmlFor="v-purpose" required><Input id="v-purpose" value={purpose} onChange={(e) => setPurpose(e.target.value)} /></Field>
            <Field label="Scheduled for" htmlFor="v-when" required><Input id="v-when" type="datetime-local" value={when} onChange={(e) => setWhen(e.target.value)} /></Field>
            <InlineError error={m.error} />
          </DialogBody>
          <DialogFooter><Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button><Button loading={m.isPending} disabled={purpose.trim().length < 3} onClick={() => m.mutate()}>Schedule</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
