import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { patch, post } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { EntitySelect } from "@/components/data/entity";
import { Field } from "@/components/data/feedback";
import { InlineError } from "@/components/data/states";
import { labelFor } from "@/components/data/status";
import { userOptions, type CaseDetail, type Transition } from "./types";

function useRefresh(id: string) {
  const qc = useQueryClient();
  return () => { qc.invalidateQueries({ queryKey: ["case", id] }); qc.invalidateQueries({ queryKey: ["cases"] }); };
}

export function AssignDialog({ c, onClose }: { c: CaseDetail; onClose: () => void }) {
  const refresh = useRefresh(c.id);
  const [owner, setOwner] = React.useState<string | null>(c.owner_id);
  const m = useMutation({
    mutationFn: () => post(`/cases/${c.id}/assign`, { owner_id: owner }),
    onSuccess: () => { toast.success("Case assigned. The owner has been notified."); refresh(); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader title={`Assign ${c.case_ref}`} description="Owners must be active users of your organization with access to cases (FR-CAS-03)." />
        <DialogBody>
          <Field label="Owner" htmlFor="owner" required>
            <EntitySelect id="owner" queryKey="users" value={owner} onChange={(v) => setOwner(v)} fetchOptions={userOptions}
              selectedLabel={owner === c.owner_id ? c.owner_name : undefined} placeholder="Search users by name or email" />
          </Field>
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={m.isPending} disabled={!owner || owner === c.owner_id} onClick={() => m.mutate()}>Assign</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function EditDialog({ c, priorities, onClose }: { c: CaseDetail; priorities: string[]; onClose: () => void }) {
  const refresh = useRefresh(c.id);
  const [priority, setPriority] = React.useState(c.priority);
  const [due, setDue] = React.useState(c.due_on ?? "");
  const [next, setNext] = React.useState(c.next_action ?? "");
  const m = useMutation({
    mutationFn: () => patch(`/cases/${c.id}`, { priority, due_on: due || null, next_action: next || null }, { "If-Match": String(c.version) }),
    onSuccess: () => { toast.success("Case updated"); refresh(); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader title="Edit case details" description="Changes are recorded on the case timeline. If someone else changed the case, reload and retry." />
        <DialogBody>
          <Field label="Priority" htmlFor="ed-prio">
            <NativeSelect id="ed-prio" value={priority} onChange={(e) => setPriority(e.target.value)}>{priorities.map((p) => <option key={p} value={p}>{labelFor(p)}</option>)}</NativeSelect>
          </Field>
          <Field label="Due date" htmlFor="ed-due"><Input id="ed-due" type="date" value={due} onChange={(e) => setDue(e.target.value)} /></Field>
          <Field label="Next action" htmlFor="ed-next" hint="Every active case keeps a next action (FR-CAS-04)."><Input id="ed-next" value={next} onChange={(e) => setNext(e.target.value)} /></Field>
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={m.isPending} onClick={() => m.mutate()}>Save changes</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function TransitionDialog({ c, t, onClose }: { c: CaseDetail; t: Transition; onClose: () => void }) {
  const refresh = useRefresh(c.id);
  const resolving = t.to === "RESOLVED";
  const [note, setNote] = React.useState("");
  const [type, setType] = React.useState(resolving ? Object.keys(c.resolution_types)[0] ?? "" : "");
  const [txn, setTxn] = React.useState("");
  const needsTxn = resolving && type === "PAYMENT_CONFIRMED";
  const needsNote = t.requires.includes("note");
  const m = useMutation({
    mutationFn: () => post(`/cases/${c.id}/transition`, {
      to: t.to, note: note || undefined, resolution_type: resolving ? type : undefined, bank_txn_ref: needsTxn ? txn.trim() : undefined,
    }),
    onSuccess: () => { toast.success(`Case moved to ${labelFor(t.to)}`); refresh(); onClose(); },
  });
  const invalid = (needsNote && note.trim().length < 3) || (needsTxn && txn.trim().length < 3);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader title={t.label} description={t.note ?? `Move ${c.case_ref} from ${labelFor(c.status)} to ${labelFor(t.to)}.`} />
        <DialogBody>
          {resolving && (
            <Field label="Resolution type" htmlFor="res-type" required>
              <NativeSelect id="res-type" value={type} onChange={(e) => setType(e.target.value)}>
                {Object.entries(c.resolution_types).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </NativeSelect>
            </Field>
          )}
          {needsTxn && (
            <Field label="Bank transaction reference" htmlFor="res-txn" required
              hint="A case is resolved as paid only on a bank-confirmed transaction (BR-11). A borrower promise is not enough.">
              <Input id="res-txn" className="font-mono" value={txn} onChange={(e) => setTxn(e.target.value)} placeholder="e.g. ANB-EDU-2021-00123-T031" />
            </Field>
          )}
          <Field label="Note" htmlFor="tr-note" required={needsNote} hint="Recorded on the case timeline and in the audit trail.">
            <Textarea id="tr-note" value={note} onChange={(e) => setNote(e.target.value)} />
          </Field>
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant={t.to === "ESCALATED" ? "danger" : "default"} loading={m.isPending} disabled={invalid} onClick={() => m.mutate()}>{t.label}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
