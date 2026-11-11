# DAPRO Design System

Original enterprise design system for financial operations. Inspired by the DAPRO identity slides (navy/blue),
not copied from them.

## Principles
1. **Facts first** - every financial or personal value shows its source and as-of time (`FreshnessBadge`).
2. **Honest states** - UNKNOWN, STALE, MOCK and NOT_CONFIGURED are first-class visible states, never hidden.
3. **One meaning per colour** - colour communicates status consistently across modules (`StatusBadge`).
4. **Explain blocked actions** - errors show the reason, the next step and a correlation reference.
5. **Restraint** - subtle borders, one shadow level for cards, no decorative gradients or illustrations.

## Tokens (`src/styles/index.css`, Tailwind `tailwind.config.js`)
| Token | Hex | Use |
|---|---|---|
| navy | #102A56 | Sidebar, brand panel, tooltips, structural emphasis |
| primary | #1D4ED8 | Primary actions, links, focus ring, active tab |
| teal | #0F766E | Secondary data series, lifecycle, completion |
| success | #059669 | Paid, verified, healthy, linked |
| warning | #D97706 | Pending, stale, MOCK, partial, demo fixtures |
| danger | #DC2626 | Overdue, failed, high severity, denied - only genuine critical states |
| background | #F5F7FB | App canvas |
| surface/card | #FFFFFF | Cards, tables, inputs |
| primary-soft | #EFF6FF | Hover rows, info badges |
| foreground | #1F2937 | Body text |
| muted-foreground | #64748B | Secondary text |
| border | #E2E8F0 | Dividers and outlines |

Typography: Inter Variable (bundled, works offline). Base 14px; page title 22-24px semibold; card titles 15px;
labels 11-13px. Numbers use tabular figures (`.num`).
Radius: 6/8/10px. Shadow: `shadow-card` (cards), `shadow-pop` (menus, dialogs).

## Status semantics (`components/data/status.tsx`)
- success: PAID, CURRENT, VERIFIED, ACTIVE, APPROVED, HEALTHY, LINKED, RESOLVED, DELIVERED, LIVE
- warning: PENDING, PARTIALLY_PAID, STALE, DEGRADED, MOCK, DRAFT, QUEUED, REVIEW_REQUIRED, DEMO_FIXTURE
- danger: OVERDUE, FAILED, HIGH, ESCALATED, REVERSAL, BLOCKED, SUSPENDED, DISPUTED
- info: NEW, UPCOMING, SCHEDULED, NOT_STARTED, ASSIGNED, MORATORIUM
- neutral: UNKNOWN, NOT_CONFIGURED, CLOSED, DISMISSED, LOW

## Layout
- AppShell: collapsible navy sidebar (252px / 68px) with grouped modules; sticky top bar with global search
  (Ctrl+K), organization scope chip, notification center and user menu; persistent DEMO banner.
- Mobile: sidebar becomes a drawer; tables scroll horizontally; field operations designed for 360px.
- Breadcrumbs in `PageHeader`; contextual actions top-right of each page.

## Components
`ui/`: Button, Card, Badge, Input, Textarea, NativeSelect, Dialog, Sheet (drawer), DropdownMenu, Tabs, Tooltip,
Popover, Label, Switch, Checkbox, Avatar, Skeleton, Kbd.
`data/`: DataTable (server pagination, sorting), Pagination, FilterBar, SearchInput, FilterSelect, DateRange,
KpiCard, ChartCard, Timeline, StatusBadge, FreshnessBadge, Money (role-masked), EmptyState, ErrorState,
InlineError, TableSkeleton, QueryBoundary, ConfirmDialog (with mandatory rationale), Field, PageHeader,
Section, KeyValue.
`layout/`: AppShell, Sidebar, GlobalSearch, NotificationCenter, UserMenu, ContextChip, DemoBanner.

## Accessibility
Skip link, visible focus rings, labelled icon buttons, `aria-invalid` on fields, `role=alert` errors, keyboard
row activation in tables, reduced-motion support, AA contrast for text tokens.
