# DAPRO - Implementation Status

As of 2026-11-06. Per-use-case evidence: [REQUIREMENTS_TRACEABILITY](REQUIREMENTS_TRACEABILITY.md).
Test results: [TESTING_AND_VALIDATION](TESTING_AND_VALIDATION.md). Blockers: [BLOCKER_REGISTER](BLOCKER_REGISTER.md).

## Modules

Columns: List / Detail / Create-Edit / Search-Filter-Pagination / Server-side permission and scope /
Persistence / Audit / Automated tests. "Y" = present and exercised by tests; "-" = not applicable.

| # | Module | UI routes | L | D | C/E | S/F/P | AuthZ | DB | Audit | Tests | Notes |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Administration and IAM | `/admin/*`, `/account`, `/accept-invite` | Y | Y | Y | Y | Y | Y | Y | B, U, E | Policies page completed this session |
| 2 | Student identity and Student 360 | `/students*`, `/verifications` | Y | Y | Y | Y | Y | Y | Y (access logged) | B, E | CSV import; SIS not configured (OD-07) |
| 3 | Loan linkage and bank mirror | `/loans*`, `/imports*`, `/reconciliation` | Y | Y | Link | Y | Y | Y | Y | B, E | MOCK bank feed (OD-06) |
| 4 | Repayment monitoring | `/repayments`, loan schedule tabs | Y | Y | - | Y | Y | Y | - | B, E | Read-only mirror; DPD from bank allocation |
| 5 | Address and contact | Student 360, `/verifications`, portal profile | Y | Y | Y | Y | Y | Y | Y | B, E | History preserved; verification methods pending OD-09 |
| 6 | Academic and employment | Student 360, portal profile | Y | Y | Y | - | Y | Y | Y | B, E | Employment never triggers financial risk |
| 7 | Guarantor and witness | Loan detail > Parties | Y | Y | Y (maker-checker) | - | Y | Y | Y | B | Witnesses have no liability fields |
| 8 | Risk intelligence and human review | `/risk*` | Y | Y | Decision, rule versions | Y | Y | Y | Y | B, E | 8 explainable DEMO_FIXTURE rules (OD-15) |
| 9 | Case management and field operations | `/cases*`, `/field*` | Y | Y | Y | Y | Y | Y | Y | B, E (desktop + mobile) | No location capture (OD-14); no offline drafts |
| 10 | Notifications and communications | `/communications`, `/templates`, bell menu | Y | - | Send, template versions | Y | Y | Y | Y | B | MOCK email/SMS (OD-16) |
| 11 | Borrower portal | `/portal*` | Y | Y | Address, employment, requests | - | Y (own record only) | Y | Y | B, U, E (desktop + mobile) | Completed this session; release decision OD-17 |
| 12 | Grievance management | `/grievances*`, `/portal/grievances` | Y | Y | Y | Y | Y | Y | Y | B, U, E | Completed this session; SLA DEMO_FIXTURE (OD-18) |
| 13 | Reports and analytics | `/`, `/reports*` | Y | Y | Export | Y | Y | Y | Y (purpose) | B, E | 14 reports; dashboard KPIs backend-derived |
| 14 | Audit and compliance | `/audit*` | Y | Y | - | Y | Y | Y | Append-only, hash-chained | B, E | Case reconstruction with completeness flag |

B = backend pytest, U = frontend unit tests, E = Playwright browser acceptance.

## Cross-cutting

| Capability | Status |
|---|---|
| Enterprise UI shell (sidebar groups, top bar, breadcrumbs, global search, notifications, account menu, responsive) | Implemented; design tokens in `design/DESIGN_SYSTEM.md` |
| Dashboard | Role-scoped KPIs and charts from `GET /dashboard/summary`; no hard-coded values |
| Data source labelling | MOCK source and as-of time on every bank figure; demo banner in demo environment; demo templates/policies labelled DEMO_FIXTURE |
| Background processing | Celery worker + single beat; fixed this session (BLK-04) |
| Docker isolation | One Compose project `dapro-platform` |
| CI | GitHub Actions: ruff, pytest, pip-audit, migration reversibility; typecheck, lint, unit tests, build, npm audit; gitleaks |

## Not implemented (by decision or pending decision)

| Item | Reason |
|---|---|
| Live bank, SMS, email integrations | No provider or credentials (OD-06, OD-16) |
| Third-party discovery/correlation from LLD-001 | Conflicts with RD-001 product boundary (CF-02, CF-03, OD-26) |
| Location capture in field visits | Disabled until approved (OD-14) |
| Offline field drafts (UC-28 exception path) | Not built; field UI requires connectivity |
| Automatic post-study update send (UC-22) | Human-reviewed send only |
| Pilot baseline comparison (UC-38) | No baseline data supplied |
| Overseas-specific contact flow (UC-20) | Marked "Not in RD" in the workbook |
| Retention/purge jobs | OD-21 |
| MFA enforcement for privileged roles | OD-20 (MFA available, optional) |
| Usage metering / billing | OD-24 |
