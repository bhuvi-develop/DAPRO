import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { MessageSquarePlus, MessageSquareWarning } from "lucide-react";
import { get, type Page } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { DataTable, Pagination, type Column } from "@/components/data/table";
import { FilterBar, FilterSelect, SearchInput } from "@/components/data/filters";
import { EmptyState } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { useUrlState } from "@/hooks/useUrlState";
import { cn, formatDate, formatDateTime, qs } from "@/lib/utils";
import { NewGrievanceDialog } from "./GrievanceDialogs";
import { GRV_CATEGORIES, GRV_STATUSES, type Grievance } from "./types";

const DEFAULTS = { status: "open", category: undefined, owner_id: undefined, q: undefined, sort: undefined };

/** Grievance and correction queue (FR-GRV-01..03, UC-33). Scope is enforced by the API. */
export default function GrievancesPage() {
  const can = useCan();
  const nav = useNavigate();
  const [creating, setCreating] = React.useState(false);
  const { state, update, page, size } = useUrlState<Record<string, string | undefined>>(DEFAULTS);
  const params = { ...state, page, size };
  const q = useQuery({ queryKey: ["grievances", params], queryFn: () => get<Page<Grievance>>(`/grievances${qs(params)}`) });
  const active = ["category", "owner_id", "q"].filter((k) => state[k]).length + (state.status !== "open" ? 1 : 0);
  const cols: Column<Grievance>[] = [
    { key: "ref", header: "Reference", cell: (r) => <div><p className="font-mono text-xs font-medium">{r.ref}</p><p className="text-[11px] text-muted-foreground">{labelFor(r.channel)}</p></div> },
    { key: "subject", header: "Subject", cell: (r) => <div className="max-w-[320px]"><p className="truncate font-medium">{r.subject}</p><Badge tone="outline" className="mt-1">{labelFor(r.category)}</Badge></div> },
    { key: "student", header: "Borrower", cell: (r) => <div><Link onClick={(e) => e.stopPropagation()} to={`/students/${r.student_id}`} className="font-medium hover:text-primary">{r.student_name}</Link><p className="font-mono text-[11px] text-muted-foreground">{r.dapro_ref}</p></div> },
    { key: "status", header: "Status", cell: (r) => <div className="flex flex-wrap gap-1"><StatusBadge status={r.status} />{r.priority !== "MEDIUM" && <StatusBadge status={r.priority} />}</div> },
    { key: "owner", header: "Owner", hideOnMobile: true, cell: (r) => r.owner_name ?? <span className="text-xs text-warning">Unassigned</span> },
    { key: "due_on", header: "Due", sortable: true, cell: (r) => <span className={cn("text-xs", r.overdue && "font-semibold text-danger")}>{formatDate(r.due_on)}{r.overdue ? " (overdue)" : ""}</span> },
    { key: "created_at", header: "Received", sortable: true, hideOnMobile: true, cell: (r) => <span className="text-xs">{formatDateTime(r.created_at)}</span> },
  ];
  return (
    <div>
      <PageHeader title="Grievances and corrections" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Grievances" }]}
        description="Borrower complaints, disputes and correction requests, tracked against the service-level target. A disputed case is paused until its grievance is resolved."
        actions={can("grievance:create") && <Button onClick={() => setCreating(true)}><MessageSquarePlus />Record grievance</Button>} />
      <Card>
        <FilterBar active={active} onClear={() => update({ status: "open", category: null, owner_id: null, q: null })}>
          <SearchInput value={state.q} onChange={(v) => update({ q: v })} placeholder="Reference or borrower name" />
          <FilterSelect label="Status" value={state.status} onChange={(v) => update({ status: v })} allLabel="All statuses"
            options={[{ value: "open", label: "Open (not resolved)" }, ...GRV_STATUSES.map((s) => ({ value: s, label: labelFor(s) }))]} />
          <FilterSelect label="Category" value={state.category} onChange={(v) => update({ category: v })} options={GRV_CATEGORIES.map((c) => ({ value: c, label: labelFor(c) }))} />
          <FilterSelect label="Owner" value={state.owner_id} onChange={(v) => update({ owner_id: v })} options={[{ value: "me", label: "Assigned to me" }]} allLabel="Anyone" />
        </FilterBar>
        <DataTable columns={cols} rows={q.data?.items} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()} rowKey={(r) => r.id}
          onRowClick={(r) => nav(`/grievances/${r.id}`)} sort={state.sort} onSort={(s) => update({ sort: s })} caption="Grievances"
          empty={<EmptyState icon={MessageSquareWarning} title="No grievances match these filters" description="Open grievances appear here as soon as a borrower raises one in the portal or staff record one." />} />
        {q.data && <Pagination page={page} size={size} total={q.data.total} onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />}
      </Card>
      {creating && <NewGrievanceDialog onClose={() => setCreating(false)} />}
    </div>
  );
}
