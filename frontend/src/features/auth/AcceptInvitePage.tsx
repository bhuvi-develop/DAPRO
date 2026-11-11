import * as React from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2 } from "lucide-react";
import { api } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import { Field } from "@/components/data/feedback";
import { InlineError } from "@/components/data/states";
import { BrandMark } from "@/components/layout/Sidebar";

export default function AcceptInvitePage() {
  const [sp] = useSearchParams();
  const [pw, setPw] = React.useState("");
  const [pw2, setPw2] = React.useState("");
  const [err, setErr] = React.useState<unknown>(null);
  const [done, setDone] = React.useState(false);
  const [busy, setBusy] = React.useState(false);
  const policyOk = pw.length >= 10 && /[A-Z]/.test(pw) && /[a-z]/.test(pw) && /\d/.test(pw);
  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setErr(null);
    try { await api("/auth/invitations/accept", { method: "POST", body: { token: sp.get("token"), password: pw } }); setDone(true); }
    catch (x) { setErr(x); } finally { setBusy(false); }
  };
  return (
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      <Card className="w-full max-w-md">
        <div className="rounded-t-lg bg-navy p-4"><BrandMark /></div>
        <CardContent>
          {done ? (
            <div className="space-y-3 text-center">
              <CheckCircle2 className="mx-auto h-10 w-10 text-success" />
              <p className="font-semibold">Your account is active</p>
              <Button asChild className="w-full"><Link to="/login">Go to sign in</Link></Button>
            </div>
          ) : (
            <form onSubmit={submit} className="space-y-4">
              <div><h1 className="text-lg font-semibold">Activate your account</h1><p className="text-sm text-muted-foreground">Set a password to accept your invitation.</p></div>
              <Field label="New password" htmlFor="pw" hint="At least 10 characters with upper case, lower case and a digit." required>
                <Input id="pw" type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} />
              </Field>
              <Field label="Confirm password" htmlFor="pw2" error={pw2 && pw2 !== pw ? "Passwords do not match" : undefined} required>
                <Input id="pw2" type="password" autoComplete="new-password" value={pw2} onChange={(e) => setPw2(e.target.value)} />
              </Field>
              <InlineError error={err} />
              <Button type="submit" className="w-full" loading={busy} disabled={!policyOk || pw !== pw2}>Activate account</Button>
            </form>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
