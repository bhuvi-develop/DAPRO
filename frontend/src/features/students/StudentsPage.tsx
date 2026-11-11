import { Link, useNavigate } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { FileSpreadsheet, UserPlus } from "lucide-react";
import { get, type Page } from "@/api/client";
import { useCan } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FilterBar, FilterSelect, SearchInput } from "@/components/data/filters";
import { PageHeader } from "@/components/data/layout";
import { StatusBadge } from "@/components/data/status";
import { DataTable, Pagination, type Column } from "@/components/data/table";
import { useUrlState } from "@/hooks/useUrlState";
import { formatDate, qs } from "@/lib/utils";
import { CompletionBar, fetchColleges, LIFECYCLE, VERIFICATION, type StudentRow } from "./shared";

const DEFAULTS = { q: undefined, college_org_id: undefined, lifecycle_status: undefined, verification_status: undefined,
  has_loan: undefined, cohort: undefined, completion_below: undefined, sort: undefined };
const FILTER_KEYS = ["q", "college_org_id", "lifecycle_status", "verification_status", "has_loan", "cohort", "completion_below"] as const;
const COHORTS = ["2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026"];

export default function StudentsPage() {
  const nav = useNavigate();
  const can = useCan();
  const { state, update, page, size } = useUrlState<Record<string, string | undefined>>(DEFAULTS);
  const colleges = useQuery({ queryKey: ["orgs", "COLLEGE"], queryFn: fetchColleges, staleTime: 300_000 });
  const params = { ...Object.fromEntries(FILTER_KEYS.map((k) => [k, state[k]])), sort: state.sort ?? "-created_at", page, size };
  const q = useQuery({ queryKey: ["students", params], queryFn: ({ signal }) => get<Page<StudentRow>>(`/students${qs(params)}`, signal), placeholderData: keepPreviousData });
  const active = FILTER_KEYS.filter((k) => k !== "q" && state[k]).length;

  const columns: Column<StudentRow>[] = [
    { key: "full_name", header: "Student", sortable: true, cell: (s) => (
      <div className="min-w-0"><Link to={`/students/${s.id}`} onClick={(e) => e.stopPropagation()} className="font-medium hover:text-primary">{s.full_name}</Link>
        <p className="font-mono text-[11px] text-muted-foreground">{s.dapro_ref} - {s.college_student_id}</p></div>) },
    { key: "college", header: "College", hideOnMobile: true, cell: (s) => <span className="text-sm">{s.college_name ?? "-"}</span> },
    { key: "lifecycle_status", header: "Lifecycle", sortable: true, cell: (s) => <StatusBadge status={s.lifecycle_status} /> },
    { key: "profile_completion", header: "Profile", sortable: true, cell: (s) => <CompletionBar value={s.profile_completion} /> },
    { key: "loans", header: "Loans", className: "num", cell: (s) => s.loan_count },
    { key: "verification_status", header: "Identity", hideOnMobile: true, cell: (s) => <StatusBadge status={s.verification_status} /> },
    { key: "created_at", header: "Registered", sortable: true, hideOnMobile: true, cell: (s) => <span className="text-xs text-muted-foreground">{formatDate(s.created_at)}</span> },
  ];

  return (
    <div>
      <PageHeader title="Students" description="Every student has one DAPRO identity, independent of college and bank identifiers (FR-STU-01)."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Students" }]}
        actions={<>
          {can("student:import") && <Button asChild variant="secondary"><Link to="/students/import"><FileSpreadsheet />Import CSV</Link></Button>}
          {can("student:write") && <Button asChild><Link to="/students/new"><UserPlus />Register student</Link></Button>}
        </>} />
      <Card>
        <FilterBar active={active} onClear={() => update(Object.fromEntries(FILTER_KEYS.map((k) => [k, undefined])))}>
          <SearchInput value={state.q} onChange={(v) => update({ q: v })} placeholder="Name, DAPRO ref or college ID" />
          <FilterSelect label="College" value={state.college_org_id} onChange={(v) => update({ college_org_id: v })}
            options={(colleges.data ?? []).map((c) => ({ value: c.id, label: c.name }))} />
          <FilterSelect label="Lifecycle" value={state.lifecycle_status} onChange={(v) => update({ lifecycle_status: v })} options={LIFECYCLE} />
          <FilterSelect label="Identity" value={state.verification_status} onChange={(v) => update({ verification_status: v })} options={VERIFICATION} />
          <FilterSelect label="Loan" value={state.has_loan} onChange={(v) => update({ has_loan: v })} options={[{ value: "true", label: "Has linked loan" }, { value: "false", label: "No loan" }]} />
          <FilterSelect label="Cohort" value={state.cohort} onChange={(v) => update({ cohort: v })} options={COHORTS.map((c) => ({ value: c, label: c }))} />
          <FilterSelect label="Profile" value={state.completion_below} onChange={(v) => update({ completion_below: v })} allLabel="Any completeness"
            options={[{ value: "50", label: "Below 50%" }, { value: "80", label: "Below 80%" }, { value: "100", label: "Incomplete" }]} />
        </FilterBar>
        <DataTable columns={columns} rows={q.data?.items} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()}
          rowKey={(s) => s.id} onRowClick={(s) => nav(`/students/${s.id}`)} sort={params.sort} onSort={(s) => update({ sort: s })} caption="Students" />
        {q.data && <Pagination page={page} size={size} total={q.data.total} onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />}
      </Card>
    </div>
  );
}
