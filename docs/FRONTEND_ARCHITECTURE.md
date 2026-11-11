# DAPRO - Frontend Architecture

React 18 + TypeScript (strict) + Vite 5. Source: `frontend/src`. Visual rules: `design/DESIGN_SYSTEM.md`.

## Layout

```
src/
  main.tsx            QueryClient, TooltipProvider, RouterProvider (v7_startTransition), Toaster
  app/                routes.tsx (lazy routes, permission guards, error element), nav.ts (sidebar + portal nav),
                      guards.tsx (RequireAuth, Perm), RouteError.tsx
  api/client.ts       Single fetch wrapper: bearer token, JSON, 401 -> one refresh -> retry, ApiError mapping
  auth/               Zustand session store (access token in memory only), bootstrap/sign-out
  components/ui/      Primitives on Radix UI (button, badge, card, dialog, input, menu, tabs, tooltip, ...)
  components/data/    DataTable + Pagination, FilterBar/SearchInput/FilterSelect, PageHeader/KeyValue,
                      Empty/Error/Inline states, StatusBadge/FreshnessBadge/Money, Timeline, EntitySelect, KPI cards
  components/layout/  AppShell (sidebar, top bar, breadcrumbs, global search, notifications, account menu)
  features/<module>/  Pages, dialogs and types per module
  hooks/              useUrlState (filters in the URL), useDebounce
  lib/utils.ts        Formatting (INR, dates), class merging, query strings
  test/               Vitest setup and render/mock helpers
```

## Features and routes

| Area | Routes |
|---|---|
| Cockpit | `/` |
| Students | `/students`, `/students/new`, `/students/import`, `/students/duplicates`, `/students/:id`, `/verifications` |
| Loans and repayment | `/loans`, `/loans/link`, `/loans/:id`, `/repayments`, `/imports`, `/imports/:id`, `/reconciliation` |
| Risk and operations | `/risk`, `/risk/rules`, `/risk/:id`, `/cases`, `/cases/new`, `/cases/:id`, `/field`, `/field/visits/:id`, `/field/review` |
| Engagement | `/communications`, `/templates`, `/grievances`, `/grievances/:id` |
| Insights and audit | `/reports`, `/reports/:code`, `/audit`, `/audit/cases/:id` |
| Administration | `/admin/organizations`, `/admin/users`, `/admin/roles`, `/admin/integrations`, `/admin/policies`, `/admin/demo` |
| Account | `/account`, `/login`, `/accept-invite` |
| Borrower portal | `/portal`, `/portal/profile`, `/portal/grievances`, `/portal/messages` |

Borrower accounts are redirected to `/portal`; staff accounts cannot open the portal.

## Conventions

- **Server state** through TanStack Query only; no business data is hard-coded in components. Query keys are
  feature-scoped (`["grievances", params]`, `["grievance", id]`); mutations invalidate them on success.
- **Filters, sort and page** live in the URL (`useUrlState`) so dashboard KPIs deep-link to filtered lists.
- **Permissions**: `useCan()` and `<Perm>` hide or explain unavailable actions for clarity. The API is the
  authority and repeats every check.
- **Every list** renders loading skeleton, error with retry and correlation id, empty state, and pagination.
- **Forms** validate on the client (required fields, formats, lengths) and show server validation details
  inline (`InlineError`). Buttons stay disabled until the form is valid.
- **Money** is a decimal string from the API rendered by `<Money>`; `null` with a restricted flag shows
  "Restricted". Bank data always shows `<FreshnessBadge>` (source, as-of, sync state, MOCK label).
- **Lazy routes**: every route is code-split and wrapped in its own Suspense boundary; a route-level
  error element replaces a crash with a recoverable page.
- **Accessibility**: labelled inputs (`Field`), table captions, keyboard-operable rows, focus rings,
  `aria-live` toasts, 4.5:1 contrast tokens.

## Tests

- Unit and component tests: Vitest + Testing Library (`src/**/*.test.ts(x)`), `npm test`.
- Browser acceptance: Playwright (`e2e/*.spec.ts`) against the running stack, desktop 1440 px and mobile 360 px,
  with direct PostgreSQL verification through `docker compose exec postgres psql`.
