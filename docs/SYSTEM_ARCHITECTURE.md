# DAPRO - System Architecture

## 1. Context
DAPRO is a bank-authorised monitoring, borrower-information maintenance, risk-indicator and follow-up coordination
platform connecting college records with bank-confirmed loan information (RD-001 3.2). It is **not** a ledger,
credit bureau, tracing tool, recovery agency or automated decision-maker.

```
 Browser (React SPA, staff + borrower portal)
        |  HTTPS, Bearer access token (memory) + HttpOnly refresh cookie
        v
 nginx (frontend)  --/api-->  FastAPI (backend)  --SQL as dapro_app (RLS)-->  PostgreSQL 16 (postgres)
                                      |                                              ^
                                      | enqueue                                      | owner role: migrations, seed
                                      v                                              |
                                 Redis 7 (redis)  <---  celery-worker, celery-beat --+
                                             |
                                             +--> MOCK bank feed adapter (labelled MOCK; no live bank, OD-06)
                                             +--> MOCK email / SMS providers (nothing delivered, OD-16)
```

## 2. Layering (LLD-001 section 1)
`api.py` (routes, declares permission) -> `service.py` (validation, authorization scope, business rules, audit)
-> `repo.py` / SQLAlchemy queries -> `app/models` (single model registry). Every service call receives a
`RequestContext` (tenant, user, org, roles, permissions, unit scope, correlation id, purpose).
Routes contain no business logic. A test fails the build if any route lacks a `require(...)` permission.

## 3. Multi-tenancy and access control
- **Tenant = programme** (one client deployment) containing colleges, banks and service providers (conflict CF-05).
- PostgreSQL **row-level security** on 42 tenant tables; the API connects as `dapro_app` (NOBYPASSRLS) and binds
  `app.tenant_id` on every transaction (`core/db.py`).
- **Organization scope** in services (`core/scope.py`): college users see their college; bank users see loans of
  their bank and the linked students; branch/region users see their branch subtree; field officers see only
  assigned cases; borrowers see only their own record.
- **Field masking** (`core/masking.py`): bank financial amounts only with `loan:financial`; contact details masked
  without `student:pii_full`.
- Deny-by-default RBAC with 10 roles and ~58 permissions (`core/permissions.py`); segregation-of-duties pairs
  enforced on role assignment; refused access is audited.

## 4. Source of truth and data integrity
- Bank data is a read-only mirror: `loan_snapshots` and `repayment_transactions` are append-only for the
  application role; `repayment_schedules` are versioned. Reversals arrive as new rows.
- DPD and display status are computed from the bank schedule and the **bank-supplied allocation** under versioned
  policy (`modules/repayments/engine.py`). Stale or failed sync gives UNKNOWN, never zero or paid.
- Imports are idempotent by stable external references (`bank_txn_ref`) and file checksums.
- Money: NUMERIC(18,2), decimal strings on the wire, explicit INR.
- Business date uses Asia/Kolkata; timestamps stored in UTC.

## 5. Audit
`audit_events` is append-only and SHA-256 hash-chained per tenant under `pg_advisory_xact_lock`; a database
trigger rejects any modification or removal of audit rows for every role. Nightly `dapro.audit.verify_chain`
writes `audit_checkpoints`.

## 6. Background jobs (Celery beat, Asia/Kolkata)
| Task | Schedule |
|---|---|
| dapro.bank.sync_all | 02:00 daily |
| dapro.bank.mark_stale | hourly |
| dapro.risk.nightly | 01:00 daily |
| dapro.audit.verify_chain | 02:30 daily |
| dapro.comms.dispatch | every 60 s |
| dapro.imports.process_student_csv, dapro.reports.export, dapro.demo.reset | on demand |

## 7. Frontend
React 18 + TypeScript + Vite; Tailwind with design tokens; Radix-based shadcn-style components; TanStack Query for
server state; Zustand for session; React Hook Form + Zod; Recharts; lazy-loaded feature routes. Filters live in
the URL so dashboard KPIs deep-link to filtered module pages.

## 8. Deployment
One Compose project `dapro-platform` with services postgres, redis, backend (migrations + idempotent demo seed
on start in the demo environment), celery-worker, celery-beat (single scheduler) and frontend (nginx serving the
SPA and proxying `/api`). See `DOCKER_SETUP.md` and `deployment/DEPLOYMENT_GUIDE.md`.

## 10. Related documents
`FRONTEND_ARCHITECTURE.md`, `BACKEND_ARCHITECTURE.md`, `DATABASE_DESIGN.md`, `SECURITY_AND_RBAC.md`,
`API_REFERENCE.md`.

## 9. Deviations from LLD-001
See the conflict register in `PROJECT_BASELINE.md` (CF-01..CF-08). Notable: sync SQLAlchemy sessions (FastAPI
threadpool) instead of async; HS256 JWT secret; offset pagination; discovery/correlation not built.
