#!/usr/bin/env bash
# DAPRO stack helper (Compose project "dapro-platform").
# Usage: scripts/stack.sh up|down|restart|logs [service]|status|seed|test-backend|test-migrations|test-e2e
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-status}" in
  up) docker compose up -d --build ;;
  down) docker compose stop ;;                      # stops containers, keeps data volumes
  restart) docker compose restart "${2:-backend}" ;;
  logs) docker compose logs -f --tail=100 "${2:-backend}" ;;
  status) docker compose ps ;;
  seed) docker compose exec backend python -m app.seed.run --if-empty ;;
  test-backend) docker compose run --rm --no-deps -e DAPRO_TEST_DB="${DAPRO_TEST_DB:-dapro_test}" backend sh -c "pytest -q -p no:warnings" ;;
  test-migrations) scripts/test-migrations.sh ;;
  test-e2e) (cd frontend && npx playwright test) ;;
  *) echo "unknown command: $1"; exit 2 ;;
esac
