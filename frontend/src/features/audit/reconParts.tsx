import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/data/status";
import { formatDate, formatDateTime, formatINR, titleCase } from "@/lib/utils";

/* eslint-disable @typescript-eslint/no-explicit-any */
export type Row = Record<string, any>;

export function Section({ n, title, source, children }: { n: number; title: string; source?: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card className="break-inside-avoid print:shadow-none">
      <CardHeader>
        <CardTitle><span className="mr-2 text-muted-foreground">{n}.</span>{title}</CardTitle>
        {source && <span className="text-[11px] text-muted-foreground">{source}</span>}
      </CardHeader>
      <CardContent className="p-0">{children}</CardContent>
    </Card>
  );
}

const STATUS_KEYS = new Set(["status", "outcome", "severity", "verification", "review_status", "decision", "kind", "link_status", "sync_state", "bank_status"]);
const MONEY_KEYS = new Set(["amount", "overdue_amount", "principal_outstanding"]);
const DATE_KEYS = /(^at$|_at$|_on$|date$|^from$)/;

export function fmt(k: string, v: any): React.ReactNode {
  if (v === null || v === undefined || v === "") return <span className="text-muted-foreground">-</span>;
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (STATUS_KEYS.has(k) && typeof v === "string") return <StatusBadge status={v} />;
  if (MONEY_KEYS.has(k)) return <span className="num">{formatINR(v, { precise: true })}</span>;
  if (DATE_KEYS.test(k) && typeof v === "string") return v.length > 10 ? formatDateTime(v) : formatDate(v);
  if (typeof v === "object") return <code className="break-all text-[10px]">{JSON.stringify(v)}</code>;
  return String(v);
}

export function MiniTable({ rows, keys, empty = "None recorded" }: { rows: Row[] | null | undefined; keys: string[]; empty?: string }) {
  if (!rows?.length) return <p className="px-5 py-4 text-sm text-muted-foreground">{empty}</p>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead><tr className="border-b bg-muted/50">{keys.map((k) => <th key={k} className="px-4 py-2 text-left font-semibold uppercase tracking-wide text-muted-foreground">{titleCase(k)}</th>)}</tr></thead>
        <tbody className="divide-y">{rows.map((r, i) => <tr key={i}>{keys.map((k) => <td key={k} className="px-4 py-2 align-top">{fmt(k, r[k])}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export function Props({ obj, keys }: { obj: Row | null | undefined; keys?: string[] }) {
  if (!obj) return <p className="px-5 py-4 text-sm text-muted-foreground">Not available</p>;
  const ks = keys ?? Object.keys(obj).filter((k) => k !== "id");
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-3 px-5 py-4 sm:grid-cols-2 lg:grid-cols-3">
      {ks.map((k) => <div key={k}><dt className="text-[11px] font-medium text-muted-foreground">{titleCase(k)}</dt><dd className="mt-0.5 text-sm">{fmt(k, obj[k])}</dd></div>)}
    </dl>
  );
}
