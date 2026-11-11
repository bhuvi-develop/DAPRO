import type { Freshness } from "@/components/data/status";

export interface PortalTxn { bank_txn_ref: string; posted_on: string; amount: string | null; kind: string; channel: string | null }
export interface PortalLoan {
  id: string; bank_name: string; bank_loan_ref: string; product: string | null; bank_status: string | null; repayment_status: string; dpd: number | null;
  sanctioned_amount: string | null; disbursed_amount: string | null; principal_outstanding: string | null; overdue_amount: string | null;
  emi_amount: string | null; next_due_date: string | null; next_due_amount: string | null; moratorium_end: string | null; repayment_start: string | null;
  tenure_months: number | null; currency: string; freshness: Freshness; recent_transactions: PortalTxn[]; note: string;
}
export interface PortalOverview { student: { id: string; name: string; dapro_ref: string; lifecycle_status: string }; loans: PortalLoan[] }

export interface PortalAddress { id: string; kind: string; line1: string; line2: string | null; city: string; state: string | null; postal_code: string | null;
  country: string; verification: string; source: string; effective_from: string | null; is_current: boolean; created_at: string }
export interface PortalProfile {
  id: string; dapro_ref: string; first_name: string; last_name: string; dob: string | null; email: string | null; mobile: string | null; lifecycle_status: string;
  college: string; addresses: PortalAddress[];
  academic: { programme: string | null; course: string | null; cohort_year: number | null; enrolment_status: string | null; expected_completion: string | null; actual_completion: string | null } | null;
  employment: { status: string; employer_name: string | null; job_title: string | null; city: string | null; country: string | null; verification: string; source: string; reported_on: string | null } | null;
  preferences: { channel: string; allowed: boolean }[]; correctable_fields: string[];
}
export interface PortalMessage { id: string; channel: string; purpose: string; subject: string | null; body: string | null; status: string; created_at: string; provider_mode: string }

export const EMP_STATES = ["STUDYING", "GRADUATED", "FURTHER_STUDY", "EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "UNKNOWN"];
