import { get } from "@/api/client";
import { cn } from "@/lib/utils";

export interface StudentRow {
  id: string; dapro_ref: string; college_student_id: string; full_name: string; first_name: string; last_name: string;
  dob: string | null; dob_masked: boolean; gender: string | null; kyc_ref_last4: string | null; email: string | null; mobile: string | null;
  college_org_id: string; college_name: string | null; campus_name?: string | null; lifecycle_status: string; record_status: string;
  verification_status: string; source: string; source_ref: string | null; profile_completion: number; data_origin: string;
  version: number; loan_count: number; created_at: string; updated_at: string;
}

export interface Org { id: string; type: string; code: string; name: string; city?: string | null; status?: string }

export const LIFECYCLE = ["STUDYING", "GRADUATED", "FURTHER_STUDY", "EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "UNKNOWN"];
export const VERIFICATION = ["VERIFIED", "UNVERIFIED", "PENDING"];
export const ADDRESS_KINDS = ["PERMANENT", "CURRENT", "CORRESPONDENCE"];
export const ADDRESS_SOURCES = ["STAFF_ENTERED", "BORROWER_REPORTED", "COLLEGE_PROVIDED", "BANK_PROVIDED", "FIELD_OBSERVED"];
export const METHODS = ["DOCUMENT", "POSTAL", "FIELD_VISIT", "PHONE_CONFIRMATION", "SELF_DECLARATION"];

export const fetchColleges = () => get<Org[]>("/admin/organizations?type=COLLEGE");

export function CompletionBar({ value, className }: { value: number; className?: string }) {
  const tone = value >= 80 ? "bg-success" : value >= 50 ? "bg-teal" : "bg-warning";
  return (
    <div className={cn("flex items-center gap-2", className)} title={`${value}% profile completion`}>
      <div className="h-1.5 w-20 rounded-full bg-muted"><div className={cn("h-1.5 rounded-full", tone)} style={{ width: `${value}%` }} /></div>
      <span className="num text-xs text-muted-foreground">{value}%</span>
    </div>
  );
}

export function CompletionRing({ value }: { value: number }) {
  const r = 26;
  const c = 2 * Math.PI * r;
  const color = value >= 80 ? "#059669" : value >= 50 ? "#0F766E" : "#D97706";
  return (
    <div className="relative h-16 w-16 shrink-0" role="img" aria-label={`Profile ${value}% complete`}>
      <svg viewBox="0 0 64 64" className="h-16 w-16 -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" stroke="#E2E8F0" strokeWidth="6" />
        <circle cx="32" cy="32" r={r} fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c - (c * value) / 100} />
      </svg>
      <span className="num absolute inset-0 flex items-center justify-center text-sm font-semibold">{value}%</span>
    </div>
  );
}
