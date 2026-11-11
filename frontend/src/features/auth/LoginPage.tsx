import * as React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Eye, EyeOff, FlaskConical, Landmark, Lock, ScaleIcon, ShieldCheck, UserCheck } from "lucide-react";
import { api } from "@/api/client";
import { useAuth } from "@/auth/store";
import { loadMe } from "@/auth/session";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { InlineError } from "@/components/data/states";
import { BrandMark } from "@/components/layout/Sidebar";

const schema = z.object({
  email: z.string().email("Enter a valid work email"),
  password: z.string().min(1, "Enter your password"),
  tenant_code: z.string().optional(),
});
type Form = z.infer<typeof schema>;

const DEMO_ACCOUNTS = [
  { email: "priya.admin@nbit.demo", who: "Priya Raman", role: "College Administrator - NBIT" },
  { email: "ravi.ops@anb.demo", who: "Ravi Subramanian", role: "Bank Loan Operations - ANB" },
  { email: "head.followup@anb.demo", who: "Suresh Pillai", role: "Follow-up Manager - ANB (all branches)" },
  { email: "meena.manager@anb.demo", who: "Meena Krishnan", role: "Follow-up Manager - Chennai Region" },
  { email: "karthik.field@anb.demo", who: "Karthik Murugan", role: "Field Officer - ANB" },
  { email: "investigator@anb.demo", who: "Deepa Raghavan", role: "Investigation Officer - ANB" },
  { email: "sanjay.audit@anb.demo", who: "Sanjay Chandran", role: "Auditor - ANB" },
  { email: "admin@anb.demo", who: "Rekha Menon", role: "Bank Administrator - ANB" },
  { email: "platform.admin@dapro.demo", who: "Anand Iyer", role: "Platform Administrator" },
  { email: "hari.borrower@student.demo", who: "Hari (borrower)", role: "Borrower portal" },
];

const PRINCIPLES = [
  { icon: Landmark, title: "Bank remains the source of truth", body: "Loan and repayment data is a read-only mirror with source and as-of on every figure." },
  { icon: ScaleIcon, title: "Explainable, human-reviewed indicators", body: "Risk signals prioritise review. They never label anyone or trigger adverse action." },
  { icon: UserCheck, title: "Accountable follow-up", body: "Every case has an owner, due date, evidence and a complete audit trail." },
];

export default function LoginPage() {
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const status = useAuth((s) => s.status);
  const [mfaToken, setMfaToken] = React.useState<string | null>(null);
  const [code, setCode] = React.useState("");
  const [show, setShow] = React.useState(false);
  const [error, setError] = React.useState<unknown>(null);
  const [busy, setBusy] = React.useState(false);
  const health = useQuery({ queryKey: ["health"], queryFn: () => fetch("/api/v1/health").then((r) => r.json()) as Promise<{ demo_mode: boolean }> });
  const { register, handleSubmit, setValue, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema) });

  React.useEffect(() => { if (status === "authenticated") nav(sp.get("next") || "/", { replace: true }); }, [status, nav, sp]);

  const finish = async (token: string) => {
    useAuth.getState().setToken(token);
    const me = await loadMe();
    nav(me.roles.includes("BORROWER") ? "/portal" : sp.get("next") || "/", { replace: true });
  };

  const onSubmit = async (v: Form) => {
    setBusy(true); setError(null);
    try {
      const r = await api<{ access_token?: string; mfa_required?: boolean; mfa_token?: string }>("/auth/login", { method: "POST", body: { ...v, tenant_code: v.tenant_code || undefined } });
      if (r.mfa_required && r.mfa_token) setMfaToken(r.mfa_token);
      else if (r.access_token) await finish(r.access_token);
    } catch (e) { setError(e); } finally { setBusy(false); }
  };

  const onVerify = async (e: React.FormEvent) => {
    e.preventDefault(); setBusy(true); setError(null);
    try {
      const r = await api<{ access_token: string }>("/auth/mfa/verify", { method: "POST", body: { mfa_token: mfaToken, code } });
      await finish(r.access_token);
    } catch (err) { setError(err); } finally { setBusy(false); }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
      <aside className="relative hidden overflow-hidden bg-navy px-12 py-10 text-white lg:flex lg:flex-col">
        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full border border-white/10" aria-hidden />
        <div className="pointer-events-none absolute -right-8 top-40 h-64 w-64 rounded-full border border-white/5" aria-hidden />
        <BrandMark />
        <div className="mt-auto max-w-lg">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#5EEAD4]">Student Loan Intelligence and Monitoring</p>
          <h1 className="mt-3 text-[34px] font-semibold leading-tight text-white">One trusted view of every student loan, from first disbursement to final EMI.</h1>
          <p className="mt-4 text-sm leading-6 text-navy-foreground/80">DAPRO connects colleges and banks so authorised teams can keep borrower information current, see bank-confirmed repayment status and coordinate fair, accountable follow-up.</p>
          <ul className="mt-8 space-y-4">
            {PRINCIPLES.map((p) => (
              <li key={p.title} className="flex gap-3">
                <span className="mt-0.5 rounded-md bg-white/10 p-2"><p.icon className="h-4 w-4 text-[#5EEAD4]" aria-hidden /></span>
                <span><span className="block text-sm font-semibold text-white">{p.title}</span><span className="block text-xs leading-5 text-navy-foreground/75">{p.body}</span></span>
              </li>
            ))}
          </ul>
        </div>
        <p className="mt-10 text-[11px] text-navy-foreground/50">DAPRO is not a core-banking ledger, credit bureau, tracing tool or automated decision-maker.</p>
      </aside>

      <main className="flex flex-col justify-center bg-background px-5 py-10 sm:px-10">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="mx-auto w-full max-w-[400px]">
          <div className="mb-8 rounded-lg bg-navy p-3 lg:hidden"><BrandMark /></div>
          {!mfaToken ? (
            <>
              <h2 className="text-2xl font-semibold">Sign in</h2>
              <p className="mt-1 text-sm text-muted-foreground">Use your institution account. Access is limited to your role and organization.</p>
              <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4" noValidate>
                <Field label="Work email" htmlFor="email" error={errors.email?.message} required>
                  <Input id="email" type="email" autoComplete="username" autoFocus aria-invalid={!!errors.email} {...register("email")} />
                </Field>
                <Field label="Password" htmlFor="password" error={errors.password?.message} required>
                  <div className="relative">
                    <Input id="password" type={show ? "text" : "password"} autoComplete="current-password" aria-invalid={!!errors.password} className="pr-10" {...register("password")} />
                    <button type="button" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:bg-muted">
                      {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </Field>
                <Field label="Workspace code" htmlFor="tenant" hint="Only needed if your email belongs to more than one workspace.">
                  <Input id="tenant" placeholder="e.g. DEMO" {...register("tenant_code")} />
                </Field>
                <InlineError error={error} />
                <Button type="submit" className="w-full" size="lg" loading={busy}><Lock />Sign in securely</Button>
              </form>
            </>
          ) : (
            <form onSubmit={onVerify} className="space-y-4">
              <div className="flex items-center gap-2 text-primary"><ShieldCheck className="h-5 w-5" /><h2 className="text-2xl font-semibold text-foreground">Two-step verification</h2></div>
              <p className="text-sm text-muted-foreground">Enter the 6-digit code from your authenticator app.</p>
              <Field label="Verification code" htmlFor="code" required>
                <Input id="code" inputMode="numeric" autoComplete="one-time-code" autoFocus maxLength={8} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))} />
              </Field>
              <InlineError error={error} />
              <Button type="submit" className="w-full" size="lg" loading={busy} disabled={code.length < 6}>Verify and continue</Button>
              <Button type="button" variant="ghost" className="w-full" onClick={() => { setMfaToken(null); setCode(""); }}>Back</Button>
            </form>
          )}

          {health.data?.demo_mode && !mfaToken && (
            <div className="mt-8 rounded-lg border border-warning/30 bg-warning-soft/60 p-4">
              <p className="flex items-center gap-1.5 text-xs font-semibold text-[hsl(32_95%_30%)]"><FlaskConical className="h-3.5 w-3.5" />Demo personas (synthetic data)</p>
              <p className="mt-1 text-[11px] text-muted-foreground">Choose a persona to fill the email. Use the demo password from your environment handover.</p>
              <ul className="mt-3 grid gap-1.5">
                {DEMO_ACCOUNTS.map((a) => (
                  <li key={a.email}>
                    <button type="button" onClick={() => setValue("email", a.email, { shouldValidate: true })} className="flex w-full items-center justify-between gap-2 rounded-md bg-surface px-3 py-1.5 text-left text-xs shadow-sm hover:ring-1 hover:ring-primary/40">
                      <span className="font-medium">{a.who}</span><span className="truncate text-muted-foreground">{a.role}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>
      </main>
    </div>
  );
}

