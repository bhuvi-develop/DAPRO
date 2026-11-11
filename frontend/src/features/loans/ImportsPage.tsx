import { useNavigate } from "react-router-dom";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { RefreshCw } from "lucide-react";
import { get, post, type Page } from "@/api/client";
import { useAuth, useCan } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { FilterBar, FilterSelect } from "@/components/data/filters";
import { DataTable, Pagination, type Column } from "@/components/data/table";
import { InlineError } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { useUrlState } from "@/hooks/useUrlState";
import { formatDateTime, formatNumber, qs } from "@/lib/utils";

export interface BatchRow { id: string; kind: string; source: string; status: string; file_name: string | null; summary: Record<string, number>;
  errors: { row?: number | null; message: string }[]; total_rows: number; applied_rows: number; duplicate_rows: number; error_rows: number;
  correlation_id: string | null; data_origin: string; started_at: string | null; finished_at: string | null; created_at: string }

const DEFAULTS = {} as Record<string, string | undefined>;
const ACTIVE = ["QUEUED", "RUNNING", "VALIDATED"];

const cols: Column<BatchRow>[] = [
  { key: "at", header: "Started", cell: (b) => <span className="text-xs">{formatDateTime(b.started_at ?? b.created_at)}</span> },
  { key: "kind", header: "Kind", cell: (b) => <span className="text-xs font-medium">{b.kind.replace(/_/g, " ")}</span> },
  { key: "src", header: "Source", cell: (b) => <div className="flex flex-wrap gap-1"><StatusBadge status={b.source.includes("MOCK") ? "MOCK" : b.source} />{b.data_origin === "DEMO" && <StatusBadge status="DEMO" dot={false} />}</div> },
  { key: "file", header: "File / feed", hideOnMobile: true, cell: (b) => <span className="font-mono text-[11px] text-muted-foreground">{b.file_name ?? "-"}</span> },
  { key: "st", header: "Status", cell: (b) => <StatusBadge status={b.status} /> },
  { key: "cnt", header: "Result", cell: (b) => (
    <span className="text-xs">{b.kind === "BANK_SYNC"
      ? `${formatNumber(b.summary?.loans_processed ?? 0)} loans, ${formatNumber(b.summary?.transactions_new ?? 0)} new txns, ${formatNumber(b.summary?.transactions_duplicate ?? 0)} duplicates`
      : `${formatNumber(b.applied_rows)} applied, ${formatNumber(b.duplicate_rows)} duplicates, ${formatNumber(b.error_rows)} errors`}</span>) },
  { key: "fin", header: "Finished", hideOnMobile: true, cell: (b) => <span className="text-xs">{formatDateTime(b.finished_at)}</span> },
];

export default function ImportsPage() {
  const nav = useNavigate();
  const can = useCan();
  const me = useAuth((s) => s.me)!;
  const qc = useQueryClient();
  const { state, update, page, size } = useUrlState(DEFAULTS);
  const q = useQuery({
    queryKey: ["imports", state.status, state.kind, page, size],
    queryFn: ({ signal }) => get<Page<BatchRow>>(`/imports${qs({ status: state.status, kind: state.kind, page, size })}`, signal),
    placeholderData: keepPreviousData,
    refetchInterval: (query) => (query.state.data?.items.some((b) => ACTIVE.includes(b.status)) ? 3000 : false),
  });
  const isBank = me.org.type === "BANK" || me.org.type === "NBFC";
  const sync = useMutation({
    mutationFn: () => post<{ status: string; batch_id?: string }>(`/banks/${me.org.id}/sync`),
    onSuccess: (r) => { toast.success(`Bank synchronization ${r.status.toLowerCase()}`); qc.invalidateQueries({ queryKey: ["imports"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); },
  });
  return (
    <div className="space-y-4">
      <PageHeader title="Bank sync and imports" description="Every synchronization and import batch, with idempotent duplicate handling and error rows. Failed syncs never change repayment status."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Bank sync and imports" }]}
        actions={can("bank:sync") && isBank && <Button onClick={() => sync.mutate()} loading={sync.isPending}><RefreshCw />Run bank sync now</Button>} />
      <InlineError error={sync.error} />
      {isBank && <p className="text-xs text-muted-foreground">The {me.org.name} feed is a MOCK bank feed in this environment. Scheduled pulls run daily at 02:00 IST.</p>}
      <Card>
        <FilterBar active={[state.status, state.kind].filter(Boolean).length} onClear={() => update({ status: undefined, kind: undefined })}>
          <FilterSelect label="Status" value={state.status} onChange={(v) => update({ status: v })} options={["QUEUED", "RUNNING", "VALIDATED", "APPLIED", "PARTIAL", "FAILED", "REJECTED"]} />
          <FilterSelect label="Kind" value={state.kind} onChange={(v) => update({ kind: v })} options={["BANK_SYNC", "STUDENT_CSV", "TRANSACTION_CSV"]} />
        </FilterBar>
        <DataTable columns={cols} rows={q.data?.items} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()} rowKey={(b) => b.id}
          onRowClick={(b) => nav(`/imports/${b.id}`)} caption="Import batches" />
        {q.data && <Pagination page={q.data.page} size={q.data.size} total={q.data.total} onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />}
      </Card>
    </div>
  );
}
