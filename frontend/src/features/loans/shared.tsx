import { useQuery } from "@tanstack/react-query";
import { Info } from "lucide-react";
import { get } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { StatusBadge, type Freshness } from "@/components/data/status";

export interface LoanItem {
  id: string; bank_loan_ref: string; bank_org_id: string; bank_name: string | null; branch_name: string | null;
  student_id: string | null; student_name: string | null; dapro_ref: string | null; product_name: string | null;
  bank_status: string; link_status: string; repayment_status: string; dpd: number | null; dpd_bucket: string | null;
  sanctioned_amount: string | null; disbursed_amount: string | null; overdue_amount: string | null; principal_outstanding: string | null;
  emi_amount: string | null; next_due_date: string | null; next_due_amount: string | null; sync_state: string; last_synced_at: string | null;
  moratorium_end: string | null; repayment_start: string | null; data_origin: string; financial_restricted: boolean; freshness: Freshness; cohort?: number | null;
}

export interface Org { id: string; name: string; type: string; code?: string }
export interface Unit { id: string; name: string; kind: string; org_id: string }

/** Organization options for filters; silently empty if the role cannot read organizations. */
export function useOrgs(type?: string) {
  return useQuery({
    queryKey: ["orgs", type],
    queryFn: () => get<Org[]>(`/admin/organizations${type ? `?type=${type}` : ""}`).catch(() => [] as Org[]),
    staleTime: 300_000,
  });
}

export function useUnits(orgId?: string) {
  return useQuery({
    queryKey: ["units", orgId],
    queryFn: () => get<Unit[]>(`/admin/org-units${orgId ? `?org_id=${orgId}` : ""}`).catch(() => [] as Unit[]),
    staleTime: 300_000,
  });
}

export const REPAYMENT_STATUSES = ["CURRENT", "OVERDUE", "NOT_STARTED", "CLOSED", "UNKNOWN"];
export const BUCKETS = [
  { value: "CURRENT", label: "Current" }, { value: "DPD_1_30", label: "1-30 DPD" }, { value: "DPD_31_60", label: "31-60 DPD" },
  { value: "DPD_61_90", label: "61-90 DPD" }, { value: "DPD_90_PLUS", label: "90+ DPD" },
];
export const LINK_STATUSES = ["LINKED", "PENDING_REVIEW", "UNLINKED", "REJECTED"];
export const SYNC_STATES = ["CURRENT", "STALE", "FAILED", "UNKNOWN"];

export function DpdCell({ dpd, bucket, restricted }: { dpd: number | null; bucket: string | null; restricted?: boolean }) {
  if (restricted) return <span className="text-xs text-muted-foreground">Restricted</span>;
  if (dpd === null || dpd === undefined) return <span className="text-xs text-muted-foreground">Unknown</span>;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={dpd > 0 ? "num font-semibold text-danger" : "num"}>{dpd}</span>
      {bucket && bucket !== "CURRENT" && <StatusBadge status={bucket} dot={false} />}
    </span>
  );
}

export function MirrorBanner() {
  return (
    <div className="flex items-start gap-2 rounded-md border border-primary/20 bg-primary-soft px-3 py-2 text-xs text-navy">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
      <span>Bank loan and repayment data is a <strong>read-only mirror</strong> of the bank system (BR-01). DAPRO never edits balances, payments or charges. Every figure shows its source and when it was last synchronized.</span>
    </div>
  );
}

export function MockBadge({ source }: { source?: string | null }) {
  if (!source || !source.includes("MOCK")) return null;
  return <Badge tone="warning">MOCK bank feed - read only</Badge>;
}
