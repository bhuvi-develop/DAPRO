import * as React from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Briefcase, Info, Scale, UserCheck } from "lucide-react";
import { get, post } from "@/api/client";
import { useAuth, useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { ErrorState, InlineError } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { Timeline } from "@/components/data/timeline";
import { PageFallback } from "@/components/layout/AppShell";
import { cn, formatDateTime } from "@/lib/utils";
import { NOT_A_FINDING, SEVERITIES, type Indicator } from "./types";

const DECISIONS = [
  { value: "CONFIRM_FOR_FOLLOW_UP", label: "Confirm for follow-up", hint: "The facts warrant follow-up; no case is opened yet." },
  { value: "CREATE_CASE", label: "Create a follow-up case", hint: "Opens an accountable case linked to this indicator." },
  { value: "DISMISS", label: "Dismiss", hint: "The facts do not warrant action. Rationale is kept in the audit trail." },
  { value: "OVERRIDE_SEVERITY", label: "Override severity", hint: "Record a different severity with justification." },
];

function fmt(v: unknown) {
  if (v === null || v === undefined) return "-";
  return typeof v === "object" ? JSON.stringify(v) : String(v);
}

export default function IndicatorDetailPage() {
  const { id } = useParams();
  const can = useCan();
  const me = useAuth((s) => s.me)!;
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["risk-ind", id], queryFn: () => get<Indicator>(`/risk/indicators/${id}`) });
  const [decision, setDecision] = React.useState("CREATE_CASE");
  const [rationale, setRationale] = React.useState("");
  const [override, setOverride] = React.useState("MEDIUM");
  const [priority, setPriority] = React.useState("MEDIUM");
  const [evidenceRef, setEvidenceRef] = React.useState("");
  const refresh = () => { qc.invalidateQueries({ queryKey: ["risk-ind", id] }); qc.invalidateQueries({ queryKey: ["risk"] }); };
  const assign = useMutation({ mutationFn: () => post(`/risk/indicators/${id}/assign`, { user_id: me.id }), onSuccess: () => { toast.success("Assigned to you"); refresh(); } });
  const decide = useMutation({
    mutationFn: () => post<Indicator>(`/risk/indicators/${id}/decision`, { decision, rationale: rationale.trim(), override_severity: decision === "OVERRIDE_SEVERITY" ? override : undefined, evidence_ref: evidenceRef || undefined, priority }),
    onSuccess: () => { toast.success("Review decision recorded"); setRationale(""); refresh(); },
  });
  if (q.isLoading) return <PageFallback />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const i = q.data;
  const closed = ["ACTIONED", "DISMISSED", "OVERRIDDEN", "SUPERSEDED"].includes(i.status);
  return (
    <div className="space-y-6">
      <PageHeader title={i.title} crumbs={[{ label: "Cockpit", to: "/" }, { label: "Risk review", to: "/risk" }, { label: i.rule_code }]}
        meta={<><StatusBadge status={i.severity} /><StatusBadge status={i.status} /><Badge tone="outline">{labelFor(i.category)}</Badge>
          <span className="text-xs text-muted-foreground">Generated {formatDateTime(i.generated_at)}</span></>}
        actions={<>{i.case_id && <Button asChild variant="secondary"><Link to={`/cases/${i.case_id}`}><Briefcase />Open linked case</Link></Button>}
          <Button asChild variant="secondary"><Link to={`/students/${i.student.id}`}>Student 360</Link></Button></>} />
      <div className="flex items-start gap-2 rounded-md border border-primary/20 bg-primary-soft px-3 py-2 text-xs text-primary"><Info className="mt-0.5 h-4 w-4 shrink-0" />{NOT_A_FINDING}</div>
      <div className="grid gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <Card>
            <CardHeader><div><CardTitle>Why this indicator was raised</CardTitle><CardDescription>Plain-language explanation and the triggering facts with their sources.</CardDescription></div></CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm leading-6">{i.explanation}</p>
              <div className="overflow-x-auto rounded-md border">
                <table className="w-full min-w-[520px] text-sm">
                  <thead><tr className="bg-muted/50 text-left text-[11px] uppercase text-muted-foreground"><th className="px-3 py-2">Fact</th><th className="px-3 py-2">Value</th><th className="px-3 py-2">Source</th><th className="px-3 py-2">As of</th></tr></thead>
                  <tbody className="divide-y">{(i.evidence ?? []).map((e, n) => (
                    <tr key={n}><td className="px-3 py-2">{e.fact}</td><td className="num px-3 py-2 font-medium">{fmt(e.value)}</td><td className="px-3 py-2 text-xs">{e.source}</td><td className="px-3 py-2 text-xs text-muted-foreground">{formatDateTime(e.as_of)}</td></tr>))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
          {i.rule && (
            <Card>
              <CardHeader><div><CardTitle>Rule applied</CardTitle><CardDescription>Versioned, approved rule definition used at generation time.</CardDescription></div>
                <Badge tone="warning">{i.rule.approval_label === "DEMO_FIXTURE" ? "Demo fixture - pending bank approval" : i.rule.approval_label}</Badge></CardHeader>
              <CardContent className="space-y-4">
                <KeyValue cols={2} items={[
                  { label: "Rule", value: `${i.rule.name} (${i.rule.code} v${i.rule.version})` },
                  { label: "Recommended review action", value: i.rule.recommended_action },
                  { label: "Definition", value: i.rule.description },
                  { label: "Parameters", value: <code className="font-mono text-xs">{JSON.stringify(i.rule.params)}</code> },
                ]} />
                <details className="rounded-md border bg-muted/30 px-3 py-2 text-xs">
                  <summary className="cursor-pointer font-medium">Input snapshot at generation</summary>
                  <pre className="mt-2 overflow-x-auto whitespace-pre-wrap font-mono text-[11px]">{JSON.stringify(i.input_snapshot ?? {}, null, 2)}</pre>
                </details>
              </CardContent>
            </Card>
          )}
          <Card>
            <CardHeader><CardTitle>Review history</CardTitle></CardHeader>
            <CardContent>
              {i.reviews?.length ? <Timeline items={i.reviews.map((r) => ({ id: r.id, at: r.created_at, actor: r.reviewer?.name, icon: Scale,
                tone: r.decision === "DISMISS" ? "default" : "info",
                title: <span>{labelFor(r.decision)}{r.override_severity ? ` to ${labelFor(r.override_severity)}` : ""}{r.case_id && <> - <Link className="text-primary hover:underline" to={`/cases/${r.case_id}`}>case opened</Link></>}</span>,
                body: <span>{r.rationale}{r.evidence_ref ? ` (evidence: ${r.evidence_ref})` : ""}</span> }))} />
                : <p className="text-sm text-muted-foreground">No review recorded yet. Prior reviews are never rewritten.</p>}
            </CardContent>
          </Card>
        </div>
        <div className="space-y-6">
          <Card>
            <CardHeader><CardTitle>Borrower and account</CardTitle></CardHeader>
            <CardContent><KeyValue cols={1} items={[
              { label: "Borrower", value: <Link className="text-primary hover:underline" to={`/students/${i.student.id}`}>{i.student.name}</Link>, hint: i.student.dapro_ref },
              { label: "Loan", value: i.loan ? <Link className="font-mono text-primary hover:underline" to={`/loans/${i.loan.id}`}>{i.loan.bank_loan_ref}</Link> : "Not loan-specific" },
              { label: "Reviewer", value: i.assigned_to_name ?? "Unassigned" },
            ]} /></CardContent>
          </Card>
          {can("risk:decide") && (
            <Card>
              <CardHeader><div><CardTitle>Record review decision</CardTitle><CardDescription>Authorised human review. The rationale is mandatory and audited.</CardDescription></div></CardHeader>
              <CardContent className="space-y-4">
                {closed ? <p className="text-sm text-muted-foreground">This indicator is {labelFor(i.status).toLowerCase()}. No further decision is needed.</p> : (
                  <>
                    {!i.assigned_to_name && <Button variant="secondary" className="w-full" loading={assign.isPending} onClick={() => assign.mutate()}><UserCheck />Assign to me</Button>}
                    <fieldset className="space-y-2">
                      <legend className="mb-1 text-[13px] font-medium">Decision</legend>
                      {DECISIONS.map((d) => (
                        <label key={d.value} className={cn("flex cursor-pointer gap-2 rounded-md border p-2.5 text-sm", decision === d.value && "border-primary bg-primary-soft")}>
                          <input type="radio" name="decision" value={d.value} checked={decision === d.value} onChange={() => setDecision(d.value)} className="mt-1 accent-[#1D4ED8]" />
                          <span><span className="block font-medium">{d.label}</span><span className="block text-[11px] text-muted-foreground">{d.hint}</span></span>
                        </label>))}
                    </fieldset>
                    {decision === "OVERRIDE_SEVERITY" && <Field label="New severity" htmlFor="ovr"><NativeSelect id="ovr" value={override} onChange={(e) => setOverride(e.target.value)}>{SEVERITIES.map((s) => <option key={s} value={s}>{labelFor(s)}</option>)}</NativeSelect></Field>}
                    {decision === "CREATE_CASE" && <Field label="Case priority" htmlFor="prio"><NativeSelect id="prio" value={priority} onChange={(e) => setPriority(e.target.value)}>{["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((s) => <option key={s} value={s}>{labelFor(s)}</option>)}</NativeSelect></Field>}
                    <Field label="Rationale" htmlFor="rationale" required hint="At least 15 characters. State the facts you relied on." error={rationale && rationale.trim().length < 15 ? "Rationale is too short" : undefined}>
                      <Textarea id="rationale" value={rationale} onChange={(e) => setRationale(e.target.value)} />
                    </Field>
                    <Field label="Evidence reference" htmlFor="evref" hint="Optional: document or bank reference supporting the decision."><Input id="evref" value={evidenceRef} onChange={(e) => setEvidenceRef(e.target.value)} /></Field>
                    <InlineError error={decide.error ?? assign.error} />
                    <Button className="w-full" loading={decide.isPending} disabled={rationale.trim().length < 15} onClick={() => decide.mutate()}>Record decision</Button>
                  </>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
