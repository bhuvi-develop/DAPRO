import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { get, type Page } from "@/api/client";
import { useCan } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { DataTable, Pagination, type Column } from "@/components/data/table";
import { FilterBar, FilterSelect, SearchInput } from "@/components/data/filters";
import { StatusBadge, labelFor } from "@/components/data/status";
import { useUrlState } from "@/hooks/useUrlState";
import { cn, formatDate, qs, relativeTime } from "@/lib/utils";
import { fetchCaseMeta, type CaseSummary } from "./types";

const DEFAULTS = { status: "open", priority: undefined, owner: undefined, category: undefined, overdue: undefined, q: undefined, sort: undefined };

export default function CasesPage() {
  const nav = useNavigate();
  const can = useCan();
  const { state, update, page, size } = useUrlState<Record<string, string | undefined>>(DEFAULTS);
  const params = { ...state, status: state.status === "all" ? undefined : state.status, page, size };
  const meta = useQuery({ queryKey: ["case-meta"], queryFn: fetchCaseMeta, staleTime: 600_000 });
  const q = useQuery({ queryKey: ["cases", params], queryFn: () => get<Page<CaseSummary>>(`/cases${qs(params)}`) });
  const active = ["priority", "owner", "category", "overdue", "q"].filter((k) => state[k]).length + (state.status !== "open" ? 1 : 0);
  const cols: Column<CaseSummary>[] = [
    { key: "case_ref", header: "Case", sortable: true, cell: (r) => <span className="font-mono text-xs font-medium">{r.case_ref}</span> },
    { key: "borrower", header: "Borrower", cell: (r) => <div><p className="font-medium">{r.student_name}</p><p className="font-mono text-[11px] text-muted-foreground">{r.bank_loan_ref ?? r.dapro_ref}</p></div> },
    { key: "category", header: "Category", hideOnMobile: true, cell: (r) => <span className="text-xs">{labelFor(r.category)}</span> },
    { key: "priority", header: "Priority", sortable: true, cell: (r) => <StatusBadge status={r.priority} /> },
    { key: "status", header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
    { key: "owner", header: "Owner", hideOnMobile: true, cell: (r) => r.owner_name ?? <span className="text-warning">Unassigned</span> },
    { key: "next_action", header: "Next action", hideOnMobile: true, cell: (r) => <span className="line-clamp-2 max-w-[220px] text-xs">{r.next_action ?? "-"}</span> },
    { key: "due_on", header: "Due", sortable: true, cell: (r) => <span className={cn("text-xs", r.overdue && "font-semibold text-danger")}>{formatDate(r.due_on)}{r.overdue && " (overdue)"}</span> },
    { key: "updated_at", header: "Updated", sortable: true, hideOnMobile: true, cell: (r) => <span className="text-xs text-muted-foreground">{relativeTime(r.updated_at)}</span> },
  ];
  return (
    <div>
      <PageHeader title="Cases" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Cases" }]}
        description="Accountable follow-up: every active case has an owner, a next action and a due date."
        actions={can("case:create") && <Button asChild><Link to="/cases/new"><Plus />New case</Link></Button>} />
      <Card>
        <FilterBar active={active} onClear={() => update({ status: "open", priority: null, owner: null, category: null, overdue: null, q: null })}>
          <SearchInput value={state.q} onChange={(v) => update({ q: v })} placeholder="Case ref, borrower or loan ref" />
          <FilterSelect label="Status" value={state.status === "all" ? "" : state.status} onChange={(v) => update({ status: v || "all" })}
            options={[{ value: "open", label: "Open (all active)" }, ...(meta.data?.statuses ?? [])]} />
          <FilterSelect label="Priority" value={state.priority} onChange={(v) => update({ priority: v })} options={meta.data?.priorities ?? ["CRITICAL", "HIGH", "MEDIUM", "LOW"]} />
          <FilterSelect label="Owner" value={state.owner} onChange={(v) => update({ owner: v })} allLabel="Anyone" options={[{ value: "me", label: "Assigned to me" }, { value: "unassigned", label: "Unassigned" }]} />
          <FilterSelect label="Category" value={state.category} onChange={(v) => update({ category: v })} options={meta.data?.categories ?? []} />
          <FilterSelect label="Due" value={state.overdue} onChange={(v) => update({ overdue: v })} allLabel="Any" options={[{ value: "true", label: "Overdue only" }]} />
        </FilterBar>
        <DataTable columns={cols} rows={q.data?.items} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()} rowKey={(r) => r.id}
          onRowClick={(r) => nav(`/cases/${r.id}`)} sort={state.sort} onSort={(s) => update({ sort: s })} caption="Cases" />
        {q.data && <Pagination page={page} size={size} total={q.data.total} onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />}
      </Card>
    </div>
  );
}
