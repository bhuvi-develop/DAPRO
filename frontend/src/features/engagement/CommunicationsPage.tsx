import * as React from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Info, Send } from "lucide-react";
import { get, type Page } from "@/api/client";
import { useCan } from "@/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { DataTable, Pagination, type Column } from "@/components/data/table";
import { FilterBar, FilterSelect, SearchInput } from "@/components/data/filters";
import { StatusBadge, labelFor } from "@/components/data/status";
import { useUrlState } from "@/hooks/useUrlState";
import { formatDateTime, qs } from "@/lib/utils";
import { SendDialog } from "./SendDialog";
import type { Comm } from "./types";

const DEFAULTS = { status: undefined, channel: undefined, purpose: undefined, q: undefined, sort: undefined };

export default function CommunicationsPage() {
  const can = useCan();
  const [send, setSend] = React.useState(false);
  const { state, update, page, size } = useUrlState<Record<string, string | undefined>>(DEFAULTS);
  const params = { ...state, page, size };
  const q = useQuery({ queryKey: ["comms", params], queryFn: () => get<Page<Comm>>(`/communications${qs(params)}`) });
  const active = ["status", "channel", "purpose", "q"].filter((k) => state[k]).length;
  const cols: Column<Comm>[] = [
    { key: "student", header: "Borrower", cell: (r) => <div><Link onClick={(e) => e.stopPropagation()} to={`/students/${r.student_id}`} className="font-medium hover:text-primary">{r.student_name}</Link><p className="font-mono text-[11px] text-muted-foreground">{r.dapro_ref}</p></div> },
    { key: "template", header: "Template", cell: (r) => <div><p className="text-xs font-medium">{r.template_code ?? "-"}{r.template_version ? ` v${r.template_version}` : ""}</p><p className="text-[11px] text-muted-foreground">{labelFor(r.purpose)} - to {labelFor(r.recipient_type).toLowerCase()}</p></div> },
    { key: "channel", header: "Channel", cell: (r) => <div className="space-y-1"><Badge tone="outline">{labelFor(r.channel)}</Badge><p className="text-[11px] text-muted-foreground">{r.recipient_masked ?? ""}</p></div> },
    { key: "status", header: "Status", cell: (r) => <div className="max-w-[260px] space-y-1"><StatusBadge status={r.status} />{r.block_reason && <p className="text-[11px] text-danger">{r.block_reason}</p>}{r.error && <p className="text-[11px] text-danger">{r.error}</p>}</div> },
    { key: "provider", header: "Provider", hideOnMobile: true, cell: (r) => <Badge tone={r.provider_mode === "LIVE" ? "success" : "warning"} title="Not delivered to a real recipient">{r.provider_mode === "LIVE" ? "LIVE" : "MOCK - not delivered"}</Badge> },
    { key: "created_at", header: "Created", sortable: true, hideOnMobile: true, cell: (r) => <div className="text-xs"><p>{formatDateTime(r.created_at)}</p><p className="text-muted-foreground">{r.delivered_at ? `delivered ${formatDateTime(r.delivered_at)}` : r.sent_at ? `sent ${formatDateTime(r.sent_at)}` : ""}</p></div> },
  ];
  return (
    <div>
      <PageHeader title="Communications" crumbs={[{ label: "Cockpit", to: "/" }, { label: "Communications" }]}
        description="Every outbound message records template version, purpose, channel and provider result (FR-COM-02)."
        actions={can("comm:send") && <Button onClick={() => setSend(true)}><Send />Send communication</Button>} />
      <div className="mb-4 flex items-start gap-2 rounded-md border border-warning/30 bg-warning-soft px-3 py-2 text-xs text-[hsl(32_95%_30%)]">
        <Info className="mt-0.5 h-4 w-4 shrink-0" />Email and SMS use MOCK providers in this environment: nothing is delivered to a real recipient. Delivery is never treated as payment or proof of receipt.
      </div>
      <Card>
        <FilterBar active={active} onClear={() => update({ status: null, channel: null, purpose: null, q: null })}>
          <SearchInput value={state.q} onChange={(v) => update({ q: v })} placeholder="Borrower or template" />
          <FilterSelect label="Status" value={state.status} onChange={(v) => update({ status: v })} options={["QUEUED", "SENT", "DELIVERED", "FAILED", "BLOCKED"]} />
          <FilterSelect label="Channel" value={state.channel} onChange={(v) => update({ channel: v })} options={["EMAIL", "SMS"]} />
          <FilterSelect label="Purpose" value={state.purpose} onChange={(v) => update({ purpose: v })} options={["REMINDER", "UPDATE_REQUEST", "GRIEVANCE_ACK", "GUARANTOR_NOTICE", "GENERAL"]} />
        </FilterBar>
        <DataTable columns={cols} rows={q.data?.items} loading={q.isLoading} error={q.error} onRetry={() => q.refetch()} rowKey={(r) => r.id}
          sort={state.sort} onSort={(s) => update({ sort: s })} caption="Communications" />
        {q.data && <Pagination page={page} size={size} total={q.data.total} onPage={(p) => update({ page: String(p) }, false)} onSize={(s) => update({ size: String(s) })} />}
      </Card>
      <SendDialog open={send} onOpenChange={setSend} />
    </div>
  );
}
