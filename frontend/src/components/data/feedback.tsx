import * as React from "react";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/misc";
import { InlineError } from "@/components/data/states";

/** Confirmation dialog; optionally collects a mandatory rationale (used for overrides, dismissals, closures). */
export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel = "Confirm", tone = "default", onConfirm, rationale, rationaleLabel = "Reason", minLength = 10, loading, error }: {
  open: boolean; onOpenChange: (o: boolean) => void; title: string; description?: React.ReactNode; confirmLabel?: string;
  tone?: "default" | "danger"; onConfirm: (reason?: string) => void; rationale?: boolean; rationaleLabel?: string; minLength?: number; loading?: boolean; error?: unknown;
}) {
  const [reason, setReason] = React.useState("");
  React.useEffect(() => { if (!open) setReason(""); }, [open]);
  const tooShort = rationale && reason.trim().length < minLength;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader title={title} description={description} />
        {(rationale || !!error) && (
          <DialogBody>
            {rationale && (
              <div className="space-y-1.5">
                <Label htmlFor="confirm-reason">{rationaleLabel}</Label>
                <Textarea id="confirm-reason" value={reason} onChange={(e) => setReason(e.target.value)} aria-invalid={tooShort && reason.length > 0} />
                <p className="text-[11px] text-muted-foreground">Required, at least {minLength} characters. Recorded in the audit trail.</p>
              </div>
            )}
            <InlineError error={error} />
          </DialogBody>
        )}
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button variant={tone === "danger" ? "danger" : "default"} loading={loading} disabled={!!tooShort} onClick={() => onConfirm(rationale ? reason.trim() : undefined)}>{confirmLabel}</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function Field({ label, htmlFor, error, hint, required, children }: { label: string; htmlFor?: string; error?: string; hint?: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={htmlFor}>{label}{required && <span className="ml-0.5 text-danger" aria-hidden>*</span>}</Label>
      {children}
      {error ? <p role="alert" className="text-[11px] font-medium text-danger">{error}</p> : hint ? <p className="text-[11px] text-muted-foreground">{hint}</p> : null}
    </div>
  );
}
