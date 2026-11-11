import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Building2, CheckCheck, KeyRound, LogOut, MonitorSmartphone, UserCircle2 } from "lucide-react";
import { get, post } from "@/api/client";
import { useAuth } from "@/auth/store";
import { signOut } from "@/auth/session";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger, Popover, PopoverContent, PopoverTrigger } from "@/components/ui/menu";
import { Avatar } from "@/components/ui/misc";
import { EmptyState } from "@/components/data/states";
import { cn, relativeTime, titleCase } from "@/lib/utils";

interface Notice { id: string; kind: string; title: string; body: string | null; link: string | null; severity: string; read_at: string | null; created_at: string }

export function NotificationCenter() {
  const qc = useQueryClient();
  const nav = useNavigate();
  const q = useQuery({ queryKey: ["notifications"], queryFn: () => get<{ items: Notice[]; unread: number }>("/notifications"), refetchInterval: 60_000 });
  const readOne = useMutation({ mutationFn: (id: string) => post(`/notifications/${id}/read`), onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }) });
  const readAll = useMutation({ mutationFn: () => post("/notifications/read-all"), onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }) });
  const unread = q.data?.unread ?? 0;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`} className="relative">
          <Bell className="h-[18px] w-[18px]" />
          {unread > 0 && <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white">{unread > 9 ? "9+" : unread}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[360px] p-0">
        <div className="flex items-center justify-between border-b px-4 py-3">
          <p className="text-sm font-semibold">Notifications</p>
          {unread > 0 && <Button variant="ghost" size="sm" onClick={() => readAll.mutate()}><CheckCheck />Mark all read</Button>}
        </div>
        <div className="max-h-[380px] overflow-y-auto scrollbar-thin">
          {!q.data?.items.length ? <EmptyState title="You are all caught up" description="Assignments, review requests and integration incidents appear here." /> : (
            <ul className="divide-y">
              {q.data.items.map((n) => (
                <li key={n.id}>
                  <button type="button" className={cn("flex w-full gap-3 px-4 py-3 text-left hover:bg-muted/60", !n.read_at && "bg-primary-soft/50")}
                    onClick={() => { if (!n.read_at) readOne.mutate(n.id); if (n.link) nav(n.link); }}>
                    <span className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", n.read_at ? "bg-transparent" : n.severity === "CRITICAL" ? "bg-danger" : "bg-primary")} aria-hidden />
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium">{n.title}</span>
                      {n.body && <span className="mt-0.5 block text-xs text-muted-foreground">{n.body}</span>}
                      <span className="mt-1 block text-[11px] text-muted-foreground">{titleCase(n.kind)} - {relativeTime(n.created_at)}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}

export function ContextChip() {
  const me = useAuth((s) => s.me);
  if (!me) return null;
  return (
    <div className="hidden items-center gap-2 rounded-md border bg-surface px-2.5 py-1.5 xl:flex" title="Your organization and data scope">
      <Building2 className="h-4 w-4 text-muted-foreground" aria-hidden />
      <div className="leading-tight">
        <p className="max-w-[220px] truncate text-xs font-semibold">{me.org.name}</p>
        <p className="max-w-[220px] truncate text-[10px] text-muted-foreground">{me.unit ? `Scope: ${me.unit.name}` : `${titleCase(me.org.type)} - full organization scope`}</p>
      </div>
    </div>
  );
}

export function UserMenu() {
  const me = useAuth((s) => s.me);
  const nav = useNavigate();
  if (!me) return null;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button type="button" className="flex items-center gap-2 rounded-md p-1 pr-2 hover:bg-muted" aria-label="Account menu">
          <Avatar name={me.full_name} />
          <span className="hidden text-left leading-tight md:block">
            <span className="block max-w-[140px] truncate text-xs font-semibold">{me.full_name}</span>
            <span className="block max-w-[140px] truncate text-[10px] text-muted-foreground">{titleCase(me.roles[0])}</span>
          </span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-64">
        <DropdownMenuLabel>
          <p className="text-sm font-semibold text-foreground">{me.full_name}</p>
          <p className="truncate font-normal">{me.email}</p>
          <div className="mt-1.5 flex flex-wrap gap-1">{me.roles.map((r) => <Badge key={r} tone="info">{titleCase(r)}</Badge>)}</div>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild><Link to="/account"><UserCircle2 />Profile and security</Link></DropdownMenuItem>
        <DropdownMenuItem asChild><Link to="/account#sessions"><MonitorSmartphone />Active sessions</Link></DropdownMenuItem>
        <DropdownMenuItem asChild><Link to="/account#mfa"><KeyRound />Two-factor authentication</Link></DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={async () => { await signOut(); nav("/login"); }} className="text-danger [&_svg]:text-danger"><LogOut />Sign out</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
