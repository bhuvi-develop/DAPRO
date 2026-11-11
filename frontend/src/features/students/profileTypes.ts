import type { Freshness } from "@/components/data/status";
import type { StudentRow } from "./shared";

export interface Address { id: string; kind: string; line1: string; line2: string | null; city: string; district: string | null; state: string | null;
  postal_code: string | null; country: string; source_type: string; verification: string; verification_method: string | null; verified_at: string | null;
  effective_from: string | null; is_current: boolean; superseded_at: string | null; notes: string | null; created_at: string }
export interface Employment { id: string; status: string; employer_name: string | null; job_title: string | null; sector: string | null; city: string | null;
  country: string | null; source: string; verification: string; verified_at: string | null; reported_on: string; effective_from: string | null;
  is_current: boolean; superseded_at: string | null; notes: string | null }
export interface Academic { id: string; college_name: string | null; programme: string; course: string; specialization: string | null; cohort_year: number;
  enrolment_status: string; start_date: string | null; expected_completion: string | null; actual_completion: string | null; source: string;
  verification: string; is_current: boolean }
export interface LoanSummary { id: string; bank_loan_ref: string; bank_name: string | null; product_name: string | null; bank_status: string;
  link_status: string; repayment_status: string; dpd: number | null; dpd_bucket: string | null; sanctioned_amount: string | null;
  principal_outstanding: string | null; overdue_amount: string | null; next_due_date: string | null; next_due_amount: string | null;
  financial_restricted: boolean; freshness: Freshness; guarantor_count?: number; witness_count?: number }
export interface Profile {
  student: StudentRow;
  completion: { percent: number; checks: { key: string; label: string; ok: boolean }[] };
  contacts: { id: string; kind: string; value: string; is_primary: boolean; source: string; verification: string }[];
  addresses?: Address[]; address_history_available?: boolean;
  academic: Academic[]; employment: Employment[];
  consents: { id: string; basis: string; purposes: string[]; notice_version: string; source: string; valid_from: string; withdrawn_at: string | null; active: boolean }[];
  loans?: LoanSummary[];
  cases?: { id: string; case_ref: string; category: string; status: string; priority: string; due_on: string | null; next_action: string | null }[];
  risk_indicators?: { id: string; rule_code: string; rule_version: number; title: string; category: string; severity: string; status: string; explanation: string; generated_at: string }[];
  grievances?: { id: string; ref: string; category: string; subject: string; status: string; due_on: string | null; created_at: string }[];
  communications?: { id: string; channel: string; purpose: string; status: string; template_code: string | null; recipient_type: string; provider_mode: string; created_at: string }[];
  pending_actions: { kind: string; label: string }[];
  timeline: { at: string; kind: string; summary: string; actor: string | null; outcome: string; source: string }[];
}
export interface FieldChange { id: string; field: string; old_value: string | null; new_value: string | null; reason: string; source: string; created_at: string }
