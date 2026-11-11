import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { post } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { InlineError } from "@/components/data/states";
import { titleCase } from "@/lib/utils";
import type { OrgRow, UnitRow } from "./types";

const o = (s: z.ZodString) => s.optional().or(z.literal(""));
const clean = (v: Record<string, unknown>) => Object.fromEntries(Object.entries(v).filter(([, x]) => x !== "" && x !== undefined));
type DP = { open: boolean; onOpenChange: (o: boolean) => void };

function useCreate(url: string, key: string, msg: string, done: () => void) {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (b: Record<string, unknown>) => post(url, b), onSuccess: () => { toast.success(msg); qc.invalidateQueries({ queryKey: [key] }); done(); } });
}

const orgSchema = z.object({ type: z.string(), code: z.string().regex(/^[A-Z0-9_-]{2,40}$/, "2-40 upper-case letters, digits, - or _"),
  name: z.string().trim().min(3, "At least 3 characters"), legal_name: o(z.string()), city: o(z.string()), state: o(z.string()), contact_email: o(z.string().email("Valid email")) });

export function CreateOrgDialog({ open, onOpenChange }: DP) {
  const { register, handleSubmit, reset, formState: { errors } } = useForm<z.infer<typeof orgSchema>>({ resolver: zodResolver(orgSchema), defaultValues: { type: "COLLEGE" } });
  const m = useCreate("/admin/organizations", "admin-orgs", "Organization created", () => { onOpenChange(false); reset(); });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}><DialogContent wide>
      <DialogHeader title="New organization" description="Onboarding requires an approved agreement before live data is shared (UC-01)." />
      <form onSubmit={handleSubmit((v) => m.mutate(clean(v)))} noValidate>
        <DialogBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Type" htmlFor="o-t" required><NativeSelect id="o-t" {...register("type")}>{["COLLEGE", "BANK", "NBFC", "AGENCY"].map((t) => <option key={t} value={t}>{titleCase(t)}</option>)}</NativeSelect></Field>
          <Field label="Code" htmlFor="o-c" error={errors.code?.message} hint="Short unique code, e.g. NBIT" required><Input id="o-c" {...register("code")} /></Field>
          <Field label="Name" htmlFor="o-n" error={errors.name?.message} required><Input id="o-n" {...register("name")} /></Field>
          <Field label="Legal name" htmlFor="o-l"><Input id="o-l" {...register("legal_name")} /></Field>
          <Field label="City" htmlFor="o-city"><Input id="o-city" {...register("city")} /></Field>
          <Field label="State" htmlFor="o-s"><Input id="o-s" {...register("state")} /></Field>
          <div className="sm:col-span-2"><Field label="Contact email" htmlFor="o-e" error={errors.contact_email?.message}><Input id="o-e" type="email" {...register("contact_email")} /></Field></div>
          <div className="sm:col-span-2"><InlineError error={m.error} /></div>
        </DialogBody>
        <DialogFooter><Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" loading={m.isPending}>Create</Button></DialogFooter>
      </form>
    </DialogContent></Dialog>
  );
}

const unitSchema = z.object({ org_id: z.string().min(1, "Select organization"), parent_id: o(z.string()), kind: z.string(),
  code: z.string().regex(/^[A-Z0-9_-]{2,40}$/, "2-40 upper-case letters, digits, - or _"), name: z.string().trim().min(2, "Required"), city: o(z.string()) });

export function CreateUnitDialog({ open, onOpenChange, orgs, units }: DP & { orgs: OrgRow[]; units: UnitRow[] }) {
  const { register, handleSubmit, reset, watch, formState: { errors } } = useForm<z.infer<typeof unitSchema>>({ resolver: zodResolver(unitSchema), defaultValues: { kind: "BRANCH", org_id: "" } });
  const m = useCreate("/admin/org-units", "admin-units", "Unit created", () => { onOpenChange(false); reset(); });
  const orgId = watch("org_id");
  return (
    <Dialog open={open} onOpenChange={onOpenChange}><DialogContent wide>
      <DialogHeader title="New branch or unit" description="Branch, region, campus and team units drive scope for users assigned to them (FR-ORG-02)." />
      <form onSubmit={handleSubmit((v) => m.mutate(clean(v)))} noValidate>
        <DialogBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Organization" htmlFor="u-o" error={errors.org_id?.message} required><NativeSelect id="u-o" {...register("org_id")}><option value="">Select</option>{orgs.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</NativeSelect></Field>
          <Field label="Kind" htmlFor="u-k" required><NativeSelect id="u-k" {...register("kind")}>{["BRANCH", "REGION", "CAMPUS", "DEPARTMENT", "TEAM"].map((k) => <option key={k} value={k}>{titleCase(k)}</option>)}</NativeSelect></Field>
          <Field label="Parent unit" htmlFor="u-p" hint="Optional - e.g. the region of a branch"><NativeSelect id="u-p" {...register("parent_id")}><option value="">None (top level)</option>{units.filter((u) => u.org_id === orgId).map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}</NativeSelect></Field>
          <Field label="Code" htmlFor="u-c" error={errors.code?.message} required><Input id="u-c" {...register("code")} /></Field>
          <Field label="Name" htmlFor="u-n" error={errors.name?.message} required><Input id="u-n" {...register("name")} /></Field>
          <Field label="City" htmlFor="u-city"><Input id="u-city" {...register("city")} /></Field>
          <div className="sm:col-span-2"><InlineError error={m.error} /></div>
        </DialogBody>
        <DialogFooter><Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" loading={m.isPending}>Create</Button></DialogFooter>
      </form>
    </DialogContent></Dialog>
  );
}

const PURPOSES = ["MONITORING", "ENGAGEMENT", "FOLLOW_UP"];
const agrSchema = z.object({ reference: z.string().trim().min(3, "Required"), college_org_id: z.string().min(1, "Select college"),
  bank_org_id: z.string().min(1, "Select bank"), purposes: z.array(z.string()).min(1, "Choose at least one purpose"),
  effective_from: z.string().min(1, "Required"), effective_to: o(z.string()), notes: o(z.string()) });

export function CreateAgreementDialog({ open, onOpenChange, orgs }: DP & { orgs: OrgRow[] }) {
  const { register, handleSubmit, reset, formState: { errors } } = useForm<z.infer<typeof agrSchema>>({ resolver: zodResolver(agrSchema), defaultValues: { purposes: ["MONITORING"] } });
  const m = useCreate("/admin/sharing-agreements", "admin-agreements", "Agreement recorded as pending legal approval", () => { onOpenChange(false); reset(); });
  return (
    <Dialog open={open} onOpenChange={onOpenChange}><DialogContent wide>
      <DialogHeader title="New data-sharing agreement" description="Cross-organization access is denied unless an agreement allows the purpose (FR-ORG-04). New agreements start pending legal approval." />
      <form onSubmit={handleSubmit((v) => m.mutate(clean(v)))} noValidate>
        <DialogBody className="grid gap-4 sm:grid-cols-2">
          <Field label="Reference" htmlFor="g-r" error={errors.reference?.message} required><Input id="g-r" {...register("reference")} /></Field>
          <div />
          <Field label="College" htmlFor="g-c" error={errors.college_org_id?.message} required><NativeSelect id="g-c" {...register("college_org_id")}><option value="">Select</option>{orgs.filter((x) => x.type === "COLLEGE").map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</NativeSelect></Field>
          <Field label="Bank" htmlFor="g-b" error={errors.bank_org_id?.message} required><NativeSelect id="g-b" {...register("bank_org_id")}><option value="">Select</option>{orgs.filter((x) => x.type === "BANK" || x.type === "NBFC").map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</NativeSelect></Field>
          <fieldset className="sm:col-span-2"><legend className="text-[13px] font-medium">Purposes <span className="text-danger">*</span></legend>
            <div className="mt-1.5 flex flex-wrap gap-4">{PURPOSES.map((p) => <label key={p} className="flex items-center gap-2 text-sm"><input type="checkbox" value={p} className="h-4 w-4 accent-[#1D4ED8]" {...register("purposes")} />{titleCase(p)}</label>)}</div>
            {errors.purposes && <p role="alert" className="mt-1 text-[11px] font-medium text-danger">{errors.purposes.message}</p>}</fieldset>
          <Field label="Effective from" htmlFor="g-f" error={errors.effective_from?.message} required><Input id="g-f" type="date" {...register("effective_from")} /></Field>
          <Field label="Effective to" htmlFor="g-t"><Input id="g-t" type="date" {...register("effective_to")} /></Field>
          <div className="sm:col-span-2"><Field label="Notes" htmlFor="g-n"><Textarea id="g-n" {...register("notes")} /></Field></div>
          <div className="sm:col-span-2"><InlineError error={m.error} /></div>
        </DialogBody>
        <DialogFooter><Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button><Button type="submit" loading={m.isPending}>Record agreement</Button></DialogFooter>
      </form>
    </DialogContent></Dialog>
  );
}
