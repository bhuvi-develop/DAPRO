# DAPRO - Deployment Guide

Reference deployment with Docker Compose. Production hosting, data residency, TLS termination, key management and
support model are open decisions (OD-19, OD-22, OD-27).

## 1. Prerequisites
Docker Engine 24+ with Compose v2, 4 GB RAM, ports 8410 (API), 8480 (web), 55480 (PostgreSQL, localhost only).

## 2. Configure
```
cp .env.example .env
# generate secrets: python -c "import secrets;print(secrets.token_urlsafe(48))"
# set DAPRO_DB_OWNER_PASSWORD, DAPRO_APP_DB_PASSWORD, DAPRO_JWT_SECRET, DAPRO_DEMO_PASSWORD
```
`.env` is git-ignored. Secrets are only read from the environment (INT-COM-02, NFR-SEC-05).

| Variable | Purpose |
|---|---|
| DAPRO_ENV | `demo` seeds the DEMO dataset on start; `production` refuses demo seeding and demo reset |
| DAPRO_DB_OWNER / _PASSWORD | Schema owner used for migrations and maintenance only |
| DAPRO_APP_DB_PASSWORD | Runtime role `dapro_app` (no BYPASSRLS), created by migration 0002 |
| DAPRO_JWT_SECRET | Access-token signing secret (32+ random characters) |
| DAPRO_BANK_ADAPTER | `mock` or `none`. No live bank adapter exists (OD-06) |
| DAPRO_EMAIL_MODE / DAPRO_SMS_MODE | `mock` or `disabled`. Nothing is delivered to real recipients |
| DAPRO_FIELD_LOCATION_CAPTURE_ENABLED | Must stay `false` until OD-14 is approved |
| DAPRO_CORS_ORIGINS | Allowed browser origins |

## 3. Start
```
docker compose up -d --build
docker compose ps            # backend healthy, celery-worker and celery-beat running, frontend on http://localhost:8480
```
The API container runs `alembic upgrade head` then (demo only) `python -m app.seed.run --if-empty`.

## 4. Migrations
- Versioned in `backend/migrations/versions`. `0001` schema, `0002` security layer (role, grants, RLS, audit trigger).
- Every migration documents its rollback (`alembic downgrade -1`). Reversibility is checked with
  `scripts/test-migrations.sh` (upgrade head, downgrade base, upgrade head on a scratch database).
- Take a backup before running migrations in any shared environment.

## 5. Backup and recovery
```
scripts/backup.sh backups/                    # pg_dump custom format + sha256
scripts/restore-check.sh backups/<file>.dump  # restores into a scratch DB and compares counts; live DB untouched
```
RPO/RTO targets are not yet agreed (OD-22); the rehearsal proves the mechanism, not a target.

## 6. Demo data
- Reset: Administration > Demo controls (platform admin, `demo:reset`, typed confirmation), or
  `docker compose exec backend python -m app.seed.run --reset`. Audit events are never deleted.
- Demo data is labelled `data_origin=DEMO`, tenant environment `DEMO`, and a banner is shown on every page.
- Never run demo seeding against a production database; the seeder refuses when `DAPRO_ENV=production`.

## 7. Operations
- Health: `GET /api/v1/health`. Metrics (Prometheus format): `GET /metrics` (restrict to the internal network).
- Logs: structured JSON with correlation ID (`docker compose logs backend celery-worker`).
- Background jobs: Celery beat schedule in `backend/app/workers/celery_app.py`.

## 8. Production hardening checklist (not done in the reference deployment)
TLS termination; secure cookies (`DAPRO_COOKIE_SECURE=true`); managed PostgreSQL with encryption at rest and PITR;
secrets manager; MFA enforcement for privileged roles (OD-20); WAF and rate limiting at the edge; restricted
`/metrics`; vulnerability scanning in CI; penetration test before go-live (NFR-SEC-08).
