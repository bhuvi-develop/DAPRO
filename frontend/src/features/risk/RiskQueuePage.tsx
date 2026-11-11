import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Info, PlayCircle } from "lucide-react";
import { get, post, type Page } from "@/api/client";
import { useCan } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { DataTable, Pagination, type Column } from "@/components/data/table";
import { FilterBar, FilterSelect, SearchInput } from "@/components/data/filters";
import { StatusBadge, labelFor } from "@/components/data/status";
import { useUrlState } from "@/hooks/useUrlState";
import { qs, relativeTime } from "@/lib/utils";
import { CATEGORIES, NOT_A_FINDING, SEVERITIES, type Indicator } from "./types";

const DEFAULTS = { status: undefined, category: undefined, severity: undefined, rule_code: undefined, mine: undefined, q: undefined, sort: undefined };
const RULES = ["REPAYMENT_OVERDUE", "REPEATED_OVERDUE", "DATA_STALE", "ADDRESS_UPDATE_NEEDED", "CONTACT_UNSUCCESSFUL", "EMPLOYMENT_UPDATE_DUE", "MORATORIUM_ENDING", "DISPUTED_RECORD"];

export default function RiskQueuePage() {
  const nav = useNavigate();
  const can = useCan();
  const qc = useQueryClient();
  const { state, update, page, size } = useUrlState<Record<string, string | undefined>>(DEFAULTS);
  const params = { ...state, page, size };
  const q = useQuery({ queryKey: ["risk", params], queryFn: () => get<Page<Indicator>>(`/risk/indicators${qs(params)}`) });
  const run = useMutation({
    mutationFn: () => post<Record<string, number>>("/risk/run"),
    onSuccess: (s) => { toast.success(`Evaluation complete: ${s.created ?? 0} new, ${s.superseded ?? 0} superseded`); qc.invalidateQueries({ queryKey: ["risk"] }); },
    onError: (e: Error) => toast.error(e.message),
  });
  const active = ["status", "category", "severity", "rule_code", "mine", "q"].filter((k) => state[k]).length;
  const cols: Column<Indicator>[] = [
    { key: "borrower", header: "Borrower", cell: (r) => <div><p className="font-medium">{r.student_name}</p><p className="font-mono text-[11px] text-muted-foreground">{r.dapro_ref}{r.bank_loan_ref ? ` - ${r.bank_loan_ref}` : ""}</p></div> },
    { key: "title", header: "Indicator", cell: (r) => <div className="max-w-[340px]"><p className="truncate">{r.title}</p><p className="text-[11px] text-muted-foreground">{r.rule_code} v{r.rule_version}</p></div> },
    { key: "category", header: "Category", hideOnMobile: true, cell: (r) => <span className="text-xs">{labelFor(r.category)}</span> },
    { key: "severity", header: "Severity", sortable: true, cell: (r) => <StatusBadge status={r.severity} /> },
    { key: "status", header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
    { key: "assigned", header: "Reviewer", hideOnMobile: true, cell: (r) => r.assigned_to_name ?? <span className="text-muted-foreground">Unassigned</span> },
    { key: "generated_at", header: "Generated", sortable: true, hideOnMobile: true, cell: (r) => <span className="text-xs text-muted-foreground">{relativeTime(r.generated_at)}</span> },
  ];
  return (
    <div>
      <PageHeader title="Risk review queue" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Risk review" }]}
        description="Explainable rule outputs awaiting authorised human review."
        actions={can("risk:decide") && <Button variant="secondary" loading={run.isPending} onClick={() => run.mutate()}><PlayCircle />Run evaluation now</Button>} />
      <div className="mb-4 flex items-start gap-2 rounded-md border border-primary/20 bg-primary-soft px-3 py-2 text-xs text-primary"><Info className="mt-0.5 h-4 w-4 shrink-0" />{NOT_A_FINDING}</div>
      <Card>
        <FilterBar active={active} onClear={() => update({ status: null, category: null, severity: null, rule_code: null, mine: null, q: null })}>
          <SearchInput value={state.q} onChange={(v) => update({ q: v })} placeholder="Borrower, ref or title" />
          <FilterSelect label="Status" value={state.status} onChange={(v) => update({ status: v })} options={[{ value: "open", label: "Open (all active)" }, "OPEN", "IN_REVIEW", "ACTIONED", "DISMISSED", "OVERRIDDEN", "SUPERSEDED"]} />
          <FilterSelect label="Category" value={state.category} onChange={(v) => update({ category: v })} options={CATEGORIES} />
          <FilterSelect label="Severity" value={state.severity} onChange={(v) => update({ severity: v })} options={SEVERITIES} />
          <FilterSelect label="Rule" value={state.rule_code} onChange={(v) => update({ rule_code: v })} options={RULES} />
          <FilterSelect label="Reviewer" value={state.mine} onChange={(v) => update({ mine: v })} allLabel="Anyone" options={[{ value: "true", label: "Assigned to me" }]} />
        </FilterBar>
        <DataTable columns={cols} rows={q.data?.items} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()} rowKey={(r) => r.id}
          onRowClick={(r) => nav(`/risk/${r.id}`)} sort={state.sort} onSort={(s) => update({ sort: s })} caption="Risk indicators" />
        {q.data && <Pagination page={page} size={size} total={q.data.total} onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />}
      </Card>
    </div>
  );
}
