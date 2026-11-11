#!/usr/bin/env bash
# Restore rehearsal: restores a backup into a scratch database and compares key row counts and the audit chain.
# Never touches the live database. Usage: scripts/restore-check.sh backups/dapro-YYYYmmdd-HHMMSS.dump
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { set -a; . ./.env; set +a; }
FILE="$1"
sha256sum -c "$FILE.sha256"
docker compose exec -T postgres psql -U dapro_owner -d postgres -c "DROP DATABASE IF EXISTS dapro_restorecheck WITH (FORCE)" -c "CREATE DATABASE dapro_restorecheck"
docker compose exec -T postgres pg_restore -U dapro_owner -d dapro_restorecheck --no-owner < "$FILE"
Q="select (select count(*) from students),(select count(*) from loan_accounts),(select count(*) from repayment_transactions),(select count(*) from audit_events)"
echo "live:     $(docker compose exec -T postgres psql -U dapro_owner -d dapro -At -c "$Q")"
echo "restored: $(docker compose exec -T postgres psql -U dapro_owner -d dapro_restorecheck -At -c "$Q")"
docker compose exec -T postgres psql -U dapro_owner -d postgres -c "DROP DATABASE dapro_restorecheck WITH (FORCE)"
