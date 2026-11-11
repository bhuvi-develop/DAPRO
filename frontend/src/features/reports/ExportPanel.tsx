import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Download, FileDown, ShieldCheck } from "lucide-react";
import { download, get, post, type Page } from "@/api/client";
import { useCan } from "@/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { DataTable, type Column } from "@/components/data/table";
import { EmptyState, InlineError } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { formatDateTime, formatNumber } from "@/lib/utils";
import type { ExportJob } from "./shared";

export function ExportButton({ code, filters }: { code: string; filters: Record<string, string> }) {
  const can = useCan();
  const qc = useQueryClient();
  const [open, setOpen] = React.useState(false);
  const [purpose, setPurpose] = React.useState("");
  const [touched, setTouched] = React.useState(false);
  const m = useMutation({
    mutationFn: () => post<ExportJob>("/exports", { report_code: code, filters, purpose: purpose.trim() }),
    onSuccess: () => { toast.success("Export queued. It appears in export history when ready."); setOpen(false); setPurpose(""); qc.invalidateQueries({ queryKey: ["exports"] }); },
  });
  if (!can("export:create")) return null;
  const err = purpose.trim().length < 10 ? "State why you need this export (at least 10 characters)" : undefined;
  return (
    <>
      <Button variant="secondary" onClick={() => { setTouched(false); setOpen(true); }}><FileDown />Export CSV</Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader title="Export report data" description="Exports are limited to fields your role may see. The purpose, filters and file hash are recorded in the audit trail (FR-RPT-04)." />
          <DialogBody>
            <Field label="Purpose of export" htmlFor="exp-purpose" required error={touched ? err : undefined} hint="For example: Monthly portfolio review for the bank credit committee.">
              <Textarea id="exp-purpose" value={purpose} onChange={(e) => setPurpose(e.target.value)} aria-invalid={touched && !!err} />
            </Field>
            <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground"><ShieldCheck className="h-3.5 w-3.5 text-teal" />Filters applied: {Object.keys(filters).length ? Object.entries(filters).map(([k, v]) => `${k}=${v}`).join(", ") : "none"}</p>
            <InlineError error={m.error} />
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setOpen(false)}>Cancel</Button>
            <Button loading={m.isPending} onClick={() => { setTouched(true); if (!err) m.mutate(); }}>Create export</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

export function ExportHistory({ code }: { code?: string }) {
  const can = useCan();
  const enabled = can(["export:create", "audit:read"]);
  const q = useQuery({
    queryKey: ["exports"], enabled,
    queryFn: () => get<Page<ExportJob>>("/exports?size=25"),
    refetchInterval: (query) => (query.state.data?.items.some((j) => ["QUEUED", "RUNNING"].includes(j.status)) ? 2500 : false),
  });
  const [err, setErr] = React.useState<unknown>(null);
  if (!enabled) return null;
  const rows = (q.data?.items ?? []).filter((j) => !code || j.report_code === code);
  const cols: Column<ExportJob>[] = [
    { key: "at", header: "Requested", cell: (j) => <span className="text-xs">{formatDateTime(j.created_at)}</span> },
    { key: "r", header: "Report", cell: (j) => <span className="text-sm">{j.title}</span> },
    { key: "p", header: "Purpose", cell: (j) => <span className="text-xs text-muted-foreground">{j.purpose}</span> },
    { key: "s", header: "Status", cell: (j) => <StatusBadge status={j.status} /> },
    { key: "n", header: "Rows", cell: (j) => <span className="num text-xs">{j.row_count === null ? "-" : formatNumber(j.row_count)}</span> },
    { key: "h", header: "SHA-256", hideOnMobile: true, cell: (j) => <span className="font-mono text-[10px] text-muted-foreground">{j.sha256 ? `${j.sha256.slice(0, 16)}...` : "-"}</span> },
    { key: "d", header: "", cell: (j) => j.status === "COMPLETED"
      ? <Button size="sm" variant="ghost" aria-label={`Download ${j.title}`} onClick={async () => { setErr(null); try { await download(`/exports/${j.id}/download`, j.file_name ?? "export.csv"); } catch (e) { setErr(e); } }}><Download />Download</Button>
      : j.error ? <span className="text-[11px] text-danger">{j.error}</span> : null },
  ];
  return (
    <Card>
      <CardHeader><div><CardTitle>Export history</CardTitle><CardDescription>Downloads are restricted to the requester and auditors, and every download is audited.</CardDescription></div></CardHeader>
      {!!err && <div className="px-5 pt-3"><InlineError error={err} /></div>}
      <DataTable dense columns={cols} rows={rows} loading={q.isLoading} error={q.error} rowKey={(j) => j.id} caption="Export history" empty={<EmptyState title="No exports yet" />} />
    </Card>
  );
}
