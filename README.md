# DAPRO - Student Loan Intelligence and Monitoring Platform

DAPRO connects college student records with bank-confirmed education-loan information so colleges, banks and
borrowers can keep borrower data current, see repayment status with its source and freshness, review explainable
risk indicators, coordinate accountable follow-up, and resolve disputes, all under role- and scope-based access
with a tamper-evident audit trail.

DAPRO is **not** a core-banking ledger, credit bureau, tracing tool, recovery agency or automated decision-maker.
The bank remains the source of truth for loan financials.

> **Status:** demo/pilot build against draft requirements DAPRO-RD-001 v1.0 (client review pending).
> Bank, email and SMS integrations are **MOCK** and labelled as such everywhere. See
> [IMPLEMENTATION_STATUS](docs/IMPLEMENTATION_STATUS.md) and [OPEN_DECISIONS](docs/OPEN_DECISIONS.md).

## Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind, Radix UI, TanStack Query, React Hook Form + Zod, Recharts |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Pydantic v2, Alembic, Celery 5 |
| Data | PostgreSQL 16 (row-level security), Redis 7 |
| Runtime | Docker Compose project `dapro-platform` |
| Tests | pytest, Vitest + Testing Library, Playwright |

## Quick start

Prerequisites: Docker Desktop (Compose v2), Node 22 (for frontend tooling), Git.

```bash
cp .env.example .env            # then fill the four secrets (see docs/ENVIRONMENT_SETUP.md)
docker compose up -d --build    # postgres, redis, backend, celery-worker, celery-beat, frontend
docker compose ps               # wait until backend and frontend are "healthy"
```

| URL | What |
|---|---|
| http://localhost:8480 | Web application (staff and borrower portal) |
| http://localhost:8410/api/v1/docs | Interactive API documentation (OpenAPI) |
| http://localhost:8410/api/v1/health | Health check |

On first start the backend applies migrations and loads the **DEMO** dataset (synthetic people and loans only).
Sign in with any demo account below using the `DAPRO_DEMO_PASSWORD` from your `.env`.

| Role | Email |
|---|---|
| Bank loan operations | ravi.ops@anb.demo |
| Collections manager | head.followup@anb.demo |
| Field officer | karthik.field@anb.demo |
| Bank administrator | admin@anb.demo |
| College administrator | priya.admin@nbit.demo |
| Compliance auditor | sanjay.audit@anb.demo |
| Platform administrator | platform.admin@dapro.demo |
| Borrower (portal) | `docker compose exec postgres psql -U dapro_owner -d dapro -c "select email from users where student_id is not null"` |

Stop without losing data: `docker compose stop`. Full reference: [DOCKER_SETUP](docs/DOCKER_SETUP.md).

## Running tests

```bash
# Backend: ruff + pytest against a disposable dapro_test database (never the dev database)
docker compose run --rm --no-deps backend sh -c "ruff check app tests && pytest -q -p no:warnings"

# Frontend: typecheck, lint, unit tests, production build
cd frontend && npm ci && npm run typecheck && npm run lint && npm test && npm run build

# Browser acceptance (stack must be running)
cd frontend && npx playwright install chromium && DAPRO_DEMO_PASSWORD=<from .env> npx playwright test

# Migration reversibility on a scratch database
scripts/test-migrations.sh
```

Details and the latest results: [TESTING_AND_VALIDATION](docs/TESTING_AND_VALIDATION.md).

## Repository layout

```
backend/            FastAPI app (app/modules/<module>/{api,service,...}.py), Alembic migrations, tests, seed
frontend/           React app (src/features/<module>), shared components, unit tests, e2e/ Playwright specs
docs/               Architecture, API, database, security, testing, traceability, decisions, status
docs/source/        Client source documents (requirements, use-case workbook, LLD)
scripts/            stack.sh, test-migrations.sh, backup.sh, restore-check.sh
docker-compose.yml  The single DAPRO Compose project
```

## Documentation

| Topic | Document |
|---|---|
| System architecture | [SYSTEM_ARCHITECTURE](docs/SYSTEM_ARCHITECTURE.md) |
| Frontend / Backend | [FRONTEND_ARCHITECTURE](docs/FRONTEND_ARCHITECTURE.md), [BACKEND_ARCHITECTURE](docs/BACKEND_ARCHITECTURE.md) |
| Database | [DATABASE_DESIGN](docs/DATABASE_DESIGN.md), generated [DATA_DICTIONARY](docs/database/DATA_DICTIONARY.md) |
| API | [API_REFERENCE](docs/API_REFERENCE.md), generated [API_INVENTORY](docs/api/API_INVENTORY.md) |
| Docker / environment | [DOCKER_SETUP](docs/DOCKER_SETUP.md), [ENVIRONMENT_SETUP](docs/ENVIRONMENT_SETUP.md) |
| Security | [SECURITY_AND_RBAC](docs/SECURITY_AND_RBAC.md) |
| Testing | [TESTING_AND_VALIDATION](docs/TESTING_AND_VALIDATION.md) |
| Requirements | [REQUIREMENTS_TRACEABILITY](docs/REQUIREMENTS_TRACEABILITY.md), [OPEN_DECISIONS](docs/OPEN_DECISIONS.md) |
| Status | [IMPLEMENTATION_STATUS](docs/IMPLEMENTATION_STATUS.md), [BLOCKER_REGISTER](docs/BLOCKER_REGISTER.md) |
| Design system | [DESIGN_SYSTEM](docs/design/DESIGN_SYSTEM.md) |
| Contributing | [TEAM_CONTRIBUTING](docs/TEAM_CONTRIBUTING.md) |
