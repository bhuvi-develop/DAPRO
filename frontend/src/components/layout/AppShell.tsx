import * as React from "react";
import { Outlet, useLocation } from "react-router-dom";
import * as D from "@radix-ui/react-dialog";
import { FlaskConical, Menu, X } from "lucide-react";
import { useAuth } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { BrandMark, Sidebar, SidebarNav } from "@/components/layout/Sidebar";
import { GlobalSearch } from "@/components/layout/GlobalSearch";
import { ContextChip, NotificationCenter, UserMenu } from "@/components/layout/TopbarParts";

const KEY = "dapro.sidebar.collapsed";

function readCollapsed() {
  try { return localStorage.getItem(KEY) === "1"; } catch { return false; }
}

/** Demo data must never be mistaken for live bank records (master prompt section 7). */
export function DemoBanner() {
  const me = useAuth((s) => s.me);
  if (!me || me.tenant.environment !== "DEMO") return null;
  return (
    <div role="note" className="flex items-center justify-center gap-2 bg-warning-soft px-4 py-1.5 text-center text-[11px] font-medium text-[hsl(32_95%_30%)]">
      <FlaskConical className="h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>DEMO environment - synthetic borrowers and fictional institutions. Bank data comes from a MOCK feed, not a live bank. Policy values are demo fixtures pending client approval.</span>
    </div>
  );
}

export function PageFallback() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-28" />)}</div>
      <Skeleton className="h-72" />
    </div>
  );
}

export function AppShell() {
  const [collapsed, setCollapsed] = React.useState(readCollapsed);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const loc = useLocation();
  React.useEffect(() => { setMobileOpen(false); }, [loc.pathname]);
  const toggle = () => setCollapsed((c) => { try { localStorage.setItem(KEY, c ? "0" : "1"); } catch { /* storage unavailable */ } return !c; });
  return (
    <div className="flex min-h-screen bg-background">
      <a href="#main" className="sr-only z-50 rounded bg-primary px-3 py-2 text-white focus:not-sr-only focus:fixed focus:left-3 focus:top-3">Skip to content</a>
      <Sidebar collapsed={collapsed} onToggle={toggle} />
      <div className="flex min-w-0 flex-1 flex-col">
        <DemoBanner />
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-surface/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-surface/80 md:px-6">
          <D.Root open={mobileOpen} onOpenChange={setMobileOpen}>
            <D.Trigger asChild><Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation"><Menu className="h-5 w-5" /></Button></D.Trigger>
            <D.Portal>
              <D.Overlay className="fixed inset-0 z-50 bg-navy/40 lg:hidden" />
              <D.Content className="fixed inset-y-0 left-0 z-50 flex w-[280px] flex-col bg-navy lg:hidden" aria-describedby={undefined}>
                <D.Title className="sr-only">Navigation</D.Title>
                <div className="flex h-16 items-center justify-between border-b border-white/10 px-4">
                  <BrandMark />
                  <D.Close className="rounded p-1.5 text-white/80 hover:bg-white/10" aria-label="Close navigation"><X className="h-5 w-5" /></D.Close>
                </div>
                <SidebarNav onNavigate={() => setMobileOpen(false)} />
              </D.Content>
            </D.Portal>
          </D.Root>
          <div className="min-w-0 flex-1"><GlobalSearch /></div>
          <ContextChip />
          <NotificationCenter />
          <UserMenu />
        </header>
        <main id="main" className="mx-auto w-full max-w-[1600px] flex-1 px-4 py-6 md:px-6 lg:px-8">
          <React.Suspense fallback={<PageFallback />}>
            <Outlet />
          </React.Suspense>
        </main>
        <footer className="border-t px-6 py-3 text-center text-[11px] text-muted-foreground">
          DAPRO monitors bank-confirmed data and records accountable follow-up. It is not a core-banking ledger, credit bureau or automated decision-maker.
        </footer>
      </div>
    </div>
  );
}
