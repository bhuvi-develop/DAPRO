import * as React from "react";
import { Search, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input, NativeSelect } from "@/components/ui/input";
import { useDebounce } from "@/hooks/useDebounce";
import { cn, titleCase } from "@/lib/utils";

export function SearchInput({ value, onChange, placeholder = "Search", className }: { value?: string; onChange: (v: string) => void; placeholder?: string; className?: string }) {
  const [v, setV] = React.useState(value ?? "");
  const d = useDebounce(v, 350);
  const first = React.useRef(true);
  React.useEffect(() => {
    if (first.current) { first.current = false; return; }
    if ((value ?? "") !== d) onChange(d);
  }, [d]); // eslint-disable-line react-hooks/exhaustive-deps
  React.useEffect(() => { setV(value ?? ""); }, [value]);
  return (
    <div className={cn("relative w-full sm:w-72", className)}>
      <Search className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
      <Input aria-label={placeholder} value={v} onChange={(e) => setV(e.target.value)} placeholder={placeholder} className="pl-8 pr-8" />
      {v && <button type="button" aria-label="Clear search" onClick={() => setV("")} className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5 text-muted-foreground hover:bg-muted"><X className="h-3.5 w-3.5" /></button>}
    </div>
  );
}

export function FilterSelect({ label, value, onChange, options, allLabel = "All", className }: {
  label: string; value?: string; onChange: (v: string) => void; options: (string | { value: string; label: string })[]; allLabel?: string; className?: string;
}) {
  return (
    <NativeSelect aria-label={label} value={value ?? ""} onChange={(e) => onChange(e.target.value)} className={cn("w-full sm:w-auto sm:min-w-[150px]", className)}>
      <option value="">{label}: {allLabel}</option>
      {options.map((o) => typeof o === "string"
        ? <option key={o} value={o}>{titleCase(o)}</option>
        : <option key={o.value} value={o.value}>{o.label}</option>)}
    </NativeSelect>
  );
}

export function FilterBar({ children, onClear, active }: { children: React.ReactNode; onClear?: () => void; active?: number }) {
  return (
    <div className="flex flex-col gap-2 border-b px-4 py-3 sm:flex-row sm:flex-wrap sm:items-center">
      {children}
      {onClear && !!active && <Button variant="ghost" size="sm" onClick={onClear} className="sm:ml-auto"><X />Clear {active} filter{active > 1 ? "s" : ""}</Button>}
    </div>
  );
}

const PRESETS = [
  { label: "Last 30 days", days: 30 }, { label: "Last 90 days", days: 90 }, { label: "Last 6 months", days: 182 },
  { label: "Last 12 months", days: 365 },
];

export function DateRange({ from, to, onChange }: { from?: string; to?: string; onChange: (from?: string, to?: string) => void }) {
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <NativeSelect aria-label="Reporting period" className="w-auto" value=""
        onChange={(e) => { const days = Number(e.target.value); if (!days) return; const t = new Date(); const f = new Date(Date.now() - days * 864e5); onChange(iso(f), iso(t)); }}>
        <option value="">Quick range</option>
        {PRESETS.map((p) => <option key={p.days} value={p.days}>{p.label}</option>)}
      </NativeSelect>
      <Input type="date" aria-label="From date" className="w-[150px]" value={from ?? ""} max={to} onChange={(e) => onChange(e.target.value || undefined, to)} />
      <span className="text-xs text-muted-foreground">to</span>
      <Input type="date" aria-label="To date" className="w-[150px]" value={to ?? ""} min={from} onChange={(e) => onChange(from, e.target.value || undefined)} />
    </div>
  );
}
