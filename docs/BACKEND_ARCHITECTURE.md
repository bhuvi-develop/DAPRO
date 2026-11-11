# DAPRO - Backend Architecture

Python 3.12, FastAPI 0.115, SQLAlchemy 2 (synchronous sessions in FastAPI's threadpool), Pydantic v2, Alembic,
Celery 5.4 on Redis 7. Source: `backend/app`.

## Layout

```
app/
  main.py              App factory: routers, CORS, correlation IDs, error envelope, /health, /metrics
  core/                Cross-cutting: config, db (engine, tenant binding), security (argon2, JWT),
                       authz (require(...) dependency), permissions (roles, SoD), scope (row filters),
                       masking (financial / PII), audit (hash-chained events), errors, context, ids (UUIDv7)
  common/              Shared helpers: pagination, policy lookup, reference numbers, notifications, clock
  models/              Single SQLAlchemy model registry (iam, students, loans, ops, engagement, platform)
  modules/<module>/    api.py (routes) -> service.py (rules) -> repo.py / queries; schemas.py (Pydantic)
  workers/             celery_app.py (beat schedule), tasks_core / tasks_financial / tasks_ops
  seed/                Idempotent DEMO dataset (foundation, students, loans, operations)
migrations/            Alembic: 0001 schema, 0002 security layer (role, grants, RLS, audit trigger)
tests/                 pytest suite against a disposable PostgreSQL database
scripts/               start-api.sh (migrate, seed in demo, uvicorn), gen_docs.py (API + data dictionary)
```

## Modules (18)

| Module | Responsibility |
|---|---|
| auth | Login, refresh, logout, MFA (TOTP), password change, invitations, own sessions |
| admin | Organizations, org units, sharing agreements, users, roles, sessions, integrations, versioned policies, demo reset |
| students | Student identity, CSV import, duplicate review, Student 360 profile, field history |
| lifecycle | Addresses and verification, contacts, contact preferences, consents, academic and employment records |
| parties | Guarantors (maker-checker changes) and witnesses (no liability fields) |
| loans | Loan linking (exact match only), MOCK bank feed adapter, sync, reconciliation |
| repayments | DPD and display status engine from bank schedule and bank-supplied allocation |
| risk | Explainable rule catalogue (8 rules), evaluation, review decisions, rule versioning and dry run |
| cases | Follow-up cases, state machine, follow-ups, evidence, payment commitments |
| field | Field officer case list, visits (check-in/out, structured outcome), supervisor review |
| comms | Templates (two-person approval), sending with consent, quiet hours and caps, MOCK providers |
| grievances | Grievances and data corrections, SLA, conflict-of-interest, dispute pause/restore of cases |
| portal | Borrower self-service, pinned to the caller's own student record |
| dashboard | Role-scoped KPIs, charts and panels computed from the database |
| reports | 14-report catalogue with definitions and as-of metadata; purpose-logged exports |
| audit | Event search, chain verification, case reconstruction |
| notifications | In-app notifications |
| search | Global search across students, loans, cases and grievances within scope |

## Request flow

1. `require("perm", ...)` (`core/authz.py`) authenticates the bearer token, loads a `RequestContext`
   (tenant, user, org, unit, roles, permissions, student id for borrowers, correlation id), checks the
   permission, records refusals in the audit log, and binds `app.tenant_id` for row-level security.
2. The route validates input with Pydantic (`Literal` enums and length limits), then calls the service.
3. The service applies organization, branch and assignment scope (`core/scope.py`), business rules and
   state transitions, writes through SQLAlchemy, appends audit events (`ctx.audit(...)`) and commits once.
4. Responses mask fields by permission (`core/masking.py`). Errors use one envelope:
   `{"error": {"code", "message", "next_step", "correlation_id", "details"}}`.

A test (`test_foundation::test_every_route_declares_permission`) fails if any route lacks a permission.

## Background jobs

| Task | Trigger | Notes |
|---|---|---|
| dapro.bank.sync_all | beat 02:00 | Pulls the MOCK bank feed; idempotent by bank transaction reference |
| dapro.bank.mark_stale | beat hourly :15 | Marks data STALE past the DATA_FRESHNESS policy |
| dapro.risk.nightly | beat 01:00 | Evaluates active rules; de-duplicates open indicators |
| dapro.audit.verify_chain | beat 02:30 | Verifies the audit hash chain, writes a checkpoint |
| dapro.comms.dispatch | beat every 60 s | Sends queued communications through MOCK providers |
| dapro.imports.process_student_csv, dapro.reports.export, dapro.demo.reset | on demand | Enqueued by the API |

Exactly one `celery-beat` container runs the schedule. In tests `DAPRO_CELERY_EAGER=true` runs tasks inline.

## Configuration

`app/core/config.py` reads `DAPRO_*` variables (12-factor). Outside demo/development/test the settings
validator refuses default secrets, default database passwords, non-Secure cookies and MOCK providers.

## Dependencies

`requirements.txt` (runtime) and `requirements-dev.txt` (tests, ruff) list direct dependencies;
`constraints.txt` locks every transitive version and is applied in the Dockerfile and CI.
Regenerate it with `pip freeze` from a verified image after changing requirements.
