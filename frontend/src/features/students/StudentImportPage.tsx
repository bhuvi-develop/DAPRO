import * as React from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { CheckCircle2, Download, Play, Upload } from "lucide-react";
import { download, get, post, upload, type Page } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { FileDrop } from "@/components/data/entity";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { InlineError } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { DataTable } from "@/components/data/table";
import { formatDateTime, formatNumber } from "@/lib/utils";

interface Batch { id: string; file_name: string | null; status: string; total_rows: number; valid_rows: number; applied_rows: number; error_rows: number;
  duplicate_rows: number; errors: { row: number | null; field: string | null; message: string }[]; checksum: string | null; created_at: string; finished_at: string | null }

export default function StudentImportPage() {
  const qc = useQueryClient();
  const [file, setFile] = React.useState<File | null>(null);
  const [batchId, setBatchId] = React.useState<string | null>(null);
  const history = useQuery({ queryKey: ["student-imports"], queryFn: () => get<Page<Batch>>("/students/imports?size=20") });
  const batch = useQuery({ queryKey: ["student-import", batchId], queryFn: () => get<Batch>(`/students/imports/${batchId}`), enabled: !!batchId,
    refetchInterval: (q) => (["QUEUED", "RUNNING"].includes(q.state.data?.status ?? "QUEUED") ? 1500 : false) });
  const up = useMutation({
    mutationFn: () => { const f = new FormData(); f.append("file", file!); return upload<Batch>("/students/imports", f); },
    onSuccess: (b) => { setBatchId(b.id); setFile(null); toast.success("File received and validated"); qc.invalidateQueries({ queryKey: ["student-imports"] }); },
  });
  const apply = useMutation({
    mutationFn: () => post<Batch>(`/students/imports/${batchId}/apply`),
    onSuccess: (b) => { toast.success(`Import applied: ${b.applied_rows} students created`); qc.invalidateQueries({ queryKey: ["student-import", batchId] }); qc.invalidateQueries({ queryKey: ["student-imports"] }); qc.invalidateQueries({ queryKey: ["students"] }); },
  });
  const b = batch.data;
  return (
    <div className="space-y-6">
      <PageHeader title="Student import" description="Approved CSV import of college student records. The source batch reference is preserved on every record (INT-COL-01)."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Students", to: "/students" }, { label: "Import" }]}
        actions={<Button variant="secondary" onClick={() => download("/students/imports/template", "dapro-student-template.csv")}><Download />Download template</Button>} />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader><div><CardTitle>1. Upload file</CardTitle><CardDescription>Re-uploading the same file is rejected as a duplicate import (INT-COM-04).</CardDescription></div></CardHeader>
          <CardContent className="space-y-3">
            <FileDrop accept=".csv,text/csv" maxMb={10} file={file} onFile={setFile} hint="DAPRO CSV v1 - use the template columns. Max 10 MB." />
            <InlineError error={up.error} />
          </CardContent>
          <CardFooter className="justify-end"><Button disabled={!file} loading={up.isPending} onClick={() => up.mutate()}><Upload />Upload and validate</Button></CardFooter>
        </Card>
        <Card>
          <CardHeader><div><CardTitle>2. Review and apply</CardTitle><CardDescription>Nothing is created until you apply a validated batch.</CardDescription></div>{b && <StatusBadge status={b.status} />}</CardHeader>
          <CardContent className="space-y-4">
            {!b ? <p className="text-sm text-muted-foreground">Upload a file, or open a previous batch below.</p> : (
              <>
                <KeyValue cols={3} items={[
                  { label: "File", value: b.file_name }, { label: "Rows", value: formatNumber(b.total_rows) }, { label: "Valid", value: formatNumber(b.valid_rows) },
                  { label: "Errors", value: <span className={b.error_rows ? "text-danger" : ""}>{formatNumber(b.error_rows)}</span> },
                  { label: "Duplicates skipped", value: formatNumber(b.duplicate_rows) }, { label: "Created", value: formatNumber(b.applied_rows) },
                ]} />
                {b.checksum && <p className="break-all font-mono text-[10px] text-muted-foreground">sha256 {b.checksum}</p>}
                {b.status === "APPLIED" && <p className="flex items-center gap-2 text-sm text-success"><CheckCircle2 className="h-4 w-4" />Applied {formatDateTime(b.finished_at)}</p>}
                <InlineError error={apply.error} />
              </>
            )}
          </CardContent>
          {b?.status === "VALIDATED" && <CardFooter className="justify-end"><Button loading={apply.isPending} disabled={!b.valid_rows} onClick={() => apply.mutate()}><Play />Apply {b.valid_rows} valid rows</Button></CardFooter>}
        </Card>
      </div>
      {b && b.errors.length > 0 && (
        <Card>
          <CardHeader><CardTitle>Row errors</CardTitle></CardHeader>
          <DataTable rows={b.errors} rowKey={(e) => `${e.row}-${e.field}-${e.message}`} dense caption="Row errors" columns={[
            { key: "row", header: "Row", cell: (e) => e.row ?? "-" }, { key: "field", header: "Field", cell: (e) => e.field ?? "-" },
            { key: "message", header: "Problem", cell: (e) => <span className="text-danger">{e.message}</span> }]} />
        </Card>
      )}
      <Card>
        <CardHeader><CardTitle>Previous imports</CardTitle></CardHeader>
        <DataTable rows={history.data?.items} loading={history.isLoading} error={history.error} rowKey={(r) => r.id} onRowClick={(r) => setBatchId(r.id)} caption="Previous imports" columns={[
          { key: "file", header: "File", cell: (r) => <span className="font-medium">{r.file_name ?? "-"}</span> },
          { key: "status", header: "Status", cell: (r) => <StatusBadge status={r.status} /> },
          { key: "rows", header: "Rows / valid / errors", cell: (r) => <span className="num text-xs">{r.total_rows} / {r.valid_rows} / {r.error_rows}</span> },
          { key: "applied", header: "Created", cell: (r) => <span className="num">{r.applied_rows}</span> },
          { key: "at", header: "Uploaded", cell: (r) => <span className="text-xs">{formatDateTime(r.created_at)}</span> }]}
          empty={<p className="p-6 text-center text-sm text-muted-foreground">No imports yet.</p>} />
      </Card>
    </div>
  );
}
