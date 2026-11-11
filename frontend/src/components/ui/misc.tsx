import * as React from "react";
import * as L from "@radix-ui/react-label";
import * as S from "@radix-ui/react-switch";
import * as C from "@radix-ui/react-checkbox";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

export function Label({ className, ...p }: React.ComponentPropsWithoutRef<typeof L.Root>) {
  return <L.Root className={cn("text-[13px] font-medium text-foreground", className)} {...p} />;
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton rounded-md", className)} aria-hidden />;
}

export function Separator({ className }: { className?: string }) {
  return <div role="separator" className={cn("h-px w-full bg-border", className)} />;
}

export function Switch({ className, ...p }: React.ComponentPropsWithoutRef<typeof S.Root>) {
  return (
    <S.Root className={cn("peer inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border-2 border-transparent bg-input transition-colors data-[state=checked]:bg-primary disabled:opacity-50", className)} {...p}>
      <S.Thumb className="block h-4 w-4 rounded-full bg-white shadow transition-transform data-[state=checked]:translate-x-4" />
    </S.Root>
  );
}

export function Checkbox({ className, ...p }: React.ComponentPropsWithoutRef<typeof C.Root>) {
  return (
    <C.Root className={cn("flex h-4 w-4 shrink-0 items-center justify-center rounded border border-input bg-surface data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-white", className)} {...p}>
      <C.Indicator><Check className="h-3 w-3" strokeWidth={3} /></C.Indicator>
    </C.Root>
  );
}

export function Avatar({ name, className }: { name: string; className?: string }) {
  const ini = name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join("");
  return (
    <span className={cn("inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-soft text-xs font-semibold text-primary", className)} aria-hidden>
      {ini}
    </span>
  );
}

export function Kbd({ children }: { children: React.ReactNode }) {
  return <kbd className="rounded border bg-muted px-1.5 py-0.5 font-sans text-[10px] font-medium text-muted-foreground">{children}</kbd>;
}
