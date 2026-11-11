import * as React from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ArrowLeft, ListChecks, MessageCircle, MessageSquarePlus, RefreshCcw } from "lucide-react";
import { get, post, type Page } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { PageHeader } from "@/components/data/layout";
import { EmptyState, ErrorState, InlineError, QueryBoundary } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { Timeline } from "@/components/data/timeline";
import { PageFallback } from "@/components/layout/AppShell";
import { formatDate, formatDateTime } from "@/lib/utils";
import { CORRECTABLE, GRV_CATEGORIES, type Grievance } from "@/features/engagement/types";
import type { PortalOverview } from "./types";

const BORROWER_LABELS: Record<string, string> = {
  DATA_CORRECTION: "Correct my personal details", AMOUNT_DISPUTE: "Question about an amount", ADDRESS_DISPUTE: "Question about my address on record",
  CONDUCT_COMPLAINT: "Complaint about how I was treated", COMMUNICATION_COMPLAINT: "Complaint about messages or calls", OTHER: "Something else",
};

function RaiseDialog({ initialCategory, onClose }: { initialCategory?: string; onClose: () => void }) {
  const qc = useQueryClient();
  const loans = useQuery({ queryKey: ["portal-overview"], queryFn: () => get<PortalOverview>("/portal/overview") });
  const [f, setF] = React.useState({ category: GRV_CATEGORIES.includes(initialCategory ?? "") ? initialCategory! : "OTHER", subject: "", description: "", loan_id: "", correction_field: "", correction_requested_value: "" });
  const set = (k: keyof typeof f, v: string) => setF((x) => ({ ...x, [k]: v }));
  const correction = f.category === "DATA_CORRECTION";
  const valid = f.subject.trim().length >= 5 && f.description.trim().length >= 10 && (!correction || (!!f.correction_field && !!f.correction_requested_value.trim()));
  const m = useMutation({
    mutationFn: () => post<Grievance>("/portal/grievances", {
      category: f.category, subject: f.subject.trim(), description: f.description.trim(), loan_id: f.loan_id || null,
      correction_field: correction ? f.correction_field : null, correction_requested_value: correction ? f.correction_requested_value.trim() : null,
    }),
    onSuccess: (g) => { toast.success(`Request ${g.ref} received. We will respond by ${formatDate(g.due_on)}.`); qc.invalidateQueries({ queryKey: ["portal-grievances"] }); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent wide>
        <DialogHeader title="Raise a request" description="Tell us what is wrong. If you dispute an amount or address, any follow-up on your loan is paused until your request is resolved." />
        <DialogBody>
          <Field label="What is this about?" htmlFor="pg-cat"><NativeSelect id="pg-cat" value={f.category} onChange={(e) => set("category", e.target.value)}>
            {GRV_CATEGORIES.map((c) => <option key={c} value={c}>{BORROWER_LABELS[c] ?? labelFor(c)}</option>)}</NativeSelect></Field>
          {(loans.data?.loans.length ?? 0) > 0 && (
            <Field label="Related loan (optional)" htmlFor="pg-loan"><NativeSelect id="pg-loan" value={f.loan_id} onChange={(e) => set("loan_id", e.target.value)}>
              <option value="">Not about a specific loan</option>{loans.data!.loans.map((l) => <option key={l.id} value={l.id}>{l.bank_name} - {l.bank_loan_ref}</option>)}</NativeSelect></Field>
          )}
          {correction && (
            <div className="grid gap-4 rounded-md border bg-muted/30 p-3 sm:grid-cols-2">
              <Field label="Detail to correct" htmlFor="pg-cf" required><NativeSelect id="pg-cf" value={f.correction_field} onChange={(e) => set("correction_field", e.target.value)}>
                <option value="">Choose</option>{CORRECTABLE.map((c) => <option key={c} value={c}>{labelFor(c.replace("primary_", ""))}</option>)}</NativeSelect></Field>
              <Field label="Correct value" htmlFor="pg-cv" required><Input id="pg-cv" type={f.correction_field === "dob" ? "date" : "text"} value={f.correction_requested_value} onChange={(e) => set("correction_requested_value", e.target.value)} /></Field>
            </div>
          )}
          <Field label="Short summary" htmlFor="pg-subj" required hint="At least 5 characters"><Input id="pg-subj" maxLength={200} value={f.subject} onChange={(e) => set("subject", e.target.value)} /></Field>
          <Field label="Details" htmlFor="pg-desc" required hint="At least 10 characters. Do not include passwords or bank PINs.">
            <Textarea id="pg-desc" className="min-h-[120px]" maxLength={4000} value={f.description} onChange={(e) => set("description", e.target.value)} /></Field>
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter><Button variant="secondary" onClick={onClose}>Cancel</Button><Button loading={m.isPending} disabled={!valid} onClick={() => m.mutate()}>Submit request</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RequestDetail({ id, onBack }: { id: string; onBack: () => void }) {
  const q = useQuery({ queryKey: ["portal-grievance", id], queryFn: () => get<Grievance>(`/portal/grievances/${id}`) });
  if (q.isLoading) return <PageFallback />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const g = q.data;
  return (
    <div className="space-y-4">
      <Button variant="ghost" size="sm" onClick={onBack}><ArrowLeft />All requests</Button>
      <Card>
        <CardHeader><div className="min-w-0"><CardTitle>{g.subject}</CardTitle><p className="mt-1 font-mono text-xs text-muted-foreground">{g.ref} - {BORROWER_LABELS[g.category] ?? labelFor(g.category)}</p></div><StatusBadge status={g.status} /></CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">Submitted {formatDateTime(g.created_at)}. Response expected by {formatDate(g.due_on)}.</p>
          <p className="whitespace-pre-wrap rounded-md bg-muted/40 p-3 text-sm">{g.description}</p>
          {g.resolution && <p className="rounded-md border bg-success-soft/50 p-3 text-sm"><span className="font-medium">Outcome:</span> {g.resolution}</p>}
          <div><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Updates</p>
            {g.events?.length ? <Timeline items={[...g.events].reverse().map((e) => ({ id: e.id, at: e.at, icon: e.type === "STATUS_CHANGED" ? RefreshCcw : MessageCircle, tone: "info",
              title: <span className="flex flex-wrap items-center gap-1.5">{e.type === "RESPONSE" ? "Response from the team" : labelFor(e.type)}{e.to && <StatusBadge status={e.to} />}</span>,
              body: <p className="whitespace-pre-wrap text-foreground/80">{e.message}</p> }))} /> : <EmptyState title="No updates yet" />}</div>
        </CardContent>
      </Card>
    </div>
  );
}

/** Borrower requests: raise, track and read responses (FR-GRV-01, FR-STU-09, UC-33). */
export default function PortalGrievancesPage() {
  const [sp, setSp] = useSearchParams();
  const id = sp.get("id");
  const raising = sp.get("new") === "1";
  const q = useQuery({ queryKey: ["portal-grievances"], queryFn: () => get<Page<Grievance>>("/portal/grievances"), enabled: !id });
  const go = (patch: Record<string, string | null>) => setSp(() => { const n = new URLSearchParams(); Object.entries(patch).forEach(([k, v]) => v && n.set(k, v)); return n; });
  if (id) return <RequestDetail id={id} onBack={() => go({})} />;
  return (
    <div className="space-y-5">
      <PageHeader title="My requests" description="Corrections, disputes and complaints you have raised, with the latest status."
        actions={<Button onClick={() => go({ new: "1" })}><MessageSquarePlus />Raise a request</Button>} />
      <QueryBoundary query={q} isEmpty={(d) => d.items.length === 0}
        empty={<Card><EmptyState icon={ListChecks} title="You have not raised any requests" description="If something on your record looks wrong, raise a request and the team will review it." /></Card>}>{(d) => (
        <ul className="space-y-3">{d.items.map((g) => (
          <li key={g.id}>
            <button type="button" onClick={() => go({ id: g.id })} className="w-full rounded-lg border bg-surface p-4 text-left shadow-sm transition-colors hover:bg-muted/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
              <div className="flex flex-wrap items-center gap-2"><span className="font-mono text-xs text-muted-foreground">{g.ref}</span><StatusBadge status={g.status} />
                {g.overdue && <Badge tone="warning">Response overdue</Badge>}<span className="ml-auto text-xs text-muted-foreground">{formatDate(g.created_at)}</span></div>
              <p className="mt-1.5 font-medium">{g.subject}</p>
              <p className="text-xs text-muted-foreground">{BORROWER_LABELS[g.category] ?? labelFor(g.category)} - response expected by {formatDate(g.due_on)}</p>
            </button>
          </li>))}</ul>
      )}</QueryBoundary>
      {raising && <RaiseDialog initialCategory={sp.get("category") ?? undefined} onClose={() => go({})} />}
    </div>
  );
}
