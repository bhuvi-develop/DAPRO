import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { get } from "@/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { DataTable, type Column } from "@/components/data/table";
import { EmptyState, ErrorState } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { PageFallback } from "@/components/layout/AppShell";
import { formatDateTime, formatNumber, relativeTime } from "@/lib/utils";
import type { BatchRow } from "./ImportsPage";

interface Recon { id: string; kind: string; severity: string; summary: string; status: string; loan_id: string | null; created_at: string }
interface Detail extends BatchRow { reconciliation_items: Recon[] }

const reconCols: Column<Recon>[] = [
  { key: "k", header: "Kind", cell: (r) => <span className="text-xs font-medium">{labelFor(r.kind)}</span> },
  { key: "s", header: "Severity", cell: (r) => <StatusBadge status={r.severity} /> },
  { key: "sum", header: "Summary", cell: (r) => <span className="text-sm">{r.summary}</span> },
  { key: "st", header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
  { key: "l", header: "", cell: (r) => r.loan_id ? <Link className="text-xs font-medium text-primary hover:underline" to={`/loans/${r.loan_id}`}>Loan</Link> : null },
];

export default function ImportDetailPage() {
  const { id = "" } = useParams();
  const q = useQuery({ queryKey: ["import", id], queryFn: () => get<Detail>(`/imports/${id}`),
    refetchInterval: (query) => (["QUEUED", "RUNNING"].includes(query.state.data?.status ?? "") ? 3000 : false) });
  if (q.isLoading) return <PageFallback />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const b = q.data;
  const summary = Object.entries(b.summary ?? {}).map(([k, v]) => ({ label: k.replace(/_/g, " "), value: <span className="num">{formatNumber(Number(v))}</span> }));
  return (
    <div className="space-y-5">
      <PageHeader title={`${b.kind.replace(/_/g, " ")} batch`} description={b.file_name ?? undefined}
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Bank sync and imports", to: "/imports" }, { label: "Batch" }]}
        meta={<><StatusBadge status={b.status} /><StatusBadge status={b.source.includes("MOCK") ? "MOCK" : b.source} />{b.data_origin === "DEMO" && <StatusBadge status="DEMO" dot={false} />}</>} />
      <div className="grid gap-4 lg:grid-cols-2">
        <Card><CardHeader><CardTitle>Run</CardTitle></CardHeader><CardContent>
          <KeyValue items={[{ label: "Started", value: `${formatDateTime(b.started_at)} (${relativeTime(b.started_at)})` }, { label: "Finished", value: formatDateTime(b.finished_at) },
            { label: "Rows / loans", value: formatNumber(b.total_rows) }, { label: "Applied", value: formatNumber(b.applied_rows) },
            { label: "Duplicates skipped", value: formatNumber(b.duplicate_rows) }, { label: "Error rows", value: formatNumber(b.error_rows) },
            { label: "Correlation reference", value: <span className="font-mono text-[11px]">{b.correlation_id ?? "-"}</span> }]} />
        </CardContent></Card>
        <Card><CardHeader><CardTitle>Summary</CardTitle></CardHeader><CardContent>
          {summary.length ? <KeyValue items={summary} /> : <EmptyState title="No summary recorded" />}
        </CardContent></Card>
      </div>
      <Card>
        <CardHeader><CardTitle>Errors</CardTitle></CardHeader>
        {b.errors?.length ? (
          <ul className="divide-y">{b.errors.map((e, i) => <li key={i} className="px-5 py-2 text-sm"><span className="mr-2 text-xs text-muted-foreground">{e.row ? `Row ${e.row}` : "Batch"}</span>{e.message}</li>)}</ul>
        ) : <EmptyState title="No errors in this batch" />}
      </Card>
      <Card>
        <CardHeader><CardTitle>Reconciliation items raised</CardTitle><Link to="/reconciliation" className="text-xs font-medium text-primary hover:underline">Open queue</Link></CardHeader>
        <DataTable dense columns={reconCols} rows={b.reconciliation_items} rowKey={(r) => r.id} empty={<EmptyState title="No reconciliation items from this batch" />} />
      </Card>
    </div>
  );
}
