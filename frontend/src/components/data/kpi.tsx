import * as React from "react";
import { Link } from "react-router-dom";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/misc";
import { cn, formatINR, formatNumber } from "@/lib/utils";

export type KpiStatus = "neutral" | "good" | "attention" | "critical" | "info";

const ICON_TONE: Record<KpiStatus, string> = {
  neutral: "bg-muted text-navy", info: "bg-primary-soft text-primary", good: "bg-success-soft text-success",
  attention: "bg-warning-soft text-warning", critical: "bg-danger-soft text-danger",
};

export function KpiCard({ label, value, unit, previous, icon: Icon, status = "neutral", to, hint, higherIsBetter = true, loading }: {
  label: string; value: number | string | null | undefined; unit?: "count" | "inr" | "pct"; previous?: number | null; icon: React.ElementType;
  status?: KpiStatus; to?: string; hint?: React.ReactNode; higherIsBetter?: boolean; loading?: boolean;
}) {
  const n = typeof value === "string" ? Number(value) : value;
  const display = n === null || n === undefined || Number.isNaN(n) ? "-"
    : unit === "inr" ? formatINR(n, { compact: true }) : unit === "pct" ? `${n}%` : formatNumber(n);
  let delta: React.ReactNode = null;
  if (previous !== null && previous !== undefined && typeof n === "number") {
    const diff = n - previous;
    const pct = previous ? Math.round((diff / previous) * 1000) / 10 : null;
    const up = diff > 0;
    const good = diff === 0 ? null : up === higherIsBetter;
    const DIcon = diff === 0 ? Minus : up ? ArrowUpRight : ArrowDownRight;
    delta = (
      <span className={cn("inline-flex items-center gap-0.5 text-[11px] font-medium", good === null ? "text-muted-foreground" : good ? "text-success" : "text-danger")}>
        <DIcon className="h-3 w-3" aria-hidden />{pct === null ? formatNumber(Math.abs(diff)) : `${Math.abs(pct)}%`}
        <span className="font-normal text-muted-foreground">vs prev. period</span>
      </span>
    );
  }
  const body = (
    <Card className={cn("group h-full p-4 transition-shadow", to && "hover:border-primary/40 hover:shadow-pop")}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <span className={cn("rounded-md p-1.5", ICON_TONE[status])}><Icon className="h-4 w-4" aria-hidden /></span>
      </div>
      {loading ? <Skeleton className="mt-2 h-7 w-24" /> : <p className="num mt-1 text-[26px] font-semibold leading-8 text-foreground">{display}</p>}
      <div className="mt-1 flex min-h-[18px] flex-wrap items-center gap-x-2 gap-y-0.5">{delta}{hint && <span className="text-[11px] text-muted-foreground">{hint}</span>}</div>
    </Card>
  );
  return to ? <Link to={to} aria-label={`${label}: ${display}. Open filtered list`} className="block rounded-lg focus-visible:ring-2 focus-visible:ring-ring">{body}</Link> : body;
}

export const CHART_COLORS = ["#1D4ED8", "#0F766E", "#102A56", "#059669", "#D97706", "#64748B", "#7C9CE8", "#5FB3AB"];
export const STATUS_COLORS: Record<string, string> = {
  CURRENT: "#059669", PAID: "#059669", OVERDUE: "#DC2626", NOT_STARTED: "#1D4ED8", UNKNOWN: "#94A3B8", CLOSED: "#102A56",
  PARTIALLY_PAID: "#D97706", STALE: "#D97706", DPD_1_30: "#F59E0B", DPD_31_60: "#D97706", DPD_61_90: "#EA580C", DPD_90_PLUS: "#DC2626",
};

export function ChartCard({ title, description, actions, children, footer, className }: { title: string; description?: React.ReactNode; actions?: React.ReactNode; children: React.ReactNode; footer?: React.ReactNode; className?: string }) {
  return (
    <Card className={cn("flex flex-col", className)}>
      <div className="flex items-start justify-between gap-3 px-5 pt-4">
        <div>
          <h3 className="text-sm font-semibold">{title}</h3>
          {description && <p className="mt-0.5 text-[11px] text-muted-foreground">{description}</p>}
        </div>
        {actions}
      </div>
      <div className="flex-1 px-3 pb-3 pt-2">{children}</div>
      {footer && <div className="border-t px-5 py-2 text-[11px] text-muted-foreground">{footer}</div>}
    </Card>
  );
}
