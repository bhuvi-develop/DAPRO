import * as React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { LogIn, LogOut, MapPinOff, Save, Send, ShieldAlert } from "lucide-react";
import { get, patch, post } from "@/api/client";
import { useAuth, useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/input";
import { Switch } from "@/components/ui/misc";
import { Field } from "@/components/data/feedback";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { ErrorState, InlineError } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { PageFallback } from "@/components/layout/AppShell";
import { cn, formatDateTime } from "@/lib/utils";
import { OUTCOMES, type Visit } from "./types";
import { ReviewPanel } from "./ReviewPanel";

export default function VisitPage() {
  const { id } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const can = useCan();
  const me = useAuth((s) => s.me)!;
  const q = useQuery({ queryKey: ["visit", id], queryFn: () => get<Visit>(`/visits/${id}`) });
  const [outcome, setOutcome] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [present, setPresent] = React.useState(false);
  const [incident, setIncident] = React.useState(false);
  const [incidentNotes, setIncidentNotes] = React.useState("");
  const draftId = React.useRef<string>("");
  React.useEffect(() => {
    const v = q.data;
    if (!v) return;
    setOutcome(v.outcome ?? "");
    setNotes(v.notes ?? "");
    setPresent(!!v.borrower_present);
    setIncident(v.safety_incident);
    setIncidentNotes(v.incident_notes ?? "");
    if (!draftId.current) draftId.current = v.client_draft_id ?? crypto.randomUUID();
  }, [q.data]);
  const refresh = (v: Visit) => { qc.setQueryData(["visit", id], v); qc.invalidateQueries({ queryKey: ["my-cases"] }); };
  const check = useMutation({ mutationFn: (which: "in" | "out") => post<Visit>(`/visits/${id}/check-${which}`), onSuccess: (v) => { refresh(v); toast.success("Time recorded. No location was captured."); } });
  const save = useMutation({
    mutationFn: () => patch<Visit>(`/visits/${id}`, { outcome: outcome || null, notes, borrower_present: present, safety_incident: incident, incident_notes: incidentNotes || null }, { "If-Match": String(q.data!.version) }),
    onSuccess: (v) => { refresh(v); toast.success("Draft saved on the server"); },
  });
  const submit = useMutation({
    mutationFn: () => post<Visit>(`/visits/${id}/submit`, { outcome, notes, borrower_present: present, safety_incident: incident, incident_notes: incident ? incidentNotes : null, client_draft_id: draftId.current }),
    onSuccess: (v) => { refresh(v); toast.success(v.review_status === "PENDING" ? "Visit submitted. A supervisor will review it." : "Visit report submitted"); },
  });
  if (q.isLoading) return <PageFallback />;
  if (q.error || !q.data) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const v = q.data;
  const mine = v.officer?.id === me.id;
  const editable = mine && ["DRAFT", "SCHEDULED"].includes(v.status) && can("visit:record");
  const valid = outcome && notes.trim().length >= 3 && (!incident || incidentNotes.trim().length >= 3);
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <PageHeader title="Field visit" crumbs={[{ label: "Field visits", to: can("visit:record") ? "/field" : "/field/review" }, { label: v.case_ref ?? "Visit" }]}
        meta={<><StatusBadge status={v.status} />{v.review_status !== "NOT_REQUIRED" && <StatusBadge status={v.review_status} />}<Badge tone="outline">Officer observation (BR-09)</Badge></>}
        actions={<Button asChild variant="secondary" size="sm"><Link to={`/cases/${v.case_id}`}>Open case</Link></Button>} />
      <Card>
        <CardContent className="space-y-3">
          <KeyValue cols={2} items={[
            { label: "Purpose", value: v.purpose },
            { label: "Officer", value: v.officer?.name },
            { label: "Scheduled", value: formatDateTime(v.scheduled_for) },
            { label: "Checked in / out", value: <span className="text-xs">{formatDateTime(v.check_in_at)} / {formatDateTime(v.check_out_at)}</span> },
          ]} />
          <p className="flex items-start gap-2 rounded-md bg-muted/60 px-3 py-2 text-xs text-muted-foreground"><MapPinOff className="mt-0.5 h-4 w-4 shrink-0" />Location is not captured (OD-14). Check-in and check-out record the time only.</p>
          {editable && (
            <div className="grid grid-cols-2 gap-2">
              <Button variant="secondary" size="lg" disabled={!!v.check_in_at} loading={check.isPending && check.variables === "in"} onClick={() => check.mutate("in")}><LogIn />Check in</Button>
              <Button variant="secondary" size="lg" disabled={!v.check_in_at || !!v.check_out_at} loading={check.isPending && check.variables === "out"} onClick={() => check.mutate("out")}><LogOut />Check out</Button>
            </div>
          )}
          <InlineError error={check.error} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader><div><CardTitle>Visit outcome</CardTitle><CardDescription>Structured outcome and factual notes. A promise to pay is recorded on the case as a commitment, never as a payment.</CardDescription></div></CardHeader>
        <CardContent className="space-y-4">
          <fieldset disabled={!editable} className="space-y-2">
            <legend className="mb-1 text-[13px] font-medium">Outcome<span className="text-danger" aria-hidden>*</span></legend>
            {OUTCOMES.map((o) => (
              <label key={o.value} className={cn("flex min-h-[44px] cursor-pointer items-center gap-3 rounded-md border px-3 text-sm", outcome === o.value && "border-primary bg-primary-soft", !editable && "cursor-default opacity-80")}>
                <input type="radio" name="outcome" value={o.value} checked={outcome === o.value} onChange={() => setOutcome(o.value)} className="h-4 w-4 accent-[#1D4ED8]" />
                {o.label}
              </label>
            ))}
          </fieldset>
          <Field label="Notes" htmlFor="v-notes" required hint="Record what you observed. Do not speculate about intent.">
            <Textarea id="v-notes" disabled={!editable} value={notes} onChange={(e) => setNotes(e.target.value)} />
          </Field>
          <label className="flex min-h-[44px] items-center justify-between gap-3 rounded-md border px-3 text-sm">
            Borrower present<Switch checked={present} onCheckedChange={setPresent} disabled={!editable} aria-label="Borrower present" />
          </label>
          <div className={cn("space-y-3 rounded-md border px-3 py-3", incident && "border-danger/40 bg-danger-soft/50")}>
            <label className="flex items-center justify-between gap-3 text-sm font-medium">
              <span className="flex items-center gap-2"><ShieldAlert className="h-4 w-4 text-danger" />Safety or conduct incident</span>
              <Switch checked={incident} onCheckedChange={setIncident} disabled={!editable} aria-label="Safety or conduct incident" />
            </label>
            {incident && (
              <Field label="Incident details" htmlFor="v-incident" required hint="Your manager is alerted and the report goes to supervisor review (FR-FLD-08).">
                <Textarea id="v-incident" disabled={!editable} value={incidentNotes} onChange={(e) => setIncidentNotes(e.target.value)} />
              </Field>
            )}
          </div>
          <InlineError error={save.error ?? submit.error} />
          {editable && (
            <div className="grid gap-2 sm:grid-cols-2">
              <Button variant="secondary" size="lg" loading={save.isPending} onClick={() => save.mutate()}><Save />Save draft</Button>
              <Button size="lg" loading={submit.isPending} disabled={!valid} onClick={() => submit.mutate()}><Send />Submit report</Button>
            </div>
          )}
          {!editable && v.status === "SUBMITTED" && <p className="text-sm text-muted-foreground">Submitted {formatDateTime(v.visited_at)} with outcome <span className="font-medium text-foreground">{labelFor(v.outcome)}</span>.</p>}
          {v.review_notes && <p className="rounded-md bg-muted/60 px-3 py-2 text-sm">Supervisor: {v.review_notes} ({v.reviewer?.name}, {formatDateTime(v.reviewed_at)})</p>}
        </CardContent>
      </Card>

      {v.review_status === "PENDING" && can("visit:review") && !mine && <ReviewPanel visit={v} onDone={() => nav("/field/review")} />}
    </div>
  );
}
