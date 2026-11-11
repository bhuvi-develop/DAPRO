import {
  Activity, AlertTriangle, BadgeCheck, BarChart3, Banknote, BookUser, Briefcase, Building2, CalendarClock, ClipboardCheck,
  FileSpreadsheet, FileStack, Gauge, GitCompareArrows, KeyRound, Landmark, LayoutDashboard, ListChecks, Mail, MapPinned,
  MessageSquareWarning, Plug, RefreshCw, ScrollText, Settings2, ShieldCheck, SlidersHorizontal, Users, UserSquare2, Copy,
} from "lucide-react";
import type { ElementType } from "react";

export interface NavItem { label: string; to: string; icon: ElementType; perm?: string[]; end?: boolean }
export interface NavGroup { label: string; items: NavItem[] }

export const NAV: NavGroup[] = [
  { label: "Overview", items: [{ label: "Enterprise Cockpit", to: "/", icon: LayoutDashboard, perm: ["dashboard:read"], end: true }] },
  {
    label: "Borrowers",
    items: [
      { label: "Students", to: "/students", icon: Users, perm: ["student:read"] },
      { label: "Student import", to: "/students/import", icon: FileSpreadsheet, perm: ["student:import"] },
      { label: "Duplicate review", to: "/students/duplicates", icon: Copy, perm: ["student:merge"] },
      { label: "Address verification", to: "/verifications", icon: MapPinned, perm: ["address:verify"] },
    ],
  },
  {
    label: "Loans & Repayment",
    items: [
      { label: "Loan accounts", to: "/loans", icon: Landmark, perm: ["loan:read"] },
      { label: "Repayment monitoring", to: "/repayments", icon: Banknote, perm: ["repayment:read"] },
      { label: "Bank sync & imports", to: "/imports", icon: RefreshCw, perm: ["bank:sync"] },
      { label: "Reconciliation", to: "/reconciliation", icon: GitCompareArrows, perm: ["loan:reconcile"] },
    ],
  },
  {
    label: "Risk & Operations",
    items: [
      { label: "Risk review queue", to: "/risk", icon: AlertTriangle, perm: ["risk:read"] },
      { label: "Risk rules", to: "/risk/rules", icon: SlidersHorizontal, perm: ["risk:rules", "risk:approve_rules"] },
      { label: "Cases", to: "/cases", icon: Briefcase, perm: ["case:read"] },
      { label: "Field visits", to: "/field", icon: CalendarClock, perm: ["visit:record"] },
      { label: "Visit review", to: "/field/review", icon: ClipboardCheck, perm: ["visit:review"] },
    ],
  },
  {
    label: "Engagement",
    items: [
      { label: "Communications", to: "/communications", icon: Mail, perm: ["comm:read"] },
      { label: "Templates", to: "/templates", icon: FileStack, perm: ["template:manage"] },
      { label: "Grievances", to: "/grievances", icon: MessageSquareWarning, perm: ["grievance:read"] },
    ],
  },
  {
    label: "Insights & Audit",
    items: [
      { label: "Reports", to: "/reports", icon: BarChart3, perm: ["report:read"] },
      { label: "Audit trail", to: "/audit", icon: ScrollText, perm: ["audit:read", "audit:verify"] },
    ],
  },
  {
    label: "Administration",
    items: [
      { label: "Organizations", to: "/admin/organizations", icon: Building2, perm: ["org:manage"] },
      { label: "Users & access", to: "/admin/users", icon: UserSquare2, perm: ["user:read", "user:manage"] },
      { label: "Roles & permissions", to: "/admin/roles", icon: KeyRound, perm: ["role:read"] },
      { label: "Integrations", to: "/admin/integrations", icon: Plug, perm: ["integration:read"] },
      { label: "Policy configuration", to: "/admin/policies", icon: Settings2, perm: ["policy:read"] },
      { label: "Demo controls", to: "/admin/demo", icon: Gauge, perm: ["demo:reset"] },
    ],
  },
];

export const PORTAL_NAV: NavItem[] = [
  { label: "My loan", to: "/portal", icon: Landmark, end: true },
  { label: "My profile", to: "/portal/profile", icon: BookUser },
  { label: "My requests", to: "/portal/grievances", icon: ListChecks },
  { label: "Messages", to: "/portal/messages", icon: Mail },
];

export const ICONS = { Activity, BadgeCheck, ShieldCheck };
