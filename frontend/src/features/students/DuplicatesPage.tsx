import * as React from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Copy, GitMerge, UserCheck } from "lucide-react";
import { get, post } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/data/feedback";
import { PageHeader } from "@/components/data/layout";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/data/states";
import { formatDate, titleCase } from "@/lib/utils";

interface Side { id: string; dapro_ref: string; full_name: string; college_student_id: string }
interface Dup { id: string; status: string; score: number; match_fields: string[]; created_at: string; notes: string | null; student: Side; candidate: Side }

function Person({ s, label }: { s: Side; label: string }) {
  return (
    <div className="flex-1 rounded-md border bg-muted/30 p-3">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <Link to={`/students/${s.id}`} target="_blank" rel="noreferrer" className="mt-1 block font-medium text-primary hover:underline">{s.full_name}</Link>
      <p className="font-mono text-xs text-muted-foreground">{s.dapro_ref}</p>
      <p className="font-mono text-xs text-muted-foreground">College ID {s.college_student_id}</p>
    </div>
  );
}

export default function DuplicatesPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["duplicates"], queryFn: () => get<Dup[]>("/students/duplicates?status=OPEN") });
  const [act, setAct] = React.useState<{ id: string; decision: "NOT_DUPLICATE" | "CONFIRMED_DUPLICATE" } | null>(null);
  const m = useMutation({
    mutationFn: (notes: string) => post(`/students/duplicates/${act!.id}/resolve`, { decision: act!.decision, notes }),
    onSuccess: () => { toast.success("Duplicate review recorded"); setAct(null); qc.invalidateQueries({ queryKey: ["duplicates"] }); },
  });
  return (
    <div>
      <PageHeader title="Duplicate review" description="Possible duplicates are routed for human review; DAPRO never merges or links automatically (FR-STU-04)."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Students", to: "/students" }, { label: "Duplicates" }]} />
      {q.isLoading ? <Card><TableSkeleton /></Card> : q.error ? <ErrorState error={q.error} onRetry={() => q.refetch()} /> : !q.data?.length ? (
        <Card><EmptyState icon={UserCheck} title="No open duplicate candidates" /></Card>
      ) : (
        <div className="space-y-4">
          {q.data.map((d) => (
            <Card key={d.id}>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap items-center gap-2"><Copy className="h-4 w-4 text-warning" /><span className="text-sm font-medium">Match score {d.score}</span>
                  {d.match_fields.map((f) => <Badge key={f} tone="warning">{titleCase(f)} matches</Badge>)}
                  <span className="ml-auto text-xs text-muted-foreground">Flagged {formatDate(d.created_at)}</span></div>
                <div className="flex flex-col gap-3 sm:flex-row"><Person s={d.student} label="New record" /><Person s={d.candidate} label="Existing record" /></div>
              </CardContent>
              <CardFooter className="justify-end">
                <Button variant="secondary" onClick={() => setAct({ id: d.id, decision: "NOT_DUPLICATE" })}><UserCheck />Different people</Button>
                <Button variant="danger" onClick={() => setAct({ id: d.id, decision: "CONFIRMED_DUPLICATE" })}><GitMerge />Confirm duplicate</Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}
      <ConfirmDialog open={!!act} onOpenChange={(o) => !o && setAct(null)} rationale minLength={3} loading={m.isPending} error={m.error}
        title={act?.decision === "CONFIRMED_DUPLICATE" ? "Confirm duplicate record" : "Mark as different people"}
        description={act?.decision === "CONFIRMED_DUPLICATE" ? "The new record is marked MERGED into the existing one. Nothing is deleted." : "Both records remain active and the candidate is closed."}
        tone={act?.decision === "CONFIRMED_DUPLICATE" ? "danger" : "default"} confirmLabel="Record decision" onConfirm={(r) => m.mutate(r ?? "")} />
    </div>
  );
}
