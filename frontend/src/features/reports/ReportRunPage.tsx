import * as React from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Play } from "lucide-react";
import { get, post } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, NativeSelect } from "@/components/ui/input";
import { Field } from "@/components/data/feedback";
import { KeyValue, PageHeader } from "@/components/data/layout";
import { DataTable, type Column } from "@/components/data/table";
import { EmptyState, ErrorState, InlineError } from "@/components/data/states";
import { Badge } from "@/components/ui/badge";
import { PageFallback } from "@/components/layout/AppShell";
import { formatDateTime, formatNumber, titleCase } from "@/lib/utils";
import { useOrgs } from "@/features/loans/shared";
import { ExportButton, ExportHistory } from "./ExportPanel";
import { ENUMS, type ReportSpec } from "./shared";

interface RunResult { meta: { report_code: string; title: string; as_of: string; period: { from: string | null; to: string | null }; filters: Record<string, string>;
  source: string; definition: string; generated_by_role: string; generated_by: string; organization: string; row_count: number; data_origin: string; truncated?: boolean };
  columns: { key: string; label: string }[]; rows: Record<string, unknown>[]; total: number }

function cell(v: unknown) {
  if (v === null || v === undefined || v === "") return <span className="text-muted-foreground">-</span>;
  if (typeof v === "number") return <span className="num">{formatNumber(v)}</span>;
  return String(v);
}

export default function ReportRunPage() {
  const { code = "" } = useParams();
  const cat = useQuery({ queryKey: ["report-catalog"], queryFn: () => get<ReportSpec[]>("/reports/catalog") });
  const banks = useOrgs("BANK");
  const colleges = useOrgs("COLLEGE");
  const [filters, setFilters] = React.useState<Record<string, string>>({});
  const run = useMutation({ mutationFn: () => post<RunResult>(`/reports/${code}/run`, { filters, page: 1, size: 500 }) });
  const spec = cat.data?.find((r) => r.code === code);
  React.useEffect(() => { if (spec?.allowed) run.mutate(); }, [spec?.code]); // eslint-disable-line react-hooks/exhaustive-deps
  if (cat.isLoading) return <PageFallback />;
  if (cat.error) return <ErrorState error={cat.error} />;
  if (!spec) return <EmptyState title="Report not found" />;
  if (!spec.allowed) return <EmptyState title="This report is not available for your role" description={`It requires ${spec.required_permissions.join(", ")}.`} />;
  const setF = (k: string, v: string) => setFilters((f) => { const n = { ...f }; if (v) n[k] = v; else delete n[k]; return n; });
  const res = run.data;
  const cols: Column<Record<string, unknown>>[] = (res?.columns ?? []).map((c) => ({ key: c.key, header: c.label, cell: (r) => cell(r[c.key]) }));
  return (
    <div className="space-y-5">
      <PageHeader title={spec.title} description={spec.description} crumbs={[{ label: "Cockpit", to: "/" }, { label: "Reports", to: "/reports" }, { label: spec.title }]}
        actions={res && <ExportButton code={code} filters={filters} />} />
      <Card>
        <CardHeader><CardTitle>Filters</CardTitle></CardHeader>
        <CardContent>
          <form className="flex flex-wrap items-end gap-3" onSubmit={(e) => { e.preventDefault(); run.mutate(); }}>
            {spec.filters.map((f) => (
              <div key={f.key} className="w-full sm:w-52">
                <Field label={f.label} htmlFor={`f-${f.key}`}>
                  {f.type === "date" ? <Input id={`f-${f.key}`} type="date" value={filters[f.key] ?? ""} onChange={(e) => setF(f.key, e.target.value)} />
                    : f.type.startsWith("org:") ? (
                      <NativeSelect id={`f-${f.key}`} value={filters[f.key] ?? ""} onChange={(e) => setF(f.key, e.target.value)}>
                        <option value="">All in scope</option>
                        {(f.type === "org:BANK" ? banks.data : colleges.data)?.map((o) => <option key={o.id} value={o.id}>{o.name}</option>)}
                      </NativeSelect>)
                    : ENUMS[f.key] ? (
                      <NativeSelect id={`f-${f.key}`} value={filters[f.key] ?? ""} onChange={(e) => setF(f.key, e.target.value)}>
                        <option value="">All</option>{ENUMS[f.key]!.map((v) => <option key={v} value={v}>{titleCase(v)}</option>)}
                      </NativeSelect>)
                    : <Input id={`f-${f.key}`} value={filters[f.key] ?? ""} onChange={(e) => setF(f.key, e.target.value.toUpperCase())} />}
                </Field>
              </div>
            ))}
            <Button type="submit" loading={run.isPending}><Play />Run report</Button>
          </form>
          <div className="mt-3"><InlineError error={run.error} /></div>
        </CardContent>
      </Card>
      {res && (
        <Card>
          <CardHeader><div><CardTitle>{res.meta.title}</CardTitle><p className="text-xs text-muted-foreground">{formatNumber(res.meta.row_count)} rows{res.meta.truncated ? " (truncated)" : ""}</p></div>
            <Badge tone={res.meta.data_origin === "DEMO" ? "warning" : "success"}>{res.meta.data_origin} data</Badge></CardHeader>
          <CardContent className="border-b bg-muted/30">
            <KeyValue cols={3} items={[{ label: "As of", value: formatDateTime(res.meta.as_of) },
              { label: "Period", value: res.meta.period.from || res.meta.period.to ? `${res.meta.period.from ?? "start"} to ${res.meta.period.to ?? "now"}` : "All dates" },
              { label: "Applied filters", value: Object.keys(res.meta.filters).length ? Object.entries(res.meta.filters).map(([k, v]) => `${k}: ${v}`).join("; ") : "None" },
              { label: "Data source", value: res.meta.source }, { label: "Calculation definition", value: res.meta.definition },
              { label: "Generated by", value: `${res.meta.generated_by} (${titleCase(res.meta.generated_by_role)}), ${res.meta.organization}` }]} />
          </CardContent>
          <DataTable dense columns={cols} rows={res.rows.map((r, i) => ({ ...r, __i: i }))} rowKey={(r) => String(r.__i)} caption={res.meta.title} empty={<EmptyState title="No rows for these filters" />} />
        </Card>
      )}
      <ExportHistory code={code} />
    </div>
  );
}
