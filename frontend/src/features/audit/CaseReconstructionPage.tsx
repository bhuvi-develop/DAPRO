import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, Printer, TriangleAlert } from "lucide-react";
import { get } from "@/api/client";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/data/layout";
import { ErrorState } from "@/components/data/states";
import { PageFallback } from "@/components/layout/AppShell";
import { cn, formatDateTime } from "@/lib/utils";
import { MiniTable, Props, Section, type Row } from "./reconParts";

interface Recon {
  case: Row; student: Row; loan: Row | null; bank_snapshot_at_creation: Row | null; bank_snapshot_now: Row | null; schedule: Row | null;
  transactions: Row[]; risk_indicators: Row[]; reviews: Row[]; addresses: Row[]; employment: Row[]; communications: Row[]; follow_ups: Row[];
  field_visits: Row[]; commitments: Row[]; evidence: Row[]; grievances: Row[]; case_events: Row[]; disposition: Row; audit_events: Row[];
  completeness: { status: "COMPLETE" | "INCOMPLETE"; checks: { key: string; ok: boolean; label: string }[]; missing: string[] };
}

export default function CaseReconstructionPage() {
  const { id = "" } = useParams();
  const q = useQuery({ queryKey: ["reconstruction", id], queryFn: () => get<Recon>(`/audit/cases/${id}/reconstruction`) });
  if (q.isLoading) return <PageFallback />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data;
  const c = d.completeness;
  const complete = c.status === "COMPLETE";
  return (
    <div className="space-y-4 print:space-y-3">
      <PageHeader title={`Case reconstruction ${d.case.case_ref}`} description="Why this case was created and prioritised, from source facts (RD 11.3). Read-only evidence view; this access is itself audited."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Audit trail", to: "/audit" }, { label: d.case.case_ref }]}
        actions={<><Button asChild variant="secondary" className="print:hidden"><Link to={`/cases/${d.case.id}`}>Open case</Link></Button>
          <Button variant="secondary" className="print:hidden" onClick={() => window.print()}><Printer />Print</Button></>} />
      <div role="status" className={cn("rounded-lg border p-4", complete ? "border-success/30 bg-success-soft" : "border-warning/40 bg-warning-soft")}>
        <p className={cn("flex items-center gap-2 font-semibold", complete ? "text-success" : "text-[hsl(32_95%_30%)]")}>
          {complete ? <CheckCircle2 className="h-5 w-5" /> : <TriangleAlert className="h-5 w-5" />}
          Reconstruction {complete ? "COMPLETE" : "INCOMPLETE"}
        </p>
        <ul className="mt-2 grid gap-1 text-xs sm:grid-cols-2">
          {c.checks.map((k) => <li key={k.key} className={k.ok ? "text-success" : "text-danger"}>{k.ok ? "Present" : "Missing"}: {k.label}</li>)}
        </ul>
        {!complete && <p className="mt-2 text-xs text-muted-foreground">A case whose source facts cannot be reconstructed is incomplete (RD 11.3). Missing: {c.missing.join(", ")}.</p>}
        <p className="mt-2 text-[11px] text-muted-foreground">Generated {formatDateTime(new Date().toISOString())}</p>
      </div>
      <Section n={1} title="Case"><Props obj={d.case} /></Section>
      <Section n={2} title="Student and loan references" source="DAPRO identity and bank link validation">
        <Props obj={d.student} keys={["dapro_ref", "college_student_id", "full_name", "lifecycle_status"]} />
        <Props obj={d.loan} keys={["bank_loan_ref", "link_status", "link_validation", "sync_state", "last_synced_at"]} />
      </Section>
      <Section n={3} title="Bank data snapshot and freshness" source="Bank-sourced (mirror)">
        <p className="px-5 pt-3 text-xs font-semibold text-muted-foreground">At case creation</p><Props obj={d.bank_snapshot_at_creation} />
        <p className="px-5 pt-1 text-xs font-semibold text-muted-foreground">Latest</p><Props obj={d.bank_snapshot_now} />
      </Section>
      <Section n={4} title="Schedule and transaction references" source={d.schedule ? `Schedule ${d.schedule.schedule_ref} v${d.schedule.version} from ${d.schedule.source}` : undefined}>
        <MiniTable rows={d.transactions} keys={["bank_txn_ref", "posted_on", "kind", "amount"]} empty="No bank transactions in the reconstruction window" />
      </Section>
      <Section n={5} title="Risk indicators, rule versions and triggering facts">
        <MiniTable rows={d.risk_indicators} keys={["rule_code", "rule_version", "category", "severity", "title", "explanation", "evidence", "status", "generated_at"]} />
      </Section>
      <Section n={6} title="Reviewer actions"><MiniTable rows={d.reviews} keys={["decision", "reviewer", "rationale", "override_severity", "at"]} /></Section>
      <Section n={7} title="Address and employment sources">
        <MiniTable rows={d.addresses} keys={["kind", "city", "country", "source", "verification", "method", "is_current", "effective_from"]} />
        <MiniTable rows={d.employment} keys={["status", "employer", "source", "verification", "reported_on", "is_current"]} />
      </Section>
      <Section n={8} title="Communications and contact attempts">
        <MiniTable rows={d.communications} keys={["channel", "purpose", "template", "template_version", "status", "block_reason", "provider_mode", "at"]} />
        <MiniTable rows={d.follow_ups} keys={["channel", "outcome", "notes", "by", "at"]} />
      </Section>
      <Section n={9} title="Field visits and supervisor review" source="Officer observations (BR-09)">
        <MiniTable rows={d.field_visits} keys={["officer", "status", "outcome", "visited_at", "review_status", "reviewer", "review_notes", "safety_incident", "location_captured"]} />
      </Section>
      <Section n={10} title="Commitments and evidence" source="Commitments are borrower-reported, never payments (BR-08)">
        <MiniTable rows={d.commitments} keys={["amount", "promised_date", "source", "status", "bank_txn_ref"]} />
        <MiniTable rows={d.evidence} keys={["title", "kind", "quality", "sha256", "at"]} />
      </Section>
      <Section n={11} title="Borrower disputes and corrections"><MiniTable rows={d.grievances} keys={["ref", "category", "status", "resolution"]} /></Section>
      <Section n={12} title="Final disposition"><Props obj={d.disposition} /></Section>
      <Section n={13} title="Case timeline"><MiniTable rows={d.case_events} keys={["type", "from", "to", "summary", "at"]} /></Section>
      <Section n={14} title="Audit events for this case" source="Hash-chained, append-only">
        <MiniTable rows={d.audit_events} keys={["occurred_at", "actor_label", "actor_role", "action", "outcome", "correlation_id"]} />
      </Section>
    </div>
  );
}
