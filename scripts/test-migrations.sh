#!/usr/bin/env bash
# Migration reversibility check on a scratch database: upgrade head -> downgrade base -> upgrade head.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { set -a; . ./.env; set +a; }
docker compose exec -T postgres psql -U dapro_owner -d postgres -c "DROP DATABASE IF EXISTS dapro_migcheck WITH (FORCE)" -c "CREATE DATABASE dapro_migcheck"
docker compose run --rm --no-deps \
  -e DAPRO_DATABASE_OWNER_URL="postgresql+psycopg://dapro_owner:${DAPRO_DB_OWNER_PASSWORD}@postgres:5432/dapro_migcheck" \
  backend sh -c "alembic upgrade head && alembic downgrade base && alembic upgrade head && alembic current"
docker compose exec -T postgres psql -U dapro_owner -d postgres -c "DROP DATABASE dapro_migcheck WITH (FORCE)"
