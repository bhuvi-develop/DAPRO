export interface Kpi { key: string; label: string; value: number | string | null; previous_value?: number | null; unit?: "count" | "inr" | "pct"; status?: string; link?: string | null; hint?: string | null }
export interface Slice { key: string; label?: string; value: number; amount?: string | null; link?: string | null }
export interface TrendPoint { month: string; collected?: string | number | null; reversed?: string | number | null; instalments_due?: number; instalments_paid?: number }
export interface LoanRow { loan_id: string; student_id?: string | null; student_name?: string | null; dapro_ref?: string | null; bank_loan_ref: string; bank?: string | null; due_date?: string | null; amount?: string | null; dpd?: number | null; dpd_bucket?: string | null; repayment_status?: string | null; overdue_amount?: string | null; sync_state?: string | null; last_synced_at?: string | null }
export interface ReconRow { id: string; kind: string; severity: string; summary: string; created_at: string; loan_id?: string | null; bank_loan_ref?: string | null }
export interface IntegrationRow { id: string; name: string; kind: string; org?: string | null; mode: string; health: string; status?: string; last_success_at?: string | null; last_failure_at?: string | null; consecutive_failures?: number; last_error?: string | null }
export interface ActivityRow { id: string; at: string; action: string; text: string; actor?: string | null; link?: string | null; outcome?: string }

export interface DashboardSummary {
  header: { org_name: string; org_type?: string; period: { from: string; to: string }; generated_at: string; demo?: boolean;
    banks?: { bank_org_id: string; name: string; last_sync_at: string | null; source: string; mode: string; health?: string }[];
    data_sources?: string[]; financial_visible?: boolean };
  kpis: Kpi[];
  charts: {
    portfolio_by_bank_college?: { bank: string; college: string; value: number }[];
    repayment_status_distribution?: Slice[];
    overdue_ageing?: { buckets: Slice[]; approval_label?: string; policy_version?: number };
    monthly_repayment_trend?: TrendPoint[];
    case_status_distribution?: Slice[];
    risk_indicator_distribution?: { category: string; severity: string; value: number }[];
    lifecycle_distribution?: Slice[];
  };
  lists?: { upcoming_repayments?: LoanRow[]; recently_overdue?: LoanRow[]; repayment_exceptions?: ReconRow[]; stale_records?: LoanRow[]; partial_payments?: LoanRow[] };
  case_ops?: { open?: number; high_priority?: number; awaiting_review?: number; assigned_field_visits?: number; overdue_follow_ups?: number;
    recent_activity?: ActivityRow[] };
  student_intel?: { recently_added?: { id: string; name: string; dapro_ref: string; college?: string; created_at: string; profile_completion?: number }[];
    avg_profile_completion?: number | null; missing_information?: number; pending_address_verification?: number; academic_exceptions?: number;
    guarantor_witness_completion?: { loans?: number; with_guarantor?: number; with_witness?: number } | number | null };
  operational_health?: { integrations?: IntegrationRow[]; failed_imports?: number; pending_jobs?: number;
    data_freshness?: Slice[]; audit_verification?: { ok: boolean | null; verified_at: string | null; events_checked?: number } | null };
  activity?: ActivityRow[];
}
