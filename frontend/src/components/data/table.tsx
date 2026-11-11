import * as React from "react";
import { ArrowDown, ArrowUp, ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NativeSelect } from "@/components/ui/input";
import { EmptyState, ErrorState, TableSkeleton } from "@/components/data/states";
import { cn, formatNumber } from "@/lib/utils";

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  cell: (row: T) => React.ReactNode;
  className?: string;
  headerClassName?: string;
  sortable?: boolean;
  hideOnMobile?: boolean;
}

export function DataTable<T>({ columns, rows, loading, error, onRetry, onRowClick, rowKey, empty, sort, onSort, dense, caption }: {
  columns: Column<T>[]; rows?: T[]; loading?: boolean; error?: unknown; onRetry?: () => void; onRowClick?: (r: T) => void;
  rowKey: (r: T) => string; empty?: React.ReactNode; sort?: string; onSort?: (s: string) => void; dense?: boolean; caption?: string;
}) {
  if (loading) return <TableSkeleton cols={Math.min(columns.length, 6)} />;
  if (error) return <ErrorState error={error} onRetry={onRetry} />;
  if (!rows || rows.length === 0) return <>{empty ?? <EmptyState title="No records match these filters" description="Try widening the filters or clearing the search." />}</>;
  const sortKey = sort?.replace(/^-/, "");
  const desc = sort?.startsWith("-");
  return (
    <div className="overflow-x-auto scrollbar-thin">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead>
          <tr className="border-b bg-muted/50 text-left">
            {columns.map((c) => (
              <th key={c.key} scope="col" className={cn("whitespace-nowrap px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground", c.hideOnMobile && "hidden md:table-cell", c.headerClassName)}>
                {c.sortable && onSort ? (
                  <button type="button" className="inline-flex items-center gap-1 hover:text-foreground" onClick={() => onSort(sortKey === c.key && !desc ? `-${c.key}` : c.key)}>
                    {c.header}
                    {sortKey === c.key && (desc ? <ArrowDown className="h-3 w-3" /> : <ArrowUp className="h-3 w-3" />)}
                  </button>
                ) : c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y">
          {rows.map((r) => (
            <tr key={rowKey(r)} onClick={onRowClick ? () => onRowClick(r) : undefined}
              onKeyDown={onRowClick ? (e) => { if (e.key === "Enter") onRowClick(r); } : undefined}
              tabIndex={onRowClick ? 0 : undefined}
              className={cn("bg-surface transition-colors", onRowClick && "cursor-pointer hover:bg-primary-soft/60 focus-visible:bg-primary-soft/60")}>
              {columns.map((c) => (
                <td key={c.key} className={cn("px-4 align-middle", dense ? "py-2" : "py-3", c.hideOnMobile && "hidden md:table-cell", c.className)}>{c.cell(r)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Pagination({ page, size, total, onPage, onSize }: { page: number; size: number; total: number; onPage: (p: number) => void; onSize?: (s: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / size));
  const from = total === 0 ? 0 : (page - 1) * size + 1;
  const to = Math.min(total, page * size);
  return (
    <div className="flex flex-col items-center justify-between gap-3 border-t px-4 py-3 text-xs text-muted-foreground sm:flex-row">
      <span>Showing <span className="num font-medium text-foreground">{formatNumber(from)}-{formatNumber(to)}</span> of <span className="num font-medium text-foreground">{formatNumber(total)}</span></span>
      <div className="flex items-center gap-2">
        {onSize && (
          <NativeSelect aria-label="Rows per page" className="h-8 w-[96px] text-xs" value={size} onChange={(e) => onSize(Number(e.target.value))}>
            {[10, 25, 50, 100].map((n) => <option key={n} value={n}>{n} / page</option>)}
          </NativeSelect>
        )}
        <Button variant="secondary" size="icon-sm" aria-label="Previous page" disabled={page <= 1} onClick={() => onPage(page - 1)}><ChevronLeft /></Button>
        <span className="num min-w-[64px] text-center">Page {page} / {pages}</span>
        <Button variant="secondary" size="icon-sm" aria-label="Next page" disabled={page >= pages} onClick={() => onPage(page + 1)}><ChevronRight /></Button>
      </div>
    </div>
  );
}
