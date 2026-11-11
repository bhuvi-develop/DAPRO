import { Fragment } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Check, KeyRound } from "lucide-react";
import { get } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger, Tooltip } from "@/components/ui/menu";
import { PageHeader } from "@/components/data/layout";
import { ErrorState, TableSkeleton } from "@/components/data/states";
import { titleCase } from "@/lib/utils";
import type { RoleRow } from "./types";

interface Catalogue { permissions: { code: string; description: string }[]; matrix: Record<string, string[]>; sod_conflicts: string[][]; approval_status: string }

export default function RolesPage() {
  const roles = useQuery({ queryKey: ["admin-roles"], queryFn: () => get<RoleRow[]>("/admin/roles") });
  const cat = useQuery({ queryKey: ["admin-permissions"], queryFn: () => get<Catalogue>("/admin/permissions") });
  const codes = roles.data?.map((r) => r.code) ?? [];
  const groups = [...new Set((cat.data?.permissions ?? []).map((p) => p.code.split(":")[0]))];
  return (
    <div>
      <PageHeader title="Roles and permissions" description="Permissions are resource:action strings. Scope (organization, branch, assignment) is evaluated separately on the server."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Administration" }, { label: "Roles" }]}
        meta={cat.data && <Badge tone="warning"><AlertTriangle className="h-3 w-3" />{cat.data.approval_status}</Badge>} />
      <Tabs defaultValue="roles">
        <TabsList><TabsTrigger value="roles"><KeyRound />Roles</TabsTrigger><TabsTrigger value="matrix">Permission matrix</TabsTrigger><TabsTrigger value="sod">Segregation of duties</TabsTrigger></TabsList>
        <TabsContent value="roles">
          {roles.isLoading ? <Card><TableSkeleton /></Card> : roles.error ? <ErrorState error={roles.error} /> : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {roles.data?.map((r) => (
                <Card key={r.id}>
                  <CardHeader><div><CardTitle>{r.name}</CardTitle><CardDescription className="font-mono">{r.code} - v{r.version}</CardDescription></div><Badge tone="neutral">{r.user_count} users</Badge></CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">{r.description}</p>
                    <div className="flex flex-wrap gap-1">{r.org_types.map((t) => <Badge key={t} tone="teal">{titleCase(t)}</Badge>)}</div>
                    <p className="text-xs"><span className="num font-semibold">{r.permissions.length}</span> permissions</p>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
        <TabsContent value="matrix">
          <Card className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[900px] text-xs">
              <thead className="bg-muted/60"><tr><th className="px-3 py-2 text-left font-semibold">Permission</th>{codes.map((c) => <th key={c} className="px-1 py-2 text-center font-semibold" title={c}><span className="inline-block max-w-[72px] truncate">{titleCase(c)}</span></th>)}</tr></thead>
              <tbody>{groups.map((g) => (
                <Fragment key={g}>
                  <tr className="border-t bg-muted/30"><td colSpan={codes.length + 1} className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{titleCase(g)}</td></tr>
                  {cat.data!.permissions.filter((p) => p.code.startsWith(g + ":")).map((p) => (
                    <tr key={p.code} className="border-t">
                      <td className="px-3 py-1.5"><Tooltip content={p.description}><span className="font-mono">{p.code}</span></Tooltip></td>
                      {codes.map((c) => <td key={c} className="px-1 py-1.5 text-center">{roles.data!.find((r) => r.code === c)?.permissions.includes(p.code) ? <Check className="mx-auto h-3.5 w-3.5 text-success" aria-label="granted" /> : <span className="text-muted-foreground/40" aria-label="not granted">-</span>}</td>)}
                    </tr>))}
                </Fragment>))}</tbody>
            </table>
          </Card>
        </TabsContent>
        <TabsContent value="sod">
          <Card><CardHeader><div><CardTitle>Conflicting permission pairs</CardTitle><CardDescription>One user may not hold both permissions in a pair. Role changes that would create a conflict are rejected (RD 6.1).</CardDescription></div></CardHeader>
            <CardContent><ul className="space-y-2">{cat.data?.sod_conflicts.map(([a, b]) => <li key={a + b} className="flex flex-wrap items-center gap-2 text-sm"><Badge tone="info" className="font-mono">{a}</Badge><span className="text-muted-foreground">cannot be combined with</span><Badge tone="danger" className="font-mono">{b}</Badge></li>)}</ul></CardContent></Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
