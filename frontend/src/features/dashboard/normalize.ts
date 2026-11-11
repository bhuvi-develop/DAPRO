/* eslint-disable @typescript-eslint/no-explicit-any */
import type { DashboardSummary, Slice } from "./types";

/** Maps the /dashboard/summary API payload onto the cockpit view model, adding drill-down links. */
export function normalize(r: any): DashboardSummary {
  const h = r.header ?? {};
  const ch = r.charts ?? {};
  const slices = (rows: any[] | undefined, link: (k: string) => string): Slice[] | undefined =>
    rows?.map((x) => ({ key: x.status ?? x.code ?? x.key, label: x.label, value: Number(x.count ?? x.value ?? 0), link: link(x.status ?? x.code ?? x.key) }));
  const loanRow = (x: any) => ({ ...x, amount: x.amount_due ?? x.amount, bank: x.bank_name ?? x.bank });
  const gw = r.student_intel?.guarantor_witness_completion;
  const acad = r.student_intel?.academic_exceptions;
  return {
    header: {
      org_name: h.org?.name ?? h.org_name ?? "", org_type: h.org?.type, period: h.period ?? { from: "", to: "" },
      generated_at: h.generated_at, demo: h.demo, financial_visible: h.financial_visible, data_sources: h.data_sources,
      banks: (h.last_sync ?? []).map((b: any) => ({ bank_org_id: b.bank_org_id, name: b.bank_name, last_sync_at: b.last_success_at, source: "MOCK_BANK_FEED", mode: b.mode, health: b.health })),
    },
    kpis: (r.kpis ?? []).map((k: any) => ({ ...k, status: k.status === "warning" ? "attention" : k.status })),
    charts: {
      portfolio_by_bank_college: ch.portfolio_by_bank_college?.map((x: any) => ({ bank: x.bank, college: x.college, value: Number(x.linked ?? x.loans ?? 0) })),
      repayment_status_distribution: slices(ch.repayment_status_distribution, (k) => `/loans?repayment_status=${k}`),
      overdue_ageing: ch.overdue_ageing && { approval_label: ch.overdue_ageing.approval_label, policy_version: ch.overdue_ageing.policy_version,
        buckets: ch.overdue_ageing.buckets.map((b: any) => ({ key: b.code, label: b.label, value: Number(b.count), amount: b.amount, link: `/loans?dpd_bucket=${b.code}` })) },
      monthly_repayment_trend: ch.monthly_repayment_trend?.map((t: any) => ({ month: t.label ?? t.month, collected: t.net ?? t.collected, instalments_due: t.instalments_due, instalments_paid: t.instalments_paid })),
      case_status_distribution: slices(ch.case_status_distribution, (k) => `/cases?status=${k}`),
      risk_indicator_distribution: ch.risk_indicator_distribution?.map((x: any) => ({ category: x.category, severity: x.severity, value: Number(x.count) })),
      lifecycle_distribution: slices(ch.lifecycle_distribution, (k) => `/students?lifecycle_status=${k}`),
    },
    lists: {
      upcoming_repayments: r.lists?.upcoming_repayments?.map(loanRow), recently_overdue: r.lists?.recently_overdue?.map(loanRow),
      stale_records: r.lists?.stale_records?.map((x: any) => ({ ...loanRow(x), last_synced_at: x.freshness?.as_of })), repayment_exceptions: r.lists?.repayment_exceptions,
    },
    case_ops: r.case_ops && { ...r.case_ops, recent_activity: r.case_ops.recent_activity?.map((a: any, i: number) => ({ id: `${a.case_id}-${i}`, at: a.at, action: `case.${a.event_type}`.toLowerCase(), text: `${a.case_ref}: ${a.summary}`, link: `/cases/${a.case_id}` })) },
    student_intel: r.student_intel && { ...r.student_intel,
      recently_added: r.student_intel.recently_added?.map((s: any) => ({ id: s.id, name: s.full_name, dapro_ref: s.dapro_ref, created_at: s.created_at, profile_completion: s.profile_completion })),
      academic_exceptions: Array.isArray(acad) ? acad.reduce((n: number, a: any) => n + Number(a.count), 0) : acad,
      guarantor_witness_completion: gw && typeof gw === "object" ? { loans: gw.linked_loans, with_guarantor: gw.with_guarantor, with_witness: gw.with_witness } : gw },
    operational_health: r.operational_health && { ...r.operational_health,
      integrations: r.operational_health.integrations?.map((i: any) => ({ ...i, mode: i.status === "FAILED" ? i.mode : i.status ?? i.mode })),
      data_freshness: r.operational_health.data_freshness?.map((f: any) => ({ key: f.bucket, label: f.label, value: Number(f.count) })),
      audit_verification: r.operational_health.audit_verification && { ok: r.operational_health.audit_verification.ok, verified_at: r.operational_health.audit_verification.verified_at, events_checked: r.operational_health.audit_verification.events_checked } },
    activity: r.activity?.map((a: any) => ({ id: a.id, at: a.at, action: a.action, text: a.sentence ?? a.text, actor: a.actor, outcome: a.outcome,
      link: a.target_type === "student" ? `/students/${a.target_id}` : a.target_type === "case" ? `/cases/${a.target_id}` : a.target_type === "loan" ? `/loans/${a.target_id}` : null })),
  };
}
