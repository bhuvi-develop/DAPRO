import { get } from "@/api/client";

export type Named = { id: string; name: string } | null;
export interface CaseSummary {
  id: string; case_ref: string; status: string; priority: string; category: string; reason: string; source: string;
  due_on: string | null; overdue: boolean; next_action: string | null; owner: Named; owner_id: string | null; owner_name: string | null;
  student_name: string; dapro_ref: string; student_id: string; bank_loan_ref: string | null;
  student: { id: string; name: string; dapro_ref: string; mobile?: string | null; email?: string | null; lifecycle_status?: string };
  loan: { id: string; bank_loan_ref: string; repayment_status: string; dpd: number | null; sync_state: string; overdue_amount?: string | null; last_synced_at?: string | null; source?: string; dpd_bucket?: string | null } | null;
  version: number; created_at: string; updated_at: string;
}
export interface Transition { to: string; label: string; requires: string[]; permitted: boolean; reason_if_blocked: string | null; note: string | null; conditional?: Record<string, string> }
export interface CaseDetail extends CaseSummary {
  previous_status: string | null; resolution_type: string | null; resolution_notes: string | null; resolved_at: string | null; closed_at: string | null;
  opened_by: Named; source_ref: string | null;
  timeline: { id: string; type: string; summary: string; from: string | null; to: string | null; actor: Named; at: string }[];
  follow_ups: { id: string; channel: string; outcome: string; notes: string; contacted_at: string; next_follow_up_on: string | null; actor: Named }[];
  evidence: { id: string; kind: string; title: string; file_name: string | null; mime_type: string | null; size_bytes: number | null; sha256: string | null; evidence_quality: string; uploaded_by: Named; created_at: string }[];
  commitments: { id: string; amount: string; promised_date: string; source: string; status: string; bank_txn_ref: string | null; notes: string | null; recorded_by: Named; created_at: string }[];
  visits: { id: string; status: string; purpose: string; scheduled_for: string | null; visited_at: string | null; outcome: string | null; review_status: string; safety_incident: boolean; officer: Named }[];
  indicators: { id: string; rule_code: string; rule_version: number; title: string; severity: string; status: string; generated_at: string }[];
  grievances: { id: string; ref: string; category: string; status: string; subject: string }[];
  allowed_transitions: Transition[]; resolution_types: Record<string, string>;
  can: { assign: boolean; update: boolean; record_visit: boolean; follow_up: boolean };
}
export interface CaseMeta { statuses: string[]; priorities: string[]; categories: string[]; channels: string[]; outcomes: { no_contact: string[]; contact: string[] }; resolution_types: Record<string, string> }

export const fetchCaseMeta = () => get<CaseMeta>("/cases/meta");

export const userOptions = (q: string) =>
  get<{ items: { id: string; full_name: string; title: string | null }[] }>(`/admin/users?size=50&status=ACTIVE&q=${encodeURIComponent(q)}`)
    .then((r) => r.items.map((u) => ({ value: u.id, label: u.full_name, sublabel: u.title })));
