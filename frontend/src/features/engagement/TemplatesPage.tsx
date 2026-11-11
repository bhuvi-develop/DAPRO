import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { FilePlus2, ShieldCheck } from "lucide-react";
import { get, post } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Input, NativeSelect, Textarea } from "@/components/ui/input";
import { Checkbox, Label } from "@/components/ui/misc";
import { Field } from "@/components/data/feedback";
import { PageHeader } from "@/components/data/layout";
import { InlineError, QueryBoundary } from "@/components/data/states";
import { StatusBadge, labelFor } from "@/components/data/status";
import { formatDateTime } from "@/lib/utils";
import type { Template } from "./types";

const PURPOSES = ["REMINDER", "UPDATE_REQUEST", "GRIEVANCE_ACK", "GUARANTOR_NOTICE", "GENERAL"];

function TemplateDialog({ base, onClose }: { base: Template | null; onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = React.useState({ code: base?.code ?? "", name: base?.name ?? "", channel: base?.channel ?? "EMAIL", purpose: base?.purpose ?? "GENERAL", subject: base?.subject ?? "", body: base?.body ?? "", shared: !base?.org_id && !!base });
  const set = (k: string, v: string | boolean) => setF((x) => ({ ...x, [k]: v }));
  const m = useMutation({
    mutationFn: () => post("/templates", { ...f, subject: f.subject || null }),
    onSuccess: () => { toast.success("Draft template saved. A second user must approve it before use."); qc.invalidateQueries({ queryKey: ["templates"] }); onClose(); },
  });
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent wide>
        <DialogHeader title={base ? `New version of ${base.code}` : "New template"} description="Templates are versioned and need approval by the responsible institution (FR-COM-03)." />
        <DialogBody>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Code" htmlFor="t-code" required hint="Upper case, for example EMI_REMINDER."><Input id="t-code" disabled={!!base} value={f.code} onChange={(e) => set("code", e.target.value.toUpperCase().replace(/[^A-Z0-9_]/g, ""))} /></Field>
            <Field label="Name" htmlFor="t-name" required><Input id="t-name" value={f.name} onChange={(e) => set("name", e.target.value)} /></Field>
            <Field label="Channel" htmlFor="t-ch"><NativeSelect id="t-ch" value={f.channel} onChange={(e) => set("channel", e.target.value)}><option value="EMAIL">Email</option><option value="SMS">SMS</option></NativeSelect></Field>
            <Field label="Purpose" htmlFor="t-pur"><NativeSelect id="t-pur" value={f.purpose} onChange={(e) => set("purpose", e.target.value)}>{PURPOSES.map((p) => <option key={p} value={p}>{labelFor(p)}</option>)}</NativeSelect></Field>
          </div>
          {f.channel === "EMAIL" && <Field label="Subject" htmlFor="t-subj"><Input id="t-subj" value={f.subject} onChange={(e) => set("subject", e.target.value)} /></Field>}
          <Field label="Body" htmlFor="t-body" required hint="Placeholders: {name} {bank} {amount} {due_date} {ref} {agreement_ref}. Use neutral, respectful language.">
            <Textarea id="t-body" className="min-h-[140px]" value={f.body} onChange={(e) => set("body", e.target.value)} />
          </Field>
          <div className="flex items-center gap-2"><Checkbox id="t-shared" checked={f.shared} onCheckedChange={(v) => set("shared", v === true)} /><Label htmlFor="t-shared">Shared across organizations in this programme</Label></div>
          <InlineError error={m.error} />
        </DialogBody>
        <DialogFooter><Button variant="secondary" onClick={onClose}>Cancel</Button><Button loading={m.isPending} disabled={f.code.length < 3 || !f.name || f.body.length < 10} onClick={() => m.mutate()}>Save draft</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function TemplatesPage() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["templates"], queryFn: () => get<{ items: Template[] }>("/templates") });
  const [dlg, setDlg] = React.useState<Template | null | undefined>(undefined);
  const approve = useMutation({
    mutationFn: (id: string) => post(`/templates/${id}/approve`),
    onSuccess: () => { toast.success("Template approved"); qc.invalidateQueries({ queryKey: ["templates"] }); },
    onError: (e: Error) => toast.error(e.message),
  });
  return (
    <div>
      <PageHeader title="Notification templates" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Templates" }]}
        description="Approved, versioned templates. The author cannot approve their own version."
        actions={<Button onClick={() => setDlg(null)}><FilePlus2 />New template</Button>} />
      <QueryBoundary query={q}>{(d) => {
        const groups = d.items.reduce<Record<string, Template[]>>((a, t) => { (a[t.code] ??= []).push(t); return a; }, {});
        return (
          <div className="grid gap-4 lg:grid-cols-2">
            {Object.entries(groups).map(([code, vs]) => {
              const sorted = [...vs].sort((a, b) => b.version - a.version);
              const cur = sorted.find((t) => t.status === "APPROVED") ?? sorted[0]!;
              return (
                <Card key={code}>
                  <CardHeader><div><CardTitle>{cur.name}</CardTitle><CardDescription className="font-mono">{code} - {labelFor(cur.channel)} - {labelFor(cur.purpose)}</CardDescription></div>
                    <Button size="sm" variant="secondary" onClick={() => setDlg(cur)}>New version</Button></CardHeader>
                  <CardContent className="space-y-3">
                    {cur.subject && <p className="text-sm font-medium">{cur.subject}</p>}
                    <p className="whitespace-pre-wrap rounded-md bg-muted/50 p-3 text-xs leading-5">{cur.body}</p>
                    <ul className="space-y-1.5">{sorted.map((t) => (
                      <li key={t.id} className="flex flex-wrap items-center gap-2 text-xs">
                        <span className="font-semibold">v{t.version}</span><StatusBadge status={t.status} />
                        {t.approval_label === "DEMO_FIXTURE" && <Badge tone="warning">Demo fixture</Badge>}
                        <span className="text-muted-foreground">by {t.created_by_name ?? "-"}{t.approved_by_name ? `, approved by ${t.approved_by_name} ${formatDateTime(t.approved_at)}` : ""}</span>
                        {t.status === "DRAFT" && <Button size="sm" className="ml-auto" loading={approve.isPending && approve.variables === t.id} onClick={() => approve.mutate(t.id)}><ShieldCheck />Approve</Button>}
                      </li>))}</ul>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        );
      }}</QueryBoundary>
      {dlg !== undefined && <TemplateDialog base={dlg} onClose={() => setDlg(undefined)} />}
    </div>
  );
}
