import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

export const badgeVariants = cva(
  "inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium leading-4",
  {
    variants: {
      tone: {
        neutral: "border-border bg-muted text-muted-foreground",
        info: "border-primary/20 bg-primary-soft text-primary",
        teal: "border-teal/20 bg-teal-soft text-teal",
        success: "border-success/20 bg-success-soft text-success",
        warning: "border-warning/25 bg-warning-soft text-[hsl(32_95%_34%)]",
        danger: "border-danger/20 bg-danger-soft text-danger",
        navy: "border-navy/20 bg-navy text-white",
        outline: "border-border bg-transparent text-foreground",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {
  dot?: boolean;
}

export function Badge({ className, tone, dot, children, ...p }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ tone }), className)} {...p}>
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />}
      {children}
    </span>
  );
}
