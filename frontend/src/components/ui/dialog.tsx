import * as React from "react";
import * as D from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

export const Dialog = D.Root;
export const DialogTrigger = D.Trigger;
export const DialogClose = D.Close;

export function DialogContent({ className, children, wide, ...p }: React.ComponentPropsWithoutRef<typeof D.Content> & { wide?: boolean }) {
  return (
    <D.Portal>
      <D.Overlay className="fixed inset-0 z-50 bg-navy/40 backdrop-blur-[1px] data-[state=open]:animate-in data-[state=open]:fade-in-0" />
      <D.Content
        className={cn("fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[calc(100%-2rem)] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border bg-surface shadow-pop scrollbar-thin data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95",
          wide ? "max-w-3xl" : "max-w-lg", className)}
        {...p}>
        {children}
        <D.Close className="absolute right-3 top-3 rounded-md p-1.5 text-muted-foreground hover:bg-muted" aria-label="Close">
          <X className="h-4 w-4" />
        </D.Close>
      </D.Content>
    </D.Portal>
  );
}

export function DialogHeader({ title, description }: { title: string; description?: React.ReactNode }) {
  return (
    <div className="border-b px-5 py-4 pr-12">
      <D.Title className="text-base font-semibold">{title}</D.Title>
      {description ? <D.Description className="mt-1 text-sm text-muted-foreground">{description}</D.Description> : <D.Description className="sr-only">{title}</D.Description>}
    </div>
  );
}

export function DialogBody({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("space-y-4 px-5 py-4", className)} {...p} />;
}

export function DialogFooter({ className, ...p }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex flex-col-reverse gap-2 border-t bg-muted/40 px-5 py-3 sm:flex-row sm:justify-end", className)} {...p} />;
}

/** Right-side detail drawer. */
export function SheetContent({ className, children, title, description, ...p }: React.ComponentPropsWithoutRef<typeof D.Content> & { title: string; description?: string }) {
  return (
    <D.Portal>
      <D.Overlay className="fixed inset-0 z-50 bg-navy/30 data-[state=open]:animate-in data-[state=open]:fade-in-0" />
      <D.Content className={cn("fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col border-l bg-surface shadow-pop data-[state=open]:animate-in data-[state=open]:slide-in-from-right", className)} {...p}>
        <div className="flex items-start justify-between border-b px-5 py-4">
          <div>
            <D.Title className="text-base font-semibold">{title}</D.Title>
            <D.Description className={description ? "mt-0.5 text-sm text-muted-foreground" : "sr-only"}>{description ?? title}</D.Description>
          </div>
          <D.Close className="rounded-md p-1.5 text-muted-foreground hover:bg-muted" aria-label="Close"><X className="h-4 w-4" /></D.Close>
        </div>
        <div className="flex-1 overflow-y-auto scrollbar-thin">{children}</div>
      </D.Content>
    </D.Portal>
  );
}
