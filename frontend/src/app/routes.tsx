import { lazy, Suspense, type ComponentType } from "react";
import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { RequireAuth, Perm } from "@/app/guards";
import { NotFound } from "@/features/auth/NotFound";
import { PageFallback } from "@/components/layout/AppShell";
import { RouteError } from "@/app/RouteError";

/** Every lazy route has its own Suspense boundary, so a cold chunk load shows a skeleton instead of crashing. */
const L = (f: () => Promise<{ default: ComponentType }>) => { const C = lazy(f); return <Suspense fallback={<div className="p-6"><PageFallback /></div>}><C /></Suspense>; };
const P = (perm: string[], el: JSX.Element) => <Perm any={perm}>{el}</Perm>;

const staff = [
  { index: true, element: P(["dashboard:read"], L(() => import("@/features/dashboard/DashboardPage"))) },
  { path: "account", element: L(() => import("@/features/auth/AccountPage")) },
  { path: "students", element: P(["student:read"], L(() => import("@/features/students/StudentsPage"))) },
  { path: "students/new", element: P(["student:write"], L(() => import("@/features/students/StudentCreatePage"))) },
  { path: "students/import", element: P(["student:import"], L(() => import("@/features/students/StudentImportPage"))) },
  { path: "students/duplicates", element: P(["student:merge"], L(() => import("@/features/students/DuplicatesPage"))) },
  { path: "students/:id", element: P(["student:read"], L(() => import("@/features/students/Student360Page"))) },
  { path: "verifications", element: P(["address:verify"], L(() => import("@/features/students/VerificationsPage"))) },
  { path: "loans", element: P(["loan:read"], L(() => import("@/features/loans/LoansPage"))) },
  { path: "loans/link", element: P(["loan:link"], L(() => import("@/features/loans/LinkLoanPage"))) },
  { path: "loans/:id", element: P(["loan:read"], L(() => import("@/features/loans/LoanDetailPage"))) },
  { path: "repayments", element: P(["repayment:read"], L(() => import("@/features/loans/RepaymentsPage"))) },
  { path: "imports", element: P(["bank:sync", "student:import"], L(() => import("@/features/loans/ImportsPage"))) },
  { path: "imports/:id", element: P(["bank:sync", "student:import"], L(() => import("@/features/loans/ImportDetailPage"))) },
  { path: "reconciliation", element: P(["loan:reconcile"], L(() => import("@/features/loans/ReconciliationPage"))) },
];

const staff2 = [
  { path: "risk", element: P(["risk:read"], L(() => import("@/features/risk/RiskQueuePage"))) },
  { path: "risk/rules", element: P(["risk:rules", "risk:approve_rules", "policy:read"], L(() => import("@/features/risk/RiskRulesPage"))) },
  { path: "risk/:id", element: P(["risk:read"], L(() => import("@/features/risk/IndicatorDetailPage"))) },
  { path: "cases", element: P(["case:read"], L(() => import("@/features/cases/CasesPage"))) },
  { path: "cases/new", element: P(["case:create"], L(() => import("@/features/cases/CaseCreatePage"))) },
  { path: "cases/:id", element: P(["case:read"], L(() => import("@/features/cases/CaseDetailPage"))) },
  { path: "field", element: P(["visit:record"], L(() => import("@/features/field/MyVisitsPage"))) },
  { path: "field/visits/:id", element: P(["visit:record", "visit:review"], L(() => import("@/features/field/VisitPage"))) },
  { path: "field/review", element: P(["visit:review"], L(() => import("@/features/field/VisitReviewPage"))) },
  { path: "communications", element: P(["comm:read"], L(() => import("@/features/engagement/CommunicationsPage"))) },
  { path: "templates", element: P(["template:manage"], L(() => import("@/features/engagement/TemplatesPage"))) },
  { path: "grievances", element: P(["grievance:read"], L(() => import("@/features/engagement/GrievancesPage"))) },
  { path: "grievances/:id", element: P(["grievance:read"], L(() => import("@/features/engagement/GrievanceDetailPage"))) },
  { path: "reports", element: P(["report:read"], L(() => import("@/features/reports/ReportsPage"))) },
  { path: "reports/:code", element: P(["report:read"], L(() => import("@/features/reports/ReportRunPage"))) },
  { path: "audit", element: P(["audit:read", "audit:verify"], L(() => import("@/features/audit/AuditPage"))) },
  { path: "audit/cases/:id", element: P(["audit:read"], L(() => import("@/features/audit/CaseReconstructionPage"))) },
  { path: "admin/organizations", element: P(["org:manage", "org:read"], L(() => import("@/features/admin/OrganizationsPage"))) },
  { path: "admin/users", element: P(["user:read", "user:manage"], L(() => import("@/features/admin/UsersPage"))) },
  { path: "admin/roles", element: P(["role:read"], L(() => import("@/features/admin/RolesPage"))) },
  { path: "admin/integrations", element: P(["integration:read"], L(() => import("@/features/admin/IntegrationsPage"))) },
  { path: "admin/policies", element: P(["policy:read"], L(() => import("@/features/admin/PoliciesPage"))) },
  { path: "admin/demo", element: P(["demo:reset"], L(() => import("@/features/admin/DemoControlsPage"))) },
  { path: "*", element: <NotFound /> },
];

const portal = [
  { index: true, element: L(() => import("@/features/portal/PortalHomePage")) },
  { path: "profile", element: L(() => import("@/features/portal/PortalProfilePage")) },
  { path: "grievances", element: L(() => import("@/features/portal/PortalGrievancesPage")) },
  { path: "messages", element: L(() => import("@/features/portal/PortalMessagesPage")) },
];

export const router = createBrowserRouter([{ errorElement: <RouteError />, children: [
  { path: "/login", element: L(() => import("@/features/auth/LoginPage")) },
  { path: "/accept-invite", element: L(() => import("@/features/auth/AcceptInvitePage")) },
  { element: <RequireAuth />, children: [{ element: <AppShell />, children: [...staff, ...staff2] }] },
  { element: <RequireAuth portal />, children: [{ path: "/portal", element: L(() => import("@/features/portal/PortalLayout")), children: portal }] },
  { path: "/home", element: <Navigate to="/" replace /> },
] }], { future: { v7_relativeSplatPath: true } });
