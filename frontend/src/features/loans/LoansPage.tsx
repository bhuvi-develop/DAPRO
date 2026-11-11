import { Link, useNavigate } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Landmark } from "lucide-react";
import { get, type Page } from "@/api/client";
import { useCan } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { FilterBar, FilterSelect, SearchInput } from "@/components/data/filters";
import { DataTable, Pagination, type Column } from "@/components/data/table";
import { FreshnessBadge, Money, StatusBadge } from "@/components/data/status";
import { useUrlState } from "@/hooks/useUrlState";
import { formatDate, qs } from "@/lib/utils";
import { BUCKETS, DpdCell, LINK_STATUSES, MirrorBanner, REPAYMENT_STATUSES, SYNC_STATES, useOrgs, type LoanItem } from "./shared";

const DEFAULTS = {} as Record<string, string | undefined>;
const FILTER_KEYS = ["repayment_status", "dpd_bucket", "link_status", "sync_state", "bank_org_id", "college_org_id", "q"];

export default function LoansPage() {
  const nav = useNavigate();
  const can = useCan();
  const { state, update, page, size } = useUrlState(DEFAULTS);
  const banks = useOrgs("BANK");
  const colleges = useOrgs("COLLEGE");
  const params = Object.fromEntries(FILTER_KEYS.map((k) => [k, state[k]]));
  const q = useQuery({
    queryKey: ["loans", params, page, size, state.sort],
    queryFn: ({ signal }) => get<Page<LoanItem>>(`/loans${qs({ ...params, page, size, sort: state.sort })}`, signal),
    placeholderData: keepPreviousData,
  });
  const active = FILTER_KEYS.filter((k) => state[k]).length;
  const cols: Column<LoanItem>[] = [
    { key: "student_name", header: "Borrower", sortable: true, cell: (r) => (
      <div className="min-w-0"><p className="truncate font-medium">{r.student_name ?? "Unlinked"}</p><p className="font-mono text-[11px] text-muted-foreground">{r.dapro_ref ?? "-"}</p></div>) },
    { key: "bank_loan_ref", header: "Bank loan ref", sortable: true, cell: (r) => <span className="font-mono text-xs">{r.bank_loan_ref}</span> },
    { key: "bank", header: "Bank / branch", hideOnMobile: true, cell: (r) => (
      <div className="text-xs"><p>{r.bank_name ?? "-"}</p><p className="text-muted-foreground">{r.branch_name ?? "-"}</p></div>) },
    { key: "link", header: "Link", cell: (r) => <StatusBadge status={r.link_status} /> },
    { key: "status", header: "Repayment", cell: (r) => <StatusBadge status={r.repayment_status} /> },
    { key: "dpd", header: "DPD", sortable: true, cell: (r) => <DpdCell dpd={r.dpd} bucket={r.dpd_bucket} restricted={r.financial_restricted} /> },
    { key: "overdue_amount", header: "Overdue", sortable: true, className: "text-right", headerClassName: "text-right",
      cell: (r) => <Money value={r.overdue_amount} restricted={r.financial_restricted} /> },
    { key: "next_due_date", header: "Next due", sortable: true, hideOnMobile: true, cell: (r) => <span className="text-xs">{formatDate(r.next_due_date)}</span> },
    { key: "fresh", header: "Data", hideOnMobile: true, cell: (r) => <FreshnessBadge f={r.freshness} compact /> },
  ];
  return (
    <div className="space-y-4">
      <PageHeader title="Loan accounts" description="Bank-owned education loan accounts linked to DAPRO students, mirrored from the bank feed."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Loan accounts" }]}
        actions={can("loan:link") && <Button asChild><Link to="/loans/link"><Landmark />Link a bank loan</Link></Button>} />
      <MirrorBanner />
      <Card>
        <FilterBar active={active} onClear={() => update(Object.fromEntries(FILTER_KEYS.map((k) => [k, undefined])))}>
          <SearchInput value={state.q} onChange={(v) => update({ q: v })} placeholder="Search name or loan ref" />
          <FilterSelect label="Repayment" value={state.repayment_status} onChange={(v) => update({ repayment_status: v })} options={REPAYMENT_STATUSES} />
          <FilterSelect label="DPD bucket" value={state.dpd_bucket} onChange={(v) => update({ dpd_bucket: v })} options={BUCKETS} />
          <FilterSelect label="Link" value={state.link_status} onChange={(v) => update({ link_status: v })} options={LINK_STATUSES} />
          <FilterSelect label="Data" value={state.sync_state} onChange={(v) => update({ sync_state: v })} options={SYNC_STATES} />
          {!!banks.data?.length && <FilterSelect label="Bank" value={state.bank_org_id} onChange={(v) => update({ bank_org_id: v })} options={banks.data.map((o) => ({ value: o.id, label: o.name }))} />}
          {!!colleges.data?.length && <FilterSelect label="College" value={state.college_org_id} onChange={(v) => update({ college_org_id: v })} options={colleges.data.map((o) => ({ value: o.id, label: o.name }))} />}
        </FilterBar>
        <DataTable columns={cols} rows={q.data?.items} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()}
          rowKey={(r) => r.id} onRowClick={(r) => nav(`/loans/${r.id}`)} sort={state.sort} onSort={(s) => update({ sort: s })} caption="Loan accounts" />
        {q.data && <Pagination page={q.data.page} size={q.data.size} total={q.data.total} onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />}
      </Card>
    </div>
  );
}
