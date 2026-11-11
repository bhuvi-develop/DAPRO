#!/usr/bin/env bash
# Logical backup of the DAPRO database (custom format). Usage: scripts/backup.sh [output-dir]
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && { set -a; . ./.env; set +a; }
OUT="${1:-backups}"
mkdir -p "$OUT"
FILE="$OUT/dapro-$(date +%Y%m%d-%H%M%S).dump"
docker compose exec -T postgres pg_dump -U dapro_owner -d dapro -Fc > "$FILE"
sha256sum "$FILE" > "$FILE.sha256"
echo "$FILE"
