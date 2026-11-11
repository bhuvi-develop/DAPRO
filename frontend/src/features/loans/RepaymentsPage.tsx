import { useNavigate } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { get, type Page } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/menu";
import { PageHeader } from "@/components/data/layout";
import { FilterBar, FilterSelect, SearchInput } from "@/components/data/filters";
import { DataTable, Pagination, type Column } from "@/components/data/table";
import { FreshnessBadge, Money, StatusBadge, labelFor } from "@/components/data/status";
import { ErrorState } from "@/components/data/states";
import { useUrlState } from "@/hooks/useUrlState";
import { formatDate, formatDateTime, formatNumber, qs } from "@/lib/utils";
import { InstTable, LoanMiniTable, ReversalTable, type Overview } from "./repaymentParts";
import { BUCKETS, DpdCell, MirrorBanner, REPAYMENT_STATUSES, SYNC_STATES, useOrgs, useUnits, type LoanItem } from "./shared";

const DEFAULTS = {} as Record<string, string | undefined>;
const KEYS = ["repayment_status", "dpd_bucket", "sync_state", "bank_org_id", "college_org_id", "branch_unit_id", "cohort", "due_from", "due_to", "q"];

const cols: Column<LoanItem>[] = [
  { key: "student_name", header: "Borrower", sortable: true, cell: (r) => (
    <div><p className="font-medium">{r.student_name}</p><p className="font-mono text-[11px] text-muted-foreground">{r.dapro_ref}</p></div>) },
  { key: "bank_loan_ref", header: "Loan", sortable: true, cell: (r) => <span className="font-mono text-xs">{r.bank_loan_ref}</span> },
  { key: "cohort", header: "Cohort", hideOnMobile: true, cell: (r) => <span className="num text-xs">{r.cohort ?? "-"}</span> },
  { key: "status", header: "Status", cell: (r) => <StatusBadge status={r.repayment_status} /> },
  { key: "dpd", header: "DPD", sortable: true, cell: (r) => <DpdCell dpd={r.dpd} bucket={r.dpd_bucket} restricted={r.financial_restricted} /> },
  { key: "next_due_date", header: "Next due", sortable: true, cell: (r) => (
    <div className="text-xs"><p>{formatDate(r.next_due_date)}</p><Money value={r.next_due_amount} restricted={r.financial_restricted} className="text-muted-foreground" /></div>) },
  { key: "overdue_amount", header: "Overdue", sortable: true, className: "text-right", headerClassName: "text-right",
    cell: (r) => <Money value={r.overdue_amount} restricted={r.financial_restricted} /> },
  { key: "f", header: "Data", hideOnMobile: true, cell: (r) => <FreshnessBadge f={r.freshness} compact /> },
];

export default function RepaymentsPage() {
  const nav = useNavigate();
  const can = useCan();
  const restricted = !can("loan:financial");
  const { state, update, page, size } = useUrlState(DEFAULTS);
  const ov = useQuery({ queryKey: ["repay-overview"], queryFn: () => get<Overview>("/repayments/overview") });
  const banks = useOrgs("BANK");
  const colleges = useOrgs("COLLEGE");
  const units = useUnits(state.bank_org_id);
  const params = Object.fromEntries(KEYS.map((k) => [k, state[k]]));
  const acc = useQuery({
    queryKey: ["repay-accounts", params, page, size, state.sort],
    queryFn: ({ signal }) => get<Page<LoanItem>>(`/repayments/accounts${qs({ ...params, page, size, sort: state.sort })}`, signal),
    placeholderData: keepPreviousData,
  });
  const active = KEYS.filter((k) => state[k]).length;
  const o = ov.data;
  const branches = (units.data ?? []).filter((u) => u.kind === "BRANCH");

  return (
    <div className="space-y-4">
      <PageHeader title="Repayment monitoring"
        description="Bank-confirmed schedules, payments and days past due. Reminders and commitments are never counted as payments."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Repayment monitoring" }]}
        meta={o && (
          <span className="text-xs text-muted-foreground">
            Business date {formatDate(o.as_of_date)} - source {o.freshness.source}, bank data from {formatDateTime(o.freshness.oldest_as_of)} to {formatDateTime(o.freshness.latest_as_of)}
          </span>
        )} />
      <MirrorBanner />
      {ov.error ? <ErrorState error={ov.error} onRetry={() => ov.refetch()} /> : o && (
        <div className="grid gap-3 lg:grid-cols-2">
          <Card className="p-4">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Linked accounts by repayment status</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(o.status_counts).map(([k, v]) => (
                <button key={k} type="button" onClick={() => update({ repayment_status: k })} className="rounded-md border px-3 py-1.5 text-left hover:border-primary/40">
                  <StatusBadge status={k} /><p className="num mt-1 text-lg font-semibold">{formatNumber(v)}</p>
                </button>
              ))}
            </div>
            <p className="mt-2 text-[11px] text-muted-foreground">{o.unknown_note}</p>
          </Card>
          <Card className="p-4">
            <p className="mb-2 text-xs font-medium text-muted-foreground">Overdue ageing - DPD buckets are a demo fixture pending bank approval</p>
            <div className="flex flex-wrap gap-2">
              {BUCKETS.map((b) => (
                <button key={b.value} type="button" onClick={() => update({ dpd_bucket: b.value })} className="rounded-md border px-3 py-1.5 text-left hover:border-primary/40">
                  <p className="text-[11px] text-muted-foreground">{labelFor(b.value)}</p>
                  <p className="num text-lg font-semibold">{formatNumber(o.bucket_counts[b.value] ?? 0)}</p>
                </button>
              ))}
              <Badge tone="warning" className="self-center">{o.reconciliation_open} open reconciliation items</Badge>
            </div>
          </Card>
        </div>
      )}
      <Tabs defaultValue="accounts">
        <TabsList>
          <TabsTrigger value="accounts">Accounts</TabsTrigger>
          <TabsTrigger value="upcoming">Upcoming 30 days <Badge tone="info">{o?.upcoming.length ?? 0}</Badge></TabsTrigger>
          <TabsTrigger value="overdue">Recently overdue <Badge tone="danger">{o?.recently_overdue.length ?? 0}</Badge></TabsTrigger>
          <TabsTrigger value="partial">Partial payments <Badge tone="warning">{o?.partial_payments.length ?? 0}</Badge></TabsTrigger>
          <TabsTrigger value="reversals">Reversals <Badge tone="danger">{o?.reversals.length ?? 0}</Badge></TabsTrigger>
          <TabsTrigger value="stale">Stale / unknown <Badge tone="neutral">{o?.stale.length ?? 0}</Badge></TabsTrigger>
        </TabsList>
        <TabsContent value="accounts">
          <Card>
            <FilterBar active={active} onClear={() => update(Object.fromEntries(KEYS.map((k) => [k, undefined])))}>
              <SearchInput value={state.q} onChange={(v) => update({ q: v })} placeholder="Search name or loan ref" />
              <FilterSelect label="Status" value={state.repayment_status} onChange={(v) => update({ repayment_status: v })} options={REPAYMENT_STATUSES} />
              <FilterSelect label="Bucket" value={state.dpd_bucket} onChange={(v) => update({ dpd_bucket: v })} options={BUCKETS} />
              <FilterSelect label="Data" value={state.sync_state} onChange={(v) => update({ sync_state: v })} options={SYNC_STATES} />
              {!!banks.data?.length && (
                <FilterSelect label="Bank" value={state.bank_org_id} onChange={(v) => update({ bank_org_id: v, branch_unit_id: undefined })}
                  options={banks.data.map((b) => ({ value: b.id, label: b.name }))} />
              )}
              {!!branches.length && (
                <FilterSelect label="Branch" value={state.branch_unit_id} onChange={(v) => update({ branch_unit_id: v })}
                  options={branches.map((u) => ({ value: u.id, label: u.name }))} />
              )}
              {!!colleges.data?.length && (
                <FilterSelect label="College" value={state.college_org_id} onChange={(v) => update({ college_org_id: v })}
                  options={colleges.data.map((c) => ({ value: c.id, label: c.name }))} />
              )}
              <Input aria-label="Cohort year" placeholder="Cohort" inputMode="numeric" className="w-24" value={state.cohort ?? ""}
                onChange={(e) => update({ cohort: e.target.value.replace(/\D/g, "").slice(0, 4) })} />
              <label className="flex items-center gap-1 text-xs text-muted-foreground">Due from
                <Input type="date" className="w-[150px]" value={state.due_from ?? ""} onChange={(e) => update({ due_from: e.target.value })} /></label>
              <label className="flex items-center gap-1 text-xs text-muted-foreground">to
                <Input type="date" className="w-[150px]" value={state.due_to ?? ""} onChange={(e) => update({ due_to: e.target.value })} /></label>
            </FilterBar>
            <DataTable columns={cols} rows={acc.data?.items} loading={acc.isLoading} error={acc.error} onRetry={() => acc.refetch()} rowKey={(r) => r.id}
              onRowClick={(r) => nav(`/loans/${r.id}`)} sort={state.sort} onSort={(s) => update({ sort: s })} caption="Repayment accounts" />
            {acc.data && (
              <Pagination page={acc.data.page} size={acc.data.size} total={acc.data.total}
                onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />
            )}
          </Card>
        </TabsContent>
        <TabsContent value="upcoming"><Card><InstTable rows={o?.upcoming ?? []} restricted={restricted} empty="No instalments due in the next 30 days" /></Card></TabsContent>
        <TabsContent value="overdue"><Card><LoanMiniTable rows={o?.recently_overdue ?? []} mode="overdue" empty="No overdue accounts in scope" /></Card></TabsContent>
        <TabsContent value="partial">
          <Card>
            <p className="border-b px-4 py-2 text-xs text-muted-foreground">A partial payment does not satisfy an instalment unless the bank allocation confirms it (BR-04).</p>
            <InstTable rows={o?.partial_payments ?? []} restricted={restricted} empty="No partially paid instalments" />
          </Card>
        </TabsContent>
        <TabsContent value="reversals"><Card><ReversalTable rows={o?.reversals ?? []} restricted={restricted} /></Card></TabsContent>
        <TabsContent value="stale">
          <Card>
            <p className="border-b px-4 py-2 text-xs text-muted-foreground">
              Stale or failed bank data is shown as UNKNOWN. It is never treated as paid, unpaid or zero, and it never creates a delinquency finding (FR-REP-06).
            </p>
            <LoanMiniTable rows={o?.stale ?? []} mode="stale" empty="All linked loans have current bank data" />
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
