import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FlaskConical, GitBranchPlus, ShieldCheck } from "lucide-react";
import { get, post } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { PageHeader } from "@/components/data/layout";
import { InlineError, QueryBoundary } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { formatDateTime } from "@/lib/utils";
import { SEVERITIES, type Rule } from "./types";

type DryRun = { would_trigger: number; sample: { title: string; severity: string }[] };

function ProposeDialog({ rule, onClose }: { rule: Rule; onClose: () => void }) {
  const qc = useQueryClient();
  const [params, setParams] = React.useState(JSON.stringify(rule.params, null, 2));
  const [severity, setSeverity] = React.useState(rule.severity);
  const [reason, setReason] = React.useState("");
  const [action, setAction] = React.useState(rule.recommended_action);
  let parsed: Record<string, unknown> | null = null;
  try { parsed = JSON.parse(params); } catch { parsed = null; }
  const m = useMutation({
    mutationFn: () => post(`/risk/rules/${rule.code}/versions`, { params: parsed, severity, change_reason: reason, recommended_action: action }),
    onSuccess: () => { toast.success("Draft version proposed. A second authorised user must approve it."); qc.invalidateQueries({ queryKey: ["risk-rules"] }); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent wide>
        <DialogHeader title={`Propose new version of ${rule.code}`} description="Rule changes are versioned and require approval by a different user (FR-RSK-09)." />
        <DialogBody>
          <Field label="Parameters (JSON)" htmlFor="params" error={parsed ? undefined : "Invalid JSON"} required>
            <Textarea id="params" className="min-h-[140px] font-mono text-xs" value={params} onChange={(e) => setParams(e.target.value)} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Severity" htmlFor="sev">
              <NativeSelect id="sev" value={severity} onChange={(e) => setSeverity(e.target.value)}>{SEVERITIES.map((s) => <option key={s} value={s}>{labelFor(s)}</option>)}</NativeSelect>
            </Field>
            <Field label="Recommended review action" htmlFor="act"><Input id="act" value={action} onChange={(e) => setAction(e.target.value)} /></Field>
          </div>
          <Field label="Reason for change" htmlFor="reason" required hint="Recorded with the version.">
            <Textarea id="reason" value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={m.isPending} disabled={!parsed || reason.trim().length < 5} onClick={() => m.mutate()}>Propose draft</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function RiskRulesPage() {
  const can = useCan();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["risk-rules"], queryFn: () => get<Rule[]>("/risk/rules") });
  const [propose, setPropose] = React.useState<Rule | null>(null);
  const [dry, setDry] = React.useState<Record<string, DryRun>>({});
  const approve = useMutation({
    mutationFn: (id: string) => post(`/risk/rules/${id}/approve`),
    onSuccess: () => { toast.success("Version approved and activated; the previous version was retired."); qc.invalidateQueries({ queryKey: ["risk-rules"] }); },
    onError: (e: Error) => toast.error(e.message),
  });
  const test = useMutation({
    mutationFn: (id: string) => post<DryRun>(`/risk/rules/${id}/test`),
    onSuccess: (r, id) => setDry((d) => ({ ...d, [id]: r })),
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <div>
      <PageHeader title="Risk rules" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Risk review", to: "/risk" }, { label: "Rules" }]}
        description="Explainable, versioned rules. Thresholds and severities are demo fixtures until the bank approves them (OD-15)." />
      <QueryBoundary query={q}>{(rules) => {
        const groups = rules.reduce<Record<string, Rule[]>>((a, r) => { (a[r.code] ??= []).push(r); return a; }, {});
        return (
          <div className="grid gap-4 lg:grid-cols-2">
            {Object.entries(groups).map(([code, versions]) => {
              const active = versions.find((v) => v.status === "ACTIVE") ?? versions[0]!;
              return (
                <Card key={code}>
                  <CardHeader>
                    <div><CardTitle>{active.name}</CardTitle><CardDescription className="font-mono">{code} - {labelFor(active.category)}</CardDescription></div>
                    {can("risk:rules") && <Button size="sm" variant="secondary" onClick={() => setPropose(active)}><GitBranchPlus />New version</Button>}
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">{active.description}</p>
                    <ul className="divide-y rounded-md border">
                      {versions.map((v) => (
                        <li key={v.id} className="space-y-2 px-3 py-2.5">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold">v{v.version}</span><StatusBadge status={v.status} /><StatusBadge status={v.severity} />
                            <Badge tone="warning">{v.approval_label === "DEMO_FIXTURE" ? "Demo fixture" : labelFor(v.approval_label)}</Badge>
                            <span className="ml-auto flex gap-1">
                              {(can("risk:rules") || can("risk:approve_rules")) && (
                                <Button size="sm" variant="ghost" loading={test.isPending && test.variables === v.id} onClick={() => test.mutate(v.id)}><FlaskConical />Dry run</Button>
                              )}
                              {v.status === "DRAFT" && can("risk:approve_rules") && (
                                <Button size="sm" loading={approve.isPending && approve.variables === v.id} onClick={() => approve.mutate(v.id)}><ShieldCheck />Approve</Button>
                              )}
                            </span>
                          </div>
                          <code className="block break-all font-mono text-[11px] text-muted-foreground">{JSON.stringify(v.params)}</code>
                          <p className="text-[11px] text-muted-foreground">
                            {v.change_reason ?? "-"} | proposed by {v.created_by?.name ?? "-"}
                            {v.approved_by ? ` | approved by ${v.approved_by.name} ${formatDateTime(v.approved_at)}` : ""}
                          </p>
                          {dry[v.id] && (
                            <div className="rounded bg-muted/60 px-2 py-1.5 text-xs">
                              Dry run against current data: <span className="font-semibold">{dry[v.id]!.would_trigger}</span> matches (nothing written).
                              {dry[v.id]!.sample.slice(0, 3).map((s, n) => <span key={n} className="block truncate text-muted-foreground">- {s.title}</span>)}
                            </div>
                          )}
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        );
      }}</QueryBoundary>
      {propose && <ProposeDialog rule={propose} onClose={() => setPropose(null)} />}
    </div>
  );
}
