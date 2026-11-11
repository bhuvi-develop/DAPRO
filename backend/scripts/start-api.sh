#!/bin/sh
set -e
echo "[dapro] applying migrations"
alembic upgrade head
if [ "$DAPRO_ENV" = "demo" ]; then
  echo "[dapro] ensuring demo dataset (idempotent)"
  python -m app.seed.run --if-empty
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --workers 2
