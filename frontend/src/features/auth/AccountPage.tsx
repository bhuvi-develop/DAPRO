import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { KeyRound, MonitorSmartphone, ShieldCheck } from "lucide-react";
import { del, get, post } from "@/api/client";
import { useAuth } from "@/auth/store";
import { loadMe } from "@/auth/session";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { InlineError } from "@/components/data/states";
import { formatDateTime, relativeTime, titleCase } from "@/lib/utils";

interface Sess { id: string; created_at: string; last_seen_at: string; ip: string | null; user_agent: string | null; current: boolean; mfa_passed: boolean }

export default function AccountPage() {
  const me = useAuth((s) => s.me)!;
  const qc = useQueryClient();
  const sessions = useQuery({ queryKey: ["my-sessions"], queryFn: () => get<Sess[]>("/auth/sessions") });
  const revoke = useMutation({ mutationFn: (id: string) => del(`/auth/sessions/${id}`), onSuccess: () => { toast.success("Session revoked"); qc.invalidateQueries({ queryKey: ["my-sessions"] }); } });
  const [setup, setSetup] = React.useState<{ secret: string; otpauth_uri: string } | null>(null);
  const [code, setCode] = React.useState("");
  const start = useMutation({ mutationFn: () => post<{ secret: string; otpauth_uri: string }>("/auth/mfa/setup"), onSuccess: setSetup });
  const enable = useMutation({ mutationFn: () => post("/auth/mfa/enable", { code }), onSuccess: async () => { toast.success("Two-factor authentication enabled"); setSetup(null); setCode(""); await loadMe(); } });
  return (
    <div className="space-y-6">
      <PageHeader title="Profile and security" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Account" }]} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><CardTitle>Profile</CardTitle></CardHeader>
          <CardContent>
            <KeyValue items={[
              { label: "Name", value: me.full_name }, { label: "Email", value: me.email },
              { label: "Organization", value: me.org.name }, { label: "Scope", value: me.unit?.name ?? "Whole organization" },
              { label: "Roles", value: <div className="flex flex-wrap gap-1">{me.roles.map((r) => <Badge key={r} tone="info">{titleCase(r)}</Badge>)}</div> },
              { label: "Last sign-in", value: formatDateTime(me.last_login_at) },
            ]} />
          </CardContent>
        </Card>
        <Card id="mfa">
          <CardHeader><div><CardTitle className="flex items-center gap-2"><KeyRound className="h-4 w-4" />Two-factor authentication</CardTitle><CardDescription>Required for privileged roles before production use (NFR-SEC-04).</CardDescription></div>
            <Badge tone={me.mfa_enabled ? "success" : "warning"}>{me.mfa_enabled ? "Enabled" : "Not enrolled"}</Badge></CardHeader>
          <CardContent className="space-y-3">
            {!me.mfa_enabled && !setup && <Button onClick={() => start.mutate()} loading={start.isPending}><ShieldCheck />Set up authenticator app</Button>}
            {setup && (
              <div className="space-y-3">
                <p className="text-sm">Add this key to your authenticator app, then enter the 6-digit code.</p>
                <code className="block break-all rounded-md bg-muted p-2 font-mono text-xs">{setup.secret}</code>
                <Field label="Verification code" htmlFor="mfa-code"><Input id="mfa-code" inputMode="numeric" maxLength={8} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} /></Field>
                <InlineError error={enable.error} />
                <Button onClick={() => enable.mutate()} loading={enable.isPending} disabled={code.length < 6}>Verify and enable</Button>
              </div>
            )}
            {me.mfa_enabled && <p className="text-sm text-muted-foreground">Your account requires a verification code at every sign-in.</p>}
          </CardContent>
        </Card>
      </div>
      <Card id="sessions">
        <CardHeader><div><CardTitle className="flex items-center gap-2"><MonitorSmartphone className="h-4 w-4" />Active sessions</CardTitle><CardDescription>Sessions expire after inactivity. Revoke any you do not recognise.</CardDescription></div></CardHeader>
        <ul className="divide-y">
          {sessions.data?.map((s) => (
            <li key={s.id} className="flex flex-col gap-2 px-5 py-3 sm:flex-row sm:items-center">
              <div className="min-w-0 flex-1"><p className="truncate text-sm font-medium">{s.user_agent || "Unknown device"}</p>
                <p className="text-xs text-muted-foreground">{s.ip ?? "unknown IP"} - signed in {formatDateTime(s.created_at)} - active {relativeTime(s.last_seen_at)}</p></div>
              {s.current ? <Badge tone="success">This session</Badge> : <Button variant="secondary" size="sm" onClick={() => revoke.mutate(s.id)}>Revoke</Button>}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
