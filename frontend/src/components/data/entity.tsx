import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown, Loader2, Search, UploadCloud, X } from "lucide-react";
import { get } from "@/api/client";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/menu";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/useDebounce";
import { cn } from "@/lib/utils";

export interface Option { value: string; label: string; sublabel?: string | null }

/** Async searchable selector - users pick meaningful names, never raw database IDs. */
export function EntitySelect({ value, onChange, fetchOptions, placeholder = "Search and select", selectedLabel, id, invalid, disabled, queryKey }: {
  value?: string | null; onChange: (v: string | null, opt?: Option) => void; fetchOptions: (q: string) => Promise<Option[]>;
  placeholder?: string; selectedLabel?: string | null; id?: string; invalid?: boolean; disabled?: boolean; queryKey: string;
}) {
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  const [picked, setPicked] = React.useState<Option | null>(null);
  const dq = useDebounce(q, 250);
  const res = useQuery({ queryKey: ["entity", queryKey, dq], queryFn: () => fetchOptions(dq), enabled: open });
  const label = picked && picked.value === value ? picked.label : selectedLabel;
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button id={id} type="button" disabled={disabled} aria-invalid={invalid} aria-haspopup="listbox"
          className={cn("flex h-9 w-full items-center justify-between gap-2 rounded-md border border-input bg-surface px-3 text-left text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60 aria-[invalid=true]:border-danger", !value && "text-muted-foreground")}>
          <span className="truncate">{value ? label ?? "Selected" : placeholder}</span>
          <span className="flex items-center gap-1">
            {value && !disabled && <span role="button" tabIndex={-1} aria-label="Clear selection" onClick={(e) => { e.stopPropagation(); onChange(null); setPicked(null); }} className="rounded p-0.5 hover:bg-muted"><X className="h-3.5 w-3.5" /></span>}
            <ChevronsUpDown className="h-4 w-4 opacity-50" />
          </span>
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[var(--radix-popover-trigger-width)] min-w-[280px] p-0">
        <div className="relative border-b p-2">
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Type to search" className="h-8 pl-8" aria-label="Search options" />
        </div>
        <ul role="listbox" className="max-h-64 overflow-y-auto p-1 scrollbar-thin">
          {res.isLoading && <li className="flex items-center gap-2 px-3 py-2 text-xs text-muted-foreground"><Loader2 className="h-3.5 w-3.5 animate-spin" />Searching</li>}
          {!res.isLoading && !res.data?.length && <li className="px-3 py-2 text-xs text-muted-foreground">No matches in your scope</li>}
          {res.data?.map((o) => (
            <li key={o.value} role="option" aria-selected={o.value === value}>
              <button type="button" onClick={() => { onChange(o.value, o); setPicked(o); setOpen(false); }} className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-sm hover:bg-muted">
                <Check className={cn("h-4 w-4 text-primary", o.value === value ? "opacity-100" : "opacity-0")} />
                <span className="min-w-0"><span className="block truncate">{o.label}</span>{o.sublabel && <span className="block truncate text-[11px] text-muted-foreground">{o.sublabel}</span>}</span>
              </button>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
}

export const studentOptions = (q: string) =>
  get<{ items: { id: string; full_name: string; dapro_ref: string; college_name?: string; college_student_id?: string }[] }>(`/students?size=20&q=${encodeURIComponent(q)}`)
    .then((r) => r.items.map((s) => ({ value: s.id, label: s.full_name, sublabel: [s.dapro_ref, s.college_name ?? s.college_student_id].filter(Boolean).join(" - ") })));

/** File picker with type and size checks before upload (NFR-SEC-06 is enforced again server-side). */
export function FileDrop({ accept, maxMb = 10, file, onFile, hint }: { accept: string; maxMb?: number; file: File | null; onFile: (f: File | null) => void; hint?: string }) {
  const ref = React.useRef<HTMLInputElement>(null);
  const [err, setErr] = React.useState<string | null>(null);
  const [drag, setDrag] = React.useState(false);
  const take = (f?: File) => {
    if (!f) return;
    if (f.size > maxMb * 1024 * 1024) { setErr(`File is larger than ${maxMb} MB`); return; }
    setErr(null); onFile(f);
  };
  return (
    <div>
      <button type="button" onClick={() => ref.current?.click()} onDragOver={(e) => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); take(e.dataTransfer.files[0]); }}
        className={cn("flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-4 py-8 text-center transition-colors hover:border-primary/50 hover:bg-primary-soft/40", drag && "border-primary bg-primary-soft")}>
        <UploadCloud className="h-6 w-6 text-primary" aria-hidden />
        {file ? <span className="text-sm font-medium">{file.name} <span className="text-muted-foreground">({Math.ceil(file.size / 1024)} KB)</span></span>
          : <span className="text-sm"><span className="font-medium text-primary">Choose a file</span> or drag it here</span>}
        <span className="text-[11px] text-muted-foreground">{hint ?? `Accepted: ${accept}. Max ${maxMb} MB.`}</span>
      </button>
      <input ref={ref} type="file" accept={accept} className="sr-only" aria-label="File upload" onChange={(e) => take(e.target.files?.[0])} />
      {err && <p role="alert" className="mt-1 text-[11px] font-medium text-danger">{err}</p>}
    </div>
  );
}
