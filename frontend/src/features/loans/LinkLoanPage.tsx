import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, GitCompareArrows, Landmark, ShieldQuestion } from "lucide-react";
import { get, post } from "@/api/client";
import { useAuth } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, NativeSelect } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { EntitySelect, studentOptions } from "@/components/data/entity";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { InlineError } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { useOrgs } from "./shared";

interface LinkResult { loan_id: string; link_status: string; sync_batch_id?: string; sync_status?: string; message?: string;
  validation: { name_match?: boolean; dob_match?: boolean; bank_name?: string; dapro_name?: string; source?: string } }

export default function LinkLoanPage() {
  const me = useAuth((s) => s.me)!;
  const [sp] = useSearchParams();
  const [studentId, setStudentId] = React.useState<string | null>(sp.get("student_id"));
  const pre = useQuery({ queryKey: ["student-label", sp.get("student_id")], enabled: !!sp.get("student_id"),
    queryFn: () => get<{ full_name: string; dapro_ref: string }>(`/students/${sp.get("student_id")}`) });
  const banks = useOrgs("BANK");
  const ownBank = me.org.type === "BANK" || me.org.type === "NBFC";
  const bankOptions = ownBank ? [{ id: me.org.id, name: me.org.name }] : (banks.data ?? []);
  const [bankId, setBankId] = React.useState<string>(ownBank ? me.org.id : "");
  const [ref, setRef] = React.useState("");
  const [touched, setTouched] = React.useState(false);
  const m = useMutation({
    mutationFn: () => post<LinkResult>("/loans/link", { student_id: studentId, bank_org_id: bankId, bank_loan_ref: ref.trim() }),
    onSuccess: (r) => toast[r.link_status === "LINKED" ? "success" : "warning"](r.link_status === "LINKED" ? "Loan linked and synchronized" : "Sent for human review"),
  });
  const errors = { student: !studentId ? "Select the student" : undefined, bank: !bankId ? "Select the lending bank" : undefined,
    ref: ref.trim().length < 4 ? "Enter the bank loan reference" : undefined };
  const valid = !errors.student && !errors.bank && !errors.ref;
  const submit = (e: React.FormEvent) => { e.preventDefault(); setTouched(true); if (valid) m.mutate(); };
  const r = m.data;
  return (
    <div className="space-y-6">
      <PageHeader title="Link a bank loan" description="Link a student to a bank-owned loan account using the bank reference. DAPRO validates the reference with the bank and never guesses a link."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Loan accounts", to: "/loans" }, { label: "Link loan" }]} />
      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <Card>
          <CardHeader><div><CardTitle>Loan reference</CardTitle><CardDescription>Validation: the bank reference must exist and the borrower name and date of birth must match exactly.</CardDescription></div></CardHeader>
          <CardContent>
            <form onSubmit={submit} className="space-y-4" noValidate>
              <Field label="Student" htmlFor="student" required error={touched ? errors.student : undefined} hint="Search by name, DAPRO reference or college ID.">
                <EntitySelect id="student" queryKey="students" value={studentId} onChange={(v) => setStudentId(v)} fetchOptions={studentOptions}
                  selectedLabel={pre.data ? `${pre.data.full_name} (${pre.data.dapro_ref})` : undefined} invalid={touched && !!errors.student} />
              </Field>
              <Field label="Lending bank" htmlFor="bank" required error={touched ? errors.bank : undefined}>
                <NativeSelect id="bank" value={bankId} onChange={(e) => setBankId(e.target.value)} disabled={ownBank}>
                  <option value="">Select bank</option>
                  {bankOptions.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                </NativeSelect>
              </Field>
              <Field label="Bank loan reference" htmlFor="ref" required error={touched ? errors.ref : undefined} hint="As shown in the bank loan system, for example ANB-EDU-2021-00123.">
                <Input id="ref" className="font-mono" value={ref} onChange={(e) => setRef(e.target.value.toUpperCase())} aria-invalid={touched && !!errors.ref} />
              </Field>
              <InlineError error={m.error} />
              <Button type="submit" loading={m.isPending}><Landmark />Validate and link</Button>
            </form>
          </CardContent>
        </Card>
        <Card aria-live="polite">
          <CardHeader><CardTitle>Result</CardTitle></CardHeader>
          <CardContent>
            {!r && <p className="text-sm text-muted-foreground">The validation result and first bank synchronization appear here.</p>}
            {r && r.link_status === "LINKED" && (
              <div className="space-y-3">
                <p className="flex items-center gap-2 font-semibold text-success"><CheckCircle2 className="h-5 w-5" />Linked to bank loan</p>
                <KeyValue cols={1} items={[{ label: "Link status", value: <StatusBadge status={r.link_status} /> },
                  { label: "First sync", value: <StatusBadge status={r.sync_status} /> },
                  { label: "Validation", value: `Name ${r.validation.name_match ? "matched" : "mismatch"}, date of birth ${r.validation.dob_match ? "matched" : "mismatch"} (${r.validation.source ?? "bank"})` }]} />
                <Button asChild className="w-full"><Link to={`/loans/${r.loan_id}`}>Open loan details</Link></Button>
              </div>
            )}
            {r && r.link_status === "PENDING_REVIEW" && (
              <div className="space-y-3">
                <p className="flex items-center gap-2 font-semibold text-warning"><ShieldQuestion className="h-5 w-5" />Held for human review</p>
                <p className="text-sm text-muted-foreground">{r.message ?? "Identity did not match exactly."} DAPRO never links on a partial match; a reconciliation reviewer decides.</p>
                <KeyValue cols={1} items={[{ label: "Name at bank", value: r.validation.bank_name ?? "-" }, { label: "Name in DAPRO", value: r.validation.dapro_name ?? "-" },
                  { label: "Date of birth", value: r.validation.dob_match ? "Matched" : "Mismatch" }]} />
                <Button asChild variant="secondary" className="w-full"><Link to="/reconciliation?kind=AMBIGUOUS_LINK"><GitCompareArrows />Open reconciliation queue</Link></Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
