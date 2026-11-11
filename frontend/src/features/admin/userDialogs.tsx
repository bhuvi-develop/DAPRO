import * as React from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Copy, FlaskConical } from "lucide-react";
import { ApiError, api, get, post } from "@/api/client";
import { useAuth } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/misc";
import { Field } from "@/components/data/feedback";
import { InlineError } from "@/components/data/states";
import type { OrgRow, RoleRow, UnitRow, UserRow } from "./types";

type DP = { open: boolean; onOpenChange: (o: boolean) => void };
const schema = z.object({ email: z.string().email("Enter a valid email"), full_name: z.string().trim().min(2, "Required"), title: z.string().optional(),
  role_code: z.string().min(1, "Select a role"), org_id: z.string().optional(), org_unit_id: z.string().optional() });

export function InviteDialog({ open, onOpenChange }: DP) {
  const me = useAuth((s) => s.me)!;
  const qc = useQueryClient();
  const isPlatform = me.org.type === "PLATFORM";
  const [result, setResult] = React.useState<{ invite_url: string; delivery: string; expires_in_days: number } | null>(null);
  const roles = useQuery({ queryKey: ["admin-roles"], queryFn: () => get<RoleRow[]>("/admin/roles"), enabled: open });
  const orgs = useQuery({ queryKey: ["admin-orgs"], queryFn: () => get<OrgRow[]>("/admin/organizations"), enabled: open });
  const units = useQuery({ queryKey: ["admin-units"], queryFn: () => get<UnitRow[]>("/admin/org-units"), enabled: open });
  const { register, handleSubmit, watch, reset, formState: { errors } } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema), defaultValues: { org_id: isPlatform ? "" : me.org.id } });
  const orgId = watch("org_id") || me.org.id;
  const orgType = orgs.data?.find((o) => o.id === orgId)?.type ?? me.org.type;
  const m = useMutation({
    mutationFn: (v: z.infer<typeof schema>) => post<{ invite_url: string; delivery: string; expires_in_days: number }>("/admin/users/invite",
      Object.fromEntries(Object.entries(v).filter(([, x]) => x))),
    onSuccess: (r) => { setResult(r); qc.invalidateQueries({ queryKey: ["admin-users"] }); toast.success("Invitation created"); },
  });
  const close = (o: boolean) => { onOpenChange(o); if (!o) { setResult(null); reset(); m.reset(); } };
  const url = result ? `${window.location.origin}${result.invite_url}` : "";
  return (
    <Dialog open={open} onOpenChange={close}><DialogContent wide>
      <DialogHeader title="Invite user" description="Invitations do not grant access until the user verifies and sets a password (FR-IAM-04)." />
      {result ? (
        <DialogBody>
          <div className="rounded-md border border-warning/30 bg-warning-soft p-3 text-xs text-[hsl(32_95%_30%)]"><FlaskConical className="mr-1 inline h-3.5 w-3.5" />{result.delivery}</div>
          <Field label="One-time invitation link" htmlFor="inv-url" hint={`Shown only once. Expires in ${result.expires_in_days} days.`}>
            <div className="flex gap-2"><Input id="inv-url" readOnly value={url} data-testid="invite-url" className="font-mono text-xs" />
              <Button type="button" variant="secondary" onClick={() => { navigator.clipboard?.writeText(url); toast.success("Link copied"); }}><Copy />Copy</Button></div>
          </Field>
          <DialogFooter className="-mx-5 -mb-4 mt-2"><Button onClick={() => close(false)}>Done</Button></DialogFooter>
        </DialogBody>
      ) : (
        <form onSubmit={handleSubmit((v) => m.mutate(v))} noValidate>
          <DialogBody className="grid gap-4 sm:grid-cols-2">
            <Field label="Full name" htmlFor="i-n" error={errors.full_name?.message} required><Input id="i-n" {...register("full_name")} /></Field>
            <Field label="Work email" htmlFor="i-e" error={errors.email?.message} required><Input id="i-e" type="email" {...register("email")} /></Field>
            <Field label="Job title" htmlFor="i-t"><Input id="i-t" {...register("title")} /></Field>
            {isPlatform ? (
              <Field label="Organization" htmlFor="i-o" required><NativeSelect id="i-o" {...register("org_id")}><option value="">My organization</option>{orgs.data?.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}</NativeSelect></Field>
            ) : <Field label="Organization" htmlFor="i-o2"><Input id="i-o2" value={me.org.name} disabled /></Field>}
            <Field label="Role" htmlFor="i-r" error={errors.role_code?.message} hint="Least privilege: choose the narrowest role for the job" required>
              <NativeSelect id="i-r" {...register("role_code")}><option value="">Select role</option>
                {roles.data?.filter((r) => r.org_types.includes(orgType)).map((r) => <option key={r.code} value={r.code}>{r.name}</option>)}</NativeSelect></Field>
            <Field label="Scope unit" htmlFor="i-u" hint="Optional - limits data to this branch or region"><NativeSelect id="i-u" {...register("org_unit_id")}><option value="">Whole organization</option>
              {units.data?.filter((u) => u.org_id === orgId).map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}</NativeSelect></Field>
            <div className="sm:col-span-2"><InlineError error={m.error} /></div>
          </DialogBody>
          <DialogFooter><Button type="button" variant="secondary" onClick={() => close(false)}>Cancel</Button><Button type="submit" loading={m.isPending}>Create invitation</Button></DialogFooter>
        </form>
      )}
    </DialogContent></Dialog>
  );
}

/** Role change with segregation-of-duties enforcement surfaced from the API (RD 6.1). */
export function RolesDialog({ user, open, onOpenChange }: DP & { user: UserRow | null }) {
  const qc = useQueryClient();
  const roles = useQuery({ queryKey: ["admin-roles"], queryFn: () => get<RoleRow[]>("/admin/roles"), enabled: open });
  const orgs = useQuery({ queryKey: ["admin-orgs"], queryFn: () => get<OrgRow[]>("/admin/organizations"), enabled: open });
  const [sel, setSel] = React.useState<string[]>([]);
  const [reason, setReason] = React.useState("");
  React.useEffect(() => { if (user) { setSel(user.roles); setReason(""); } }, [user]);
  const orgType = orgs.data?.find((o) => o.id === user?.org_id)?.type;
  const m = useMutation({
    mutationFn: () => api(`/admin/users/${user!.id}/roles`, { method: "PUT", body: { role_codes: sel, reason } }),
    onSuccess: () => { toast.success("Roles updated"); qc.invalidateQueries({ queryKey: ["admin-users"] }); onOpenChange(false); },
  });
  const sod = m.error instanceof ApiError && m.error.code === "SOD_CONFLICT";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}><DialogContent>
      <DialogHeader title={`Change roles - ${user?.full_name ?? ""}`} description="Conflicting duties (for example user administration with case closure) are rejected." />
      <DialogBody>
        <ul className="space-y-2">{roles.data?.filter((r) => !orgType || r.org_types.includes(orgType)).map((r) => (
          <li key={r.code} className="flex items-start gap-2"><Checkbox id={`r-${r.code}`} checked={sel.includes(r.code)} onCheckedChange={(c) => setSel((s) => c ? [...s, r.code] : s.filter((x) => x !== r.code))} />
            <label htmlFor={`r-${r.code}`} className="text-sm leading-tight"><span className="font-medium">{r.name}</span><span className="block text-[11px] text-muted-foreground">{r.description}</span></label></li>))}</ul>
        <Field label="Reason" htmlFor="r-reason" hint="Recorded in the audit trail" required><Textarea id="r-reason" value={reason} onChange={(e) => setReason(e.target.value)} /></Field>
        {sod ? <div role="alert" className="rounded-md border border-danger/20 bg-danger-soft p-3 text-sm text-danger"><p className="font-medium">Segregation-of-duties conflict</p><p className="text-xs">{(m.error as ApiError).message}</p></div> : <InlineError error={m.error} />}
      </DialogBody>
      <DialogFooter><Button variant="secondary" onClick={() => onOpenChange(false)}>Cancel</Button><Button loading={m.isPending} disabled={!sel.length || reason.trim().length < 5} onClick={() => m.mutate()}>Save roles</Button></DialogFooter>
    </DialogContent></Dialog>
  );
}
