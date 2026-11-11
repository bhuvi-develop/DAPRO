import { Link } from "react-router-dom";
import { DataTable, type Column } from "@/components/data/table";
import { EmptyState } from "@/components/data/states";
import { FreshnessBadge, Money, StatusBadge } from "@/components/data/status";
import { formatDate, formatDateTime, relativeTime } from "@/lib/utils";
import type { LoanItem } from "./shared";

export interface InstRow { loan_id: string; bank_loan_ref: string; student_name: string; student_id: string; instalment_no: number; due_date: string; amount_due: string | null; bank_allocated: string | null; status: string; dpd: number | null }
export interface RevRow { loan_id: string; bank_loan_ref: string; bank_txn_ref: string; reverses: string | null; posted_on: string; amount: string | null; reason: string | null }
export interface Overview {
  as_of_date: string; freshness: { source: string; oldest_as_of: string | null; latest_as_of: string | null };
  status_counts: Record<string, number>; bucket_counts: Record<string, number>; unknown_note: string;
  upcoming: InstRow[]; partial_payments: InstRow[]; recently_overdue: LoanItem[]; stale: LoanItem[]; reversals: RevRow[]; reconciliation_open: number;
}

const loanLink = (id: string, ref: string) => <Link className="font-mono text-xs text-primary hover:underline" to={`/loans/${id}`}>{ref}</Link>;

export function InstTable({ rows, restricted, empty }: { rows: InstRow[]; restricted: boolean; empty: string }) {
  const cols: Column<InstRow>[] = [
    { key: "b", header: "Borrower", cell: (r) => <Link className="font-medium hover:text-primary" to={`/students/${r.student_id}`}>{r.student_name}</Link> },
    { key: "ref", header: "Loan", cell: (r) => loanLink(r.loan_id, r.bank_loan_ref) },
    { key: "no", header: "Instalment", cell: (r) => <span className="num">#{r.instalment_no}</span> },
    { key: "due", header: "Due", cell: (r) => formatDate(r.due_date) },
    { key: "amt", header: "Due amount", className: "text-right", headerClassName: "text-right", cell: (r) => <Money value={r.amount_due} restricted={restricted} precise /> },
    { key: "al", header: "Bank allocated", className: "text-right", headerClassName: "text-right", cell: (r) => <Money value={r.bank_allocated} restricted={restricted} precise /> },
    { key: "st", header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
  ];
  return <DataTable dense columns={cols} rows={rows} rowKey={(r) => r.loan_id + r.instalment_no} empty={<EmptyState title={empty} />} />;
}

export function LoanMiniTable({ rows, mode, empty }: { rows: LoanItem[]; mode: "overdue" | "stale"; empty: string }) {
  const cols: Column<LoanItem>[] = [
    { key: "b", header: "Borrower", cell: (r) => <span className="font-medium">{r.student_name}</span> },
    { key: "ref", header: "Loan", cell: (r) => loanLink(r.id, r.bank_loan_ref) },
    mode === "overdue"
      ? { key: "dpd", header: "DPD", cell: (r) => <span className="num font-semibold text-danger">{r.dpd ?? "-"}</span> }
      : { key: "sync", header: "Data state", cell: (r) => <StatusBadge status={r.sync_state} /> },
    mode === "overdue"
      ? { key: "ovd", header: "Overdue", className: "text-right", headerClassName: "text-right", cell: (r) => <Money value={r.overdue_amount} restricted={r.financial_restricted} /> }
      : { key: "last", header: "Last synchronized", cell: (r) => <span className="text-xs">{r.last_synced_at ? `${formatDateTime(r.last_synced_at)} (${relativeTime(r.last_synced_at)})` : "never"}</span> },
    { key: "f", header: "Source", cell: (r) => <FreshnessBadge f={r.freshness} compact /> },
  ];
  return <DataTable dense columns={cols} rows={rows} rowKey={(r) => r.id} empty={<EmptyState title={empty} />} />;
}

export function ReversalTable({ rows, restricted }: { rows: RevRow[]; restricted: boolean }) {
  const cols: Column<RevRow>[] = [
    { key: "p", header: "Posted", cell: (r) => formatDate(r.posted_on) },
    { key: "ref", header: "Loan", cell: (r) => loanLink(r.loan_id, r.bank_loan_ref) },
    { key: "t", header: "Reversal ref", cell: (r) => <span className="font-mono text-xs">{r.bank_txn_ref}</span> },
    { key: "o", header: "Reverses", cell: (r) => <span className="font-mono text-xs">{r.reverses ?? "-"}</span> },
    { key: "a", header: "Amount", className: "text-right", headerClassName: "text-right", cell: (r) => <Money value={r.amount} restricted={restricted} precise className="text-danger" /> },
    { key: "why", header: "Bank reason", cell: (r) => <span className="text-xs text-muted-foreground">{r.reason ?? "-"}</span> },
  ];
  return <DataTable dense columns={cols} rows={rows} rowKey={(r) => r.bank_txn_ref} empty={<EmptyState title="No reversals received from the bank" />} />;
}
