import { useNavigate, useSearchParams } from "react-router-dom";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { get, post, type Page } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { EntitySelect, studentOptions } from "@/components/data/entity";
import { Field } from "@/components/data/feedback";
import { PageHeader } from "@/components/data/layout";
import { InlineError } from "@/components/data/states";
import { labelFor } from "@/components/data/status";
import { fetchCaseMeta } from "./types";

const schema = z.object({
  student_id: z.string({ required_error: "Choose the borrower" }).min(1, "Choose the borrower"),
  loan_id: z.string().optional(),
  category: z.string().min(1, "Choose a category"),
  priority: z.string().min(1),
  reason: z.string().min(5, "Describe the reason (at least 5 characters)").max(500),
  next_action: z.string().max(300).optional(),
  due_on: z.string().optional(),
});
type Form = z.infer<typeof schema>;

export default function CaseCreatePage() {
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const meta = useQuery({ queryKey: ["case-meta"], queryFn: fetchCaseMeta, staleTime: 600_000 });
  const { register, control, handleSubmit, watch, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { student_id: sp.get("student_id") ?? "", category: "REPAYMENT_FOLLOW_UP", priority: "MEDIUM", loan_id: sp.get("loan_id") ?? "" },
  });
  const studentId = watch("student_id");
  const loans = useQuery({
    queryKey: ["student-loans", studentId], enabled: !!studentId,
    queryFn: () => get<Page<{ id: string; bank_loan_ref: string; bank_name?: string; repayment_status: string }>>(`/loans?size=20&student_id=${studentId}`),
  });
  const create = useMutation({
    mutationFn: (v: Form) => post<{ id: string; case_ref: string }>("/cases", {
      ...v, loan_id: v.loan_id || undefined, due_on: v.due_on || undefined, next_action: v.next_action || undefined,
    }),
    onSuccess: (c) => { toast.success(`Case ${c.case_ref} opened`); nav(`/cases/${c.id}`); },
  });
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader title="Open a follow-up case" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Cases", to: "/cases" }, { label: "New" }]}
        description="Cases record why follow-up is needed, who owns it and what happens next (FR-CAS-01)." />
      <form onSubmit={handleSubmit((v) => create.mutate(v))} noValidate>
        <Card>
          <CardContent className="space-y-4">
            <Field label="Borrower" htmlFor="student" required error={errors.student_id?.message}>
              <Controller control={control} name="student_id" render={({ field }) => (
                <EntitySelect id="student" queryKey="students" value={field.value || null} onChange={(v) => field.onChange(v ?? "")}
                  fetchOptions={studentOptions} placeholder="Search by name, DAPRO ref or college ID" invalid={!!errors.student_id}
                  selectedLabel={sp.get("student_id") === field.value ? "Selected borrower" : undefined} />)} />
            </Field>
            <Field label="Loan account" htmlFor="loan" hint="Optional. Link the case to a specific bank loan where relevant.">
              <NativeSelect id="loan" disabled={!studentId || loans.isLoading} {...register("loan_id")}>
                <option value="">Not loan-specific</option>
                {loans.data?.items.map((l) => <option key={l.id} value={l.id}>{l.bank_loan_ref}{l.bank_name ? ` - ${l.bank_name}` : ""} ({labelFor(l.repayment_status)})</option>)}
              </NativeSelect>
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Category" htmlFor="category" required error={errors.category?.message}>
                <NativeSelect id="category" {...register("category")}>{(meta.data?.categories ?? []).map((c) => <option key={c} value={c}>{labelFor(c)}</option>)}</NativeSelect>
              </Field>
              <Field label="Priority" htmlFor="priority" required>
                <NativeSelect id="priority" {...register("priority")}>{(meta.data?.priorities ?? ["CRITICAL", "HIGH", "MEDIUM", "LOW"]).map((c) => <option key={c} value={c}>{labelFor(c)}</option>)}</NativeSelect>
              </Field>
            </div>
            <Field label="Reason" htmlFor="reason" required error={errors.reason?.message} hint="State the facts that justify follow-up. Avoid judgements about intent.">
              <Textarea id="reason" aria-invalid={!!errors.reason} {...register("reason")} />
            </Field>
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Next action" htmlFor="next" hint="For example: call borrower to confirm contact details.">
                <Input id="next" {...register("next_action")} />
              </Field>
              <Field label="Due date" htmlFor="due" hint="Leave empty to use the policy default for the priority.">
                <Input id="due" type="date" {...register("due_on")} />
              </Field>
            </div>
            <InlineError error={create.error} />
          </CardContent>
          <CardFooter className="justify-end">
            <Button type="button" variant="secondary" onClick={() => nav(-1)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Open case</Button>
          </CardFooter>
        </Card>
      </form>
    </div>
  );
}
