import * as React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Activity as ActivityIcon, AlertTriangle, Banknote, Briefcase, CheckCircle2, CircleDollarSign, ClipboardCheck, Clock, Database,
  FilePlus2, Landmark, Link2, RefreshCw, Users,
} from "lucide-react";
import { get } from "@/api/client";
import { useAuth, useCan } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DateRange } from "@/components/data/filters";
import { ChartCard, KpiCard, type KpiStatus } from "@/components/data/kpi";
import { ErrorState } from "@/components/data/states";
import { PageFallback } from "@/components/layout/AppShell";
import { useUrlState } from "@/hooks/useUrlState";
import { formatDate, qs, relativeTime } from "@/lib/utils";
import { BucketBars, DonutChart, HBars, TrendChart } from "./Charts";
import { ActivityList, CaseOps, OperationalHealth, PortfolioMatrix, RepaymentIntel, RiskMatrix, StudentIntel } from "./Panels";
import { normalize } from "./normalize";

const KPI_ICONS: Record<string, React.ElementType> = {
  total_students: Users, linked_loans: Link2, active_monitoring: ActivityIcon, current_repayment: CheckCircle2,
  overdue_accounts: AlertTriangle, total_overdue_amount: CircleDollarSign, open_cases: Briefcase, pending_reviews: ClipboardCheck,
};
const HIGHER_IS_BETTER: Record<string, boolean> = { overdue_accounts: false, total_overdue_amount: false, open_cases: false, pending_reviews: false };
const STATUS: Record<string, KpiStatus> = { good: "good", attention: "attention", critical: "critical", info: "info", neutral: "neutral" };
const DEFAULTS = { from: undefined, to: undefined };

export default function DashboardPage() {
  const me = useAuth((s) => s.me)!;
  const can = useCan();
  const { state, update } = useUrlState<{ from?: string; to?: string }>(DEFAULTS);
  const q = useQuery({
    queryKey: ["dashboard", state.from, state.to],
    queryFn: ({ signal }) => get<unknown>(`/dashboard/summary${qs({ from: state.from, to: state.to })}`, signal).then(normalize),
    staleTime: 60_000,
  });
  if (q.isLoading) return <PageFallback />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data;
  const ch = d.charts ?? {};
  const money = !!d.header.financial_visible;
  const ageingLabel = ch.overdue_ageing?.approval_label === "DEMO_FIXTURE" ? "Demo fixture - bank approval pending" : ch.overdue_ageing?.approval_label;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary">DAPRO Enterprise Cockpit</p>
          <h1 className="mt-1 text-[24px] font-semibold leading-8">{d.header.org_name}</h1>
          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1"><Clock className="h-3.5 w-3.5" aria-hidden />
              Period {formatDate(d.header.period.from)} - {formatDate(d.header.period.to)}</span>
            {(d.header.banks ?? []).map((b) => (
              <span key={b.bank_org_id} className="inline-flex items-center gap-1.5">
                <Database className="h-3.5 w-3.5" aria-hidden />{b.name}: {b.last_sync_at ? `synced ${relativeTime(b.last_sync_at)}` : "never synced"}
                <Badge tone={b.mode === "LIVE" ? "success" : "warning"}>{b.mode}</Badge>
                {b.health === "FAILED" && <Badge tone="danger">last pull failed</Badge>}
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center xl:justify-end">
          <DateRange from={state.from} to={state.to} onChange={(from, to) => update({ from, to })} />
          <div className="flex flex-wrap gap-2">
            <Button variant="secondary" size="icon" aria-label="Refresh dashboard" onClick={() => q.refetch()}>
              <RefreshCw className={q.isFetching ? "animate-spin" : ""} />
            </Button>
            {can("student:write") && <Button asChild variant="secondary"><Link to="/students/new"><FilePlus2 />Register student</Link></Button>}
            {can("loan:link") && <Button asChild variant="secondary"><Link to="/loans/link"><Landmark />Link loan</Link></Button>}
            {can("case:create") && <Button asChild><Link to="/cases/new"><Briefcase />Open case</Link></Button>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {d.kpis.map((k) => (
          <KpiCard key={k.key} label={k.label} value={k.value} unit={k.unit} previous={k.previous_value} icon={KPI_ICONS[k.key] ?? Banknote}
            status={STATUS[k.status ?? "neutral"] ?? "neutral"} to={k.link ?? undefined} hint={k.hint}
            higherIsBetter={HIGHER_IS_BETTER[k.key] ?? true} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        {ch.repayment_status_distribution && (
          <ChartCard title="Repayment status" description="Display status from the bank schedule and bank allocation. Click to drill down."
            footer="Source: bank feed mirror. UNKNOWN means stale, missing or unlinked data - never assumed paid.">
            <DonutChart data={ch.repayment_status_distribution} />
          </ChartCard>
        )}
        {ch.overdue_ageing && (
          <ChartCard title="Overdue ageing" description="Accounts by days past due (bank-confirmed)"
            footer={<span>DPD bucket policy v{ch.overdue_ageing.policy_version ?? 1} <Badge tone="warning" className="ml-1">{ageingLabel}</Badge></span>}>
            <BucketBars data={ch.overdue_ageing.buckets} money={money} />
          </ChartCard>
        )}
        {ch.monthly_repayment_trend && (
          <ChartCard title="Monthly repayment trend" description="Bank-confirmed collections net of reversals; instalments paid vs due"
            footer="Last 12 months. Payment commitments and reminders are never counted as payments.">
            <TrendChart data={ch.monthly_repayment_trend} money={money} />
          </ChartCard>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="xl:col-span-2"><RepaymentIntel d={d} /></div>
        <CaseOps d={d} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 xl:grid-cols-4">
        {ch.portfolio_by_bank_college && (
          <ChartCard title="Linked portfolio" description="Linked loan accounts by college and lending bank" className="lg:col-span-2">
            <PortfolioMatrix rows={ch.portfolio_by_bank_college} />
          </ChartCard>
        )}
        {ch.case_status_distribution && <ChartCard title="Case status"><HBars data={ch.case_status_distribution} colorIndex={0} /></ChartCard>}
        {ch.lifecycle_distribution && (
          <ChartCard title="Student lifecycle" description="Post-study status is time-bound and source-labelled">
            <HBars data={ch.lifecycle_distribution} colorIndex={1} />
          </ChartCard>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        {ch.risk_indicator_distribution && (
          <ChartCard title="Risk indicators awaiting review" description="Explainable rule outputs for human review - not findings">
            <RiskMatrix rows={ch.risk_indicator_distribution} />
          </ChartCard>
        )}
        <StudentIntel d={d} />
        <OperationalHealth d={d} />
      </div>

      {d.activity?.length ? (
        <Card>
          <CardHeader>
            <div><CardTitle>Recent activity</CardTitle><CardDescription>Authorised events in your scope, from the audit trail</CardDescription></div>
            {can("audit:read") && <Link to="/audit" className="text-xs font-medium text-primary hover:underline">Audit trail</Link>}
          </CardHeader>
          <CardContent className="max-h-[460px] overflow-y-auto scrollbar-thin"><ActivityList rows={d.activity} /></CardContent>
        </Card>
      ) : null}
      <p className="text-center text-[11px] text-muted-foreground">
        Generated {relativeTime(d.header.generated_at)} for {me.full_name} ({me.roles.join(", ")}). Figures are computed from stored records in your scope.
      </p>
    </div>
  );
}
