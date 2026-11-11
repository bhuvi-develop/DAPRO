import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, Plug, RefreshCw, Settings2 } from "lucide-react";
import { api, get, post } from "@/api/client";
import { useAuth, useCan } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, NativeSelect } from "@/components/ui/input";
import { Switch } from "@/components/ui/misc";
import { Field } from "@/components/data/feedback";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { EmptyState, ErrorState, InlineError, TableSkeleton } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { formatDateTime, relativeTime, titleCase } from "@/lib/utils";
import type { IntegrationRow } from "./types";

function ConfigureDialog({ i, onClose }: { i: IntegrationRow; onClose: () => void }) {
  const qc = useQueryClient();
  const [mode, setMode] = React.useState(i.mode);
  const [hours, setHours] = React.useState(String(i.refresh_interval_hours));
  const m = useMutation({
    mutationFn: () => api(`/admin/integrations/${i.id}`, { method: "PATCH", body: { mode, refresh_interval_hours: Number(hours) } }),
    onSuccess: () => { toast.success("Integration updated"); qc.invalidateQueries({ queryKey: ["admin-integrations"] }); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}><DialogContent>
      <DialogHeader title={`Configure ${i.name}`} description="Credentials are never entered or shown here; they are held in environment secrets (INT-COM-02)." />
      <DialogBody>
        <Field label="Mode" htmlFor="ig-m" hint="LIVE requires a contracted, sandbox-tested provider. None exists yet (OD-06, OD-16)."><NativeSelect id="ig-m" value={mode} onChange={(e) => setMode(e.target.value)}>
          {["MOCK", "NOT_CONFIGURED", "DISABLED", "LIVE"].map((x) => <option key={x} value={x}>{titleCase(x)}</option>)}</NativeSelect></Field>
        <Field label="Refresh interval (hours)" htmlFor="ig-h" hint="Data older than the freshness policy shows as STALE"><Input id="ig-h" type="number" min={1} max={168} value={hours} onChange={(e) => setHours(e.target.value)} /></Field>
        <InlineError error={m.error} />
      </DialogBody>
      <DialogFooter><Button variant="secondary" onClick={onClose}>Cancel</Button><Button loading={m.isPending} onClick={() => m.mutate()}>Save</Button></DialogFooter>
    </DialogContent></Dialog>
  );
}

function IntegrationCard({ i }: { i: IntegrationRow }) {
  const can = useCan();
  const me = useAuth((s) => s.me)!;
  const qc = useQueryClient();
  const [cfg, setCfg] = React.useState(false);
  const sim = useMutation({ mutationFn: (v: boolean) => api(`/admin/integrations/${i.id}`, { method: "PATCH", body: { simulate_failure: v } }),
    onSuccess: (_d, v) => { toast.success(v ? "Next sync will fail (demo simulation)" : "Failure simulation off"); qc.invalidateQueries({ queryKey: ["admin-integrations"] }); } });
  const sync = useMutation({ mutationFn: () => post<{ status: string; batch_id?: string }>(`/banks/${i.org_id}/sync`),
    onSuccess: (r) => { toast.success(`Bank sync ${r.status.toLowerCase()}`); qc.invalidateQueries({ queryKey: ["admin-integrations"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); } });
  const isBank = i.kind === "BANK_LOAN_FEED";
  return (
    <Card data-testid={`integration-${i.kind}`}>
      <CardHeader>
        <div className="min-w-0"><CardTitle>{i.name}</CardTitle><CardDescription>{titleCase(i.kind)}{i.org_name ? ` - ${i.org_name}` : ""} - provider {i.provider}</CardDescription></div>
        <div className="flex flex-col items-end gap-1"><StatusBadge status={i.status} />{i.health !== "HEALTHY" && i.health !== "UNKNOWN" && <StatusBadge status={i.health} />}</div>
      </CardHeader>
      <CardContent className="space-y-3">
        {i.is_mock && <p className="flex items-start gap-1.5 rounded-md bg-warning-soft px-3 py-2 text-xs text-[hsl(32_95%_30%)]"><AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />MOCK provider - not a live integration. Data is synthetic and nothing reaches real people or banks.</p>}
        <KeyValue cols={2} items={[
          { label: "Last success", value: i.last_success_at ? relativeTime(i.last_success_at) : "Never", hint: i.last_success_at ? formatDateTime(i.last_success_at) : undefined },
          { label: "Last failure", value: i.last_failure_at ? relativeTime(i.last_failure_at) : "None" },
          { label: "Consecutive failures", value: <span className={i.consecutive_failures >= 3 ? "font-semibold text-danger" : ""}>{i.consecutive_failures}</span>, hint: i.consecutive_failures >= 3 ? "Integration incident raised" : undefined },
          { label: "Refresh interval", value: `${i.refresh_interval_hours} h` },
        ]} />
        {i.last_error && <p className="rounded-md bg-danger-soft px-3 py-2 text-xs text-danger">{i.last_error}</p>}
        {isBank && me.environment.demo && can("integration:manage") && (
          <label className="flex items-center justify-between gap-3 rounded-md border px-3 py-2 text-sm">
            <span>Simulate feed failure <span className="block text-[11px] text-muted-foreground">Demo control: proves a failed sync shows STALE, never overdue (AC-05)</span></span>
            <Switch aria-label="Simulate feed failure" checked={i.simulate_failure} disabled={sim.isPending} onCheckedChange={(v) => sim.mutate(v)} />
          </label>
        )}
      </CardContent>
      {(can("integration:manage") || (isBank && can("bank:sync"))) && (
        <CardFooter className="justify-end">
          {can("integration:manage") && <Button variant="secondary" size="sm" onClick={() => setCfg(true)}><Settings2 />Configure</Button>}
          {isBank && can("bank:sync") && i.org_id === me.org.id && <Button size="sm" loading={sync.isPending} onClick={() => sync.mutate()}><RefreshCw />Run bank sync now</Button>}
        </CardFooter>
      )}
      {sync.error ? <div className="px-5 pb-4"><InlineError error={sync.error} /></div> : null}
      {cfg && <ConfigureDialog i={i} onClose={() => setCfg(false)} />}
    </Card>
  );
}

export default function IntegrationsPage() {
  const q = useQuery({ queryKey: ["admin-integrations"], queryFn: () => get<IntegrationRow[]>("/admin/integrations") });
  return (
    <div>
      <PageHeader title="Integrations" description="Status values: LIVE, MOCK, NOT_CONFIGURED, DEGRADED, FAILED, DISABLED. An unavailable integration is never shown as current (FR-ADM-02)."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Administration" }, { label: "Integrations" }]} />
      {q.isLoading ? <Card><TableSkeleton /></Card> : q.error ? <ErrorState error={q.error} onRetry={() => q.refetch()} /> : !q.data?.length ? <Card><EmptyState icon={Plug} title="No integrations in your scope" /></Card> : (
        <div className="grid gap-4 lg:grid-cols-2">{q.data.map((i) => <IntegrationCard key={i.id} i={i} />)}</div>
      )}
    </div>
  );
}
