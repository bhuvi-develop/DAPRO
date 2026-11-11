export interface OrgRow { id: string; type: string; code: string; name: string; legal_name: string | null; status: string; city: string | null; state: string | null;
  contact_email: string | null; user_count: number | null; unit_count: number; created_at: string }
export interface UnitRow { id: string; org_id: string; parent_id: string | null; kind: string; code: string; name: string; city: string | null; state: string | null; status: string }
export interface Agreement { id: string; reference: string; college_org_id: string; college_name: string | null; bank_org_id: string; bank_name: string | null;
  purposes: string[]; shared_fields: string[]; status: string; effective_from: string; effective_to: string | null; approval_label: string; notes: string | null }
export interface UserRow { id: string; email: string; full_name: string; title: string | null; status: string; org_id: string; org_name: string | null;
  org_unit_id: string | null; unit_name: string | null; roles: string[]; mfa_enabled: boolean; mfa_required: boolean; locked: boolean;
  failed_logins: number; last_login_at: string | null; activated_at: string | null; created_at: string }
export interface RoleRow { id: string; code: string; name: string; description: string | null; org_types: string[]; permissions: string[]; is_system: boolean; version: number; user_count: number }
export interface SessionRow { id: string; user_id: string; user_name: string; email: string; ip: string | null; user_agent: string | null; created_at: string; last_seen_at: string; mfa_passed: boolean; current: boolean }
export interface IntegrationRow { id: string; org_id: string | null; org_name: string | null; kind: string; name: string; provider: string; mode: string; health: string;
  status: string; last_success_at: string | null; last_failure_at: string | null; last_error: string | null; consecutive_failures: number;
  refresh_interval_hours: number; simulate_failure: boolean; config: Record<string, unknown>; is_mock: boolean; updated_at: string }
export interface PolicyRow { id: string; key: string; version: number; value: Record<string, unknown>; status: string; approval_label: string; description: string;
  effective_from: string; created_by: string | null; approved_by: string | null; created_at: string }
