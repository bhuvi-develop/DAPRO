import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { get } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/menu";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { DataTable, type Column } from "@/components/data/table";
import { EmptyState, ErrorState } from "@/components/data/states";
import { FreshnessBadge, Money, StatusBadge, type Freshness } from "@/components/data/status";
import { PageFallback } from "@/components/layout/AppShell";
import { formatDate, formatDateTime, formatNumber } from "@/lib/utils";
import { ScheduleTab, SnapshotsTab, TransactionsTab } from "./loanTabs";
import { GuarantorsTab, WitnessesTab } from "./parties";
import { DpdCell, MirrorBanner, MockBadge, type LoanItem } from "./shared";

interface Batch { id: string; kind: string; source: string; status: string; summary: Record<string, number>; started_at: string | null; finished_at: string | null; created_at: string }
interface LoanDetail extends LoanItem {
  bank_borrower_ref: string | null; scheme: string | null; sanction_date: string | null; first_disbursement_date: string | null; tenure_months: number | null;
  interest_rate_pct: string | null; link_validation: Record<string, unknown>; linked_at: string | null; source_system: string; source_record_id: string | null;
  snapshot: { as_of: string; principal_outstanding: string | null; interest_charges: string | null; overdue_amount: string | null; total_due: string | null;
    bank_dpd: number | null; bank_status: string | null; freshness: Freshness } | null;
  parties: { id: string; role: string; full_name: string; relationship: string | null; source: string }[];
  guarantors: unknown[] | null; witnesses: unknown[] | null; sync_history: Batch[];
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="rounded-md border bg-surface px-4 py-3">
      <p className="text-[11px] font-medium text-muted-foreground">{label}</p>
      <div className="mt-0.5 text-[17px] font-semibold">{children}</div>
    </div>
  );
}

const batchCols: Column<Batch>[] = [
  { key: "at", header: "Started", cell: (b) => formatDateTime(b.started_at ?? b.created_at) },
  { key: "kind", header: "Kind", cell: (b) => <span className="text-xs">{b.kind}</span> },
  { key: "src", header: "Source", cell: (b) => <StatusBadge status={b.source.includes("MOCK") ? "MOCK" : b.source} /> },
  { key: "st", header: "Status", cell: (b) => <StatusBadge status={b.status} /> },
  { key: "sum", header: "Summary", cell: (b) => (
    <span className="text-xs text-muted-foreground">
      {formatNumber(b.summary?.transactions_new ?? 0)} new transactions, {formatNumber(b.summary?.transactions_duplicate ?? 0)} duplicates skipped
    </span>) },
  { key: "open", header: "", cell: (b) => <Link className="text-xs font-medium text-primary hover:underline" to={`/imports/${b.id}`}>Open</Link> },
];

export default function LoanDetailPage() {
  const { id = "" } = useParams();
  const can = useCan();
  const q = useQuery({ queryKey: ["loan", id], queryFn: () => get<LoanDetail>(`/loans/${id}`) });
  if (q.isLoading) return <PageFallback />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const l = q.data;
  const r = l.financial_restricted;
  const termItems = [
    { label: "Bank borrower ref", value: <span className="font-mono">{l.bank_borrower_ref ?? "-"}</span> },
    { label: "Scheme", value: l.scheme },
    { label: "Sanction date", value: formatDate(l.sanction_date) },
    { label: "First disbursement", value: formatDate(l.first_disbursement_date) },
    { label: "Moratorium ends", value: formatDate(l.moratorium_end) },
    { label: "Repayment starts", value: formatDate(l.repayment_start) },
    { label: "Tenure", value: l.tenure_months ? `${l.tenure_months} months` : "-" },
    { label: "Interest rate (bank)", value: r ? "Restricted" : l.interest_rate_pct ? `${l.interest_rate_pct}%` : "-" },
    { label: "EMI", value: <Money value={l.emi_amount} restricted={r} precise /> },
    { label: "Source record", value: <span className="font-mono text-xs">{l.source_system} / {l.source_record_id ?? "-"}</span> },
  ];
  const validationItems = Object.entries(l.link_validation ?? {})
    .map(([k, v]) => ({ label: k.replace(/_/g, " "), value: String(v) }))
    .concat([{ label: "linked at", value: formatDateTime(l.linked_at) }]);

  return (
    <div className="space-y-5">
      <PageHeader
        title={<span className="font-mono">{l.bank_loan_ref}</span>}
        description={<>
          {l.product_name ?? "Education loan"} with {l.bank_name}{l.branch_name ? `, ${l.branch_name}` : ""}. Borrower:{" "}
          {l.student_id
            ? <Link className="font-medium text-primary hover:underline" to={`/students/${l.student_id}`}>{l.student_name} ({l.dapro_ref})</Link>
            : "not linked"}
        </>}
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Loan accounts", to: "/loans" }, { label: l.bank_loan_ref }]}
        meta={<>
          <StatusBadge status={l.link_status} /><StatusBadge status={l.repayment_status} />
          <Badge tone="outline">Bank status: {l.bank_status}</Badge><MockBadge source={l.source_system} /><FreshnessBadge f={l.freshness} />
        </>}
      />
      <MirrorBanner />
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <Stat label="Sanctioned"><Money value={l.sanctioned_amount} restricted={r} /></Stat>
        <Stat label="Disbursed"><Money value={l.disbursed_amount} restricted={r} /></Stat>
        <Stat label="Principal outstanding"><Money value={l.snapshot?.principal_outstanding ?? l.principal_outstanding} restricted={r} /></Stat>
        <Stat label="Overdue (bank)">
          <Money value={l.snapshot?.overdue_amount ?? l.overdue_amount} restricted={r} className={l.repayment_status === "OVERDUE" ? "text-danger" : undefined} />
        </Stat>
        <Stat label="Days past due"><DpdCell dpd={l.dpd} bucket={l.dpd_bucket} restricted={r} /></Stat>
        <Stat label="Next due">
          <span className="text-sm">{formatDate(l.next_due_date)}</span>
          {!r && l.next_due_amount && <p className="text-xs font-normal text-muted-foreground"><Money value={l.next_due_amount} /></p>}
        </Stat>
      </div>
      {l.repayment_status === "UNKNOWN" && (
        <p className="rounded-md bg-warning-soft px-3 py-2 text-xs text-[hsl(32_95%_30%)]">
          Repayment status is UNKNOWN because bank data is {l.sync_state.toLowerCase()} or incomplete. DAPRO does not assume paid, unpaid or zero (BR-03).
        </p>
      )}
      <Tabs defaultValue={can("repayment:read") ? "schedule" : "details"}>
        <TabsList>
          {can("repayment:read") && <TabsTrigger value="schedule">Schedule</TabsTrigger>}
          {can("repayment:read") && <TabsTrigger value="txns">Transactions</TabsTrigger>}
          {can("loan:financial") && <TabsTrigger value="snaps">Snapshots</TabsTrigger>}
          <TabsTrigger value="details">Details and parties</TabsTrigger>
          {can("guarantor:read") && <TabsTrigger value="guarantors">Guarantors</TabsTrigger>}
          {can("witness:read") && <TabsTrigger value="witnesses">Witnesses</TabsTrigger>}
          <TabsTrigger value="sync">Sync history</TabsTrigger>
        </TabsList>
        {can("repayment:read") && <TabsContent value="schedule"><Card className="p-3"><ScheduleTab loanId={id} restricted={r} /></Card></TabsContent>}
        {can("repayment:read") && <TabsContent value="txns"><Card className="p-3"><TransactionsTab loanId={id} restricted={r} /></Card></TabsContent>}
        {can("loan:financial") && <TabsContent value="snaps"><Card className="p-3"><SnapshotsTab loanId={id} /></Card></TabsContent>}
        <TabsContent value="details">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Bank-sourced loan terms</CardTitle><FreshnessBadge f={l.freshness} compact /></CardHeader>
              <CardContent><KeyValue items={termItems} /></CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Link validation and parties</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <KeyValue items={validationItems} />
                {l.parties.length ? (
                  <ul className="divide-y rounded-md border">
                    {l.parties.map((p) => (
                      <li key={p.id} className="flex items-center justify-between px-3 py-2 text-sm">
                        <span>{p.full_name} <span className="text-xs text-muted-foreground">({p.relationship ?? "-"})</span></span>
                        <Badge tone="info">{p.role.replace("_", "-")}</Badge>
                      </li>
                    ))}
                  </ul>
                ) : <EmptyState title="No parties supplied by the bank" />}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
        {can("guarantor:read") && <TabsContent value="guarantors"><GuarantorsTab loanId={id} /></TabsContent>}
        {can("witness:read") && <TabsContent value="witnesses"><WitnessesTab loanId={id} /></TabsContent>}
        <TabsContent value="sync">
          <Card>
            <DataTable dense columns={batchCols} rows={l.sync_history} rowKey={(b) => b.id} caption="Sync history"
              empty={<EmptyState title="No synchronization recorded" />} />
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
