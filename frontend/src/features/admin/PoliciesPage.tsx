import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FilePenLine, Settings2, ShieldCheck, XCircle } from "lucide-react";
import { get, post } from "@/api/client";
import { useAuth, useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, Textarea } from "@/components/ui/input";
import { Tooltip } from "@/components/ui/menu";
import { ConfirmDialog, Field } from "@/components/data/feedback";
import { PageHeader } from "@/components/data/layout";
import { EmptyState, InlineError, QueryBoundary } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { formatDate, formatDateTime } from "@/lib/utils";
import type { PolicyRow } from "./types";

const today = () => new Date().toISOString().slice(0, 10);

/** Propose a new version. It stays DRAFT until a different authorised user approves it (BR-12). */
function ProposeDialog({ base, onClose }: { base: PolicyRow; onClose: () => void }) {
  const qc = useQueryClient();
  const [text, setText] = React.useState(JSON.stringify(base.value, null, 2));
  const [effective, setEffective] = React.useState(today());
  const [reason, setReason] = React.useState("");
  const parsed = React.useMemo(() => {
    try { const v = JSON.parse(text); return v && typeof v === "object" && !Array.isArray(v) ? { value: v as Record<string, unknown> } : { error: "The value must be a JSON object." }; }
    catch (e) { return { error: `Invalid JSON: ${(e as Error).message}` }; }
  }, [text]);
  const m = useMutation({
    mutationFn: () => post("/admin/policies", { key: base.key, value: parsed.value, description: base.description, effective_from: effective, reason: reason.trim() }),
    onSuccess: () => { toast.success("New version proposed. A different authorised user must approve it."); qc.invalidateQueries({ queryKey: ["admin-policies"] }); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent wide>
        <DialogHeader title={`Propose a new version of ${base.key}`} description="The server validates the structure. Earlier versions stay on record and calculations reference the version in force." />
        <DialogBody>
          <Field label="Policy value (JSON)" htmlFor="p-val" required error={"error" in parsed ? parsed.error : undefined}>
            <Textarea id="p-val" spellCheck={false} className="min-h-[220px] font-mono text-xs" value={text} onChange={(e) => setText(e.target.value)} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Effective from" htmlFor="p-eff" required><Input id="p-eff" type="date" value={effective} onChange={(e) => setEffective(e.target.value)} /></Field>
            <Field label="Reason for change" htmlFor="p-why" required hint="At least 5 characters. Recorded in the audit trail."><Input id="p-why" maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
          </div>
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter><Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={m.isPending} disabled={"error" in parsed || !effective || reason.trim().length < 5} onClick={() => m.mutate()}>Submit for approval</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function PolicyCard({ versions }: { versions: PolicyRow[] }) {
  const can = useCan();
  const me = useAuth((s) => s.me)!;
  const qc = useQueryClient();
  const [propose, setPropose] = React.useState(false);
  const [decide, setDecide] = React.useState<{ p: PolicyRow; approve: boolean } | null>(null);
  const m = useMutation({
    mutationFn: ({ p, approve, reason }: { p: PolicyRow; approve: boolean; reason: string }) => post(`/admin/policies/${p.id}/${approve ? "approve" : "reject"}`, { reason }),
    onSuccess: (_d, v) => { toast.success(v.approve ? "Policy version approved and now in force" : "Policy version rejected"); qc.invalidateQueries({ queryKey: ["admin-policies"] }); setDecide(null); },
  });
  const active = versions.find((v) => v.status === "ACTIVE");
  const head = active ?? versions[0]!;
  const manage = can("policy:manage");
  return (
    <Card data-testid={`policy-${head.key}`}>
      <CardHeader>
        <div className="min-w-0"><CardTitle className="font-mono">{head.key}</CardTitle><CardDescription>{head.description}</CardDescription></div>
        {manage && <Button size="sm" variant="secondary" onClick={() => setPropose(true)}><FilePenLine />Propose change</Button>}
      </CardHeader>
      <CardContent className="space-y-3">
        {active ? (
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2 text-xs"><span className="font-semibold">In force: v{active.version}</span><StatusBadge status="ACTIVE" />
              {active.approval_label === "DEMO_FIXTURE" ? <Badge tone="warning">Demo fixture - pending client approval</Badge> : <Badge tone="outline">{labelFor(active.approval_label)}</Badge>}
              <span className="text-muted-foreground">from {formatDate(active.effective_from)}</span></div>
            <pre className="max-h-56 overflow-auto rounded-md bg-muted/50 p-3 text-[11px] leading-5 scrollbar-thin">{JSON.stringify(active.value, null, 2)}</pre>
          </div>
        ) : <p className="text-xs text-warning">No approved version. The built-in default applies and is labelled NOT_CONFIGURED.</p>}
        <ul className="divide-y rounded-md border">
          {versions.map((v) => {
            const own = v.created_by === me.id;
            return (
              <li key={v.id} className="flex flex-wrap items-center gap-2 px-3 py-2 text-xs">
                <span className="font-semibold">v{v.version}</span><StatusBadge status={v.status} />
                <span className="text-muted-foreground">proposed {formatDateTime(v.created_at)}, effective {formatDate(v.effective_from)}</span>
                {v.status === "DRAFT" && manage && (
                  <span className="ml-auto flex gap-1.5">
                    {own ? (
                      <Tooltip content="You proposed this version. A different authorised user must approve or reject it (BR-12).">
                        <span tabIndex={0} className="flex gap-1.5"><Button size="sm" variant="secondary" disabled><XCircle />Reject</Button><Button size="sm" disabled><ShieldCheck />Approve</Button></span>
                      </Tooltip>
                    ) : (<>
                      <Button size="sm" variant="secondary" onClick={() => setDecide({ p: v, approve: false })}><XCircle />Reject</Button>
                      <Button size="sm" onClick={() => setDecide({ p: v, approve: true })}><ShieldCheck />Approve</Button>
                    </>)}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </CardContent>
      {propose && <ProposeDialog base={head} onClose={() => setPropose(false)} />}
      {decide && (
        <ConfirmDialog open onOpenChange={(o) => !o && setDecide(null)} title={`${decide.approve ? "Approve" : "Reject"} ${decide.p.key} v${decide.p.version}`}
          description={decide.approve ? "The approved version replaces the one in force from its effective date." : "The draft is kept on record as rejected."}
          confirmLabel={decide.approve ? "Approve" : "Reject"} tone={decide.approve ? "default" : "danger"} rationale minLength={3} rationaleLabel="Reason"
          loading={m.isPending} error={m.error} onConfirm={(reason) => m.mutate({ p: decide.p, approve: decide.approve, reason: reason ?? "" })} />
      )}
    </Card>
  );
}

export default function PoliciesPage() {
  const q = useQuery({ queryKey: ["admin-policies"], queryFn: () => get<PolicyRow[]>("/admin/policies") });
  return (
    <div>
      <PageHeader title="Policy configuration" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Administration" }, { label: "Policies" }]}
        description="Versioned, effective-dated business parameters: DPD buckets, grace days, freshness, grievance SLA and contact windows. Changes need maker-checker approval (FR-ADM-01, BR-12). Values marked as demo fixtures are pending client decisions (OD register)." />
      <QueryBoundary query={q} isEmpty={(d) => d.length === 0} empty={<Card><EmptyState icon={Settings2} title="No policy versions recorded" /></Card>}>{(d) => {
        const groups = d.reduce<Record<string, PolicyRow[]>>((a, p) => { (a[p.key] ??= []).push(p); return a; }, {});
        return <div className="grid gap-4 xl:grid-cols-2">{Object.values(groups).map((vs) => <PolicyCard key={vs[0]!.key} versions={[...vs].sort((a, b) => b.version - a.version)} />)}</div>;
      }}</QueryBoundary>
    </div>
  );
}
