export interface Indicator {
  id: string; title: string; explanation: string; rule_code: string; rule_version: number; category: string; severity: string;
  status: string; generated_at: string; updated_at: string; case_id: string | null; student_name: string; dapro_ref: string;
  student: { id: string; name: string; dapro_ref: string }; loan: { id: string; bank_loan_ref: string } | null;
  bank_loan_ref: string | null; assigned_to_name: string | null; not_a_finding: string;
  evidence?: { fact: string; value: unknown; source: string; as_of: string | null }[];
  input_snapshot?: Record<string, unknown>;
  rule?: { code: string; version: number; name: string; description: string; params: Record<string, unknown>; recommended_action: string; approval_label: string };
  reviews?: { id: string; decision: string; rationale: string; override_severity: string | null; evidence_ref: string | null; case_id: string | null; reviewer: { id: string; name: string } | null; created_at: string }[];
}
export interface Rule {
  id: string; code: string; version: number; name: string; category: string; description: string; params: Record<string, unknown>;
  severity: string; recommended_action: string; status: string; approval_label: string; effective_from: string | null;
  change_reason: string | null; created_by: { id: string; name: string } | null; approved_by: { id: string; name: string } | null; approved_at: string | null;
}
export const CATEGORIES = ["FINANCIAL_DELINQUENCY", "CONTACT_DATA_QUALITY", "DATA_SYNCHRONIZATION", "OPERATIONAL_FOLLOW_UP"];
export const SEVERITIES = ["LOW", "MEDIUM", "HIGH", "REVIEW_REQUIRED"];
export const NOT_A_FINDING = "Indicators prioritise human review. They are not findings of default, fraud or absconding (FR-RSK-07).";
