import * as React from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, Circle, History, Landmark, Mail, MapPin, Phone, Plus, ShieldAlert } from "lucide-react";
import { get, post } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/misc";
import { EmptyState } from "@/components/data/states";
import { FreshnessBadge, Money, StatusBadge, labelFor } from "@/components/data/status";
import { KeyValue } from "@/components/data/layout";
import { Timeline } from "@/components/data/timeline";
import { formatDate, formatDateTime, titleCase } from "@/lib/utils";
import { AcademicDialog, AddAddressDialog, EmploymentDialog, SimpleActionDialog } from "./dialogs";
import type { Address, Profile } from "./profileTypes";

const src = (s: string) => <span className="text-[11px] text-muted-foreground">Source: {titleCase(s)}</span>;

export function OverviewTab({ p }: { p: Profile }) {
  const s = p.student;
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader><div><CardTitle>Identity</CardTitle><CardDescription>Material fields show their source and verification status (FR-STU-06).</CardDescription></div></CardHeader>
        <CardContent>
          <KeyValue cols={3} items={[
            { label: "Full name", value: s.full_name, hint: src(s.source) },
            { label: "DAPRO reference", value: <span className="font-mono">{s.dapro_ref}</span> },
            { label: "College student ID", value: <span className="font-mono">{s.college_student_id}</span>, hint: s.college_name },
            { label: "Date of birth", value: s.dob ? formatDate(s.dob) : s.dob_masked ? <span className="text-muted-foreground">Masked for your role</span> : "Not recorded" },
            { label: "Gender", value: s.gender ?? "Not stated" },
            { label: "KYC reference", value: s.kyc_ref_last4 ? `**** ${s.kyc_ref_last4}` : "Not recorded" },
            { label: "Identity verification", value: <StatusBadge status={s.verification_status} /> },
            { label: "Record status", value: <StatusBadge status={s.record_status} />, hint: s.data_origin === "DEMO" ? "Synthetic demo record" : undefined },
            { label: "Last updated", value: formatDateTime(s.updated_at), hint: s.source_ref },
          ]} />
          {p.consents.length > 0 && (
            <div className="mt-5 border-t pt-4">
              <p className="mb-2 text-xs font-medium text-muted-foreground">Lawful basis and consent</p>
              <ul className="space-y-1.5 text-sm">{p.consents.map((c) => (
                <li key={c.id} className="flex flex-wrap items-center gap-2"><Badge tone={c.active ? "success" : "neutral"}>{c.active ? "Active" : "Withdrawn"}</Badge>
                  {titleCase(c.basis)} - {c.purposes.map(titleCase).join(", ")} <span className="text-[11px] text-muted-foreground">notice {c.notice_version}{c.withdrawn_at ? `, withdrawn ${formatDate(c.withdrawn_at)}` : ""}</span></li>))}</ul>
            </div>
          )}
        </CardContent>
      </Card>
      <div className="space-y-4">
        <Card>
          <CardHeader><CardTitle>Profile completion</CardTitle></CardHeader>
          <CardContent><ul className="space-y-2">{p.completion.checks.map((c) => (
            <li key={c.key} className="flex items-center gap-2 text-sm">{c.ok ? <CheckCircle2 className="h-4 w-4 text-success" /> : <Circle className="h-4 w-4 text-muted-foreground" />}<span className={c.ok ? "" : "text-muted-foreground"}>{c.label}</span></li>))}</ul></CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle>Pending actions</CardTitle></CardHeader>
          <CardContent>{p.pending_actions.length ? <ul className="space-y-2">{p.pending_actions.map((a, i) => (
            <li key={i} className="flex items-start gap-2 text-sm"><ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" />{a.label}</li>))}</ul>
            : <p className="text-sm text-muted-foreground">Nothing pending.</p>}</CardContent>
        </Card>
      </div>
      <Card className="lg:col-span-3">
        <CardHeader><div><CardTitle>Recent timeline</CardTitle><CardDescription>From the audit trail and correction history</CardDescription></div></CardHeader>
        <CardContent>{p.timeline.length ? <Timeline items={p.timeline.slice(0, 12).map((t, i) => ({ id: String(i), at: t.at, title: t.summary, actor: t.actor,
          tone: t.outcome === "SUCCESS" ? "default" : "danger" }))} /> : <EmptyState title="No events yet" />}</CardContent>
      </Card>
    </div>
  );
}

export function LoansTab({ p }: { p: Profile }) {
  const can = useCan();
  if (!p.loans) return <EmptyState icon={ShieldAlert} title="Loan information is not available for your role" />;
  return (
    <div className="space-y-4">
      {can("loan:link") && <div className="flex justify-end"><Button asChild variant="secondary"><Link to={`/loans/link?student_id=${p.student.id}`}><Landmark />Link bank loan</Link></Button></div>}
      {!p.loans.length && <Card><EmptyState title="No linked bank loans" description="Loans are linked by a bank-provided reference after validation (FR-LON-01)." /></Card>}
      {p.loans.map((l) => (
        <Card key={l.id}>
          <CardHeader>
            <div className="min-w-0"><CardTitle className="font-mono">{l.bank_loan_ref}</CardTitle><CardDescription>{l.bank_name} - {l.product_name ?? "Education loan"}</CardDescription></div>
            <div className="flex flex-wrap items-center gap-1.5"><StatusBadge status={l.link_status} /><StatusBadge status={l.repayment_status} />{l.dpd_bucket && <StatusBadge status={l.dpd_bucket} />}</div>
          </CardHeader>
          <CardContent className="space-y-4">
            <KeyValue cols={4} items={[
              { label: "Bank status", value: labelFor(l.bank_status) },
              { label: "Days past due", value: l.financial_restricted ? <Money restricted /> : l.dpd ?? "-" },
              { label: "Sanctioned", value: <Money value={l.sanctioned_amount} restricted={l.financial_restricted} /> },
              { label: "Principal outstanding", value: <Money value={l.principal_outstanding} restricted={l.financial_restricted} /> },
              { label: "Overdue (bank-confirmed)", value: <Money value={l.overdue_amount} restricted={l.financial_restricted} /> },
              { label: "Next due", value: l.next_due_date ? formatDate(l.next_due_date) : "-", hint: l.financial_restricted ? undefined : <Money value={l.next_due_amount} /> },
              { label: "Guarantors", value: l.guarantor_count ?? "-" }, { label: "Witnesses", value: l.witness_count ?? "-", hint: "Witnesses carry no repayment liability" },
            ]} />
            <div className="flex flex-wrap items-center justify-between gap-2 border-t pt-3"><FreshnessBadge f={l.freshness} />
              <Button asChild variant="link"><Link to={`/loans/${l.id}`}>Open loan, schedule and transactions</Link></Button></div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function AddressCard({ a, studentId, history }: { a: Address; studentId: string; history?: boolean }) {
  const can = useCan();
  const [dlg, setDlg] = React.useState<"verify" | "dispute" | null>(null);
  return (
    <div className={history ? "rounded-md border border-dashed p-3 opacity-80" : "rounded-md border p-3"}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-muted-foreground"><MapPin className="h-3.5 w-3.5" />{titleCase(a.kind)}{history && " (superseded)"}</p>
          <p className="mt-1 text-sm">{a.line1}{a.line2 ? `, ${a.line2}` : ""}</p>
          <p className="text-sm">{[a.city, a.state, a.postal_code, a.country].filter(Boolean).join(", ")}</p>
          <p className="mt-1 text-[11px] text-muted-foreground">Source: {titleCase(a.source_type)} - effective {formatDate(a.effective_from ?? a.created_at)}{a.superseded_at ? ` - superseded ${formatDate(a.superseded_at)}` : ""}</p>
          {a.notes && <p className="mt-1 text-[11px] text-muted-foreground">Note: {a.notes}</p>}
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <StatusBadge status={a.verification} />
          {a.verification_method && <span className="text-[11px] text-muted-foreground">via {titleCase(a.verification_method)}{a.verified_at ? `, ${formatDate(a.verified_at)}` : ""}</span>}
        </div>
      </div>
      {!history && can("address:write") && (
        <div className="mt-3 flex flex-wrap gap-2 border-t pt-2">
          {a.verification !== "VERIFIED" && a.verification !== "PENDING" && <Button size="sm" variant="secondary" onClick={() => setDlg("verify")}>Request verification</Button>}
          {a.verification !== "DISPUTED" && <Button size="sm" variant="ghost" onClick={() => setDlg("dispute")}>Flag as disputed</Button>}
        </div>
      )}
      <SimpleActionDialog studentId={studentId} open={dlg === "verify"} onOpenChange={(o) => setDlg(o ? "verify" : null)} title="Request address verification"
        description="Creates a pending verification task. Location is never inferred from devices or social media (FR-ADR-07)." url={`/addresses/${a.id}/verification-requests`} kind="method" success="Verification requested" />
      <SimpleActionDialog studentId={studentId} open={dlg === "dispute"} onOpenChange={(o) => setDlg(o ? "dispute" : null)} title="Flag address as disputed"
        description="Marks the address DISPUTED for review (FR-ADR-06). The record is not deleted." url={`/addresses/${a.id}/dispute`} kind="reason" success="Address flagged as disputed" />
    </div>
  );
}

export function ContactTab({ p }: { p: Profile }) {
  const can = useCan();
  const id = p.student.id;
  const [add, setAdd] = React.useState(false);
  const [showHist, setShowHist] = React.useState(false);
  const hist = useQuery({ queryKey: ["addr-history", id], queryFn: () => get<Address[]>(`/students/${id}/addresses?history=true`), enabled: showHist });
  const past = (hist.data ?? []).filter((a) => !a.is_current);
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card>
        <CardHeader><div><CardTitle>Contact details</CardTitle><CardDescription>{can("student:pii_full") ? "Full values shown for your role" : "Masked for your role"}</CardDescription></div></CardHeader>
        <CardContent>{p.contacts.length ? <ul className="space-y-3">{p.contacts.map((c) => (
          <li key={c.id} className="flex items-start gap-2 text-sm">{c.kind === "EMAIL" ? <Mail className="mt-0.5 h-4 w-4 text-muted-foreground" /> : <Phone className="mt-0.5 h-4 w-4 text-muted-foreground" />}
            <div className="min-w-0"><p className="break-all">{c.value}</p><p className="text-[11px] text-muted-foreground">{titleCase(c.source)}{c.is_primary ? " - primary" : ""}</p></div>
            <StatusBadge status={c.verification} className="ml-auto" /></li>))}</ul> : <EmptyState title="No contact details" />}</CardContent>
      </Card>
      <Card className="lg:col-span-2">
        <CardHeader>
          <div><CardTitle>Addresses</CardTitle><CardDescription>History is preserved; verification records method, actor and date (FR-ADR-03..05).</CardDescription></div>
          {can("address:write") && <Button size="sm" onClick={() => setAdd(true)}><Plus />Add address</Button>}
        </CardHeader>
        <CardContent className="space-y-3">
          {!p.addresses && <EmptyState icon={ShieldAlert} title="Addresses are not available for your role" />}
          {p.addresses?.length === 0 && <EmptyState title="No current address recorded" />}
          {p.addresses?.map((a) => <AddressCard key={a.id} a={a} studentId={id} />)}
          {p.address_history_available && (
            <div className="border-t pt-3">
              <label className="flex items-center gap-2 text-sm"><Switch checked={showHist} onCheckedChange={setShowHist} aria-label="Show address history" /><History className="h-4 w-4 text-muted-foreground" />
                Show address history <span className="text-[11px] text-muted-foreground">(access is audited - FR-ADR-08)</span></label>
              {showHist && <div className="mt-3 space-y-2">{hist.isLoading ? <p className="text-xs text-muted-foreground">Loading history</p> : past.length ? past.map((a) => <AddressCard key={a.id} a={a} studentId={id} history />) : <p className="text-xs text-muted-foreground">No superseded addresses.</p>}</div>}
            </div>
          )}
        </CardContent>
      </Card>
      <AddAddressDialog studentId={id} open={add} onOpenChange={setAdd} />
    </div>
  );
}

export function LifecycleTab({ p }: { p: Profile }) {
  const can = useCan();
  const id = p.student.id;
  const [dlg, setDlg] = React.useState<"acad" | "emp" | null>(null);
  const [verify, setVerify] = React.useState<string | null>(null);
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader><div><CardTitle>Academic history</CardTitle><CardDescription>From the college of record</CardDescription></div>
          {can("academic:write") && <Button size="sm" variant="secondary" onClick={() => setDlg("acad")}><Plus />Record status</Button>}</CardHeader>
        <CardContent>{p.academic.length ? <ul className="space-y-3">{p.academic.map((a) => (
          <li key={a.id} className={a.is_current ? "rounded-md border p-3" : "rounded-md border border-dashed p-3 opacity-80"}>
            <div className="flex flex-wrap items-start justify-between gap-2"><div><p className="text-sm font-medium">{a.programme} - {a.course}</p>
              <p className="text-xs text-muted-foreground">{a.college_name} - cohort {a.cohort_year}</p></div><StatusBadge status={a.enrolment_status} /></div>
            <p className="mt-1 text-[11px] text-muted-foreground">Start {formatDate(a.start_date)} - expected {formatDate(a.expected_completion)}{a.actual_completion ? ` - completed ${formatDate(a.actual_completion)}` : ""} - {titleCase(a.source)}{a.is_current ? "" : " (superseded)"}</p>
          </li>))}</ul> : <EmptyState title="No academic record" />}</CardContent>
      </Card>
      <Card>
        <CardHeader><div><CardTitle>Post-study status and employment</CardTitle><CardDescription>Borrower-reported and institution-verified values are distinguished (FR-EMP-05).</CardDescription></div>
          {can("employment:write") && <Button size="sm" variant="secondary" onClick={() => setDlg("emp")}><Plus />Record status</Button>}</CardHeader>
        <CardContent>{p.employment.length ? <ul className="space-y-3">{p.employment.map((e) => (
          <li key={e.id} className={e.is_current ? "rounded-md border p-3" : "rounded-md border border-dashed p-3 opacity-80"}>
            <div className="flex flex-wrap items-start justify-between gap-2"><div><p className="text-sm font-medium">{e.employer_name ?? labelFor(e.status)}</p>
              <p className="text-xs text-muted-foreground">{[e.job_title, e.city, e.country].filter(Boolean).join(" - ") || "-"}</p></div>
              <div className="flex gap-1"><StatusBadge status={e.status} /><StatusBadge status={e.verification} /></div></div>
            <p className="mt-1 text-[11px] text-muted-foreground">{titleCase(e.source)} - reported {formatDate(e.reported_on)}{e.superseded_at ? ` - superseded ${formatDate(e.superseded_at)}` : ""}</p>
            {e.is_current && e.verification !== "VERIFIED" && can("employment:write") && <Button size="sm" variant="ghost" className="mt-1" onClick={() => setVerify(e.id)}>Mark as verified</Button>}
          </li>))}</ul> : <EmptyState title="No post-study status recorded" description="A neutral update request can be sent if communication preferences allow." />}</CardContent>
      </Card>
      <AcademicDialog studentId={id} open={dlg === "acad"} onOpenChange={(o) => setDlg(o ? "acad" : null)} />
      <EmploymentDialog studentId={id} open={dlg === "emp"} onOpenChange={(o) => setDlg(o ? "emp" : null)} />
      <SimpleActionDialog studentId={id} open={!!verify} onOpenChange={(o) => !o && setVerify(null)} title="Verify employment record"
        description="The original source is preserved; verification adds who verified it and when." url={`/employment/${verify}/verify`} kind="notes" success="Employment verified" />
    </div>
  );
}

export function OperationsTab({ p }: { p: Profile }) {
  const sections = [
    p.cases && { title: "Cases", empty: "No follow-up cases", rows: p.cases.map((c) => ({ id: c.id, to: `/cases/${c.id}`, main: `${c.case_ref} - ${labelFor(c.category)}`, sub: c.next_action ?? "", badges: [c.status, c.priority], date: c.due_on })) },
    p.risk_indicators && { title: "Risk indicators", empty: "No indicators - indicators are review prompts, not findings", rows: p.risk_indicators.map((r) => ({ id: r.id, to: `/risk/${r.id}`, main: r.title, sub: `${r.rule_code} v${r.rule_version} - ${r.explanation}`, badges: [r.severity, r.status], date: r.generated_at })) },
    p.grievances && { title: "Grievances and corrections", empty: "No grievances", rows: p.grievances.map((g) => ({ id: g.id, to: `/grievances/${g.id}`, main: `${g.ref} - ${g.subject}`, sub: labelFor(g.category), badges: [g.status], date: g.created_at })) },
    p.communications && { title: "Communications", empty: "No communications", rows: p.communications.map((c) => ({ id: c.id, to: "/communications", main: `${labelFor(c.purpose)} by ${c.channel}`, sub: `${c.template_code ?? ""} to ${labelFor(c.recipient_type)}`, badges: [c.status, c.provider_mode], date: c.created_at })) },
  ].filter(Boolean) as { title: string; empty: string; rows: { id: string; to: string; main: string; sub: string; badges: string[]; date: string | null }[] }[];
  if (!sections.length) return <EmptyState icon={ShieldAlert} title="Operational records are not available for your role" />;
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {sections.map((s) => (
        <Card key={s.title}>
          <CardHeader><CardTitle>{s.title}</CardTitle><Badge tone="neutral">{s.rows.length}</Badge></CardHeader>
          {s.rows.length ? <ul className="divide-y">{s.rows.map((r) => (
            <li key={r.id}><Link to={r.to} className="flex items-start justify-between gap-3 px-5 py-3 hover:bg-muted/50">
              <span className="min-w-0"><span className="block truncate text-sm font-medium">{r.main}</span><span className="block truncate text-xs text-muted-foreground">{r.sub}</span></span>
              <span className="flex shrink-0 flex-col items-end gap-1"><span className="flex gap-1">{r.badges.map((b) => <StatusBadge key={b} status={b} />)}</span><span className="text-[11px] text-muted-foreground">{formatDate(r.date)}</span></span>
            </Link></li>))}</ul> : <CardContent><p className="text-sm text-muted-foreground">{s.empty}</p></CardContent>}
        </Card>
      ))}
    </div>
  );
}

export function useVerifyAddress() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (v: { id: string; status: string; notes: string }) => post(`/address-verifications/${v.id}/outcome`, { status: v.status, notes: v.notes }),
    onSuccess: () => { toast.success("Verification outcome recorded"); qc.invalidateQueries({ queryKey: ["verifications"] }); } });
}
