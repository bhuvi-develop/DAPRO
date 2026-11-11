import * as React from "react";
import { useNavigate } from "react-router-dom";
import { Command } from "cmdk";
import { useQuery } from "@tanstack/react-query";
import { Briefcase, Landmark, Loader2, MessageSquareWarning, Search, User } from "lucide-react";
import { get } from "@/api/client";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Kbd } from "@/components/ui/misc";
import { useDebounce } from "@/hooks/useDebounce";

interface Hit { id: string; title: string; subtitle?: string | null; link: string }
interface SearchResult { students?: Hit[]; loans?: Hit[]; cases?: Hit[]; grievances?: Hit[] }

const GROUPS: { key: keyof SearchResult; label: string; icon: React.ElementType }[] = [
  { key: "students", label: "Students", icon: User }, { key: "loans", label: "Loan accounts", icon: Landmark },
  { key: "cases", label: "Cases", icon: Briefcase }, { key: "grievances", label: "Grievances", icon: MessageSquareWarning },
];

export function GlobalSearch() {
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  const dq = useDebounce(q.trim(), 250);
  const nav = useNavigate();
  React.useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen((o) => !o); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const res = useQuery({ queryKey: ["search", dq], queryFn: () => get<SearchResult>(`/search?q=${encodeURIComponent(dq)}`), enabled: dq.length >= 2 });
  const go = (link: string) => { setOpen(false); setQ(""); nav(link); };
  return (
    <>
      <button type="button" onClick={() => setOpen(true)} className="flex h-9 w-full max-w-md items-center gap-2 rounded-md border bg-muted/60 px-3 text-sm text-muted-foreground transition-colors hover:bg-muted" aria-label="Search students, loans, cases and grievances">
        <Search className="h-4 w-4" aria-hidden />
        <span className="flex-1 truncate text-left">Search students, loan refs, cases...</span>
        <span className="hidden gap-0.5 sm:flex"><Kbd>Ctrl</Kbd><Kbd>K</Kbd></span>
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="top-[15%] max-w-xl translate-y-0 p-0" aria-describedby={undefined}>
          <Command shouldFilter={false} label="Global search" className="flex flex-col">
            <div className="flex items-center gap-2 border-b px-4">
              <Search className="h-4 w-4 text-muted-foreground" aria-hidden />
              <Command.Input autoFocus value={q} onValueChange={setQ} placeholder="Name, DAPRO ref, college ID, loan ref, case or grievance ref" className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground" />
              {res.isFetching && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
            </div>
            <Command.List className="max-h-[360px] overflow-y-auto p-2 scrollbar-thin">
              {dq.length < 2 && <p className="px-3 py-6 text-center text-xs text-muted-foreground">Type at least 2 characters. Results respect your access scope.</p>}
              {dq.length >= 2 && !res.isFetching && <Command.Empty className="px-3 py-6 text-center text-sm text-muted-foreground">No matches in your scope.</Command.Empty>}
              {GROUPS.map((g) => {
                const hits = res.data?.[g.key];
                if (!hits?.length) return null;
                return (
                  <Command.Group key={g.key} heading={g.label} className="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1.5 [&_[cmdk-group-heading]]:text-[11px] [&_[cmdk-group-heading]]:font-semibold [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:text-muted-foreground">
                    {hits.map((h) => (
                      <Command.Item key={h.id} value={`${g.key}-${h.id}`} onSelect={() => go(h.link)} className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-2 text-sm aria-selected:bg-primary-soft">
                        <g.icon className="h-4 w-4 text-muted-foreground" aria-hidden />
                        <div className="min-w-0"><p className="truncate font-medium">{h.title}</p>{h.subtitle && <p className="truncate text-xs text-muted-foreground">{h.subtitle}</p>}</div>
                      </Command.Item>
                    ))}
                  </Command.Group>
                );
              })}
            </Command.List>
          </Command>
        </DialogContent>
      </Dialog>
    </>
  );
}
