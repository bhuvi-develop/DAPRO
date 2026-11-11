import * as React from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import { AlertTriangle, FlaskConical, RotateCcw } from "lucide-react";
import { post } from "@/api/client";
import { useAuth } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { InlineError } from "@/components/data/states";

const PHRASE = "RESET DEMO DATA";

export default function DemoControlsPage() {
  const me = useAuth((s) => s.me)!;
  const [typed, setTyped] = React.useState("");
  const [note, setNote] = React.useState<string | null>(null);
  const m = useMutation({ mutationFn: () => post<{ status: string; note: string }>("/admin/demo/reset", { confirm: typed }), onSuccess: (r) => { setNote(r.note); setTyped(""); toast.success("Demo reset queued"); } });
  const env = me.environment;
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader title="Demo controls" description="Controls for the DEMO environment only. Demo data is synthetic and must never be loaded into production."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Administration" }, { label: "Demo controls" }]} />
      <Card>
        <CardHeader><CardTitle className="flex items-center gap-2"><FlaskConical className="h-4 w-4 text-warning" />Environment</CardTitle><Badge tone={me.tenant.environment === "DEMO" ? "warning" : "success"}>{me.tenant.environment}</Badge></CardHeader>
        <CardContent><KeyValue cols={3} items={[
          { label: "Workspace", value: me.tenant.name }, { label: "Runtime environment", value: env.env },
          { label: "Bank data adapter", value: <Badge tone="warning">{env.bank_adapter.toUpperCase()} - not a live bank</Badge> },
          { label: "Email provider", value: <Badge tone="warning">{env.email_mode.toUpperCase()}</Badge> }, { label: "SMS provider", value: <Badge tone="warning">{env.sms_mode.toUpperCase()}</Badge> },
          { label: "Field location capture", value: env.location_capture ? "Enabled" : "Disabled (OD-14 pending)" },
        ]} /></CardContent>
      </Card>
      <Card className="border-danger/30">
        <CardHeader><div><CardTitle className="flex items-center gap-2 text-danger"><AlertTriangle className="h-4 w-4" />Reset demo dataset</CardTitle>
          <CardDescription>Deletes and rebuilds all DEMO business records. The audit trail is append-only and is retained.</CardDescription></div></CardHeader>
        <CardContent className="space-y-3">
          <Field label={`Type ${PHRASE} to confirm`} htmlFor="demo-confirm" hint="This affects every user of the demo workspace. Everyone must sign in again afterwards." required>
            <Input id="demo-confirm" value={typed} onChange={(e) => setTyped(e.target.value)} autoComplete="off" />
          </Field>
          <InlineError error={m.error} />
          {note && <p className="rounded-md bg-success-soft px-3 py-2 text-sm text-success">{note}</p>}
        </CardContent>
        <CardFooter className="justify-end"><Button variant="danger" disabled={typed !== PHRASE} loading={m.isPending} onClick={() => m.mutate()}><RotateCcw />Reset demo data</Button></CardFooter>
      </Card>
    </div>
  );
}
