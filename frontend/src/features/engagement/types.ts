export interface Comm {
  id: string; student_id: string; student_name: string; dapro_ref: string; case_id: string | null; recipient_type: string;
  template_code: string | null; template_version: number | null; channel: string; recipient_masked: string | null; purpose: string;
  status: string; block_reason: string | null; provider: string | null; provider_mode: string; error: string | null;
  subject: string | null; body: string | null; created_by_name: string | null; created_at: string; sent_at: string | null;
  delivered_at: string | null; delivery_note: string;
}
export interface Template {
  id: string; code: string; version: number; name: string; channel: string; purpose: string; language: string; subject: string | null;
  body: string; status: string; approval_label: string; org_id: string | null; created_by_name: string | null; approved_by_name: string | null;
  approved_at: string | null; created_at: string;
}
export interface GrievanceEvent { id: string; type: string; visibility: string; message: string; from: string | null; to: string | null; actor_name: string | null; at: string }
export interface Grievance {
  id: string; ref: string; category: string; subject: string; status: string; priority: string; channel: string; due_on: string | null;
  overdue: boolean; student_id: string; student_name: string; dapro_ref: string; owner_id: string | null; owner_name: string | null;
  case_id: string | null; loan_id: string | null; created_at: string; updated_at: string; resolved_at: string | null;
  description?: string; resolution?: string | null; closed_at?: string | null; correction_field?: string | null;
  correction_requested_value?: string | null; case_ref?: string | null; case_status?: string | null; events?: GrievanceEvent[];
  subject_user_name?: string | null; allowed_transitions?: string[];
}
export const GRV_CATEGORIES = ["DATA_CORRECTION", "AMOUNT_DISPUTE", "ADDRESS_DISPUTE", "CONDUCT_COMPLAINT", "COMMUNICATION_COMPLAINT", "OTHER"];
export const GRV_STATUSES = ["SUBMITTED", "ACKNOWLEDGED", "UNDER_REVIEW", "AWAITING_INFORMATION", "RESOLVED", "REJECTED", "CLOSED"];
export const CORRECTABLE = ["primary_email", "primary_mobile", "first_name", "last_name", "dob"];
