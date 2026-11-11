import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { post } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Checkbox, Label } from "@/components/ui/misc";
import { Field } from "@/components/data/feedback";
import { EntitySelect, studentOptions } from "@/components/data/entity";
import { InlineError } from "@/components/data/states";
import { labelFor } from "@/components/data/status";
import { userOptions } from "@/features/cases/types";
import { CORRECTABLE, GRV_CATEGORIES, type Grievance } from "./types";

const useRefresh = (id?: string) => {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["grievances"] });
    if (id) qc.invalidateQueries({ queryKey: ["grievance", id] });
  };
};

/** Staff-recorded grievance on behalf of a borrower (FR-GRV-01, UC-33). */
export function NewGrievanceDialog({ onClose }: { onClose: () => void }) {
  const nav = useNavigate();
  const refresh = useRefresh();
  const [f, setF] = React.useState({ student_id: null as string | null, category: "OTHER", subject: "", description: "", priority: "MEDIUM", channel: "STAFF", correction_field: "", correction_requested_value: "" });
  const set = (k: keyof typeof f, v: string | null) => setF((x) => ({ ...x, [k]: v }));
  const isCorrection = f.category === "DATA_CORRECTION";
  const valid = !!f.student_id && f.subject.trim().length >= 5 && f.description.trim().length >= 10 && (!isCorrection || (!!f.correction_field && !!f.correction_requested_value.trim()));
  const m = useMutation({
    mutationFn: () => post<Grievance>("/grievances", {
      student_id: f.student_id, category: f.category, subject: f.subject.trim(), description: f.description.trim(), priority: f.priority, channel: f.channel,
      correction_field: isCorrection ? f.correction_field : null, correction_requested_value: isCorrection ? f.correction_requested_value.trim() : null,
    }),
    onSuccess: (g) => { toast.success(`Grievance ${g.ref} recorded. An acknowledgement was queued to the borrower.`); refresh(); onClose(); nav(`/grievances/${g.id}`); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent wide>
        <DialogHeader title="Record a grievance" description="Amount and address disputes pause the borrower's open case as DISPUTED until the grievance is resolved (BR-14)." />
        <DialogBody>
          <Field label="Borrower" htmlFor="g-student" required>
            <EntitySelect id="g-student" queryKey="students" value={f.student_id} onChange={(v) => set("student_id", v)} fetchOptions={studentOptions} placeholder="Search by name or DAPRO ref" />
          </Field>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Category" htmlFor="g-cat"><NativeSelect id="g-cat" value={f.category} onChange={(e) => set("category", e.target.value)}>{GRV_CATEGORIES.map((c) => <option key={c} value={c}>{labelFor(c)}</option>)}</NativeSelect></Field>
            <Field label="Priority" htmlFor="g-pri"><NativeSelect id="g-pri" value={f.priority} onChange={(e) => set("priority", e.target.value)}>{["LOW", "MEDIUM", "HIGH", "CRITICAL"].map((p) => <option key={p} value={p}>{labelFor(p)}</option>)}</NativeSelect></Field>
            <Field label="Received via" htmlFor="g-ch"><NativeSelect id="g-ch" value={f.channel} onChange={(e) => set("channel", e.target.value)}>{["STAFF", "PHONE", "EMAIL", "IN_PERSON", "LETTER"].map((p) => <option key={p} value={p}>{labelFor(p)}</option>)}</NativeSelect></Field>
          </div>
          <Field label="Subject" htmlFor="g-subj" required hint="At least 5 characters"><Input id="g-subj" maxLength={200} value={f.subject} onChange={(e) => set("subject", e.target.value)} /></Field>
          <Field label="Description" htmlFor="g-desc" required hint="Record what the borrower said, in neutral terms. At least 10 characters.">
            <Textarea id="g-desc" maxLength={4000} className="min-h-[110px]" value={f.description} onChange={(e) => set("description", e.target.value)} />
          </Field>
          {isCorrection && (
            <div className="grid gap-4 rounded-md border bg-muted/30 p-3 sm:grid-cols-2">
              <Field label="Field to correct" htmlFor="g-cf" required><NativeSelect id="g-cf" value={f.correction_field} onChange={(e) => set("correction_field", e.target.value)}>
                <option value="">Choose a field</option>{CORRECTABLE.map((c) => <option key={c} value={c}>{labelFor(c)}</option>)}</NativeSelect></Field>
              <Field label="Correct value" htmlFor="g-cv" required hint={f.correction_field === "dob" ? "Format YYYY-MM-DD" : undefined}>
                <Input id="g-cv" type={f.correction_field === "dob" ? "date" : "text"} value={f.correction_requested_value} onChange={(e) => set("correction_requested_value", e.target.value)} /></Field>
            </div>
          )}
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter><Button variant="secondary" onClick={onClose}>Cancel</Button><Button loading={m.isPending} disabled={!valid} onClick={() => m.mutate()}>Record grievance</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function AssignGrievanceDialog({ g, onClose }: { g: Grievance; onClose: () => void }) {
  const refresh = useRefresh(g.id);
  const [owner, setOwner] = React.useState<string | null>(g.owner_id);
  const m = useMutation({
    mutationFn: () => post(`/grievances/${g.id}/assign`, { owner_id: owner }),
    onSuccess: () => { toast.success("Grievance assigned. The owner has been notified."); refresh(); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader title={`Assign ${g.ref}`} description="The owner must be able to manage grievances and must not be the person the grievance is about (FR-GRV-03)." />
        <DialogBody>
          <Field label="Owner" htmlFor="g-owner" required>
            <EntitySelect id="g-owner" queryKey="users" value={owner} onChange={(v) => setOwner(v)} fetchOptions={userOptions}
              selectedLabel={owner === g.owner_id ? g.owner_name : undefined} placeholder="Search users by name or email" />
          </Field>
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter><Button variant="secondary" onClick={onClose}>Cancel</Button><Button loading={m.isPending} disabled={!owner || owner === g.owner_id} onClick={() => m.mutate()}>Assign</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const NEEDS_REASON = ["RESOLVED", "REJECTED"];

export function GrievanceTransitionDialog({ g, to, onClose }: { g: Grievance; to: string; onClose: () => void }) {
  const refresh = useRefresh(g.id);
  const [reason, setReason] = React.useState("");
  const [applyCorrection, setApply] = React.useState(false);
  const required = NEEDS_REASON.includes(to);
  const canCorrect = to === "RESOLVED" && g.category === "DATA_CORRECTION" && !!g.correction_field;
  const m = useMutation({
    mutationFn: () => post(`/grievances/${g.id}/transition`, { to, reason: reason.trim() || null, approve_correction: canCorrect && applyCorrection }),
    onSuccess: () => { toast.success(`Grievance moved to ${labelFor(to).toLowerCase()}`); refresh(); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader title={`Move ${g.ref} to ${labelFor(to)}`} description={required ? "The outcome is shown to the borrower. Explain it clearly and respectfully." : "The status change is visible to the borrower."} />
        <DialogBody>
          <Field label={required ? "Outcome for the borrower" : "Note (optional)"} htmlFor="g-reason" required={required} hint={required ? "At least 5 characters" : undefined}>
            <Textarea id="g-reason" className="min-h-[100px]" maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
          {canCorrect && (
            <div className="space-y-2 rounded-md border bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">Requested correction: <span className="font-medium text-foreground">{labelFor(g.correction_field)}</span> to <span className="font-mono text-foreground">{g.correction_requested_value}</span></p>
              <div className="flex items-center gap-2"><Checkbox id="g-apply" checked={applyCorrection} onCheckedChange={(v) => setApply(v === true)} />
                <Label htmlFor="g-apply">Apply this correction to the student record (recorded with the before value)</Label></div>
            </div>
          )}
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter><Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button variant={to === "REJECTED" ? "danger" : to === "RESOLVED" || to === "CLOSED" ? "success" : "default"} loading={m.isPending}
            disabled={required && reason.trim().length < 5} onClick={() => m.mutate()}>Confirm</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function RespondForm({ g }: { g: Grievance }) {
  const refresh = useRefresh(g.id);
  const [message, setMessage] = React.useState("");
  const [visibility, setVisibility] = React.useState("BORROWER");
  const m = useMutation({
    mutationFn: () => post(`/grievances/${g.id}/respond`, { message: message.trim(), visibility }),
    onSuccess: () => { toast.success(visibility === "BORROWER" ? "Response added. The borrower can see it in the portal." : "Internal note added"); setMessage(""); refresh(); },
  });
  return (
    <div className="space-y-3">
      <Field label="Add a response or internal note" htmlFor="g-msg">
        <Textarea id="g-msg" className="min-h-[90px]" maxLength={4000} value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Write a clear, respectful update" />
      </Field>
      <div className="flex flex-wrap items-center gap-3">
        <NativeSelect aria-label="Visibility" className="w-auto" value={visibility} onChange={(e) => setVisibility(e.target.value)}>
          <option value="BORROWER">Visible to borrower</option><option value="INTERNAL">Internal note (staff only)</option>
        </NativeSelect>
        <Button className="ml-auto" loading={m.isPending} disabled={message.trim().length < 3} onClick={() => m.mutate()}>Add</Button>
      </div>
      <InlineError error={m.error} />
    </div>
  );
}
