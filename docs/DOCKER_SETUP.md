# DAPRO - Docker Setup

DAPRO runs as **one** Docker Compose project named `dapro-platform` (set by `name:` in `docker-compose.yml`).
All resources it creates carry that prefix, so it cannot collide with other projects on the same machine.

## Services

| Service | Image | Purpose | Host port (127.0.0.1 only) | Memory limit |
|---|---|---|---|---|
| postgres | postgres:16.4-alpine | Application database (volume `dapro-platform_pgdata`) | 55480 | 512 MB |
| redis | redis:7.4-alpine | Celery broker and short-lived cache; no persistence | - | 160 MB |
| backend | dapro-platform/backend:dev | FastAPI; runs `alembic upgrade head` and the idempotent demo seed on start | 8410 | 768 MB |
| celery-worker | dapro-platform/backend:dev | Background jobs (imports, bank sync, exports, comms dispatch) | - | 512 MB |
| celery-beat | dapro-platform/backend:dev | The single scheduler for the jobs in `app/workers/celery_app.py` | - | 256 MB |
| frontend | dapro-platform/frontend:dev | nginx serving the SPA and proxying `/api` to `backend:8000` | 8480 | 64 MB |

Health checks: postgres (`pg_isready`), redis (`PING`), backend (`/api/v1/health`), celery-worker (`celery inspect ping`),
frontend (`/healthz`); celery-beat has no endpoint (healthcheck disabled; its dispatches appear in worker logs).
Start order: postgres + redis healthy, then backend healthy, then worker, beat and frontend.

Resource names: containers `dapro-platform-<service>-1`, network `dapro-platform_default`, volumes
`dapro-platform_pgdata` (database) and `dapro-platform_storage` (uploaded evidence and exports).

## Commands

```bash
docker compose up -d --build          # build and start everything
docker compose ps                     # status and health
docker compose logs -f backend        # follow logs (any service name)
docker compose restart backend        # restart one service
docker compose stop                   # stop; data volumes are kept
docker compose start                  # start again
docker compose down                   # remove containers and network; volumes are kept
docker compose exec postgres psql -U dapro_owner -d dapro    # database shell
docker compose exec backend python -m app.seed.run --if-empty # (re)ensure demo data, idempotent
```

`scripts/stack.sh up|down|restart|logs|status|seed|test-backend|test-migrations|test-e2e` wraps these.

**Never** use `docker system prune -a`, `docker volume prune` or `docker compose down -v` on a machine that holds
data you need. `down -v` deletes `dapro-platform_pgdata`.

## Images

- `backend/Dockerfile`: `python:3.12-slim`, non-root user `dapro` (uid 10001), dev dependencies only when built
  with `INSTALL_DEV=true` (the Compose default, so tests can run in the container).
- `frontend/Dockerfile`: multi-stage, `node:22.12-alpine` build stage with a BuildKit npm cache mount and npm
  retry settings, then `nginx:1.27-alpine` serving `dist/`.
- `.dockerignore` files exclude `.env*`, caches, `node_modules`, build output and logs.

## Other DAPRO-named resources on a developer machine

Earlier prototypes used other Compose projects (`dapro-app`, `dapro-qa`, `dapro-v1`, `dapro-ent`, `dapro`) from
the old OneDrive folders, plus an unlabelled network `dapro-platform-test-net` (created 2026-11-03, no
containers). They are **not** part of this project and were not modified. The `dapro-ent_*` volumes hold the
previous dev database of this codebase. Remove any of them only after confirming ownership, for example:

```bash
docker compose -p dapro-ent down          # containers only; add -v ONLY if you are sure the data is not needed
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| `set DAPRO_..._PASSWORD in .env` on any command | `.env` missing or incomplete; see ENVIRONMENT_SETUP |
| Port already allocated | Change `DAPRO_*_HOST_PORT` in `.env` |
| Frontend build fails in `npm ci` with "Exit handler never called" or TLS timeouts | Registry/network problem; rerun `docker compose build frontend` (the npm cache mount keeps progress) |
| Backend unhealthy | `docker compose logs backend`; usually a migration or DB password mismatch |
