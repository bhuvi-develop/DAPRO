import * as React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { MapPinned } from "lucide-react";
import { get } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog, DialogBody, DialogContent, DialogFooter, DialogHeader } from "@/components/ui/dialog";
import { NativeSelect, Textarea } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { PageHeader } from "@/components/data/layout";
import { EmptyState, InlineError } from "@/components/data/states";
import { StatusBadge } from "@/components/data/status";
import { DataTable } from "@/components/data/table";
import { formatDate, titleCase } from "@/lib/utils";
import { useVerifyAddress } from "./tabs360";

interface V { id: string; student_id: string; method: string; status: string; created_at: string;
  address?: { kind: string; city: string; state: string | null; country: string; source_type: string }; student?: { dapro_ref: string; full_name: string } }

export default function VerificationsPage() {
  const [status, setStatus] = React.useState("PENDING");
  const q = useQuery({ queryKey: ["verifications", status], queryFn: () => get<V[]>(`/address-verifications?status=${status}`) });
  const [sel, setSel] = React.useState<V | null>(null);
  const [outcome, setOutcome] = React.useState("VERIFIED");
  const [notes, setNotes] = React.useState("");
  const m = useVerifyAddress();
  return (
    <div>
      <PageHeader title="Address verification" description="Record who verified an address, how, when and with what outcome (FR-ADR-04/05). Verification never uses device location or social media."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Address verification" }]}
        actions={<NativeSelect aria-label="Status" className="w-40" value={status} onChange={(e) => setStatus(e.target.value)}>{["PENDING", "VERIFIED", "FAILED"].map((s) => <option key={s} value={s}>{titleCase(s)}</option>)}</NativeSelect>} />
      <Card>
        <DataTable rows={q.data} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()} rowKey={(v) => v.id} caption="Address verifications"
          empty={<EmptyState icon={MapPinned} title={`No ${status.toLowerCase()} verifications`} />}
          columns={[
            { key: "student", header: "Student", cell: (v) => <Link className="font-medium hover:text-primary" to={`/students/${v.student_id}`}>{v.student?.full_name}<span className="block font-mono text-[11px] text-muted-foreground">{v.student?.dapro_ref}</span></Link> },
            { key: "addr", header: "Address", cell: (v) => v.address ? <span className="text-sm">{titleCase(v.address.kind)} - {[v.address.city, v.address.state, v.address.country].filter(Boolean).join(", ")}<span className="block text-[11px] text-muted-foreground">{titleCase(v.address.source_type)}</span></span> : "-" },
            { key: "method", header: "Method", cell: (v) => titleCase(v.method) },
            { key: "status", header: "Status", cell: (v) => <StatusBadge status={v.status} /> },
            { key: "at", header: "Requested", hideOnMobile: true, cell: (v) => <span className="text-xs">{formatDate(v.created_at)}</span> },
            { key: "act", header: "", cell: (v) => v.status === "PENDING" ? <Button size="sm" onClick={() => { setSel(v); setOutcome("VERIFIED"); setNotes(""); }}>Record outcome</Button> : null },
          ]} />
      </Card>
      <Dialog open={!!sel} onOpenChange={(o) => !o && setSel(null)}>
        <DialogContent>
          <DialogHeader title="Record verification outcome" description={sel ? `${sel.student?.full_name} - ${titleCase(sel.method)}` : undefined} />
          <DialogBody>
            <Field label="Outcome" htmlFor="v-o" required><NativeSelect id="v-o" value={outcome} onChange={(e) => setOutcome(e.target.value)}><option value="VERIFIED">Verified</option><option value="FAILED">Failed</option></NativeSelect></Field>
            <Field label="Basis and notes" htmlFor="v-n" hint="What evidence was used. A failed verification is not evidence of absconding (BR-05)." required><Textarea id="v-n" value={notes} onChange={(e) => setNotes(e.target.value)} /></Field>
            <InlineError error={m.error} />
          </DialogBody>
          <DialogFooter><Button variant="secondary" onClick={() => setSel(null)}>Cancel</Button>
            <Button loading={m.isPending} disabled={notes.trim().length < 3} onClick={() => m.mutate({ id: sel!.id, status: outcome, notes: notes.trim() }, { onSuccess: () => setSel(null) })}>Save outcome</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
