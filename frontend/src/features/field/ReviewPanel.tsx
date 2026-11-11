import * as React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, Undo2 } from "lucide-react";
import { post } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { InlineError } from "@/components/data/states";
import type { Visit } from "./types";

/** Supervisor review (FR-FLD-05). The visiting officer cannot review their own report (RD 6.1). */
export function ReviewPanel({ visit, onDone, compact }: { visit: Visit; onDone?: () => void; compact?: boolean }) {
  const qc = useQueryClient();
  const [notes, setNotes] = React.useState("");
  const m = useMutation({
    mutationFn: (decision: "APPROVED" | "RETURNED") => post<Visit>(`/visits/${visit.id}/review`, { decision, notes }),
    onSuccess: (_v, d) => {
      toast.success(d === "APPROVED" ? "Visit report approved" : "Visit report returned to the officer");
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["visit", visit.id] });
      setNotes("");
      onDone?.();
    },
  });
  const body = (
    <div className="space-y-3">
      <Field label="Review notes" htmlFor={`rv-${visit.id}`} required hint="At least 5 characters. Recorded in the audit trail.">
        <Textarea id={`rv-${visit.id}`} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </Field>
      <InlineError error={m.error} />
      <div className="flex flex-wrap gap-2">
        <Button variant="success" loading={m.isPending && m.variables === "APPROVED"} disabled={notes.trim().length < 5} onClick={() => m.mutate("APPROVED")}><CheckCircle2 />Approve</Button>
        <Button variant="secondary" loading={m.isPending && m.variables === "RETURNED"} disabled={notes.trim().length < 5} onClick={() => m.mutate("RETURNED")}><Undo2 />Return for changes</Button>
      </div>
    </div>
  );
  if (compact) return body;
  return (
    <Card>
      <CardHeader><div><CardTitle>Supervisor review</CardTitle><CardDescription>Approve the report or return it to the officer with notes.</CardDescription></div></CardHeader>
      <CardContent>{body}</CardContent>
    </Card>
  );
}
