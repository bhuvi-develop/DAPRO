import * as React from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { useAuth, useCan } from "@/auth/store";
import { EmptyState } from "@/components/data/states";
import { PageFallback } from "@/components/layout/AppShell";

export function RequireAuth({ portal }: { portal?: boolean }) {
  const { status, me } = useAuth();
  const loc = useLocation();
  if (status === "booting") return <div className="p-8"><PageFallback /></div>;
  if (status !== "authenticated" || !me) return <Navigate to={`/login?next=${encodeURIComponent(loc.pathname + loc.search)}`} replace />;
  const borrower = me.roles.includes("BORROWER");
  if (borrower && !portal) return <Navigate to="/portal" replace />;
  if (!borrower && portal) return <Navigate to="/" replace />;
  return <Outlet />;
}

/** UI-level guard for clarity; the API enforces the same permission server-side. */
export function Perm({ any, children }: { any: string[]; children: React.ReactNode }) {
  const can = useCan();
  if (!can(any)) {
    return <EmptyState icon={ShieldAlert} title="This area is not available for your role"
      description={`It requires one of: ${any.join(", ")}. Ask your administrator if you need access for an approved purpose.`} />;
  }
  return <>{children}</>;
}
