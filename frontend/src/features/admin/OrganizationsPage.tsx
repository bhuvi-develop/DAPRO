import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Building2, ChevronRight, FileSignature, GitBranch, Plus } from "lucide-react";
import { get } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/menu";
import { PageHeader } from "@/components/data/layout";
import { EmptyState } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { DataTable } from "@/components/data/table";
import { formatDate, titleCase } from "@/lib/utils";
import { CreateAgreementDialog, CreateOrgDialog, CreateUnitDialog } from "./orgDialogs";
import type { Agreement, OrgRow, UnitRow } from "./types";

function UnitTree({ units, parent = null, depth = 0 }: { units: UnitRow[]; parent?: string | null; depth?: number }) {
  const kids = units.filter((u) => u.parent_id === parent);
  if (!kids.length) return null;
  return (
    <ul className={depth ? "ml-5 border-l pl-3" : ""}>
      {kids.map((u) => (
        <li key={u.id} className="py-1">
          <div className="flex items-center gap-2 text-sm">{depth > 0 && <ChevronRight className="h-3 w-3 text-muted-foreground" />}
            <GitBranch className="h-3.5 w-3.5 text-teal" /><span className="font-medium">{u.name}</span><Badge tone="neutral">{titleCase(u.kind)}</Badge>
            <span className="font-mono text-[11px] text-muted-foreground">{u.code}</span></div>
          <UnitTree units={units} parent={u.id} depth={depth + 1} />
        </li>
      ))}
    </ul>
  );
}

export default function OrganizationsPage() {
  const can = useCan();
  const orgs = useQuery({ queryKey: ["admin-orgs"], queryFn: () => get<OrgRow[]>("/admin/organizations") });
  const units = useQuery({ queryKey: ["admin-units"], queryFn: () => get<UnitRow[]>("/admin/org-units") });
  const agr = useQuery({ queryKey: ["admin-agreements"], queryFn: () => get<Agreement[]>("/admin/sharing-agreements") });
  const [dlg, setDlg] = React.useState<"org" | "unit" | "agr" | null>(null);
  const manage = can("org:manage");
  return (
    <div>
      <PageHeader title="Organizations" description="Colleges, banks and service providers are separate organizations; every record is scoped to its owner (FR-ORG-01..04)."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Administration" }, { label: "Organizations" }]}
        actions={manage ? <Button onClick={() => setDlg("org")}><Plus />New organization</Button> : undefined} />
      <Tabs defaultValue="orgs">
        <TabsList>
          <TabsTrigger value="orgs"><Building2 />Organizations</TabsTrigger>
          <TabsTrigger value="units"><GitBranch />Branches and units</TabsTrigger>
          <TabsTrigger value="agreements"><FileSignature />Data-sharing agreements</TabsTrigger>
        </TabsList>
        <TabsContent value="orgs">
          <Card>
            <DataTable rows={orgs.data} loading={orgs.isLoading} error={orgs.error} rowKey={(o) => o.id} caption="Organizations" columns={[
              { key: "name", header: "Organization", cell: (o) => <div><p className="font-medium">{o.name}</p><p className="font-mono text-[11px] text-muted-foreground">{o.code}</p></div> },
              { key: "type", header: "Type", cell: (o) => <Badge tone={o.type === "BANK" ? "info" : o.type === "COLLEGE" ? "teal" : "neutral"}>{titleCase(o.type)}</Badge> },
              { key: "city", header: "Location", hideOnMobile: true, cell: (o) => [o.city, o.state].filter(Boolean).join(", ") || "-" },
              { key: "users", header: "Users", className: "num", cell: (o) => o.user_count ?? "-" },
              { key: "units", header: "Units", className: "num", cell: (o) => o.unit_count },
              { key: "status", header: "Status", cell: (o) => <StatusBadge status={o.status} /> },
            ]} />
          </Card>
        </TabsContent>
        <TabsContent value="units">
          <div className="mb-3 flex justify-end">{(manage || can("user:manage")) && <Button variant="secondary" onClick={() => setDlg("unit")}><Plus />New unit</Button>}</div>
          <div className="grid gap-4 lg:grid-cols-2">
            {(orgs.data ?? []).filter((o) => (units.data ?? []).some((u) => u.org_id === o.id)).map((o) => (
              <Card key={o.id}><CardHeader><div><CardTitle>{o.name}</CardTitle><CardDescription>Users scoped to a branch or region see only that subtree</CardDescription></div></CardHeader>
                <CardContent><UnitTree units={(units.data ?? []).filter((u) => u.org_id === o.id)} /></CardContent></Card>
            ))}
            {units.data?.length === 0 && <Card><EmptyState title="No units configured" /></Card>}
          </div>
        </TabsContent>
        <TabsContent value="agreements">
          <div className="mb-3 flex justify-end">{manage && <Button variant="secondary" onClick={() => setDlg("agr")}><Plus />New agreement</Button>}</div>
          <Card>
            <DataTable rows={agr.data} loading={agr.isLoading} error={agr.error} rowKey={(a) => a.id} caption="Sharing agreements" columns={[
              { key: "ref", header: "Reference", cell: (a) => <span className="font-mono text-xs">{a.reference}</span> },
              { key: "parties", header: "College and bank", cell: (a) => <span className="text-sm">{a.college_name} <span className="text-muted-foreground">with</span> {a.bank_name}</span> },
              { key: "purposes", header: "Purposes", cell: (a) => <div className="flex flex-wrap gap-1">{a.purposes.map((p) => <Badge key={p} tone="info">{titleCase(p)}</Badge>)}</div> },
              { key: "eff", header: "Effective", hideOnMobile: true, cell: (a) => <span className="text-xs">{formatDate(a.effective_from)}{a.effective_to ? ` - ${formatDate(a.effective_to)}` : ""}</span> },
              { key: "status", header: "Status", cell: (a) => <div className="flex flex-col items-start gap-1"><StatusBadge status={a.status} /><StatusBadge status={a.approval_label} /></div> },
            ]} />
          </Card>
        </TabsContent>
      </Tabs>
      <CreateOrgDialog open={dlg === "org"} onOpenChange={(o) => setDlg(o ? "org" : null)} />
      <CreateUnitDialog open={dlg === "unit"} onOpenChange={(o) => setDlg(o ? "unit" : null)} orgs={orgs.data ?? []} units={units.data ?? []} />
      <CreateAgreementDialog open={dlg === "agr"} onOpenChange={(o) => setDlg(o ? "agr" : null)} orgs={orgs.data ?? []} />
    </div>
  );
}
