"""Human-readable sequential references per tenant (DAP-2026-000123, CASE-.., GRV-..)."""
from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.ids import uuid7


def next_ref(db: Session, tenant_id, name: str, prefix: str, width: int = 6) -> str:
    value = db.execute(text(
        "INSERT INTO ref_counters (id, tenant_id, name, value) VALUES (:id, :t, :n, 1) "
        "ON CONFLICT (tenant_id, name) DO UPDATE SET value = ref_counters.value + 1 RETURNING value"),
        {"id": uuid7(), "t": tenant_id, "n": name}).scalar_one()
    return f"{prefix}-{date.today().year}-{value:0{width}d}"
