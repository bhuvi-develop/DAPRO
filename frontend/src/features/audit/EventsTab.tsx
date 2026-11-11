import * as React from "react";
import { Link } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { get, type Page } from "@/api/client";
import { Card } from "@/components/ui/card";
import { Dialog, SheetContent } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { FilterBar, FilterSelect, SearchInput } from "@/components/data/filters";
import { KeyValue } from "@/components/data/layout";
import { DataTable, Pagination, type Column } from "@/components/data/table";
import { StatusBadge } from "@/components/data/status";
import { useUrlState } from "@/hooks/useUrlState";
import { formatDateTime, qs, titleCase } from "@/lib/utils";

export interface AuditEvent { seq: number; id: string; occurred_at: string; actor_id: string | null; actor_label: string | null; actor_role: string | null; org_id: string | null;
  action: string; target_type: string | null; target_id: string | null; target_label: string | null; outcome: string; purpose: string | null; correlation_id: string;
  payload: Record<string, unknown>; hash: string; prev_hash: string }

const DEFAULTS = {} as Record<string, string | undefined>;
const KEYS = ["action", "target_type", "outcome", "date_from", "date_to", "q"];
const TARGETS = ["student", "loan", "case", "grievance", "user", "import_batch", "report", "export", "route", "indicator", "visit", "session"];

export function targetLink(t: string | null, id: string | null) {
  if (!t || !id) return null;
  const map: Record<string, string> = { student: "/students/", loan: "/loans/", case: "/cases/", grievance: "/grievances/", import_batch: "/imports/" };
  return map[t] ? map[t] + id : null;
}

const cols: Column<AuditEvent>[] = [
  { key: "at", header: "When", cell: (e) => <span className="text-xs">{formatDateTime(e.occurred_at)}</span> },
  { key: "actor", header: "Actor", cell: (e) => <div className="text-xs"><p className="font-medium">{e.actor_label ?? "System"}</p><p className="text-muted-foreground">{titleCase(e.actor_role)}</p></div> },
  { key: "action", header: "Action", cell: (e) => <span className="font-mono text-xs">{e.action}</span> },
  { key: "target", header: "Target", hideOnMobile: true, cell: (e) => <span className="text-xs">{e.target_type ? `${e.target_type}: ${e.target_label ?? e.target_id}` : "-"}</span> },
  { key: "outcome", header: "Outcome", cell: (e) => <StatusBadge status={e.outcome} /> },
  { key: "corr", header: "Correlation", hideOnMobile: true, cell: (e) => <span className="font-mono text-[10px] text-muted-foreground">{e.correlation_id.slice(0, 13)}</span> },
];

export function EventsTab() {
  const { state, update, page, size } = useUrlState(DEFAULTS);
  const [open, setOpen] = React.useState<AuditEvent | null>(null);
  const params = { action: state.action, target_type: state.target_type, outcome: state.outcome, q: state.q,
    date_from: state.date_from ? `${state.date_from}T00:00:00` : undefined, date_to: state.date_to ? `${state.date_to}T23:59:59` : undefined };
  const q = useQuery({
    queryKey: ["audit-events", params, page, size],
    queryFn: ({ signal }) => get<Page<AuditEvent>>(`/audit/events${qs({ ...params, page, size })}`, signal),
    placeholderData: keepPreviousData,
  });
  const link = open ? targetLink(open.target_type, open.target_id) : null;
  return (
    <Card>
      <FilterBar active={KEYS.filter((k) => state[k]).length} onClear={() => update(Object.fromEntries(KEYS.map((k) => [k, undefined])))}>
        <SearchInput value={state.q} onChange={(v) => update({ q: v })} placeholder="Search actor or target" />
        <Input aria-label="Action prefix" placeholder="Action prefix, e.g. loan." className="w-full sm:w-48" value={state.action ?? ""} onChange={(e) => update({ action: e.target.value })} />
        <FilterSelect label="Target" value={state.target_type} onChange={(v) => update({ target_type: v })} options={TARGETS} />
        <FilterSelect label="Outcome" value={state.outcome} onChange={(v) => update({ outcome: v })} options={["SUCCESS", "DENIED", "FAILURE"]} />
        <Input type="date" aria-label="From date" className="w-[150px]" value={state.date_from ?? ""} onChange={(e) => update({ date_from: e.target.value })} />
        <Input type="date" aria-label="To date" className="w-[150px]" value={state.date_to ?? ""} onChange={(e) => update({ date_to: e.target.value })} />
      </FilterBar>
      <DataTable dense columns={cols} rows={q.data?.items} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()} rowKey={(e) => e.id} onRowClick={setOpen} caption="Audit events" />
      {q.data && <Pagination page={q.data.page} size={q.data.size} total={q.data.total} onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />}
      <Dialog open={!!open} onOpenChange={(o) => !o && setOpen(null)}>
        {open && (
          <SheetContent title={open.action} description={`Sequence ${open.seq} - read-only evidence`}>
            <div className="space-y-5 p-5">
              <KeyValue items={[{ label: "Occurred", value: formatDateTime(open.occurred_at) }, { label: "Outcome", value: <StatusBadge status={open.outcome} /> },
                { label: "Actor", value: `${open.actor_label ?? "System"} (${titleCase(open.actor_role)})` }, { label: "Purpose", value: open.purpose ?? "-" },
                { label: "Target", value: link ? <Link className="text-primary hover:underline" to={link}>{open.target_label ?? open.target_id}</Link> : `${open.target_type ?? "-"} ${open.target_label ?? open.target_id ?? ""}` },
                { label: "Correlation ID", value: <span className="font-mono text-[11px]">{open.correlation_id}</span> }]} />
              <div><p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Payload</p>
                <pre className="max-h-72 overflow-auto rounded-md bg-muted p-3 text-[11px] scrollbar-thin">{JSON.stringify(open.payload, null, 2)}</pre></div>
              <div><p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Hash chain</p>
                <p className="break-all font-mono text-[10px] text-muted-foreground">prev {open.prev_hash}</p>
                <p className="break-all font-mono text-[10px]">hash {open.hash}</p>
                <p className="mt-2 text-[11px] text-muted-foreground">Audit events are append-only. No role can edit or delete them (FR-AUD-03).</p></div>
            </div>
          </SheetContent>
        )}
      </Dialog>
    </Card>
  );
}
