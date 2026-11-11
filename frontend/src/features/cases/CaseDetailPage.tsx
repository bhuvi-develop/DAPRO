import * as React from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CalendarClock, FileSearch, History, Pencil, UserPlus } from "lucide-react";
import { get } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger, Tooltip } from "@/components/ui/menu";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { EmptyState, ErrorState } from "@/components/data/states";
import { FreshnessBadge, Money, StatusBadge, labelFor } from "@/components/data/status";
import { Timeline } from "@/components/data/timeline";
import { PageFallback } from "@/components/layout/AppShell";
import { cn, formatDate, formatDateTime } from "@/lib/utils";
import { AssignDialog, EditDialog, TransitionDialog } from "./CaseDialogs";
import { CommitmentsTab, EvidenceTab, FollowUpsTab, VisitsTab } from "./CaseTabs";
import { fetchCaseMeta, type CaseDetail, type Transition } from "./types";

export default function CaseDetailPage() {
  const { id } = useParams();
  const can = useCan();
  const q = useQuery({ queryKey: ["case", id], queryFn: () => get<CaseDetail>(`/cases/${id}`) });
  const meta = useQuery({ queryKey: ["case-meta"], queryFn: fetchCaseMeta, staleTime: 600_000 });
  const [dialog, setDialog] = React.useState<"assign" | "edit" | null>(null);
  const [transition, setTransition] = React.useState<Transition | null>(null);
  if (q.isLoading) return <PageFallback />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const c = q.data;
  const active = !["RESOLVED", "CLOSED"].includes(c.status);
  return (
    <div className="space-y-6">
      <PageHeader title={<span className="flex flex-wrap items-center gap-3"><span className="font-mono">{c.case_ref}</span><span className="text-base font-normal text-muted-foreground">{labelFor(c.category)}</span></span>}
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Cases", to: "/cases" }, { label: c.case_ref }]}
        meta={<><StatusBadge status={c.status} /><StatusBadge status={c.priority} />{c.previous_status && c.status === "DISPUTED" && <Badge tone="outline">Paused from {labelFor(c.previous_status)}</Badge>}
          <span className="text-xs text-muted-foreground">Source: {labelFor(c.source)}{c.source_ref ? ` (${c.source_ref})` : ""} - opened by {c.opened_by?.name ?? "system"} {formatDateTime(c.created_at)}</span></>}
        actions={<>
          {can("audit:read") && <Button asChild variant="ghost"><Link to={`/audit/cases/${c.id}`}><FileSearch />Reconstruction</Link></Button>}
          {c.can.update && active && <Button variant="secondary" onClick={() => setDialog("edit")}><Pencil />Edit</Button>}
          {c.can.assign && active && <Button variant="secondary" onClick={() => setDialog("assign")}><UserPlus />{c.owner_id ? "Reassign" : "Assign"}</Button>}
        </>} />

      <Card>
        <CardContent className="grid gap-6 lg:grid-cols-3">
          <KeyValue cols={2} className="lg:col-span-2" items={[
            { label: "Borrower", value: <Link to={`/students/${c.student.id}`} className="font-medium text-primary hover:underline">{c.student.name}</Link>, hint: c.student.dapro_ref },
            { label: "Contact", value: <span className="text-xs">{c.student.mobile ?? "-"}<br />{c.student.email ?? ""}</span> },
            { label: "Owner", value: c.owner_name ?? <span className="text-warning">Unassigned</span> },
            { label: "Due", value: <span className={cn(c.overdue && "font-semibold text-danger")}>{formatDate(c.due_on)}{c.overdue && " (overdue)"}</span> },
            { label: "Next action", value: c.next_action },
            { label: "Reason", value: c.reason },
          ]} />
          <div className="rounded-lg border bg-muted/30 p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Linked loan</p>
            {c.loan ? (
              <div className="space-y-2 text-sm">
                <Link to={`/loans/${c.loan.id}`} className="font-mono font-medium text-primary hover:underline">{c.loan.bank_loan_ref}</Link>
                <div className="flex flex-wrap gap-1.5"><StatusBadge status={c.loan.repayment_status} />{c.loan.dpd ? <Badge tone="danger">{c.loan.dpd} DPD</Badge> : null}</div>
                <p className="text-xs">Overdue (bank): <Money value={c.loan.overdue_amount} restricted={c.loan.overdue_amount === null && !can("loan:financial")} /></p>
                <FreshnessBadge f={{ source: c.loan.source, as_of: c.loan.last_synced_at, sync_state: c.loan.sync_state }} />
              </div>
            ) : <p className="text-sm text-muted-foreground">Not loan-specific.</p>}
          </div>
        </CardContent>
        {c.allowed_transitions.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t px-5 py-3">
            <span className="mr-1 text-xs font-medium text-muted-foreground">Next step:</span>
            {c.allowed_transitions.map((t) => {
              const btn = (
                <Button key={t.to} size="sm" variant={t.to === "ESCALATED" ? "danger" : t.to === "RESOLVED" || t.to === "CLOSED" ? "success" : "secondary"}
                  disabled={!t.permitted} onClick={() => setTransition(t)}>{t.label}</Button>
              );
              return t.permitted ? btn : <Tooltip key={t.to} content={t.reason_if_blocked ?? "Not permitted"}><span tabIndex={0}>{btn}</span></Tooltip>;
            })}
          </div>
        )}
        {c.status === "NEW" && <p className="border-t px-5 py-3 text-xs text-muted-foreground">A new case moves forward once it has an owner.</p>}
        {c.resolution_type && <p className="border-t px-5 py-3 text-sm">Resolution: <span className="font-medium">{c.resolution_types[c.resolution_type] ?? labelFor(c.resolution_type)}</span>{c.resolution_notes ? ` - ${c.resolution_notes}` : ""}</p>}
      </Card>

      <Tabs defaultValue="timeline">
        <TabsList>
          <TabsTrigger value="timeline"><History />Timeline</TabsTrigger>
          <TabsTrigger value="followups">Follow-ups <Badge>{c.follow_ups.length}</Badge></TabsTrigger>
          <TabsTrigger value="evidence">Evidence <Badge>{c.evidence.length}</Badge></TabsTrigger>
          <TabsTrigger value="commitments">Commitments <Badge>{c.commitments.length}</Badge></TabsTrigger>
          <TabsTrigger value="visits"><CalendarClock />Field visits <Badge>{c.visits.length}</Badge></TabsTrigger>
          <TabsTrigger value="indicators"><AlertTriangle />Indicators <Badge>{c.indicators.length}</Badge></TabsTrigger>
          <TabsTrigger value="grievances">Grievances <Badge>{c.grievances.length}</Badge></TabsTrigger>
        </TabsList>
        <TabsContent value="timeline">
          <Card><CardContent>{c.timeline.length ? <Timeline items={c.timeline.map((e) => ({ id: e.id, at: e.at, actor: e.actor?.name,
            title: <span>{e.summary}{e.to ? <> <StatusBadge status={e.to} className="ml-1" /></> : null}</span>,
            tone: e.type.includes("ESCALAT") ? "danger" : e.type.includes("RESOLV") || e.type.includes("CLOS") ? "success" : "default" }))} />
            : <EmptyState title="No events yet" />}</CardContent></Card>
        </TabsContent>
        <TabsContent value="followups"><FollowUpsTab c={c} meta={meta.data} /></TabsContent>
        <TabsContent value="evidence"><EvidenceTab c={c} /></TabsContent>
        <TabsContent value="commitments"><CommitmentsTab c={c} /></TabsContent>
        <TabsContent value="visits"><VisitsTab c={c} /></TabsContent>
        <TabsContent value="indicators">
          {c.indicators.length ? <ul className="divide-y rounded-md border bg-surface">{c.indicators.map((i) => (
            <li key={i.id}><Link to={`/risk/${i.id}`} className="flex flex-wrap items-center gap-3 px-3 py-2.5 hover:bg-muted/50">
              <span className="min-w-0 flex-1 text-sm">{i.title}<span className="block text-[11px] text-muted-foreground">{i.rule_code} v{i.rule_version} - {formatDateTime(i.generated_at)}</span></span>
              <StatusBadge status={i.severity} /><StatusBadge status={i.status} /></Link></li>))}</ul>
            : <EmptyState title="No linked risk indicators" />}
        </TabsContent>
        <TabsContent value="grievances">
          {c.grievances.length ? <ul className="divide-y rounded-md border bg-surface">{c.grievances.map((g) => (
            <li key={g.id}><Link to={`/grievances/${g.id}`} className="flex flex-wrap items-center gap-3 px-3 py-2.5 hover:bg-muted/50">
              <span className="font-mono text-xs">{g.ref}</span><span className="min-w-0 flex-1 truncate text-sm">{g.subject}</span>
              <Badge tone="outline">{labelFor(g.category)}</Badge><StatusBadge status={g.status} /></Link></li>))}</ul>
            : <EmptyState title="No grievances linked" description="When a borrower disputes this case it pauses as DISPUTED until the grievance is resolved." />}
        </TabsContent>
      </Tabs>

      {dialog === "assign" && <AssignDialog c={c} onClose={() => setDialog(null)} />}
      {dialog === "edit" && <EditDialog c={c} priorities={meta.data?.priorities ?? ["CRITICAL", "HIGH", "MEDIUM", "LOW"]} onClose={() => setDialog(null)} />}
      {transition && <TransitionDialog c={c} t={transition} onClose={() => setTransition(null)} />}
    </div>
  );
}
