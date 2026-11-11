"""Append-only, SHA-256 hash-chained audit trail (FR-AUD-01..03, LLD section 7).

Every write takes pg_advisory_xact_lock(hashtext(tenant_id)) so the chain is serialised per tenant.
Payloads must never contain secrets or full identifiers (NFR-LOG-02).
"""
import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.ids import uuid7

GENESIS = "0" * 64


def canonical(event: dict) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), default=str, ensure_ascii=True)


def compute_hash(prev_hash: str, event: dict) -> str:
    return hashlib.sha256((prev_hash + canonical(event)).encode()).hexdigest()


def chain_fields(row) -> dict:
    return {
        "id": str(row.id), "tenant_id": str(row.tenant_id), "occurred_at": row.occurred_at.isoformat(),
        "actor_id": str(row.actor_id) if row.actor_id else None, "actor_role": row.actor_role,
        "org_id": str(row.org_id) if row.org_id else None, "action": row.action,
        "target_type": row.target_type, "target_id": row.target_id, "outcome": row.outcome,
        "purpose": row.purpose, "correlation_id": row.correlation_id, "payload": row.payload,
    }


def write(db: Session, *, tenant_id, action: str, outcome: str = "SUCCESS", actor_id=None,
          actor_label: str | None = None, actor_role: str | None = None, org_id=None,
          target_type: str | None = None, target_id=None, target_label: str | None = None,
          purpose: str | None = None, correlation_id: str | None = None, ip: str | None = None,
          payload: dict | None = None, occurred_at: datetime | None = None):
    from app.models.platform import AuditEvent

    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:t))"), {"t": str(tenant_id)})
    prev = db.execute(
        select(AuditEvent.hash).where(AuditEvent.tenant_id == tenant_id).order_by(AuditEvent.seq.desc()).limit(1)
    ).scalar()
    row = AuditEvent(
        id=uuid7(), tenant_id=tenant_id if isinstance(tenant_id, UUID) else UUID(str(tenant_id)),
        occurred_at=(occurred_at or datetime.now(UTC)).replace(microsecond=0), actor_id=actor_id,
        actor_label=actor_label, actor_role=actor_role, org_id=org_id, action=action,
        target_type=target_type, target_id=str(target_id) if target_id else None, target_label=target_label,
        outcome=outcome, purpose=purpose, correlation_id=correlation_id or str(uuid7()), ip=ip,
        payload=json.loads(canonical(payload or {})), prev_hash=prev or GENESIS,
    )
    row.hash = compute_hash(row.prev_hash, chain_fields(row))
    db.add(row)
    db.flush()
    return row


def verify_chain(db: Session, tenant_id) -> dict:
    """Recompute the tenant chain; return the first break if any."""
    from app.models.platform import AuditEvent

    prev = GENESIS
    count = 0
    last_seq = 0
    for row in db.execute(select(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
                          .order_by(AuditEvent.seq)).scalars().yield_per(1000):
        count += 1
        if row.prev_hash != prev or compute_hash(prev, chain_fields(row)) != row.hash:
            return {"ok": False, "events_checked": count, "broken_at_seq": row.seq, "last_seq": row.seq,
                    "last_hash": prev, "error": f"Hash mismatch at sequence {row.seq}"}
        prev = row.hash
        last_seq = row.seq
    return {"ok": True, "events_checked": count, "last_seq": last_seq, "last_hash": prev if count else None,
            "error": None}
