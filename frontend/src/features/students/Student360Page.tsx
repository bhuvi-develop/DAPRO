import * as React from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Briefcase, GraduationCap, History, Landmark, LayoutGrid, MapPin, Pencil, ShieldAlert } from "lucide-react";
import { get } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/menu";
import { PageHeader } from "@/components/data/layout";
import { ErrorState } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { DataTable } from "@/components/data/table";
import { PageFallback } from "@/components/layout/AppShell";
import { formatDateTime, relativeTime, titleCase } from "@/lib/utils";
import { EditStudentDialog } from "./dialogs";
import type { FieldChange, Profile } from "./profileTypes";
import { CompletionRing } from "./shared";
import { ContactTab, LifecycleTab, LoansTab, OperationsTab, OverviewTab } from "./tabs360";

function HistoryTab({ id }: { id: string }) {
  const q = useQuery({ queryKey: ["student-history", id], queryFn: () => get<FieldChange[]>(`/students/${id}/history`) });
  return (
    <Card>
      <DataTable rows={q.data} loading={q.isLoading} error={q.error} rowKey={(r) => r.id} caption="Correction history"
        empty={<p className="p-6 text-center text-sm text-muted-foreground">No corrections recorded. Every future change keeps the previous value, actor and reason.</p>}
        columns={[
          { key: "at", header: "When", cell: (r) => <span className="text-xs">{formatDateTime(r.created_at)}</span> },
          { key: "field", header: "Field", cell: (r) => titleCase(r.field) },
          { key: "old", header: "Previous value", cell: (r) => <span className="text-muted-foreground line-through decoration-muted-foreground/50">{r.old_value ?? "-"}</span> },
          { key: "new", header: "New value", cell: (r) => r.new_value ?? "-" },
          { key: "reason", header: "Reason", cell: (r) => <span className="text-xs">{r.reason}</span> },
          { key: "source", header: "Source", hideOnMobile: true, cell: (r) => <span className="text-xs">{titleCase(r.source)}</span> },
        ]} />
    </Card>
  );
}

export default function Student360Page() {
  const { id = "" } = useParams();
  const can = useCan();
  const [edit, setEdit] = React.useState(false);
  const q = useQuery({ queryKey: ["student360", id], queryFn: () => get<Profile>(`/students/${id}/profile`) });
  if (q.isLoading) return <PageFallback />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const p = q.data;
  const s = p.student;
  const opsCount = (p.cases?.length ?? 0) + (p.risk_indicators?.length ?? 0) + (p.grievances?.length ?? 0);
  return (
    <div className="space-y-5">
      <PageHeader title="Student 360" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Students", to: "/students" }, { label: s.dapro_ref }]} className="mb-0" />
      <Card className="p-5">
        <div className="flex flex-col gap-5 md:flex-row md:items-center">
          <CompletionRing value={p.completion.percent} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold" data-testid="student-name">{s.full_name}</h2>
              <StatusBadge status={s.lifecycle_status} /><StatusBadge status={s.verification_status} />
              {s.data_origin === "DEMO" && <Badge tone="warning">Demo record</Badge>}
            </div>
            <p className="mt-1 flex flex-wrap gap-x-3 font-mono text-xs text-muted-foreground"><span>{s.dapro_ref}</span><span>{s.college_name} - {s.college_student_id}</span>{s.campus_name && <span className="font-sans">{s.campus_name}</span>}</p>
            <p className="mt-1 text-[11px] text-muted-foreground">Source {titleCase(s.source)} - updated {relativeTime(s.updated_at)} - version {s.version}</p>
            {p.pending_actions.length > 0 && <div className="mt-2 flex flex-wrap gap-1.5">{p.pending_actions.slice(0, 4).map((a, i) => <Badge key={i} tone="warning"><ShieldAlert className="h-3 w-3" />{a.label}</Badge>)}
              {p.pending_actions.length > 4 && <Badge tone="neutral">+{p.pending_actions.length - 4} more</Badge>}</div>}
          </div>
          {can("student:write") && <Button variant="secondary" onClick={() => setEdit(true)}><Pencil />Correct record</Button>}
        </div>
      </Card>
      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview"><LayoutGrid />Overview</TabsTrigger>
          <TabsTrigger value="loans"><Landmark />Loans and repayment{p.loans ? ` (${p.loans.length})` : ""}</TabsTrigger>
          <TabsTrigger value="contact"><MapPin />Contact and address</TabsTrigger>
          <TabsTrigger value="lifecycle"><GraduationCap />Academic and employment</TabsTrigger>
          <TabsTrigger value="ops"><Briefcase />Cases, risk and grievances{opsCount ? ` (${opsCount})` : ""}</TabsTrigger>
          <TabsTrigger value="history"><History />Correction history</TabsTrigger>
        </TabsList>
        <TabsContent value="overview"><OverviewTab p={p} /></TabsContent>
        <TabsContent value="loans"><LoansTab p={p} /></TabsContent>
        <TabsContent value="contact"><ContactTab p={p} /></TabsContent>
        <TabsContent value="lifecycle"><LifecycleTab p={p} /></TabsContent>
        <TabsContent value="ops"><OperationsTab p={p} /></TabsContent>
        <TabsContent value="history"><HistoryTab id={s.id} /></TabsContent>
      </Tabs>
      <EditStudentDialog s={s} open={edit} onOpenChange={setEdit} />
    </div>
  );
}
