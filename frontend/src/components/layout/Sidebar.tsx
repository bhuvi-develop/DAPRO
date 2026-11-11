import { NavLink } from "react-router-dom";
import { ChevronsLeft, ChevronsRight } from "lucide-react";
import { NAV } from "@/app/nav";
import { useCan } from "@/auth/store";
import { Tooltip } from "@/components/ui/menu";
import { cn } from "@/lib/utils";

export function BrandMark({ collapsed }: { collapsed?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <svg viewBox="0 0 32 32" className="h-8 w-8 shrink-0" aria-hidden>
        <rect width="32" height="32" rx="7" fill="#1D4ED8" />
        <path d="M9 8h7.5a8 8 0 0 1 0 16H9z" fill="none" stroke="#fff" strokeWidth="3" />
        <circle cx="23" cy="9" r="3" fill="#5EEAD4" />
      </svg>
      {!collapsed && (
        <div className="leading-tight">
          <p className="text-[15px] font-bold tracking-wide text-white">DAPRO</p>
          <p className="text-[10px] font-medium uppercase tracking-[0.12em] text-navy-foreground/70">Loan Intelligence</p>
        </div>
      )}
    </div>
  );
}

export function SidebarNav({ collapsed, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const can = useCan();
  return (
    <nav aria-label="Main navigation" className="flex-1 space-y-5 overflow-y-auto px-3 py-4 scrollbar-thin">
      {NAV.map((g) => {
        const items = g.items.filter((i) => !i.perm || can(i.perm));
        if (!items.length) return null;
        return (
          <div key={g.label}>
            {!collapsed && <p className="mb-1.5 px-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-navy-foreground/50">{g.label}</p>}
            <ul className="space-y-0.5">
              {items.map((i) => {
                const link = (
                  <NavLink to={i.to} end={i.end ?? i.to.split("/").length > 2} onClick={onNavigate}
                    className={({ isActive }) => cn(
                      "group flex items-center gap-2.5 rounded-md px-2.5 py-2 text-[13px] font-medium transition-colors",
                      collapsed && "justify-center px-0",
                      isActive ? "bg-white/10 text-white shadow-[inset_3px_0_0_0_#5EEAD4]" : "text-navy-foreground/75 hover:bg-white/5 hover:text-white",
                    )}>
                    <i.icon className="h-[18px] w-[18px] shrink-0" aria-hidden />
                    {!collapsed && <span className="truncate">{i.label}</span>}
                    {collapsed && <span className="sr-only">{i.label}</span>}
                  </NavLink>
                );
                return <li key={i.to}>{collapsed ? <Tooltip content={i.label} side="right">{link}</Tooltip> : link}</li>;
              })}
            </ul>
          </div>
        );
      })}
    </nav>
  );
}

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  return (
    <aside className={cn("sticky top-0 hidden h-screen shrink-0 flex-col bg-navy transition-[width] duration-200 lg:flex", collapsed ? "w-[68px]" : "w-[252px]")}>
      <div className={cn("flex h-16 items-center border-b border-white/10", collapsed ? "justify-center px-2" : "px-4")}>
        <BrandMark collapsed={collapsed} />
      </div>
      <SidebarNav collapsed={collapsed} />
      <div className="border-t border-white/10 p-3">
        <button type="button" onClick={onToggle} className="flex w-full items-center justify-center gap-2 rounded-md py-2 text-xs text-navy-foreground/70 hover:bg-white/5 hover:text-white" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}>
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : <><ChevronsLeft className="h-4 w-4" />Collapse</>}
        </button>
      </div>
    </aside>
  );
}
