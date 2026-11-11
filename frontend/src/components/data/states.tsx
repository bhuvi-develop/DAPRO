import * as React from "react";
import { AlertTriangle, Inbox, RefreshCw, ShieldAlert } from "lucide-react";
import { ApiError } from "@/api/client";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/misc";
import { cn } from "@/lib/utils";

export function EmptyState({ title, description, icon: Icon = Inbox, action, className }: { title: string; description?: React.ReactNode; icon?: React.ElementType; action?: React.ReactNode; className?: string }) {
  return (
    <div className={cn("flex flex-col items-center justify-center px-6 py-12 text-center", className)}>
      <div className="mb-3 rounded-full bg-muted p-3 text-muted-foreground"><Icon className="h-5 w-5" aria-hidden /></div>
      <p className="text-sm font-medium">{title}</p>
      {description && <p className="mt-1 max-w-sm text-xs text-muted-foreground">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/** Blocked actions explain the reason and next step (NFR-USA-02). */
export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  const e = error instanceof ApiError ? error : null;
  const forbidden = e?.status === 403;
  const Icon = forbidden ? ShieldAlert : AlertTriangle;
  return (
    <div role="alert" className={cn("flex flex-col items-center justify-center px-6 py-10 text-center", className)}>
      <div className={cn("mb-3 rounded-full p-3", forbidden ? "bg-warning-soft text-warning" : "bg-danger-soft text-danger")}><Icon className="h-5 w-5" /></div>
      <p className="text-sm font-medium">{forbidden ? "You do not have access to this information" : e?.message ?? "Something went wrong"}</p>
      {e?.nextStep && <p className="mt-1 max-w-md text-xs text-muted-foreground">{e.nextStep}</p>}
      {e?.correlationId && <p className="mt-2 font-mono text-[10px] text-muted-foreground">Reference: {e.correlationId}</p>}
      {onRetry && !forbidden && <Button variant="secondary" size="sm" className="mt-4" onClick={onRetry}><RefreshCw />Retry</Button>}
    </div>
  );
}

export function InlineError({ error }: { error: unknown }) {
  if (!error) return null;
  const e = error instanceof ApiError ? error : null;
  return (
    <div role="alert" className="rounded-md border border-danger/20 bg-danger-soft px-3 py-2 text-sm text-danger">
      <p className="font-medium">{e?.message ?? String(error)}</p>
      {e?.nextStep && <p className="mt-0.5 text-xs opacity-90">{e.nextStep}</p>}
      {e?.details?.length ? <ul className="mt-1 list-disc pl-4 text-xs">{e.details.map((d) => <li key={d.field + d.message}>{d.field}: {d.message}</li>)}</ul> : null}
    </div>
  );
}

export function TableSkeleton({ rows = 8, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="divide-y">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 px-4 py-3">
          {Array.from({ length: cols }).map((__, j) => <Skeleton key={j} className={cn("h-4", j === 0 ? "w-40" : "flex-1")} />)}
        </div>
      ))}
    </div>
  );
}

export function QueryBoundary<T>({ query, children, skeleton, empty, isEmpty }: {
  query: { data?: T; isLoading: boolean; error: unknown; refetch: () => unknown };
  children: (data: T) => React.ReactNode; skeleton?: React.ReactNode; empty?: React.ReactNode; isEmpty?: (d: T) => boolean;
}) {
  if (query.isLoading) return <>{skeleton ?? <TableSkeleton />}</>;
  if (query.error) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  if (query.data === undefined) return null;
  if (isEmpty?.(query.data)) return <>{empty ?? <EmptyState title="Nothing to show yet" />}</>;
  return <>{children(query.data)}</>;
}
