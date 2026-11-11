import * as React from "react";
import * as M from "@radix-ui/react-dropdown-menu";
import * as T from "@radix-ui/react-tabs";
import * as Tip from "@radix-ui/react-tooltip";
import * as P from "@radix-ui/react-popover";
import { cn } from "@/lib/utils";

export const DropdownMenu = M.Root;
export const DropdownMenuTrigger = M.Trigger;
export function DropdownMenuContent({ className, align = "end", ...p }: React.ComponentPropsWithoutRef<typeof M.Content>) {
  return (
    <M.Portal>
      <M.Content align={align} sideOffset={6} className={cn("z-50 min-w-[200px] overflow-hidden rounded-md border bg-popover p-1 shadow-pop data-[state=open]:animate-in data-[state=open]:fade-in-0", className)} {...p} />
    </M.Portal>
  );
}
export function DropdownMenuItem({ className, ...p }: React.ComponentPropsWithoutRef<typeof M.Item>) {
  return <M.Item className={cn("flex cursor-pointer select-none items-center gap-2 rounded-sm px-2.5 py-1.5 text-sm outline-none data-[highlighted]:bg-muted data-[disabled]:opacity-50 [&_svg]:size-4 [&_svg]:text-muted-foreground", className)} {...p} />;
}
export const DropdownMenuSeparator = () => <M.Separator className="-mx-1 my-1 h-px bg-border" />;
export function DropdownMenuLabel({ className, ...p }: React.ComponentPropsWithoutRef<typeof M.Label>) {
  return <M.Label className={cn("px-2.5 py-1.5 text-xs font-medium text-muted-foreground", className)} {...p} />;
}

export const Tabs = T.Root;
export function TabsList({ className, ...p }: React.ComponentPropsWithoutRef<typeof T.List>) {
  return <T.List className={cn("flex items-center gap-1 overflow-x-auto border-b scrollbar-thin", className)} {...p} />;
}
export function TabsTrigger({ className, ...p }: React.ComponentPropsWithoutRef<typeof T.Trigger>) {
  return <T.Trigger className={cn("-mb-px inline-flex items-center gap-1.5 whitespace-nowrap border-b-2 border-transparent px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground data-[state=active]:border-primary data-[state=active]:text-primary [&_svg]:size-4", className)} {...p} />;
}
export function TabsContent({ className, ...p }: React.ComponentPropsWithoutRef<typeof T.Content>) {
  return <T.Content className={cn("pt-5 focus-visible:outline-none", className)} {...p} />;
}

export const TooltipProvider = Tip.Provider;
export function Tooltip({ content, children, side = "top" }: { content: React.ReactNode; children: React.ReactNode; side?: "top" | "bottom" | "left" | "right" }) {
  return (
    <Tip.Root delayDuration={200}>
      <Tip.Trigger asChild>{children}</Tip.Trigger>
      <Tip.Portal>
        <Tip.Content side={side} sideOffset={6} className="z-50 max-w-xs rounded-md bg-navy px-2.5 py-1.5 text-xs text-white shadow-pop">
          {content}
        </Tip.Content>
      </Tip.Portal>
    </Tip.Root>
  );
}

export const Popover = P.Root;
export const PopoverTrigger = P.Trigger;
export function PopoverContent({ className, align = "end", ...p }: React.ComponentPropsWithoutRef<typeof P.Content>) {
  return (
    <P.Portal>
      <P.Content align={align} sideOffset={8} className={cn("z-50 rounded-lg border bg-popover shadow-pop outline-none data-[state=open]:animate-in data-[state=open]:fade-in-0", className)} {...p} />
    </P.Portal>
  );
}
