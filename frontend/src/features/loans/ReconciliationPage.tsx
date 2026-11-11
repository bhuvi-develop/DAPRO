import * as React from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { get, type Page } from "@/api/client";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { FilterBar, FilterSelect } from "@/components/data/filters";
import { DataTable, Pagination, type Column } from "@/components/data/table";
import { EmptyState } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { useUrlState } from "@/hooks/useUrlState";
import { qs, relativeTime } from "@/lib/utils";
import { ReconDrawer, type ReconItem } from "./reconDrawer";

const DEFAULTS = { status: "OPEN" } as Record<string, string | undefined>;
const KINDS = ["AMBIGUOUS_LINK", "UNMATCHED_LOAN", "DPD_MISMATCH", "UNKNOWN_TRANSACTION", "REVERSAL_REVIEW", "SYNC_FAILURE", "MISSING_AT_BANK", "DUPLICATE_REFERENCE", "SCHEDULE_MISMATCH"];

const cols: Column<ReconItem>[] = [
  { key: "kind", header: "Exception", cell: (r) => <div><p className="text-sm font-medium">{labelFor(r.kind)}</p><p className="text-xs text-muted-foreground">{r.summary}</p></div> },
  { key: "sev", header: "Severity", cell: (r) => <StatusBadge status={r.severity} /> },
  { key: "who", header: "Borrower / loan", hideOnMobile: true, cell: (r) => (
    <div className="text-xs"><p>{r.student_name ?? "-"}</p><p className="font-mono text-muted-foreground">{r.bank_loan_ref ?? (r.details?.bank_loan_ref as string) ?? "-"}</p></div>) },
  { key: "st", header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
  { key: "age", header: "Raised", cell: (r) => <span className="text-xs">{relativeTime(r.created_at)}</span> },
];

export default function ReconciliationPage() {
  const { state, update, page, size } = useUrlState(DEFAULTS);
  const [open, setOpen] = React.useState<ReconItem | null>(null);
  const q = useQuery({
    queryKey: ["recon", state.kind, state.status, state.severity, page, size],
    queryFn: ({ signal }) => get<Page<ReconItem>>(`/reconciliation${qs({ kind: state.kind, status: state.status, severity: state.severity, page, size })}`, signal),
    placeholderData: keepPreviousData,
  });
  const active = [state.kind, state.severity].filter(Boolean).length + (state.status && state.status !== "OPEN" ? 1 : 0);
  return (
    <div className="space-y-4">
      <PageHeader title="Reconciliation queue" description="Missing, conflicting, stale or ambiguous bank data routed for human review (FR-LON-06, FR-REP-08). Nothing here is resolved automatically."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Reconciliation" }]} />
      <Card>
        <FilterBar active={active} onClear={() => update({ kind: undefined, severity: undefined, status: "OPEN" })}>
          <FilterSelect label="Exception" value={state.kind} onChange={(v) => update({ kind: v })} options={KINDS} />
          <FilterSelect label="Status" value={state.status} onChange={(v) => update({ status: v || "ALL" })} options={["OPEN", "RESOLVED", "DISMISSED"]} allLabel="All" />
          <FilterSelect label="Severity" value={state.severity} onChange={(v) => update({ severity: v })} options={["HIGH", "MEDIUM", "LOW"]} />
        </FilterBar>
        <DataTable columns={cols} rows={q.data?.items} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()} rowKey={(r) => r.id}
          onRowClick={setOpen} caption="Reconciliation items" empty={<EmptyState title="No reconciliation items match" description="Bank data in scope reconciles with DAPRO records." />} />
        {q.data && <Pagination page={q.data.page} size={q.data.size} total={q.data.total} onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />}
      </Card>
      <ReconDrawer item={open} onClose={() => setOpen(null)} />
    </div>
  );
}
