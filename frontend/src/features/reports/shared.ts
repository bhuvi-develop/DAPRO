export interface FilterSpec { key: string; type: string; label: string }
export interface ReportSpec { code: string; title: string; category: string; description: string; calculation_definition: string; data_source: string;
  required_permissions: string[]; filters: FilterSpec[]; allowed: boolean }
export interface ExportJob { id: string; report_code: string; title: string; filters: Record<string, string>; purpose: string; format: string; status: string;
  row_count: number | null; file_name: string | null; sha256: string | null; as_of: string | null; error: string | null; requested_by: string; created_at: string; completed_at: string | null }

/** Known enum values for catalogue filters (values mirror backend status vocabularies). */
export const ENUMS: Record<string, string[]> = {
  lifecycle_status: ["STUDYING", "GRADUATED", "FURTHER_STUDY", "EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "UNKNOWN"],
  link_status: ["LINKED", "PENDING_REVIEW", "UNLINKED", "REJECTED"],
  repayment_status: ["CURRENT", "OVERDUE", "NOT_STARTED", "CLOSED", "UNKNOWN"],
  dpd_bucket: ["CURRENT", "DPD_1_30", "DPD_31_60", "DPD_61_90", "DPD_90_PLUS"],
  priority: ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
};
