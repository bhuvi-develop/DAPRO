import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRightLeft } from "lucide-react";
import { get } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { NativeSelect } from "@/components/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/menu";
import { DataTable, type Column } from "@/components/data/table";
import { EmptyState } from "@/components/data/states";
import { FreshnessBadge, Money, StatusBadge, type Freshness } from "@/components/data/status";
import { formatDate, formatDateTime } from "@/lib/utils";

interface Inst { no: number; due_date: string; amount_due: string | null; principal: string | null; interest: string | null; bank_allocated: string | null; bank_status: string | null; status: string; dpd: number | null }
interface Sched { freshness: Freshness; versions: { id: string; version: number; schedule_ref: string; reason: string; effective_from: string; is_current: boolean; received_at: string; source: string }[]; instalments: Inst[] }
interface Txn { id: string; bank_txn_ref: string; posted_on: string; value_on: string | null; amount: string | null; kind: string; channel: string | null; payment_reference: string | null; reverses_txn_ref: string | null; reversed_by: string | null; allocations: { instalment_no: number; amount: string }[]; allocated: boolean; source: string }
interface Snap { id: string; as_of: string; principal_outstanding: string | null; interest_charges: string | null; overdue_amount: string | null; total_due: string | null; bank_dpd: number | null; bank_status: string | null; source: string }

export function ScheduleTab({ loanId, restricted }: { loanId: string; restricted: boolean }) {
  const q = useQuery({ queryKey: ["loan-schedule", loanId], queryFn: () => get<Sched>(`/loans/${loanId}/schedule`) });
  const [only, setOnly] = React.useState("all");
  const rows = (q.data?.instalments ?? []).filter((i) => only === "all" || (only === "due" ? i.status !== "UPCOMING" : i.status === only));
  const cols: Column<Inst>[] = [
    { key: "no", header: "#", cell: (r) => <span className="num">{r.no}</span> },
    { key: "due", header: "Due date", cell: (r) => formatDate(r.due_date) },
    { key: "amt", header: "Instalment", className: "text-right", headerClassName: "text-right", cell: (r) => <Money value={r.amount_due} restricted={restricted} precise /> },
    { key: "alloc", header: "Bank allocated", className: "text-right", headerClassName: "text-right", cell: (r) => <Money value={r.bank_allocated} restricted={restricted} precise /> },
    { key: "bank", header: "Bank status", hideOnMobile: true, cell: (r) => <span className="text-xs text-muted-foreground">{r.bank_status ?? "-"}</span> },
    { key: "status", header: "Display status", cell: (r) => <StatusBadge status={r.status} /> },
    { key: "dpd", header: "DPD", cell: (r) => (r.dpd ? <span className="num font-semibold text-danger">{r.dpd}</span> : <span className="text-muted-foreground">-</span>) },
  ];
  if (!q.isLoading && !q.error && !q.data?.versions.length) {
    return <EmptyState title="No repayment schedule received from the bank yet" description="The loan may still be in moratorium. Status shows NOT_STARTED, never paid or overdue." />;
  }
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2 px-1">
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
          {q.data?.versions.map((v) => <Badge key={v.id} tone={v.is_current ? "info" : "neutral"}>v{v.version} {v.reason}{v.is_current ? " (current)" : ""} from {formatDate(v.effective_from)}</Badge>)}
          {q.data && <FreshnessBadge f={q.data.freshness} />}
        </div>
        <NativeSelect aria-label="Instalment filter" className="w-auto" value={only} onChange={(e) => setOnly(e.target.value)}>
          <option value="all">All instalments</option><option value="due">Due to date</option><option value="OVERDUE">Overdue</option>
          <option value="PARTIALLY_PAID">Partially paid</option><option value="UPCOMING">Upcoming</option>
        </NativeSelect>
      </div>
      <p className="px-1 text-[11px] text-muted-foreground">Display status uses the bank schedule and the bank-supplied allocation only. Partial payments never count as full satisfaction (BR-04).</p>
      <DataTable dense columns={cols} rows={rows} loading={q.isLoading} error={q.error} rowKey={(r) => String(r.no)} caption="Repayment schedule" />
    </div>
  );
}

export function SnapshotsTab({ loanId }: { loanId: string }) {
  const q = useQuery({ queryKey: ["loan-snaps", loanId], queryFn: () => get<{ items: Snap[] }>(`/loans/${loanId}/snapshots`) });
  const cols: Column<Snap>[] = [
    { key: "asof", header: "As of", cell: (r) => formatDateTime(r.as_of) },
    { key: "out", header: "Principal outstanding", className: "text-right", headerClassName: "text-right", cell: (r) => <Money value={r.principal_outstanding} /> },
    { key: "ovd", header: "Overdue", className: "text-right", headerClassName: "text-right", cell: (r) => <Money value={r.overdue_amount} /> },
    { key: "due", header: "Total due", className: "text-right", headerClassName: "text-right", cell: (r) => <Money value={r.total_due} /> },
    { key: "dpd", header: "Bank DPD", cell: (r) => <span className="num">{r.bank_dpd ?? "-"}</span> },
    { key: "st", header: "Bank status", cell: (r) => <StatusBadge status={r.bank_status} /> },
    { key: "src", header: "Source", hideOnMobile: true, cell: (r) => <span className="text-xs text-muted-foreground">{r.source}</span> },
  ];
  return <DataTable dense columns={cols} rows={q.data?.items} loading={q.isLoading} error={q.error} rowKey={(r) => r.id} caption="Bank snapshots" />;
}

function KindCell({ r }: { r: Txn }) {
  return (
    <div className="space-y-0.5">
      {r.kind === "REVERSAL" ? <StatusBadge status="REVERSAL" dot={false} /> : r.allocated ? <Badge tone="success">Payment</Badge> : <Badge tone="warning">Payment - unallocated</Badge>}
      {r.reverses_txn_ref && <p className="flex items-center gap-1 text-[11px] text-danger"><ArrowRightLeft className="h-3 w-3" />reverses {r.reverses_txn_ref}</p>}
      {r.reversed_by && <p className="text-[11px] text-danger">reversed by {r.reversed_by}</p>}
    </div>
  );
}

function AllocCell({ r }: { r: Txn }) {
  if (!r.allocations.length) return <span className="text-xs text-muted-foreground">-</span>;
  return (
    <Popover>
      <PopoverTrigger className="text-xs font-medium text-primary hover:underline">{r.allocations.length} instalment(s)</PopoverTrigger>
      <PopoverContent className="w-56 p-3">
        <p className="mb-2 text-xs font-semibold">Bank-supplied allocation</p>
        <ul className="space-y-1 text-xs">{r.allocations.map((a) => <li key={a.instalment_no + a.amount} className="flex justify-between"><span>Instalment {a.instalment_no}</span><Money value={a.amount} precise /></li>)}</ul>
      </PopoverContent>
    </Popover>
  );
}

export function TransactionsTab({ loanId, restricted }: { loanId: string; restricted: boolean }) {
  const q = useQuery({ queryKey: ["loan-txns", loanId], queryFn: () => get<{ freshness: Freshness; items: Txn[] }>(`/loans/${loanId}/transactions`) });
  const cols: Column<Txn>[] = [
    { key: "posted", header: "Posted", cell: (r) => formatDate(r.posted_on) },
    { key: "value", header: "Value date", hideOnMobile: true, cell: (r) => formatDate(r.value_on) },
    { key: "ref", header: "Bank txn ref", cell: (r) => <span className="font-mono text-xs">{r.bank_txn_ref}</span> },
    { key: "kind", header: "Kind", cell: (r) => <KindCell r={r} /> },
    { key: "channel", header: "Channel / ref", hideOnMobile: true, cell: (r) => <span className="text-xs">{r.channel ?? "-"}<br /><span className="text-muted-foreground">{r.payment_reference ?? ""}</span></span> },
    { key: "amount", header: "Amount", className: "text-right", headerClassName: "text-right", cell: (r) => <Money value={r.amount} restricted={restricted} precise className={r.kind === "REVERSAL" ? "text-danger" : undefined} /> },
    { key: "alloc", header: "Allocation", cell: (r) => <AllocCell r={r} /> },
  ];
  return (
    <div className="space-y-3">
      {q.data && <div className="px-1"><FreshnessBadge f={q.data.freshness} /></div>}
      <DataTable dense columns={cols} rows={q.data?.items} loading={q.isLoading} error={q.error} rowKey={(r) => r.id} caption="Bank transactions"
        empty={<EmptyState title="No bank transactions received" description="No payment data is not the same as no payment: absence never creates a delinquency finding." />} />
    </div>
  );
}
