import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api, post } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/misc";
import { Field } from "@/components/data/feedback";
import { InlineError } from "@/components/data/states";
import { titleCase } from "@/lib/utils";
import { ADDRESS_KINDS, ADDRESS_SOURCES, LIFECYCLE, METHODS, type StudentRow } from "./shared";

const o = (s: z.ZodString) => s.optional().or(z.literal(""));
const clean = (v: Record<string, unknown>) => Object.fromEntries(Object.entries(v).filter(([, x]) => x !== "" && x !== undefined));

export function useSave(studentId: string, done: () => void, msg: string, fn: (b: Record<string, unknown>) => Promise<unknown>) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => { toast.success(msg); qc.invalidateQueries({ queryKey: ["student360", studentId] }); qc.invalidateQueries({ queryKey: ["student-history", studentId] }); done(); },
  });
}

const addrSchema = z.object({
  kind: z.string().min(1), line1: z.string().trim().min(3, "At least 3 characters"), line2: o(z.string()),
  city: z.string().trim().min(2, "City is required"), state: o(z.string()), postal_code: o(z.string().max(12)),
  country: z.string().trim().length(2, "2-letter ISO code"), source_type: z.string(), effective_from: o(z.string()),
  notes: o(z.string().max(500)), request_verification: z.boolean(), verification_method: o(z.string()),
});

export function AddAddressDialog({ studentId, open, onOpenChange }: { studentId: string; open: boolean; onOpenChange: (o: boolean) => void }) {
  const { register, handleSubmit, watch, setValue, reset, formState: { errors } } = useForm<z.infer<typeof addrSchema>>({
    resolver: zodResolver(addrSchema), defaultValues: { kind: "CURRENT", country: "IN", source_type: "STAFF_ENTERED", request_verification: false, verification_method: "DOCUMENT" },
  });
  const m = useSave(studentId, () => { onOpenChange(false); reset(); }, "Address recorded. The previous address is kept in history.",
    (b) => post(`/students/${studentId}/addresses`, b));
  const rv = watch("request_verification");
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent wide>
        <DialogHeader title="Add address" description="A new address never overwrites the previous one; it is superseded and kept in history (FR-ADR-03)." />
        <form onSubmit={handleSubmit((v) => m.mutate(clean({ ...v, verification_method: v.request_verification ? v.verification_method : undefined })))} noValidate>
          <DialogBody className="grid gap-4 sm:grid-cols-2">
            <Field label="Address type" htmlFor="a-kind" required><NativeSelect id="a-kind" {...register("kind")}>{ADDRESS_KINDS.map((k) => <option key={k} value={k}>{titleCase(k)}</option>)}</NativeSelect></Field>
            <Field label="Source" htmlFor="a-src" hint="Who supplied this address" required><NativeSelect id="a-src" {...register("source_type")}>{ADDRESS_SOURCES.map((k) => <option key={k} value={k}>{titleCase(k)}</option>)}</NativeSelect></Field>
            <div className="sm:col-span-2"><Field label="Address line 1" htmlFor="a-l1" error={errors.line1?.message} required><Input id="a-l1" aria-invalid={!!errors.line1} {...register("line1")} /></Field></div>
            <div className="sm:col-span-2"><Field label="Address line 2" htmlFor="a-l2"><Input id="a-l2" {...register("line2")} /></Field></div>
            <Field label="City" htmlFor="a-city" error={errors.city?.message} required><Input id="a-city" aria-invalid={!!errors.city} {...register("city")} /></Field>
            <Field label="State / region" htmlFor="a-state"><Input id="a-state" {...register("state")} /></Field>
            <Field label="Postal code" htmlFor="a-pc"><Input id="a-pc" {...register("postal_code")} /></Field>
            <Field label="Country" htmlFor="a-cty" error={errors.country?.message} hint="ISO code, e.g. IN, US" required><Input id="a-cty" maxLength={2} {...register("country")} /></Field>
            <Field label="Effective from" htmlFor="a-eff"><Input id="a-eff" type="date" {...register("effective_from")} /></Field>
            <div className="flex items-center gap-2 pt-6"><Checkbox id="a-rv" checked={rv} onCheckedChange={(c) => setValue("request_verification", c === true)} /><label htmlFor="a-rv" className="text-sm">Request verification now</label></div>
            {rv && <Field label="Verification method" htmlFor="a-m"><NativeSelect id="a-m" {...register("verification_method")}>{METHODS.map((k) => <option key={k} value={k}>{titleCase(k)}</option>)}</NativeSelect></Field>}
            <div className="sm:col-span-2"><Field label="Notes" htmlFor="a-notes"><Textarea id="a-notes" {...register("notes")} /></Field></div>
            <div className="sm:col-span-2"><InlineError error={m.error} /></div>
          </DialogBody>
          <DialogFooter><Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" loading={m.isPending}>Save address</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

const empSchema = z.object({ status: z.string().min(1), employer_name: o(z.string().max(160)), job_title: o(z.string().max(120)), sector: o(z.string()),
  city: o(z.string()), country: o(z.string().length(2, "2-letter ISO code")), source: z.string(), effective_from: o(z.string()), notes: o(z.string().max(500)) });

export function EmploymentDialog({ studentId, open, onOpenChange }: { studentId: string; open: boolean; onOpenChange: (o: boolean) => void }) {
  const { register, handleSubmit, reset, formState: { errors } } = useForm<z.infer<typeof empSchema>>({ resolver: zodResolver(empSchema), defaultValues: { status: "EMPLOYED", source: "STAFF_ENTERED" } });
  const m = useSave(studentId, () => { onOpenChange(false); reset(); }, "Post-study status recorded", (b) => post(`/students/${studentId}/employment`, b));
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent wide>
        <DialogHeader title="Record post-study status" description="Employment is time-bound and source-labelled. It is never used on its own to classify default (FR-EMP-07). No income is collected (OD-10)." />
        <form onSubmit={handleSubmit((v) => m.mutate(clean(v)))} noValidate>
          <DialogBody className="grid gap-4 sm:grid-cols-2">
            <Field label="Status" htmlFor="e-st" required><NativeSelect id="e-st" {...register("status")}>{LIFECYCLE.map((k) => <option key={k} value={k}>{titleCase(k)}</option>)}</NativeSelect></Field>
            <Field label="Source" htmlFor="e-src" required><NativeSelect id="e-src" {...register("source")}>{["STAFF_ENTERED", "BORROWER_REPORTED", "COLLEGE_PROVIDED"].map((k) => <option key={k} value={k}>{titleCase(k)}</option>)}</NativeSelect></Field>
            <Field label="Employer / institution" htmlFor="e-emp"><Input id="e-emp" {...register("employer_name")} /></Field>
            <Field label="Job title" htmlFor="e-job"><Input id="e-job" {...register("job_title")} /></Field>
            <Field label="Sector" htmlFor="e-sec"><Input id="e-sec" {...register("sector")} /></Field>
            <Field label="City" htmlFor="e-city"><Input id="e-city" {...register("city")} /></Field>
            <Field label="Country" htmlFor="e-cty" error={errors.country?.message} hint="ISO code"><Input id="e-cty" maxLength={2} {...register("country")} /></Field>
            <Field label="Effective from" htmlFor="e-eff"><Input id="e-eff" type="date" {...register("effective_from")} /></Field>
            <div className="sm:col-span-2"><Field label="Notes" htmlFor="e-notes"><Textarea id="e-notes" {...register("notes")} /></Field></div>
            <div className="sm:col-span-2"><InlineError error={m.error} /></div>
          </DialogBody>
          <DialogFooter><Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" loading={m.isPending}>Save</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

const acadSchema = z.object({ programme: z.string().trim().min(2, "Required"), course: z.string().trim().min(2, "Required"), specialization: o(z.string()),
  cohort_year: z.string().regex(/^(19|20)\d{2}$/, "4-digit year"), enrolment_status: z.string(), start_date: o(z.string()),
  expected_completion: o(z.string()), actual_completion: o(z.string()) });

export function AcademicDialog({ studentId, open, onOpenChange }: { studentId: string; open: boolean; onOpenChange: (o: boolean) => void }) {
  const { register, handleSubmit, reset, formState: { errors } } = useForm<z.infer<typeof acadSchema>>({ resolver: zodResolver(acadSchema), defaultValues: { enrolment_status: "ENROLLED" } });
  const m = useSave(studentId, () => { onOpenChange(false); reset(); }, "Academic status recorded", (b) => post(`/students/${studentId}/academic`, { ...b, cohort_year: Number(b.cohort_year) }));
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent wide>
        <DialogHeader title="Record academic status" description="The college SIS remains the system of record for academic data (OX-10)." />
        <form onSubmit={handleSubmit((v) => m.mutate(clean(v)))} noValidate>
          <DialogBody className="grid gap-4 sm:grid-cols-2">
            <Field label="Programme" htmlFor="c-p" error={errors.programme?.message} required><Input id="c-p" {...register("programme")} /></Field>
            <Field label="Course" htmlFor="c-c" error={errors.course?.message} required><Input id="c-c" {...register("course")} /></Field>
            <Field label="Specialization" htmlFor="c-s"><Input id="c-s" {...register("specialization")} /></Field>
            <Field label="Cohort year" htmlFor="c-y" error={errors.cohort_year?.message} required><Input id="c-y" maxLength={4} {...register("cohort_year")} /></Field>
            <Field label="Enrolment status" htmlFor="c-st" hint="COMPLETED marks the student as graduated" required>
              <NativeSelect id="c-st" {...register("enrolment_status")}>{["ENROLLED", "ON_LEAVE", "COMPLETED", "DISCONTINUED", "TRANSFERRED"].map((k) => <option key={k} value={k}>{titleCase(k)}</option>)}</NativeSelect></Field>
            <Field label="Start date" htmlFor="c-sd"><Input id="c-sd" type="date" {...register("start_date")} /></Field>
            <Field label="Expected completion" htmlFor="c-ec"><Input id="c-ec" type="date" {...register("expected_completion")} /></Field>
            <Field label="Actual completion" htmlFor="c-ac"><Input id="c-ac" type="date" {...register("actual_completion")} /></Field>
            <div className="sm:col-span-2"><InlineError error={m.error} /></div>
          </DialogBody>
          <DialogFooter><Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" loading={m.isPending}>Save</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

const editSchema = z.object({ first_name: z.string().trim().min(1, "Required").max(80), last_name: z.string().trim().min(1, "Required").max(80),
  dob: o(z.string()), gender: o(z.string()), kyc_ref_last4: o(z.string().regex(/^[0-9A-Za-z]{4}$/, "Exactly 4 letters or digits")),
  reason: z.string().trim().min(5, "Give a reason of at least 5 characters") });

/** Correction with mandatory reason; prior values are retained (FR-STU-08, BR-14). Uses If-Match for concurrency. */
export function EditStudentDialog({ s, open, onOpenChange }: { s: StudentRow; open: boolean; onOpenChange: (o: boolean) => void }) {
  const { register, handleSubmit, reset, formState: { errors } } = useForm<z.infer<typeof editSchema>>({ resolver: zodResolver(editSchema),
    values: { first_name: s.first_name, last_name: s.last_name, dob: s.dob ?? "", gender: s.gender ?? "", kyc_ref_last4: s.kyc_ref_last4 ?? "", reason: "" } });
  const m = useSave(s.id, () => { onOpenChange(false); reset(); }, "Record corrected. Previous values are kept in history.",
    (b) => api(`/students/${s.id}`, { method: "PATCH", body: b, headers: { "If-Match": String(s.version) } }));
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent wide>
        <DialogHeader title="Correct student record" description="Every change records the previous value, the new value, who changed it and why." />
        <form onSubmit={handleSubmit((v) => {
          const body: Record<string, unknown> = { reason: v.reason };
          (["first_name", "last_name", "dob", "gender", "kyc_ref_last4"] as const).forEach((k) => {
            const cur = (s[k] ?? "") as string; if ((v[k] ?? "") !== cur && v[k] !== "") body[k] = v[k];
          });
          m.mutate(body);
        })} noValidate>
          <DialogBody className="grid gap-4 sm:grid-cols-2">
            <Field label="First name" htmlFor="ed-fn" error={errors.first_name?.message} required><Input id="ed-fn" {...register("first_name")} /></Field>
            <Field label="Last name" htmlFor="ed-ln" error={errors.last_name?.message} required><Input id="ed-ln" {...register("last_name")} /></Field>
            <Field label="Date of birth" htmlFor="ed-dob" hint={s.dob_masked ? "Masked for your role - leave empty to keep" : undefined}><Input id="ed-dob" type="date" {...register("dob")} /></Field>
            <Field label="Gender" htmlFor="ed-g"><NativeSelect id="ed-g" {...register("gender")}><option value="">Not stated</option><option value="F">Female</option><option value="M">Male</option><option value="X">Other</option></NativeSelect></Field>
            <Field label="KYC reference (last 4)" htmlFor="ed-k" error={errors.kyc_ref_last4?.message}><Input id="ed-k" maxLength={4} {...register("kyc_ref_last4")} /></Field>
            <div className="sm:col-span-2"><Field label="Reason for change" htmlFor="ed-r" error={errors.reason?.message} hint="Recorded in the correction history and audit trail" required><Textarea id="ed-r" {...register("reason")} /></Field></div>
            <div className="sm:col-span-2"><InlineError error={m.error} /></div>
          </DialogBody>
          <DialogFooter><Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" loading={m.isPending}>Save correction</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/** Small generic dialog: a method selector or free-text reason posted to an endpoint. */
export function SimpleActionDialog({ studentId, open, onOpenChange, title, description, url, kind, success }: {
  studentId: string; open: boolean; onOpenChange: (o: boolean) => void; title: string; description: string; url: string;
  kind: "method" | "reason" | "notes"; success: string;
}) {
  const [val, setVal] = React.useState(kind === "method" ? "DOCUMENT" : "");
  const m = useSave(studentId, () => { onOpenChange(false); setVal(kind === "method" ? "DOCUMENT" : ""); }, success, (b) => post(url, b));
  const minLen = kind === "reason" ? 5 : 3;
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader title={title} description={description} />
        <DialogBody>
          {kind === "method" ? (
            <Field label="Verification method" htmlFor="sa-m"><NativeSelect id="sa-m" value={val} onChange={(e) => setVal(e.target.value)}>{METHODS.map((k) => <option key={k} value={k}>{titleCase(k)}</option>)}</NativeSelect></Field>
          ) : (
            <Field label={kind === "reason" ? "Reason" : "Notes"} htmlFor="sa-t" hint={`At least ${minLen} characters`} required><Textarea id="sa-t" value={val} onChange={(e) => setVal(e.target.value)} /></Field>
          )}
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button loading={m.isPending} disabled={kind !== "method" && val.trim().length < minLen} onClick={() => m.mutate({ [kind]: val.trim() })}>Confirm</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
