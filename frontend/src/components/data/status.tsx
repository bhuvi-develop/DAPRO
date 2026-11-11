import { Clock, Database, Lock } from "lucide-react";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Tooltip } from "@/components/ui/menu";
import { cn, formatDateTime, formatINR, relativeTime, titleCase } from "@/lib/utils";

type Tone = NonNullable<BadgeProps["tone"]>;

const TONES: Record<string, Tone> = {};
const set = (tone: Tone, codes: string) => codes.split(" ").forEach((c) => (TONES[c] = tone));
set("success", "PAID CURRENT VERIFIED ACTIVE APPROVED HEALTHY LINKED RESOLVED DELIVERED APPLIED CONNECTED COMPLETED EMPLOYED SELF_EMPLOYED SUCCESS LIVE BANK_CONFIRMED CONFIRMED ACTIONED CONSISTENT ENROLLED");
set("warning", "PENDING PENDING_REVIEW PARTIALLY_PAID PARTIAL IN_GRACE STALE DEGRADED IN_REVIEW CONTACT_ATTEMPTED BORROWER_UPDATE_PENDING DRAFT QUEUED INVITED REVIEW_REQUIRED MEDIUM AWAITING_INFORMATION AWAITING_APPROVAL VALIDATED MOCK RETURNED PENDING_APPROVAL ON_LEAVE OPEN LAPSED DEMO_FIXTURE DEMO");
set("danger", "OVERDUE FAILED CRITICAL HIGH ESCALATED REVERSAL BLOCKED SUSPENDED REJECTED REVOKED DISPUTED DENIED FAILURE CONFLICT DISCONTINUED UNEMPLOYED");
set("info", "NEW UPCOMING SCHEDULED SUBMITTED NOT_STARTED STUDYING RUNNING CONTACT_ESTABLISHED ACKNOWLEDGED UNDER_REVIEW ASSIGNED SENT FURTHER_STUDY GRADUATED MORATORIUM IN_REPAYMENT");
set("neutral", "UNKNOWN NOT_CONFIGURED DISABLED CLOSED DISMISSED SUPERSEDED LOW RETIRED UNVERIFIED CANCELLED WITHDRAWN NOT_REQUIRED SINGLE_SOURCE");

const LABELS: Record<string, string> = {
  DPD_1_30: "1-30 DPD", DPD_31_60: "31-60 DPD", DPD_61_90: "61-90 DPD", DPD_90_PLUS: "90+ DPD",
  NOT_CONFIGURED: "Not configured", MOCK: "MOCK", LIVE: "LIVE", DEMO_FIXTURE: "Demo fixture - pending approval",
  IN_GRACE: "In grace", REVIEW_REQUIRED: "Review required",
};

export const toneFor = (code?: string | null): Tone => (code ? TONES[code] ?? "neutral" : "neutral");
export const labelFor = (code?: string | null) => (code ? LABELS[code] ?? titleCase(code) : "-");

export function StatusBadge({ status, className, dot = true }: { status?: string | null; className?: string; dot?: boolean }) {
  if (!status) return <span className="text-muted-foreground">-</span>;
  return <Badge tone={toneFor(status)} dot={dot} className={className}>{labelFor(status)}</Badge>;
}

export interface Freshness { source?: string | null; as_of?: string | null; sync_state?: string | null }

/** Every financial value shows its source and last synchronization time (RD 4.3, FR-REP-10, AC-03). */
export function FreshnessBadge({ f, compact }: { f?: Freshness | null; compact?: boolean }) {
  if (!f) return null;
  const state = f.sync_state ?? "UNKNOWN";
  const mock = (f.source ?? "").includes("MOCK");
  return (
    <Tooltip content={<span>Source: {f.source ?? "unknown"}<br />As of: {formatDateTime(f.as_of)}<br />Sync state: {state}{mock ? <><br />Demo data from a MOCK bank feed - not a live bank.</> : null}</span>}>
      <span className={cn("inline-flex items-center gap-1.5 text-[11px] text-muted-foreground", state !== "CURRENT" && "text-[hsl(32_95%_34%)]")}>
        <Database className="h-3 w-3" aria-hidden />
        {!compact && <span>{mock ? "Mock bank feed" : f.source ?? "Unknown source"}</span>}
        <Clock className="h-3 w-3" aria-hidden />
        <span>{f.as_of ? relativeTime(f.as_of) : "never synced"}</span>
        {state !== "CURRENT" && <Badge tone={toneFor(state)} className="ml-0.5">{labelFor(state)}</Badge>}
      </span>
    </Tooltip>
  );
}

/** Money is a decimal string from the API; null + restricted flag means masked by role (AC-02). */
export function Money({ value, restricted, precise, compact, className }: { value?: string | number | null; restricted?: boolean; precise?: boolean; compact?: boolean; className?: string }) {
  if (restricted) {
    return (
      <Tooltip content="Bank financial details are restricted for your role.">
        <span className={cn("inline-flex items-center gap-1 text-muted-foreground", className)}><Lock className="h-3 w-3" />Restricted</span>
      </Tooltip>
    );
  }
  const s = formatINR(value ?? null, { precise, compact });
  return <span className={cn("num", !s && "text-muted-foreground", className)}>{s ?? "Not supplied"}</span>;
}
