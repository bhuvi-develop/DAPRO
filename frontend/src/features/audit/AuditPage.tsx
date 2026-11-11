import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ShieldCheck, ShieldX } from "lucide-react";
import { get } from "@/api/client";
import { useCan } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/menu";
import { PageHeader } from "@/components/data/layout";
import { DataTable, type Column } from "@/components/data/table";
import { EmptyState, InlineError } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { cn, formatDateTime, formatNumber } from "@/lib/utils";
import { EventsTab } from "./EventsTab";

interface Checkpoint { id: string; verified_at: string; last_seq: number; events_checked: number; ok: boolean; error: string | null; triggered_by: string }
interface VerifyResult { ok: boolean; events_checked: number; last_seq: number; error: string | null; broken_at_seq?: number; verified_at: string }

const cpCols: Column<Checkpoint>[] = [
  { key: "at", header: "Verified", cell: (c) => <span className="text-xs">{formatDateTime(c.verified_at)}</span> },
  { key: "ok", header: "Result", cell: (c) => <StatusBadge status={c.ok ? "VERIFIED" : "FAILED"} /> },
  { key: "n", header: "Events checked", cell: (c) => <span className="num text-xs">{formatNumber(c.events_checked)}</span> },
  { key: "seq", header: "Up to sequence", cell: (c) => <span className="num text-xs">{c.last_seq}</span> },
  { key: "by", header: "Trigger", cell: (c) => <span className="text-xs">{c.triggered_by}</span> },
  { key: "err", header: "Detail", cell: (c) => <span className="text-xs text-danger">{c.error ?? ""}</span> },
];

function ChainTab() {
  const qc = useQueryClient();
  const cps = useQuery({ queryKey: ["audit-checkpoints"], queryFn: () => get<Checkpoint[]>("/audit/checkpoints") });
  const v = useMutation({
    mutationFn: () => get<VerifyResult>("/audit/verify"),
    onSuccess: (r) => { (r.ok ? toast.success : toast.error)(r.ok ? "Audit chain verified" : "Audit chain verification FAILED"); qc.invalidateQueries({ queryKey: ["audit-checkpoints"] }); },
  });
  const r = v.data;
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader><div><CardTitle>Hash-chain verification</CardTitle><CardDescription>Recomputes the SHA-256 chain of every audit event for this tenant. Any edit, deletion or reordering breaks the chain.</CardDescription></div>
          <Button onClick={() => v.mutate()} loading={v.isPending}><ShieldCheck />Run verification</Button></CardHeader>
        <CardContent>
          <InlineError error={v.error} />
          {r ? (
            <div role="status" className={cn("flex items-center gap-3 rounded-md p-4", r.ok ? "bg-success-soft text-success" : "bg-danger-soft text-danger")}>
              {r.ok ? <ShieldCheck className="h-6 w-6" /> : <ShieldX className="h-6 w-6" />}
              <div><p className="font-semibold">{r.ok ? "Chain verified" : "Chain broken"}</p>
                <p className="text-xs">{formatNumber(r.events_checked)} events checked up to sequence {r.last_seq}{r.error ? ` - ${r.error}` : ""}</p></div>
            </div>
          ) : <p className="text-sm text-muted-foreground">Run a verification to record a new checkpoint. Nightly verification runs at 02:30 IST.</p>}
        </CardContent>
      </Card>
      <Card><CardHeader><CardTitle>Checkpoints</CardTitle></CardHeader>
        <DataTable dense columns={cpCols} rows={cps.data} loading={cps.isLoading} error={cps.error} rowKey={(c) => c.id} empty={<EmptyState title="No checkpoints yet" />} />
      </Card>
    </div>
  );
}

export default function AuditPage() {
  const can = useCan();
  const def = can("audit:read") ? "events" : "chain";
  return (
    <div className="space-y-4">
      <PageHeader title="Audit trail" description="Authentication, sensitive access, data changes, exports, approvals, overrides and case actions. Read-only, append-only and hash-chained."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Audit trail" }]} />
      <Tabs defaultValue={def}>
        <TabsList>
          {can("audit:read") && <TabsTrigger value="events">Events</TabsTrigger>}
          {can("audit:verify") && <TabsTrigger value="chain">Chain verification</TabsTrigger>}
        </TabsList>
        {can("audit:read") && <TabsContent value="events"><EventsTab /></TabsContent>}
        {can("audit:verify") && <TabsContent value="chain"><ChainTab /></TabsContent>}
      </Tabs>
    </div>
  );
}
