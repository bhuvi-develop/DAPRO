import * as React from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Ban, KeyRound, Lock, MailPlus, MonitorSmartphone, MoreHorizontal, RotateCcw, ShieldCheck, UserCheck, UserPlus, Users, XCircle } from "lucide-react";
import { del, get, post, type Page } from "@/api/client";
import { useAuth, useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger, Tabs, TabsContent, TabsList, TabsTrigger, Tooltip } from "@/components/ui/menu";
import { Avatar } from "@/components/ui/misc";
import { ConfirmDialog } from "@/components/data/feedback";
import { FilterBar, FilterSelect, SearchInput } from "@/components/data/filters";
import { PageHeader } from "@/components/data/layout";
import { StatusBadge } from "@/components/data/status";
import { DataTable, Pagination } from "@/components/data/table";
import { useUrlState } from "@/hooks/useUrlState";
import { formatDateTime, qs, relativeTime, titleCase } from "@/lib/utils";
import { InviteDialog, RolesDialog } from "./userDialogs";
import type { SessionRow, UserRow } from "./types";

type Action = "suspend" | "activate" | "revoke";
const ACTION_COPY: Record<Action, { title: string; desc: string; tone: "danger" | "default" }> = {
  suspend: { title: "Suspend user", desc: "The user cannot sign in and all active sessions end immediately.", tone: "danger" },
  activate: { title: "Reactivate user", desc: "The user can sign in again with existing credentials.", tone: "default" },
  revoke: { title: "Revoke access permanently", desc: "Revocation cannot be undone; a new invitation would be needed.", tone: "danger" },
};
const DEFAULTS = { q: undefined, status: undefined, sort: undefined };

function SessionsTab() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["admin-sessions"], queryFn: () => get<SessionRow[]>("/admin/sessions") });
  const r = useMutation({ mutationFn: (id: string) => del(`/admin/sessions/${id}`), onSuccess: () => { toast.success("Session revoked"); qc.invalidateQueries({ queryKey: ["admin-sessions"] }); } });
  return (
    <Card>
      <DataTable rows={q.data} loading={q.isLoading} error={q.error} rowKey={(s) => s.id} caption="Active sessions" columns={[
        { key: "user", header: "User", cell: (s) => <div><p className="font-medium">{s.user_name}</p><p className="text-[11px] text-muted-foreground">{s.email}</p></div> },
        { key: "device", header: "Device", hideOnMobile: true, cell: (s) => <span className="line-clamp-1 max-w-[280px] text-xs">{s.user_agent ?? "-"}</span> },
        { key: "ip", header: "IP", hideOnMobile: true, cell: (s) => <span className="font-mono text-xs">{s.ip ?? "-"}</span> },
        { key: "mfa", header: "MFA", cell: (s) => s.mfa_passed ? <Badge tone="success">Passed</Badge> : <Badge tone="neutral">No</Badge> },
        { key: "seen", header: "Last active", cell: (s) => <span className="text-xs" title={formatDateTime(s.last_seen_at)}>{relativeTime(s.last_seen_at)}</span> },
        { key: "act", header: "", cell: (s) => s.current ? <Badge tone="success">You</Badge> : <Button size="sm" variant="secondary" loading={r.isPending && r.variables === s.id} onClick={() => r.mutate(s.id)}>Revoke</Button> },
      ]} />
    </Card>
  );
}

export default function UsersPage() {
  const can = useCan();
  const me = useAuth((s) => s.me)!;
  const qc = useQueryClient();
  const { state, update, page, size } = useUrlState<Record<string, string | undefined>>(DEFAULTS);
  const params = { q: state.q, status: state.status, sort: state.sort ?? "full_name", page, size };
  const q = useQuery({ queryKey: ["admin-users", params], queryFn: () => get<Page<UserRow>>(`/admin/users${qs(params)}`), placeholderData: keepPreviousData });
  const [invite, setInvite] = React.useState(false);
  const [rolesFor, setRolesFor] = React.useState<UserRow | null>(null);
  const [act, setAct] = React.useState<{ u: UserRow; a: Action } | null>(null);
  const done = (msg: string) => { toast.success(msg); qc.invalidateQueries({ queryKey: ["admin-users"] }); };
  const status = useMutation({ mutationFn: (reason: string) => post(`/admin/users/${act!.u.id}/${act!.a}`, { reason }), onSuccess: () => { done("User status updated"); setAct(null); } });
  const unlock = useMutation({ mutationFn: (id: string) => post(`/admin/users/${id}/unlock`), onSuccess: () => done("Account unlocked") });
  const resend = useMutation({ mutationFn: (id: string) => post(`/admin/users/${id}/resend-invitation`), onSuccess: () => done("A new invitation was generated; the previous link no longer works") });
  const manage = can("user:manage");
  return (
    <div>
      <PageHeader title="Users and access" description="Named users only, deny-by-default permissions, and server-side authorization on every request (FR-IAM-01..05)."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Administration" }, { label: "Users" }]}
        actions={manage ? <Button onClick={() => setInvite(true)}><UserPlus />Invite user</Button> : undefined} />
      <Tabs defaultValue="users">
        <TabsList><TabsTrigger value="users"><Users />Users</TabsTrigger>{can("session:manage") && <TabsTrigger value="sessions"><MonitorSmartphone />Active sessions</TabsTrigger>}</TabsList>
        <TabsContent value="users">
          <Card>
            <FilterBar active={state.status ? 1 : 0} onClear={() => update({ status: undefined })}>
              <SearchInput value={state.q} onChange={(v) => update({ q: v })} placeholder="Name or email" />
              <FilterSelect label="Status" value={state.status} onChange={(v) => update({ status: v })} options={["ACTIVE", "INVITED", "SUSPENDED", "REVOKED"]} />
            </FilterBar>
            <DataTable rows={q.data?.items} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()} rowKey={(u) => u.id} caption="Users"
              sort={params.sort} onSort={(s) => update({ sort: s })} columns={[
                { key: "full_name", header: "User", sortable: true, cell: (u) => <div className="flex items-center gap-2.5"><Avatar name={u.full_name} /><div className="min-w-0"><p className="font-medium">{u.full_name}</p><p className="truncate text-[11px] text-muted-foreground">{u.email}</p></div></div> },
                { key: "org", header: "Organization / scope", hideOnMobile: true, cell: (u) => <div className="text-sm">{u.org_name}<p className="text-[11px] text-muted-foreground">{u.unit_name ?? "Whole organization"}</p></div> },
                { key: "roles", header: "Roles", cell: (u) => <div className="flex flex-wrap gap-1">{u.roles.map((r) => <Badge key={r} tone="info">{titleCase(r)}</Badge>)}</div> },
                { key: "status", header: "Status", sortable: true, cell: (u) => <div className="flex flex-wrap gap-1"><StatusBadge status={u.status} />{u.locked && <Badge tone="danger"><Lock className="h-3 w-3" />Locked</Badge>}</div> },
                { key: "mfa", header: "MFA", cell: (u) => u.mfa_enabled ? <Badge tone="success"><ShieldCheck className="h-3 w-3" />Enrolled</Badge> : u.mfa_required ? <Tooltip content="Privileged role: MFA required before production use (NFR-SEC-04)"><span><Badge tone="warning">Required</Badge></span></Tooltip> : <Badge tone="neutral">Optional</Badge> },
                { key: "last_login_at", header: "Last sign-in", sortable: true, hideOnMobile: true, cell: (u) => <span className="text-xs">{u.last_login_at ? relativeTime(u.last_login_at) : "Never"}</span> },
                { key: "act", header: "", cell: (u) => manage && u.id !== me.id ? (
                  <DropdownMenu><DropdownMenuTrigger asChild><Button variant="ghost" size="icon-sm" aria-label={`Actions for ${u.full_name}`}><MoreHorizontal /></Button></DropdownMenuTrigger>
                    <DropdownMenuContent>
                      <DropdownMenuItem onSelect={() => setRolesFor(u)}><KeyRound />Change roles</DropdownMenuItem>
                      {u.status === "INVITED" && <DropdownMenuItem onSelect={() => resend.mutate(u.id)}><MailPlus />Regenerate invitation</DropdownMenuItem>}
                      {u.locked && <DropdownMenuItem onSelect={() => unlock.mutate(u.id)}><RotateCcw />Unlock account</DropdownMenuItem>}
                      <DropdownMenuSeparator />
                      {u.status === "ACTIVE" && <DropdownMenuItem onSelect={() => setAct({ u, a: "suspend" })}><Ban />Suspend</DropdownMenuItem>}
                      {u.status === "SUSPENDED" && <DropdownMenuItem onSelect={() => setAct({ u, a: "activate" })}><UserCheck />Reactivate</DropdownMenuItem>}
                      {u.status !== "REVOKED" && <DropdownMenuItem className="text-danger [&_svg]:text-danger" onSelect={() => setAct({ u, a: "revoke" })}><XCircle />Revoke access</DropdownMenuItem>}
                    </DropdownMenuContent></DropdownMenu>) : null },
              ]} />
            {q.data && <Pagination page={page} size={size} total={q.data.total} onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />}
          </Card>
        </TabsContent>
        {can("session:manage") && <TabsContent value="sessions"><SessionsTab /></TabsContent>}
      </Tabs>
      <InviteDialog open={invite} onOpenChange={setInvite} />
      <RolesDialog user={rolesFor} open={!!rolesFor} onOpenChange={(o) => !o && setRolesFor(null)} />
      {act && <ConfirmDialog open onOpenChange={(o) => !o && setAct(null)} title={`${ACTION_COPY[act.a].title}: ${act.u.full_name}`} description={ACTION_COPY[act.a].desc}
        tone={ACTION_COPY[act.a].tone} rationale minLength={3} loading={status.isPending} error={status.error} confirmLabel={ACTION_COPY[act.a].title} onConfirm={(r) => status.mutate(r ?? "")} />}
    </div>
  );
}
