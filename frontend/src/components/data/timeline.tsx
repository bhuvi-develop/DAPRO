import * as React from "react";
import { Link } from "react-router-dom";
import { Circle } from "lucide-react";
import { cn, formatDateTime, relativeTime } from "@/lib/utils";

export interface TimelineItem { id: string; at: string; title: React.ReactNode; body?: React.ReactNode; actor?: string | null; icon?: React.ElementType; tone?: "default" | "success" | "warning" | "danger" | "info"; link?: string | null }

const DOT: Record<string, string> = { default: "bg-muted text-muted-foreground", success: "bg-success-soft text-success", warning: "bg-warning-soft text-warning", danger: "bg-danger-soft text-danger", info: "bg-primary-soft text-primary" };

export function Timeline({ items, compact }: { items: TimelineItem[]; compact?: boolean }) {
  return (
    <ol className="relative space-y-0">
      {items.map((it, i) => {
        const Icon = it.icon ?? Circle;
        const content = (
          <div className="min-w-0 flex-1 pb-4">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3">
              <p className="text-sm text-foreground">{it.title}</p>
              <time dateTime={it.at} title={formatDateTime(it.at)} className="shrink-0 text-[11px] text-muted-foreground">{relativeTime(it.at)}</time>
            </div>
            {it.actor && <p className="text-[11px] text-muted-foreground">by {it.actor}</p>}
            {it.body && !compact && <div className="mt-1 text-xs text-muted-foreground">{it.body}</div>}
          </div>
        );
        return (
          <li key={it.id} className="relative flex gap-3">
            {i < items.length - 1 && <span className="absolute left-[13px] top-7 h-[calc(100%-20px)] w-px bg-border" aria-hidden />}
            <span className={cn("relative z-10 mt-0.5 flex h-[27px] w-[27px] shrink-0 items-center justify-center rounded-full", DOT[it.tone ?? "default"])}><Icon className="h-3.5 w-3.5" aria-hidden /></span>
            {it.link ? <Link to={it.link} className="min-w-0 flex-1 rounded hover:bg-muted/50">{content}</Link> : content}
          </li>
        );
      })}
    </ol>
  );
}
