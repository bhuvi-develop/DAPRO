import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { BarChart3, Database, Lock, Play } from "lucide-react";
import { get } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { ErrorState } from "@/components/data/states";
import { Skeleton } from "@/components/ui/misc";
import type { ReportSpec } from "./shared";

export default function ReportsPage() {
  const q = useQuery({ queryKey: ["report-catalog"], queryFn: () => get<ReportSpec[]>("/reports/catalog") });
  const groups = (q.data ?? []).reduce<Record<string, ReportSpec[]>>((acc, r) => { (acc[r.category] ??= []).push(r); return acc; }, {});
  return (
    <div className="space-y-6">
      <PageHeader title="Reports and analytics" description="Every report states its as-of time, filters, data source and calculation definition (FR-RPT-03). Exports are permission-controlled and purpose-logged."
        crumbs={[{ label: "Cockpit", to: "/" }, { label: "Reports" }]} />
      {q.isLoading && <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-44" />)}</div>}
      {q.error && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {Object.entries(groups).map(([cat, items]) => (
        <section key={cat} className="space-y-3">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">{cat}</h2>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {items.map((r) => (
              <Card key={r.code} className="flex flex-col">
                <CardContent className="flex-1 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <p className="flex items-center gap-2 font-semibold"><BarChart3 className="h-4 w-4 text-primary" />{r.title}</p>
                    {!r.allowed && <Badge tone="neutral"><Lock className="h-3 w-3" />Restricted</Badge>}
                  </div>
                  <p className="text-sm text-muted-foreground">{r.description}</p>
                  <p className="text-[11px] text-muted-foreground"><span className="font-medium text-foreground">Definition: </span>{r.calculation_definition}</p>
                  <p className="flex items-start gap-1 text-[11px] text-muted-foreground"><Database className="mt-0.5 h-3 w-3 shrink-0" />{r.data_source}</p>
                </CardContent>
                <CardFooter className="justify-between">
                  <span className="text-[11px] text-muted-foreground">{r.allowed ? `${r.filters.length} filter(s)` : `Requires ${r.required_permissions.join(", ")}`}</span>
                  {r.allowed ? <Button asChild size="sm"><Link to={`/reports/${r.code}`}><Play />Run</Link></Button>
                    : <Button size="sm" variant="secondary" disabled>Not available</Button>}
                </CardFooter>
              </Card>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
