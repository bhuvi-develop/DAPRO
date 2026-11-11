import { Link } from "react-router-dom";
import { ArrowRight, CircleAlert, ClipboardList, Clock3, FileWarning, MapPinned, ShieldCheck, ShieldX, UserPlus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/menu";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/data/states";
import { Money, StatusBadge, labelFor } from "@/components/data/status";
import { Timeline } from "@/components/data/timeline";
import { cn, formatDate, formatDateTime, formatNumber, relativeTime } from "@/lib/utils";
import type { ActivityRow, DashboardSummary, LoanRow, ReconRow } from "./types";

function LoanList({ rows, mode, money }: { rows?: LoanRow[]; mode: "due" | "overdue" | "stale"; money: boolean }) {
  if (!rows?.length) return <EmptyState title={mode === "due" ? "No instalments due in the next 30 days" : mode === "overdue" ? "No recently overdue accounts" : "No stale records - all feeds are fresh"} />;
  return (
    <ul className="divide-y">
      {rows.slice(0, 8).map((r) => (
        <li key={r.loan_id + (r.due_date ?? "")}>
          <Link to={`/loans/${r.loan_id}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-muted/50">
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{r.student_name ?? "Unlinked borrower"}</p>
              <p className="truncate font-mono text-[11px] text-muted-foreground">{r.bank_loan_ref}{r.bank ? ` - ${r.bank}` : ""}</p>
            </div>
            <div className="text-right text-xs">
              {mode === "due" && <><Money value={r.amount} restricted={!money} className="font-medium" /><p className="text-muted-foreground">due {formatDate(r.due_date, "dd MMM")}</p></>}
              {mode === "overdue" && <><p className="num font-medium text-danger">{r.dpd} DPD</p>{money && <Money value={r.overdue_amount} className="text-muted-foreground" />}</>}
              {mode === "stale" && <><StatusBadge status={r.sync_state} /><p className="mt-0.5 text-muted-foreground">synced {relativeTime(r.last_synced_at)}</p></>}
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function ReconList({ rows }: { rows?: ReconRow[] }) {
  if (!rows?.length) return <EmptyState title="No open repayment exceptions" />;
  return (
    <ul className="divide-y">
      {rows.slice(0, 8).map((r) => (
        <li key={r.id}>
          <Link to={`/reconciliation?kind=${r.kind}`} className="flex items-start gap-3 px-4 py-2.5 hover:bg-muted/50">
            <FileWarning className={cn("mt-0.5 h-4 w-4 shrink-0", r.severity === "HIGH" ? "text-danger" : "text-warning")} aria-hidden />
            <div className="min-w-0 flex-1"><p className="text-sm">{r.summary}</p><p className="text-[11px] text-muted-foreground">{labelFor(r.kind)} - {relativeTime(r.created_at)}</p></div>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function RepaymentIntel({ d }: { d: DashboardSummary }) {
  const money = !!d.header.financial_visible;
  const l = d.lists ?? {};
  return (
    <Card className="flex flex-col">
      <CardHeader><div><CardTitle>Repayment intelligence</CardTitle><CardDescription>Bank-confirmed data only. Stale data is shown as unknown, never as paid or zero.</CardDescription></div>
        <Link to="/repayments" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">Monitor <ArrowRight className="h-3 w-3" /></Link></CardHeader>
      <Tabs defaultValue="due" className="flex-1">
        <TabsList className="px-3">
          <TabsTrigger value="due">Upcoming <Badge tone="info">{l.upcoming_repayments?.length ?? 0}</Badge></TabsTrigger>
          <TabsTrigger value="overdue">Recently overdue <Badge tone="danger">{l.recently_overdue?.length ?? 0}</Badge></TabsTrigger>
          <TabsTrigger value="exceptions">Exceptions <Badge tone="warning">{l.repayment_exceptions?.length ?? 0}</Badge></TabsTrigger>
          <TabsTrigger value="stale">Stale <Badge tone="neutral">{l.stale_records?.length ?? 0}</Badge></TabsTrigger>
        </TabsList>
        <TabsContent value="due" className="pt-0"><LoanList rows={l.upcoming_repayments} mode="due" money={money} /></TabsContent>
        <TabsContent value="overdue" className="pt-0"><LoanList rows={l.recently_overdue} mode="overdue" money={money} /></TabsContent>
        <TabsContent value="exceptions" className="pt-0"><ReconList rows={l.repayment_exceptions} /></TabsContent>
        <TabsContent value="stale" className="pt-0"><LoanList rows={l.stale_records} mode="stale" money={money} /></TabsContent>
      </Tabs>
    </Card>
  );
}

function Stat({ label, value, to, tone = "neutral", icon: Icon }: { label: string; value?: number | null; to?: string; tone?: "neutral" | "warning" | "danger" | "info"; icon: React.ElementType }) {
  const color = { neutral: "text-navy bg-muted", warning: "text-warning bg-warning-soft", danger: "text-danger bg-danger-soft", info: "text-primary bg-primary-soft" }[tone];
  const inner = (
    <div className="flex items-center gap-3 rounded-md border p-3 transition-colors hover:border-primary/40">
      <span className={cn("rounded-md p-2", color)}><Icon className="h-4 w-4" aria-hidden /></span>
      <div><p className="num text-lg font-semibold leading-6">{value === null || value === undefined ? "-" : formatNumber(value)}</p><p className="text-[11px] text-muted-foreground">{label}</p></div>
    </div>
  );
  return to ? <Link to={to} className="block rounded-md">{inner}</Link> : inner;
}

export function CaseOps({ d }: { d: DashboardSummary }) {
  const c = d.case_ops;
  if (!c) return null;
  return (
    <Card>
      <CardHeader><div><CardTitle>Case and follow-up operations</CardTitle><CardDescription>Accountable follow-up: every active case has an owner, next action and due date.</CardDescription></div></CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-3 xl:grid-cols-3">
          <Stat label="Open cases" value={c.open} to="/cases?status=open" icon={ClipboardList} tone="info" />
          <Stat label="High priority" value={c.high_priority} to="/cases?status=open&priority=HIGH" icon={CircleAlert} tone="danger" />
          <Stat label="Awaiting review" value={c.awaiting_review} to="/field/review" icon={ShieldCheck} tone="warning" />
          <Stat label="Field visits scheduled" value={c.assigned_field_visits} to="/cases?status=open" icon={MapPinned} />
          <Stat label="Overdue follow-ups" value={c.overdue_follow_ups} to="/cases?status=open&overdue=true" icon={Clock3} tone="danger" />
        </div>
        {c.recent_activity?.length ? <ActivityList rows={c.recent_activity.slice(0, 5)} compact /> : null}
      </CardContent>
    </Card>
  );
}

export function StudentIntel({ d }: { d: DashboardSummary }) {
  const s = d.student_intel;
  if (!s) return null;
  const gw = typeof s.guarantor_witness_completion === "object" && s.guarantor_witness_completion ? s.guarantor_witness_completion : null;
  return (
    <Card>
      <CardHeader><div><CardTitle>Student intelligence</CardTitle><CardDescription>Profile quality and lifecycle data that needs attention.</CardDescription></div>
        <Link to="/students" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">Students <ArrowRight className="h-3 w-3" /></Link></CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="mb-1 flex justify-between text-xs"><span className="text-muted-foreground">Average profile completion</span><span className="num font-semibold">{s.avg_profile_completion ?? "-"}%</span></div>
          <div className="h-2 rounded-full bg-muted"><div className="h-2 rounded-full bg-teal" style={{ width: `${s.avg_profile_completion ?? 0}%` }} /></div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Missing key information" value={s.missing_information} to="/students?completion_below=80" icon={UserPlus} tone="warning" />
          <Stat label="Address verification pending" value={s.pending_address_verification} to="/verifications" icon={MapPinned} tone="info" />
          <Stat label="Academic exceptions" value={s.academic_exceptions} to="/students?lifecycle_status=UNKNOWN" icon={CircleAlert} />
          {gw && <Stat label={`Loans with guarantor (of ${gw.loans ?? 0})`} value={gw.with_guarantor} icon={ShieldCheck} />}
        </div>
        {s.recently_added?.length ? (
          <div>
            <p className="mb-1.5 text-xs font-medium text-muted-foreground">Recently registered</p>
            <ul className="divide-y rounded-md border">
              {s.recently_added.slice(0, 5).map((r) => (
                <li key={r.id}><Link to={`/students/${r.id}`} className="flex items-center justify-between gap-2 px-3 py-2 text-sm hover:bg-muted/50">
                  <span className="min-w-0"><span className="block truncate font-medium">{r.name}</span><span className="block font-mono text-[11px] text-muted-foreground">{r.dapro_ref}</span></span>
                  <span className="shrink-0 text-right text-[11px] text-muted-foreground">{relativeTime(r.created_at)}{r.profile_completion !== undefined && <span className="block">{r.profile_completion}% complete</span>}</span>
                </Link></li>
              ))}
            </ul>
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

const ACTION_TONE: Record<string, "success" | "warning" | "danger" | "info" | "default"> = { DENIED: "danger", FAILURE: "danger" };

export function ActivityList({ rows, compact }: { rows: ActivityRow[]; compact?: boolean }) {
  return <Timeline compact={compact} items={rows.map((r) => ({ id: r.id, at: r.at, title: r.text, actor: r.actor, link: r.link ?? null,
    tone: ACTION_TONE[r.outcome ?? ""] ?? (r.action.startsWith("risk") ? "warning" : r.action.startsWith("bank") ? "info" : r.action.includes("resolved") || r.action.includes("verified") ? "success" : "default") }))} />;
}

export const fmtGenerated = (s: string) => formatDateTime(s);

export function OperationalHealth({ d }: { d: DashboardSummary }) {
  const o = d.operational_health;
  if (!o) return null;
  const audit = o.audit_verification;
  const fresh = o.data_freshness ?? [];
  const total = fresh.reduce((s, x) => s + x.value, 0) || 1;
  const bar = ["bg-success", "bg-teal", "bg-warning", "bg-danger", "bg-slate-400"];
  return (
    <Card>
      <CardHeader><div><CardTitle>Operational health</CardTitle><CardDescription>MOCK feeds are always labelled and never presented as live integrations.</CardDescription></div>
        <Link to="/admin/integrations" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">Integrations <ArrowRight className="h-3 w-3" /></Link></CardHeader>
      <CardContent className="space-y-4">
        <ul className="divide-y rounded-md border">
          {(o.integrations ?? []).map((i) => (
            <li key={i.id} className="flex items-center gap-3 px-3 py-2">
              <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{i.name}</p>
                <p className="truncate text-[11px] text-muted-foreground">{i.last_success_at ? `Last success ${relativeTime(i.last_success_at)}` : "No successful run"}{i.consecutive_failures ? ` - ${i.consecutive_failures} consecutive failure(s)` : ""}</p></div>
              <div className="flex shrink-0 gap-1"><StatusBadge status={i.mode} />{i.health === "FAILED" || i.health === "DEGRADED" ? <StatusBadge status={i.health} /> : null}</div>
            </li>
          ))}
        </ul>
        <div className="grid grid-cols-2 gap-3">
          <Stat label="Failed imports / syncs" value={o.failed_imports} to="/imports?status=FAILED" icon={FileWarning} tone={o.failed_imports ? "danger" : "neutral"} />
          <Stat label="Pending background jobs" value={o.pending_jobs} icon={Clock3} />
        </div>
        {fresh.length ? (
          <div><p className="mb-1.5 text-xs font-medium text-muted-foreground">Bank data freshness (linked loans)</p>
            <div className="flex h-2.5 overflow-hidden rounded-full bg-muted">
              {fresh.map((f, i) => <div key={f.key} title={`${f.label ?? f.key}: ${f.value}`} style={{ width: `${(f.value / total) * 100}%` }} className={bar[i] ?? "bg-slate-400"} />)}
            </div>
            <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">{fresh.map((f) => <span key={f.key}>{f.label ?? labelFor(f.key)}: <span className="num font-medium text-foreground">{f.value}</span></span>)}</div>
          </div>
        ) : null}
        <div className={cn("flex items-center gap-2 rounded-md px-3 py-2 text-xs", audit?.ok ? "bg-success-soft text-success" : audit?.ok === false ? "bg-danger-soft text-danger" : "bg-muted text-muted-foreground")}>
          {audit?.ok === false ? <ShieldX className="h-4 w-4" /> : <ShieldCheck className="h-4 w-4" />}
          {audit?.verified_at ? <span>Audit hash chain {audit.ok ? "verified" : "BROKEN"} {relativeTime(audit.verified_at)}{audit.events_checked ? ` - ${formatNumber(audit.events_checked)} events` : ""}</span> : <span>Audit chain not yet verified in this period</span>}
        </div>
      </CardContent>
    </Card>
  );
}

export function PortfolioMatrix({ rows }: { rows: { bank: string; college: string; value: number }[] }) {
  const banks = [...new Set(rows.map((r) => r.bank))];
  const colleges = [...new Set(rows.map((r) => r.college))];
  if (!rows.length) return <EmptyState title="No linked portfolio in scope" />;
  const v = (b: string, c: string) => rows.find((r) => r.bank === b && r.college === c)?.value ?? 0;
  const max = Math.max(...rows.map((r) => r.value), 1);
  const th = "px-2 py-2 text-[11px] font-semibold uppercase text-muted-foreground";
  return (
    <div className="overflow-x-auto px-2">
      <table className="w-full text-sm">
        <thead><tr><th className={cn(th, "text-left")}>College / Bank</th>{banks.map((b) => <th key={b} className={cn(th, "text-right")}>{b}</th>)}<th className={cn(th, "text-right")}>Total</th></tr></thead>
        <tbody>{colleges.map((c) => (
          <tr key={c} className="border-t"><td className="px-2 py-2.5 font-medium">{c}</td>
            {banks.map((b) => <td key={b} className="px-2 py-2.5 text-right"><span className="num inline-block min-w-[44px] rounded px-2 py-0.5" style={{ background: `rgba(29,78,216,${0.06 + (v(b, c) / max) * 0.3})` }}>{v(b, c)}</span></td>)}
            <td className="num px-2 py-2.5 text-right font-semibold">{banks.reduce((s, b) => s + v(b, c), 0)}</td></tr>))}
        </tbody>
      </table>
    </div>
  );
}

export function RiskMatrix({ rows }: { rows: { category: string; severity: string; value: number }[] }) {
  const sev = ["LOW", "MEDIUM", "HIGH", "REVIEW_REQUIRED"];
  const cats = [...new Set(rows.map((r) => r.category))];
  if (!rows.length) return <EmptyState title="No open risk indicators" description="Indicators appear when approved rules match bank-confirmed or lifecycle data." />;
  const v = (c: string, s: string) => rows.filter((r) => r.category === c && r.severity === s).reduce((a, r) => a + r.value, 0);
  return (
    <div className="overflow-x-auto px-2">
      <table className="w-full text-xs">
        <thead><tr><th className="px-2 py-2 text-left font-semibold uppercase text-muted-foreground">Category</th>{sev.map((s) => <th key={s} className="px-2 py-2 text-center font-semibold uppercase text-muted-foreground">{labelFor(s)}</th>)}</tr></thead>
        <tbody>{cats.map((c) => (
          <tr key={c} className="border-t"><td className="px-2 py-2"><Link className="hover:text-primary" to={`/risk?category=${c}`}>{labelFor(c)}</Link></td>
            {sev.map((s) => { const n = v(c, s); return <td key={s} className="px-2 py-2 text-center">{n ? <Link to={`/risk?category=${c}&severity=${s}`}><Badge tone={s === "HIGH" ? "danger" : s === "LOW" ? "neutral" : "warning"} className="num">{n}</Badge></Link> : <span className="text-muted-foreground">-</span>}</td>; })}
          </tr>))}
        </tbody>
      </table>
    </div>
  );
}
