import * as React from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Briefcase, GraduationCap, Home, Pencil, UserRound } from "lucide-react";
import { get, post } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, NativeSelect } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { InlineError, QueryBoundary } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { formatDate } from "@/lib/utils";
import { EMP_STATES, type PortalProfile } from "./types";

const PIN = /^[0-9]{6}$/;

function AddressDialog({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = React.useState({ kind: "CURRENT", line1: "", line2: "", city: "", state: "", postal_code: "", country: "IN" });
  const set = (k: keyof typeof f, v: string) => setF((x) => ({ ...x, [k]: v }));
  const pinBad = f.country === "IN" && f.postal_code !== "" && !PIN.test(f.postal_code);
  const m = useMutation({
    mutationFn: () => post("/portal/address", { ...f, line2: f.line2 || null, state: f.state || null, postal_code: f.postal_code || null }),
    onSuccess: () => { toast.success("Address submitted. It is marked unverified until your institution checks it."); qc.invalidateQueries({ queryKey: ["portal-profile"] }); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader title="Update your address" description="Your previous address is kept on record. A new address is unverified until it is checked." />
        <DialogBody>
          <Field label="Address type" htmlFor="a-kind"><NativeSelect id="a-kind" value={f.kind} onChange={(e) => set("kind", e.target.value)}><option value="CURRENT">Current address</option><option value="CORRESPONDENCE">Correspondence address</option></NativeSelect></Field>
          <Field label="Address line 1" htmlFor="a-l1" required><Input id="a-l1" autoComplete="address-line1" maxLength={200} value={f.line1} onChange={(e) => set("line1", e.target.value)} /></Field>
          <Field label="Address line 2" htmlFor="a-l2"><Input id="a-l2" autoComplete="address-line2" maxLength={200} value={f.line2} onChange={(e) => set("line2", e.target.value)} /></Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="City" htmlFor="a-city" required><Input id="a-city" autoComplete="address-level2" maxLength={80} value={f.city} onChange={(e) => set("city", e.target.value)} /></Field>
            <Field label="State" htmlFor="a-state"><Input id="a-state" autoComplete="address-level1" maxLength={80} value={f.state} onChange={(e) => set("state", e.target.value)} /></Field>
            <Field label="PIN code" htmlFor="a-pin" error={pinBad ? "Enter a 6-digit PIN code" : undefined}><Input id="a-pin" inputMode="numeric" autoComplete="postal-code" maxLength={12} value={f.postal_code} onChange={(e) => set("postal_code", e.target.value.trim())} /></Field>
            <Field label="Country" htmlFor="a-country" hint="Two-letter code"><Input id="a-country" maxLength={2} value={f.country} onChange={(e) => set("country", e.target.value.toUpperCase())} /></Field>
          </div>
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter><Button variant="secondary" onClick={onClose}>Cancel</Button>
          <Button loading={m.isPending} disabled={f.line1.trim().length < 3 || f.city.trim().length < 2 || pinBad || f.country.length !== 2} onClick={() => m.mutate()}>Submit address</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function EmploymentDialog({ current, onClose }: { current: string | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = React.useState({ status: current ?? "EMPLOYED", employer_name: "", job_title: "", city: "" });
  const set = (k: keyof typeof f, v: string) => setF((x) => ({ ...x, [k]: v }));
  const working = f.status === "EMPLOYED" || f.status === "SELF_EMPLOYED";
  const m = useMutation({
    mutationFn: () => post<{ note: string }>("/portal/employment", { status: f.status, employer_name: working ? f.employer_name || null : null, job_title: working ? f.job_title || null : null, city: f.city || null }),
    onSuccess: (r) => { toast.success(r.note); qc.invalidateQueries({ queryKey: ["portal-profile"] }); qc.invalidateQueries({ queryKey: ["portal-overview"] }); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader title="Update study or work status" description="Sharing this is voluntary. It is never used on its own to assess repayment (FR-EMP-07)." />
        <DialogBody>
          <Field label="Current status" htmlFor="e-st"><NativeSelect id="e-st" value={f.status} onChange={(e) => set("status", e.target.value)}>{EMP_STATES.map((s) => <option key={s} value={s}>{labelFor(s)}</option>)}</NativeSelect></Field>
          {working && (
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Employer or business" htmlFor="e-emp"><Input id="e-emp" maxLength={200} value={f.employer_name} onChange={(e) => set("employer_name", e.target.value)} /></Field>
              <Field label="Job title" htmlFor="e-job"><Input id="e-job" maxLength={120} value={f.job_title} onChange={(e) => set("job_title", e.target.value)} /></Field>
            </div>
          )}
          <Field label="City" htmlFor="e-city"><Input id="e-city" maxLength={80} value={f.city} onChange={(e) => set("city", e.target.value)} /></Field>
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter><Button variant="secondary" onClick={onClose}>Cancel</Button><Button loading={m.isPending} onClick={() => m.mutate()}>Submit update</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function PortalProfilePage() {
  const q = useQuery({ queryKey: ["portal-profile"], queryFn: () => get<PortalProfile>("/portal/profile") });
  const [dlg, setDlg] = React.useState<"address" | "employment" | null>(null);
  return (
    <div className="space-y-5">
      <PageHeader title="My profile" description="Keep your contact details current so your institution and bank can reach you. Changes you submit are recorded with their source." />
      <QueryBoundary query={q}>{(p) => (
        <>
          <Card>
            <CardHeader><div><CardTitle className="flex items-center gap-2"><UserRound className="h-4 w-4 text-teal" />Personal details</CardTitle>
              <CardDescription>To correct these, raise a correction request. Your record changes only after review.</CardDescription></div>
              <Button asChild size="sm" variant="secondary"><Link to="/portal/grievances?new=1&category=DATA_CORRECTION"><Pencil />Request correction</Link></Button></CardHeader>
            <CardContent><KeyValue cols={3} items={[
              { label: "Name", value: `${p.first_name} ${p.last_name}` }, { label: "DAPRO reference", value: <span className="font-mono">{p.dapro_ref}</span> },
              { label: "Date of birth", value: formatDate(p.dob) }, { label: "Email", value: p.email ?? "-" }, { label: "Mobile", value: p.mobile ?? "-" },
              { label: "Institution", value: p.college },
            ]} /></CardContent>
          </Card>

          <Card>
            <CardHeader><div><CardTitle className="flex items-center gap-2"><Home className="h-4 w-4 text-teal" />Addresses</CardTitle></div>
              <Button size="sm" onClick={() => setDlg("address")}>Update address</Button></CardHeader>
            <CardContent>{p.addresses.length ? (
              <ul className="grid gap-3 sm:grid-cols-2">{p.addresses.map((a) => (
                <li key={a.id} className="rounded-lg border p-3 text-sm">
                  <div className="mb-1 flex flex-wrap items-center gap-1.5"><span className="font-medium">{labelFor(a.kind)}</span><StatusBadge status={a.verification} /><Badge tone="outline">{labelFor(a.source)}</Badge></div>
                  <p>{a.line1}{a.line2 ? `, ${a.line2}` : ""}</p><p>{[a.city, a.state, a.postal_code].filter(Boolean).join(", ")} {a.country}</p>
                  <p className="mt-1 text-[11px] text-muted-foreground">Since {formatDate(a.effective_from)}</p>
                </li>))}</ul>
            ) : <p className="text-sm text-muted-foreground">No address on record. Please add your current address.</p>}</CardContent>
          </Card>

          <div className="grid gap-5 md:grid-cols-2">
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><GraduationCap className="h-4 w-4 text-teal" />Studies</CardTitle></CardHeader>
              <CardContent>{p.academic ? <KeyValue cols={2} items={[
                { label: "Programme", value: p.academic.programme ?? "-" }, { label: "Course", value: p.academic.course ?? "-" },
                { label: "Cohort", value: p.academic.cohort_year ?? "-" }, { label: "Enrolment", value: <StatusBadge status={p.academic.enrolment_status} /> },
                { label: "Expected completion", value: formatDate(p.academic.expected_completion) }, { label: "Completed", value: formatDate(p.academic.actual_completion) },
              ]} /> : <p className="text-sm text-muted-foreground">Your institution has not recorded academic details yet.</p>}</CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle className="flex items-center gap-2"><Briefcase className="h-4 w-4 text-teal" />Work status</CardTitle>
                <Button size="sm" variant="secondary" onClick={() => setDlg("employment")}>Update</Button></CardHeader>
              <CardContent>{p.employment ? <KeyValue cols={2} items={[
                { label: "Status", value: <StatusBadge status={p.employment.status} /> }, { label: "Employer", value: p.employment.employer_name ?? "-" },
                { label: "Job title", value: p.employment.job_title ?? "-" }, { label: "City", value: p.employment.city ?? "-" },
                { label: "Verification", value: <StatusBadge status={p.employment.verification} /> }, { label: "Reported", value: formatDate(p.employment.reported_on) },
              ]} /> : <p className="text-sm text-muted-foreground">Nothing reported yet. Sharing your status is optional.</p>}</CardContent>
            </Card>
          </div>
          {p.preferences.length > 0 && (
            <p className="text-xs text-muted-foreground">Contact preferences: {p.preferences.map((x) => `${labelFor(x.channel)} ${x.allowed ? "allowed" : "not allowed"}`).join(", ")}.</p>
          )}
          {dlg === "address" && <AddressDialog onClose={() => setDlg(null)} />}
          {dlg === "employment" && <EmploymentDialog current={p.employment?.status ?? null} onClose={() => setDlg(null)} />}
        </>
      )}</QueryBoundary>
    </div>
  );
}
