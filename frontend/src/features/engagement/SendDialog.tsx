import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Ban, CheckCircle2 } from "lucide-react";
import { get, post } from "@/api/client";
import { useCan } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { NativeSelect } from "@/components/ui/input";
import { EntitySelect, studentOptions } from "@/components/data/entity";
import { Field } from "@/components/data/feedback";
import { InlineError } from "@/components/data/states";
import { labelFor } from "@/components/data/status";
import type { Comm, Template } from "./types";

type GuarantorRow = { id: string; full_name: string; communication_permitted: boolean };

export function SendDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (o: boolean) => void }) {
  const can = useCan();
  const qc = useQueryClient();
  const [student, setStudent] = React.useState<string | null>(null);
  const [code, setCode] = React.useState("");
  const [recipient, setRecipient] = React.useState("BORROWER");
  const [guarantor, setGuarantor] = React.useState("");
  const [result, setResult] = React.useState<Comm | null>(null);
  const tpls = useQuery({ queryKey: ["templates"], queryFn: () => get<{ items: Template[] }>("/templates"), enabled: open });
  const approved = (tpls.data?.items ?? []).filter((t) => t.status === "APPROVED");
  const guarantors = useQuery({
    queryKey: ["send-guarantors", student],
    enabled: open && !!student && recipient === "GUARANTOR",
    queryFn: async () => {
      const loans = await get<{ items: { id: string }[] }>(`/loans?size=10&student_id=${student}`);
      const lists = await Promise.all(loans.items.map((l) => get<GuarantorRow[] | { items: GuarantorRow[] }>(`/loans/${l.id}/guarantors`)));
      return lists.flatMap((x) => (Array.isArray(x) ? x : x.items));
    },
  });
  React.useEffect(() => {
    if (!open) { setResult(null); setStudent(null); setCode(""); setRecipient("BORROWER"); setGuarantor(""); }
  }, [open]);
  const tpl = approved.find((t) => t.code === code);
  const m = useMutation({
    mutationFn: () => post<Comm>("/communications", {
      student_id: student, template_code: code, channel: tpl?.channel, recipient_type: recipient,
      guarantor_id: recipient === "GUARANTOR" ? guarantor : undefined,
    }),
    onSuccess: (c) => {
      setResult(c);
      qc.invalidateQueries({ queryKey: ["comms"] });
      if (c.status !== "BLOCKED") toast.success("Message queued (MOCK provider)");
    },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader title="Send approved communication"
          description="Consent, contact preferences, quiet hours, frequency caps and open disputes are checked before anything is sent (FR-COM-04)." />
        <DialogBody>
          {result ? (
            result.status === "BLOCKED" ? (
              <div role="status" className="space-y-2 rounded-md border border-danger/20 bg-danger-soft p-3 text-sm">
                <p className="flex items-center gap-2 font-semibold text-danger"><Ban className="h-4 w-4" />Not sent: blocked by policy</p>
                <p data-testid="block-reason">{result.block_reason}</p>
                <p className="text-xs text-muted-foreground">The blocked attempt is recorded in the communication history and the audit trail.</p>
              </div>
            ) : (
              <div role="status" className="space-y-1 rounded-md border border-success/20 bg-success-soft p-3 text-sm">
                <p className="flex items-center gap-2 font-semibold text-success"><CheckCircle2 className="h-4 w-4" />Queued for delivery</p>
                <p className="text-xs">{result.delivery_note}</p>
              </div>
            )
          ) : (
            <>
              <Field label="Borrower" htmlFor="cm-student" required>
                <EntitySelect id="cm-student" queryKey="students" value={student} onChange={setStudent} fetchOptions={studentOptions} />
              </Field>
              <Field label="Template" htmlFor="cm-tpl" required hint="Only approved template versions can be used (FR-COM-03).">
                <NativeSelect id="cm-tpl" value={code} onChange={(e) => setCode(e.target.value)}>
                  <option value="">Choose a template</option>
                  {approved.map((t) => <option key={t.id} value={t.code}>{t.name} ({labelFor(t.channel)}, v{t.version})</option>)}
                </NativeSelect>
              </Field>
              <Field label="Recipient" htmlFor="cm-rcp">
                <NativeSelect id="cm-rcp" value={recipient} onChange={(e) => setRecipient(e.target.value)}>
                  <option value="BORROWER">Borrower</option>
                  {can("comm:guarantor") && <option value="GUARANTOR">Guarantor (lawful basis required)</option>}
                </NativeSelect>
              </Field>
              {recipient === "GUARANTOR" && (
                <Field label="Guarantor" htmlFor="cm-gua" required hint="Only guarantors whose agreement permits communication can be contacted (BR-13).">
                  <NativeSelect id="cm-gua" value={guarantor} onChange={(e) => setGuarantor(e.target.value)}>
                    <option value="">Choose a guarantor</option>
                    {(guarantors.data ?? []).map((g) => (
                      <option key={g.id} value={g.id}>{g.full_name}{g.communication_permitted ? "" : " (contact not permitted)"}</option>
                    ))}
                  </NativeSelect>
                </Field>
              )}
              <InlineError error={m.error} />
            </>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>{result ? "Close" : "Cancel"}</Button>
          {!result && (
            <Button loading={m.isPending} disabled={!student || !code || (recipient === "GUARANTOR" && !guarantor)} onClick={() => m.mutate()}>Send</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
