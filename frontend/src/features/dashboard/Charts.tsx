import { useNavigate } from "react-router-dom";
import { Area, Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, Pie, PieChart, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis } from "recharts";
import { EmptyState } from "@/components/data/states";
import { CHART_COLORS, STATUS_COLORS } from "@/components/data/kpi";
import { labelFor } from "@/components/data/status";
import { formatINR, formatNumber } from "@/lib/utils";
import type { Slice, TrendPoint } from "./types";

const axis = { fontSize: 11, fill: "#64748B" };
const tooltipStyle = { borderRadius: 8, border: "1px solid #E2E8F0", fontSize: 12, boxShadow: "0 10px 30px -10px rgb(16 42 86 / .25)" };

export function DonutChart({ data, height = 230 }: { data: Slice[]; height?: number }) {
  const nav = useNavigate();
  const total = data.reduce((s, d) => s + d.value, 0);
  if (!total) return <EmptyState title="No data in scope" />;
  return (
    <div className="flex flex-col items-center gap-4 sm:flex-row">
      <div className="relative h-[200px] w-[200px] shrink-0">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="key" innerRadius={62} outerRadius={92} paddingAngle={1.5} strokeWidth={0}
              onClick={(d: Slice) => d.link && nav(d.link)} className="cursor-pointer">
              {data.map((d, i) => <Cell key={d.key} fill={STATUS_COLORS[d.key] ?? CHART_COLORS[i % CHART_COLORS.length]} />)}
            </Pie>
            <RTooltip contentStyle={tooltipStyle} formatter={(v: number, k: string) => [formatNumber(v), labelFor(k)]} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="num text-2xl font-semibold">{formatNumber(total)}</span><span className="text-[11px] text-muted-foreground">accounts</span>
        </div>
      </div>
      <ul className="w-full space-y-1.5" style={{ minHeight: height - 60 }}>
        {data.map((d, i) => (
          <li key={d.key}>
            <button type="button" disabled={!d.link} onClick={() => d.link && nav(d.link)} className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left text-xs hover:bg-muted disabled:cursor-default disabled:hover:bg-transparent">
              <span className="h-2.5 w-2.5 shrink-0 rounded-sm" style={{ background: STATUS_COLORS[d.key] ?? CHART_COLORS[i % CHART_COLORS.length] }} aria-hidden />
              <span className="flex-1">{d.label ?? labelFor(d.key)}</span>
              <span className="num font-medium">{formatNumber(d.value)}</span>
              <span className="num w-10 text-right text-muted-foreground">{Math.round((d.value / total) * 100)}%</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function BucketBars({ data, money }: { data: Slice[]; money?: boolean }) {
  const nav = useNavigate();
  if (!data.length || !data.some((d) => d.value)) return <EmptyState title="No overdue accounts in scope" />;
  return (
    <div className="h-[230px]">
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
          <CartesianGrid vertical={false} stroke="#E2E8F0" />
          <XAxis dataKey="label" tick={axis} tickLine={false} axisLine={false} interval={0} />
          <YAxis tick={axis} tickLine={false} axisLine={false} allowDecimals={false} />
          <RTooltip cursor={{ fill: "#EFF6FF" }} contentStyle={tooltipStyle}
            formatter={(v: number, _n, p) => [`${formatNumber(v)} accounts${money && p.payload.amount ? ` - ${formatINR(p.payload.amount)}` : ""}`, p.payload.label]} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={48} className="cursor-pointer" onClick={(d: Slice) => d.link && nav(d.link)}>
            {data.map((d) => <Cell key={d.key} fill={STATUS_COLORS[d.key] ?? "#1D4ED8"} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function TrendChart({ data, money }: { data: TrendPoint[]; money: boolean }) {
  if (!data.length) return <EmptyState title="No repayment history in scope" />;
  const rows = data.map((d) => ({ ...d, collected: d.collected === null || d.collected === undefined ? null : Number(d.collected),
    rate: d.instalments_due ? Math.round(((d.instalments_paid ?? 0) / d.instalments_due) * 100) : null }));
  return (
    <div className="h-[250px]">
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 4, left: -4, bottom: 0 }}>
          <defs><linearGradient id="col" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#1D4ED8" stopOpacity={0.25} /><stop offset="100%" stopColor="#1D4ED8" stopOpacity={0.02} /></linearGradient></defs>
          <CartesianGrid vertical={false} stroke="#E2E8F0" />
          <XAxis dataKey="month" tick={axis} tickLine={false} axisLine={false} />
          {money && <YAxis yAxisId="amt" tick={axis} tickLine={false} axisLine={false} tickFormatter={(v) => formatINR(v, { compact: true }) ?? ""} width={64} />}
          <YAxis yAxisId="pct" orientation="right" tick={axis} tickLine={false} axisLine={false} domain={[0, 100]} unit="%" width={40} />
          <RTooltip contentStyle={tooltipStyle} formatter={(v: number, n: string) => n === "rate" ? [`${v}%`, "Instalments paid on schedule"] : [formatINR(v) ?? "-", "Bank-confirmed collections"]} />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 11 }} formatter={(v) => (v === "rate" ? "Paid vs due (%)" : "Collections (bank-confirmed)")} />
          {money && <Area yAxisId="amt" type="monotone" dataKey="collected" stroke="#1D4ED8" strokeWidth={2} fill="url(#col)" />}
          <Line yAxisId="pct" type="monotone" dataKey="rate" stroke="#0F766E" strokeWidth={2} dot={{ r: 2 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HBars({ data, colorIndex = 0 }: { data: Slice[]; colorIndex?: number }) {
  const nav = useNavigate();
  const max = Math.max(1, ...data.map((d) => d.value));
  if (!data.length) return <EmptyState title="No data in scope" />;
  return (
    <ul className="space-y-2.5 px-2 py-1">
      {data.map((d) => (
        <li key={d.key}>
          <button type="button" disabled={!d.link} onClick={() => d.link && nav(d.link)} className="group w-full text-left disabled:cursor-default">
            <div className="mb-1 flex justify-between text-xs"><span>{d.label ?? labelFor(d.key)}</span><span className="num font-medium">{formatNumber(d.value)}</span></div>
            <div className="h-2 rounded-full bg-muted"><div className="h-2 rounded-full transition-all group-hover:opacity-80" style={{ width: `${(d.value / max) * 100}%`, background: STATUS_COLORS[d.key] ?? CHART_COLORS[colorIndex] }} /></div>
          </button>
        </li>
      ))}
    </ul>
  );
}
