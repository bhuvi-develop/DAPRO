export type Named = { id: string; name: string } | null;
export interface MyCase {
  case_id: string; case_ref: string; status: string; priority: string; due_on: string | null; overdue: boolean; next_action: string | null;
  student: { id: string; name: string; dapro_ref: string; mobile: string | null };
  address: { id: string; kind: string; text: string; verification?: string } | null;
  loan: { bank_loan_ref: string; repayment_status: string; dpd: number | null; sync_state: string } | null;
  next_visit: { id: string; status: string; scheduled_for: string | null } | null;
}
export interface Visit {
  id: string; case_id: string; status: string; purpose: string; scheduled_for: string | null; check_in_at: string | null; check_out_at: string | null;
  visited_at: string | null; outcome: string | null; notes: string | null; borrower_present: boolean | null; safety_incident: boolean;
  incident_notes: string | null; location_captured: boolean; evidence_quality: string; review_status: string; review_notes: string | null;
  reviewer: Named; reviewed_at: string | null; officer: Named; client_draft_id: string | null; version: number;
  case_ref?: string; case_status?: string; case_priority?: string; student_name?: string; dapro_ref?: string;
}
export const OUTCOMES = [
  { value: "COMPLETED", label: "Visit completed - borrower met" },
  { value: "ATTEMPTED", label: "Visit attempted" },
  { value: "NO_CONTACT", label: "No contact" },
  { value: "ADDRESS_NOT_FOUND", label: "Address not found" },
  { value: "BORROWER_UNAVAILABLE", label: "Borrower unavailable" },
  { value: "RESCHEDULE_REQUESTED", label: "Borrower requested reschedule" },
];
