import * as React from "react";
import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";

export interface Crumb { label: string; to?: string }

export function PageHeader({ title, description, crumbs, actions, meta, className }: { title: React.ReactNode; description?: React.ReactNode; crumbs?: Crumb[]; actions?: React.ReactNode; meta?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("mb-6", className)}>
      {crumbs && crumbs.length > 0 && (
        <nav aria-label="Breadcrumb" className="mb-2 flex flex-wrap items-center gap-1 text-xs text-muted-foreground">
          {crumbs.map((c, i) => (
            <span key={i} className="inline-flex items-center gap-1">
              {i > 0 && <ChevronRight className="h-3 w-3" aria-hidden />}
              {c.to ? <Link to={c.to} className="hover:text-foreground">{c.label}</Link> : <span aria-current="page" className="text-foreground">{c.label}</span>}
            </span>
          ))}
        </nav>
      )}
      <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div className="min-w-0">
          <h1 className="truncate text-[22px] font-semibold leading-8">{title}</h1>
          {description && <p className="mt-1 max-w-3xl text-sm text-muted-foreground">{description}</p>}
          {meta && <div className="mt-2 flex flex-wrap items-center gap-2">{meta}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}

export function Section({ title, description, actions, children, className }: { title: string; description?: string; actions?: React.ReactNode; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("space-y-3", className)}>
      <div className="flex items-end justify-between gap-3">
        <div>
          <h2 className="text-[15px] font-semibold">{title}</h2>
          {description && <p className="text-xs text-muted-foreground">{description}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  );
}

export function KeyValue({ items, cols = 2, className }: { items: { label: string; value: React.ReactNode; hint?: React.ReactNode }[]; cols?: 1 | 2 | 3 | 4; className?: string }) {
  const grid = { 1: "sm:grid-cols-1", 2: "sm:grid-cols-2", 3: "sm:grid-cols-3", 4: "sm:grid-cols-2 lg:grid-cols-4" }[cols];
  return (
    <dl className={cn("grid grid-cols-1 gap-x-6 gap-y-4", grid, className)}>
      {items.map((it) => (
        <div key={it.label} className="min-w-0">
          <dt className="text-xs font-medium text-muted-foreground">{it.label}</dt>
          <dd className="mt-0.5 break-words text-sm">{it.value ?? <span className="text-muted-foreground">-</span>}</dd>
          {it.hint && <dd className="mt-0.5 text-[11px] text-muted-foreground">{it.hint}</dd>}
        </div>
      ))}
    </dl>
  );
}
