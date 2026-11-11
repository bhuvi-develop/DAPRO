import * as React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, UserPlus } from "lucide-react";
import { ApiError, post } from "@/api/client";
import { useAuth } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, NativeSelect } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { PageHeader } from "@/components/data/layout";
import { InlineError } from "@/components/data/states";
import { fetchColleges, type StudentRow } from "./shared";

const opt = (s: z.ZodString) => s.optional().or(z.literal(""));
const schema = z.object({
  college_org_id: z.string().min(1, "Select the college"),
  college_student_id: z.string().trim().min(2, "College student ID is required").max(60),
  first_name: z.string().trim().min(1, "First name is required").max(80),
  last_name: z.string().trim().min(1, "Last name is required").max(80),
  dob: opt(z.string()),
  gender: opt(z.string()),
  email: opt(z.string().email("Enter a valid email")),
  mobile: opt(z.string().regex(/^\+?[0-9 ]{8,16}$/, "Use 8-16 digits, optional leading +")),
  kyc_ref_last4: opt(z.string().regex(/^[0-9A-Za-z]{4}$/, "Exactly 4 letters or digits")),
  programme: opt(z.string()),
  course: opt(z.string()),
  cohort_year: opt(z.string().regex(/^(19|20)\d{2}$/, "Enter a 4-digit year")),
  expected_completion: opt(z.string()),
});
type Form = z.infer<typeof schema>;
interface Candidate { id: string; dapro_ref: string; full_name: string; college_student_id?: string }

export default function StudentCreatePage() {
  const nav = useNavigate();
  const me = useAuth((s) => s.me)!;
  const isCollege = me.org.type === "COLLEGE";
  const colleges = useQuery({ queryKey: ["orgs", "COLLEGE"], queryFn: fetchColleges, enabled: !isCollege });
  const [dups, setDups] = React.useState<Candidate[] | null>(null);
  const { register, handleSubmit, getValues, setError, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema), defaultValues: { college_org_id: isCollege ? me.org.id : "" },
  });
  const create = useMutation({
    mutationFn: (v: Form & { confirm_not_duplicate?: boolean }) => {
      const body: Record<string, unknown> = {};
      Object.entries(v).forEach(([k, val]) => { if (val !== "" && val !== undefined) body[k] = k === "cohort_year" ? Number(val) : val; });
      return post<StudentRow>("/students", body);
    },
    onSuccess: (s) => { toast.success(`Student registered as ${s.dapro_ref}`); nav(`/students/${s.id}`); },
    onError: (e) => {
      if (e instanceof ApiError && e.code === "POSSIBLE_DUPLICATE") setDups(e.details as unknown as Candidate[]);
      if (e instanceof ApiError && e.code === "DUPLICATE_STUDENT_ID") setError("college_student_id", { message: "This college student ID is already registered" });
    },
  });
  const sameId = create.error instanceof ApiError && create.error.code === "DUPLICATE_STUDENT_ID" ? (create.error.details as unknown as Candidate[]) : null;
  const showError = create.error && !(create.error instanceof ApiError && ["POSSIBLE_DUPLICATE", "DUPLICATE_STUDENT_ID"].includes(create.error.code));

  return (
    <div className="mx-auto max-w-4xl">
      <PageHeader title="Register student" description="Creates a DAPRO identity. College and bank identifiers are stored as external references (FR-STU-03)."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Students", to: "/students" }, { label: "Register" }]} />
      <form onSubmit={handleSubmit((v) => { setDups(null); create.mutate(v); })} noValidate>
        <Card>
          <CardHeader><div><CardTitle>Identity</CardTitle><CardDescription>Only client-approved identity fields are collected (FR-STU-02).</CardDescription></div></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field label="College" htmlFor="college" error={errors.college_org_id?.message} required>
              {isCollege ? <Input id="college" value={me.org.name} disabled /> : (
                <NativeSelect id="college" aria-invalid={!!errors.college_org_id} {...register("college_org_id")}>
                  <option value="">Select college</option>
                  {colleges.data?.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </NativeSelect>)}
            </Field>
            <Field label="College student ID" htmlFor="csid" error={errors.college_student_id?.message} hint="As issued by the college SIS" required>
              <Input id="csid" aria-invalid={!!errors.college_student_id} {...register("college_student_id")} />
            </Field>
            <Field label="First name" htmlFor="fn" error={errors.first_name?.message} required><Input id="fn" aria-invalid={!!errors.first_name} {...register("first_name")} /></Field>
            <Field label="Last name" htmlFor="ln" error={errors.last_name?.message} required><Input id="ln" aria-invalid={!!errors.last_name} {...register("last_name")} /></Field>
            <Field label="Date of birth" htmlFor="dob" error={errors.dob?.message} hint="Used for duplicate detection and bank loan validation"><Input id="dob" type="date" {...register("dob")} /></Field>
            <Field label="Gender" htmlFor="gender"><NativeSelect id="gender" {...register("gender")}><option value="">Not stated</option><option value="F">Female</option><option value="M">Male</option><option value="X">Other</option></NativeSelect></Field>
            <Field label="KYC reference (last 4)" htmlFor="kyc" error={errors.kyc_ref_last4?.message} hint="Full identifiers are never stored"><Input id="kyc" maxLength={4} {...register("kyc_ref_last4")} /></Field>
          </CardContent>
        </Card>
        <Card className="mt-4">
          <CardHeader><CardTitle>Contact and academic</CardTitle></CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <Field label="Email" htmlFor="email" error={errors.email?.message}><Input id="email" type="email" {...register("email")} /></Field>
            <Field label="Mobile" htmlFor="mobile" error={errors.mobile?.message} hint="Include country code, e.g. +91"><Input id="mobile" inputMode="tel" {...register("mobile")} /></Field>
            <Field label="Programme" htmlFor="prog" hint="e.g. B.E., MBA"><Input id="prog" {...register("programme")} /></Field>
            <Field label="Course" htmlFor="course"><Input id="course" {...register("course")} /></Field>
            <Field label="Cohort year" htmlFor="cohort" error={errors.cohort_year?.message}><Input id="cohort" inputMode="numeric" maxLength={4} {...register("cohort_year")} /></Field>
            <Field label="Expected completion" htmlFor="exp"><Input id="exp" type="date" {...register("expected_completion")} /></Field>
          </CardContent>
          <CardFooter className="flex-col items-stretch gap-3">
            {sameId && (
              <div role="alert" className="rounded-md border border-danger/20 bg-danger-soft p-3 text-sm text-danger">
                This college student ID is already registered:{" "}
                {sameId.map((c) => <Link key={c.id} className="font-medium underline" to={`/students/${c.id}`}>{c.full_name} ({c.dapro_ref})</Link>)}
              </div>
            )}
            {dups && (
              <div role="alert" className="rounded-md border border-warning/30 bg-warning-soft p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-[hsl(32_95%_30%)]"><AlertTriangle className="h-4 w-4" />Possible duplicate student</p>
                <p className="mt-1 text-xs text-muted-foreground">A record with the same name and date of birth exists. Check before creating a new identity (FR-STU-04).</p>
                <ul className="mt-2 space-y-1 text-sm">
                  {dups.map((d) => <li key={d.id}><Link to={`/students/${d.id}`} className="font-medium text-primary hover:underline" target="_blank" rel="noreferrer">{d.full_name}</Link> <span className="font-mono text-xs text-muted-foreground">{d.dapro_ref} {d.college_student_id ?? ""}</span></li>)}
                </ul>
                <div className="mt-3 flex flex-wrap gap-2">
                  <Button type="button" variant="secondary" size="sm" onClick={() => setDups(null)}>Cancel and review</Button>
                  <Button type="button" size="sm" loading={create.isPending} onClick={() => create.mutate({ ...getValues(), confirm_not_duplicate: true })}>Not a duplicate - create anyway</Button>
                </div>
                <p className="mt-2 text-[11px] text-muted-foreground">The pair will be queued for duplicate review.</p>
              </div>
            )}
            {showError && <InlineError error={create.error} />}
            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => nav("/students")}>Cancel</Button>
              <Button type="submit" loading={create.isPending && !dups}><UserPlus />Register student</Button>
            </div>
          </CardFooter>
        </Card>
      </form>
    </div>
  );
}
