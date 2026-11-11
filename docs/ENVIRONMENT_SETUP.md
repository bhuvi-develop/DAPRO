# DAPRO - Environment Setup

## Prerequisites

| Tool | Version | Used for |
|---|---|---|
| Docker Desktop / Engine | Compose v2 | Running the stack and backend tests |
| Node.js | 22.x | Frontend tooling, Vite dev server, Playwright |
| Python | 3.12 (optional) | Running the backend outside Docker |
| Git | any recent | Source control |

## 1. Environment file

```bash
cp .env.example .env
```

`.env` is ignored by Git and must never be committed. Generate each secret with
`python -c "import secrets;print(secrets.token_urlsafe(48))"`.

| Variable | Required | Meaning |
|---|---|---|
| DAPRO_ENV | yes | `demo` (seeded demo data, demo controls), `development`, `test`, `production` |
| DAPRO_DB_NAME / DAPRO_DB_OWNER | defaults | Database and owner role (migrations, seed) |
| DAPRO_DB_OWNER_PASSWORD | **yes** | Owner role password |
| DAPRO_APP_DB_PASSWORD | **yes** | Password of `dapro_app`, the runtime role subject to row-level security |
| DAPRO_JWT_SECRET | **yes** | HS256 signing secret, at least 32 random characters |
| DAPRO_DEMO_PASSWORD | demo only | Shared password of the generated demo accounts |
| DAPRO_*_HOST_PORT | defaults | Host ports 55480 (db), 8410 (api), 8480 (web) |
| DAPRO_CORS_ORIGINS | default | Allowed browser origins |
| DAPRO_EMAIL_MODE / DAPRO_SMS_MODE | default `mock` | `mock` or `disabled`; no live provider exists (OD-16) |
| DAPRO_BANK_ADAPTER | default `mock` | `mock` or `none`; no live bank API exists (OD-06) |

Outside `demo`, `development` and `test` the backend **refuses to start** if the JWT secret or database
passwords are defaults, the refresh cookie is not `Secure`, or a MOCK provider is configured
(`app/core/config.py`). This prevents a production deploy from running with public defaults or fake data.

## 2. Full stack in Docker (recommended)

```bash
docker compose up -d --build
```

## 3. Frontend with hot reload

Run the backend in Docker and the Vite dev server on the host:

```bash
docker compose up -d postgres redis backend celery-worker celery-beat
cd frontend && npm ci && npm run dev      # http://localhost:5180, proxies /api to http://localhost:8410
```

## 4. Backend on the host (optional)

```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate      # Windows Git Bash; use .venv/bin/activate elsewhere
pip install -r requirements-dev.txt
export DAPRO_DATABASE_URL=postgresql+psycopg://dapro_app:<app pw>@localhost:55480/dapro
export DAPRO_DATABASE_OWNER_URL=postgresql+psycopg://dapro_owner:<owner pw>@localhost:55480/dapro
export DAPRO_APP_DB_PASSWORD=<app pw> DAPRO_JWT_SECRET=<secret> DAPRO_ENV=demo
alembic upgrade head && python -m app.seed.run --if-empty
uvicorn app.main:app --reload --port 8000
```

## 5. Demo data

The seed (`backend/app/seed/`) creates one DEMO tenant with two colleges, two banks plus isolation fixtures,
staff users for every role, synthetic students, MOCK bank loans, schedules and transactions, risk indicators,
cases, field visits, communications, grievances and borrower portal logins. It is idempotent
(`--if-empty`) and runs automatically when the backend starts with `DAPRO_ENV=demo`. Every record belongs to the
`DEMO` tenant, and bank data is labelled `MOCK` in the UI. No real person is represented.

Rebuild demo data from the UI (Administration > Demo controls, `demo:reset` permission, phrase
`RESET DEMO DATA`); the audit trail is preserved.

## Windows notes

- Git Bash rewrites arguments that look like POSIX paths (`/app` becomes `C:/Program Files/Git/app`).
  Prefix commands passing container paths with `MSYS_NO_PATHCONV=1`.
- Use LF line endings for `*.sh` files (they run inside Linux containers).
