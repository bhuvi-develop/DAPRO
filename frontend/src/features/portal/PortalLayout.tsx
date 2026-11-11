import * as React from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LogOut, ShieldCheck } from "lucide-react";
import { PORTAL_NAV } from "@/app/nav";
import { useAuth } from "@/auth/store";
import { signOut } from "@/auth/session";
import { Button } from "@/components/ui/button";
import { BrandMark } from "@/components/layout/Sidebar";
import { DemoBanner, PageFallback } from "@/components/layout/AppShell";
import { cn } from "@/lib/utils";

/** Borrower self-service portal (FR-BRW-01, UC-34): own records only, enforced by the API. */
export default function PortalLayout() {
  const me = useAuth((s) => s.me)!;
  const nav = useNavigate();
  return (
    <div className="min-h-screen bg-background">
      <DemoBanner />
      <header className="bg-navy text-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <BrandMark />
          <div className="flex items-center gap-3">
            <span className="hidden text-right text-xs leading-tight sm:block"><span className="block font-semibold">{me.full_name}</span><span className="text-navy-foreground/70">{me.org.name}</span></span>
            <Button variant="ghost" size="sm" className="text-white hover:bg-white/10" onClick={async () => { await signOut(); nav("/login"); }}><LogOut />Sign out</Button>
          </div>
        </div>
        <nav aria-label="Portal" className="mx-auto flex max-w-5xl gap-1 overflow-x-auto px-2">
          {PORTAL_NAV.map((i) => (
            <NavLink key={i.to} to={i.to} end={i.end} className={({ isActive }) => cn("flex items-center gap-2 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm font-medium", isActive ? "border-[#5EEAD4] text-white" : "border-transparent text-navy-foreground/70 hover:text-white")}>
              <i.icon className="h-4 w-4" aria-hidden />{i.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <React.Suspense fallback={<PageFallback />}><Outlet /></React.Suspense>
        <p className="mt-10 flex items-start gap-2 rounded-md border bg-surface p-3 text-xs text-muted-foreground">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-teal" />
          Loan figures come from your bank and show when they were last updated. If anything looks wrong, raise a request. Your record is not changed without review.
        </p>
      </main>
    </div>
  );
}
