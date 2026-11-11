import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground shadow-sm hover:bg-primary/90",
        navy: "bg-navy text-white shadow-sm hover:bg-navy-800",
        secondary: "border bg-surface text-foreground shadow-sm hover:bg-muted",
        ghost: "text-foreground hover:bg-muted",
        subtle: "bg-primary-soft text-primary hover:bg-primary/10",
        danger: "bg-danger text-white shadow-sm hover:bg-danger/90",
        success: "bg-success text-white shadow-sm hover:bg-success/90",
        link: "h-auto p-0 text-primary underline-offset-4 hover:underline",
      },
      size: { sm: "h-8 px-3 text-xs", md: "h-9 px-4", lg: "h-10 px-5", icon: "h-9 w-9", "icon-sm": "h-8 w-8" },
    },
    defaultVariants: { variant: "default", size: "md" },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild, loading, children, disabled, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp ref={ref} className={cn(buttonVariants({ variant, size }), className)} disabled={disabled || loading} {...props}>
        {asChild ? children : (<>{loading && <Loader2 className="animate-spin" aria-hidden />}{children}</>)}
      </Comp>
    );
  },
);
Button.displayName = "Button";
