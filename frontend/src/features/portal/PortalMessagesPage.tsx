import { useQuery } from "@tanstack/react-query";
import { Mail, MessageSquare } from "lucide-react";
import { get, type Page } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { PageHeader } from "@/components/data/layout";
import { EmptyState, QueryBoundary } from "@/components/data/states";
import { labelFor } from "@/components/data/status";
import { formatDateTime } from "@/lib/utils";
import type { PortalMessage } from "./types";

/** Messages sent to the borrower (own records only). MOCK messages are labelled as not delivered. */
export default function PortalMessagesPage() {
  const q = useQuery({ queryKey: ["portal-messages"], queryFn: () => get<Page<PortalMessage>>("/portal/communications") });
  return (
    <div className="space-y-5">
      <PageHeader title="Messages" description="Reminders and updates sent to you by your institution or bank." />
      <QueryBoundary query={q} isEmpty={(d) => d.items.length === 0}
        empty={<Card><EmptyState icon={Mail} title="No messages yet" description="Messages sent to you will be listed here." /></Card>}>{(d) => (
        <ul className="space-y-3">{d.items.map((m) => {
          const Icon = m.channel === "SMS" ? MessageSquare : Mail;
          return (
            <li key={m.id}><Card className="p-4">
              <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                <Icon className="h-4 w-4 text-teal" aria-hidden /><span className="font-medium text-foreground">{labelFor(m.purpose)}</span>
                <Badge tone="outline">{labelFor(m.channel)}</Badge>
                {m.provider_mode !== "LIVE" && <Badge tone="warning" title="Demo environment: not delivered to a real phone or inbox">Demo - not delivered</Badge>}
                <time className="ml-auto" dateTime={m.created_at}>{formatDateTime(m.created_at)}</time>
              </div>
              {m.subject && <p className="mt-2 text-sm font-medium">{m.subject}</p>}
              <p className="mt-1 whitespace-pre-wrap text-sm text-foreground/85">{m.body}</p>
            </Card></li>
          );
        })}</ul>
      )}</QueryBoundary>
    </div>
  );
}
