import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Landmark, MessageSquarePlus } from "lucide-react";
import { get } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { EmptyState, QueryBoundary } from "@/components/data/states";
import { FreshnessBadge, Money, StatusBadge, labelFor } from "@/components/data/status";
import { formatDate } from "@/lib/utils";
import type { PortalLoan, PortalOverview } from "./types";

function LoanCard({ l }: { l: PortalLoan }) {
  return (
    <Card data-testid="portal-loan">
      <CardHeader>
        <div className="min-w-0"><CardTitle>{l.bank_name}</CardTitle><CardDescription className="font-mono">{l.bank_loan_ref}{l.product ? ` - ${l.product}` : ""}</CardDescription></div>
        <div className="flex flex-wrap justify-end gap-1.5"><StatusBadge status={l.repayment_status} />{l.dpd ? <Badge tone="danger">{l.dpd} days past due</Badge> : null}</div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="rounded-lg border bg-muted/30 p-3"><p className="text-[11px] uppercase tracking-wide text-muted-foreground">Next instalment</p>
            <p className="mt-1 text-lg font-semibold"><Money value={l.next_due_amount ?? l.emi_amount} /></p><p className="text-xs text-muted-foreground">{l.next_due_date ? `due ${formatDate(l.next_due_date)}` : "No due date supplied by the bank"}</p></div>
          <div className="rounded-lg border bg-muted/30 p-3"><p className="text-[11px] uppercase tracking-wide text-muted-foreground">Overdue amount</p>
            <p className="mt-1 text-lg font-semibold"><Money value={l.overdue_amount} /></p><p className="text-xs text-muted-foreground">As reported by your bank</p></div>
          <div className="rounded-lg border bg-muted/30 p-3"><p className="text-[11px] uppercase tracking-wide text-muted-foreground">Principal outstanding</p>
            <p className="mt-1 text-lg font-semibold"><Money value={l.principal_outstanding} /></p><p className="text-xs text-muted-foreground">Sanctioned <Money value={l.sanctioned_amount} compact /></p></div>
        </div>
        <KeyValue cols={3} items={[
          { label: "Bank status", value: labelFor(l.bank_status) },
          { label: "Repayment start", value: formatDate(l.repayment_start) },
          { label: "Moratorium ends", value: formatDate(l.moratorium_end) },
          { label: "Tenure", value: l.tenure_months ? `${l.tenure_months} months` : "-" },
          { label: "Disbursed", value: <Money value={l.disbursed_amount} /> },
          { label: "Data as of", value: <FreshnessBadge f={l.freshness} /> },
        ]} />
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Recent payments recorded by the bank</p>
          {l.recent_transactions.length ? (
            <ul className="divide-y rounded-md border text-sm">{l.recent_transactions.map((t) => (
              <li key={t.bank_txn_ref} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2">
                <span className="w-24 text-xs text-muted-foreground">{formatDate(t.posted_on)}</span>
                <span className="min-w-0 flex-1">{labelFor(t.kind)}{t.channel ? <span className="text-xs text-muted-foreground"> via {labelFor(t.channel).toLowerCase()}</span> : null}</span>
                <Money value={t.amount} className="font-medium" />
              </li>))}</ul>
          ) : <p className="text-sm text-muted-foreground">No payments recorded yet.</p>}
        </div>
        <p className="rounded-md bg-primary-soft/50 px-3 py-2 text-xs text-muted-foreground">{l.note}</p>
      </CardContent>
    </Card>
  );
}

/** Borrower home: own loans only, read-only bank data with freshness (FR-BRW-01, AC-03). */
export default function PortalHomePage() {
  const q = useQuery({ queryKey: ["portal-overview"], queryFn: () => get<PortalOverview>("/portal/overview") });
  return (
    <div className="space-y-5">
      <QueryBoundary query={q}>{(d) => (
        <>
          <PageHeader title={`Welcome, ${d.student.name.split(" ")[0]}`} description={<>Your DAPRO reference is <span className="font-mono">{d.student.dapro_ref}</span>. Current status: {labelFor(d.student.lifecycle_status).toLowerCase()}.</>}
            actions={<Button asChild variant="secondary"><Link to="/portal/grievances?new=1"><MessageSquarePlus />Raise a request</Link></Button>} />
          {d.loans.length ? d.loans.map((l) => <LoanCard key={l.id} l={l} />)
            : <Card><EmptyState icon={Landmark} title="No linked loan yet" description="When your bank confirms your education loan it will appear here." /></Card>}
        </>
      )}</QueryBoundary>
    </div>
  );
}
