"""Audit search, chain verification and case reconstruction (FR-AUD-01..04, RD 11.3, UC-37, US-08)."""
from datetime import UTC, datetime

from sqlalchemy import String, cast, or_, select

from app.common.notify import notify
from app.common.pagination import paginate
from app.core import audit as audit_core
from app.core.scope import case_clause, loan_clause, student_clause
from app.models.iam import Role, User, UserRole
from app.models.loans import LoanAccount
from app.models.ops import Case
from app.models.platform import AuditCheckpoint, AuditEvent
from app.models.students import Student


def iso(v):
    return v.isoformat() if v else None


def event_row(e: AuditEvent) -> dict:
    return {"seq": e.seq, "id": str(e.id), "occurred_at": iso(e.occurred_at), "actor_id": str(e.actor_id) if e.actor_id else None,
            "actor_label": e.actor_label, "actor_role": e.actor_role, "org_id": str(e.org_id) if e.org_id else None,
            "action": e.action, "target_type": e.target_type, "target_id": e.target_id, "target_label": e.target_label,
            "outcome": e.outcome, "purpose": e.purpose, "correlation_id": e.correlation_id, "payload": e.payload,
            "hash": e.hash, "prev_hash": e.prev_hash}


def scope_clause(ctx):
    if ctx.org_type == "PLATFORM":
        return AuditEvent.org_id == ctx.org_id
    return or_(AuditEvent.org_id == ctx.org_id,
               AuditEvent.target_id.in_(select(cast(Student.id, String)).where(student_clause(ctx))),
               AuditEvent.target_id.in_(select(cast(LoanAccount.id, String)).where(loan_clause(ctx))),
               AuditEvent.target_id.in_(select(cast(Case.id, String)).where(case_clause(ctx))))


def search(ctx, f: dict, page: int, size: int) -> dict:
    stmt = select(AuditEvent).where(scope_clause(ctx))
    if f.get("actor_id"):
        stmt = stmt.where(AuditEvent.actor_id == f.get("actor_id"))
    if f.get("action"):
        stmt = stmt.where(AuditEvent.action.like(f.get("action") + "%"))
    for key, col in (("target_type", AuditEvent.target_type), ("target_id", AuditEvent.target_id),
                     ("outcome", AuditEvent.outcome)):
        if f.get(key):
            stmt = stmt.where(col == str(f.get(key)))
    if f.get("date_from"):
        stmt = stmt.where(AuditEvent.occurred_at >= f.get("date_from"))
    if f.get("date_to"):
        stmt = stmt.where(AuditEvent.occurred_at <= f.get("date_to"))
    if f.get("q"):
        q = "%" + f.get("q") + "%"
        stmt = stmt.where(or_(AuditEvent.actor_label.ilike(q), AuditEvent.target_label.ilike(q),
                              AuditEvent.action.ilike(q)))
    rows, total, page, size = paginate(ctx.db, stmt.order_by(AuditEvent.seq.desc()), page, size)
    return {"items": [event_row(e) for e in rows], "total": total, "page": page, "size": size}


def run_verification(db, tenant_id, triggered_by: str = "SCHEDULE") -> dict:
    res = audit_core.verify_chain(db, tenant_id)
    cp = AuditCheckpoint(tenant_id=tenant_id, last_seq=res["last_seq"], last_hash=res["last_hash"],
                         events_checked=res["events_checked"], ok=res["ok"], error=res["error"],
                         triggered_by=triggered_by)
    db.add(cp)
    if not res["ok"]:
        auditors = db.execute(select(User.id).join(UserRole, UserRole.user_id == User.id)
                              .join(Role, Role.id == UserRole.role_id)
                              .where(User.tenant_id == tenant_id, Role.code.in_(["AUDITOR", "PLATFORM_ADMIN"]))).scalars()
        for uid in auditors:
            notify(db, tenant_id, uid, "AUDIT_CHAIN_BROKEN", "Audit chain verification failed", res["error"],
                   "/audit", "CRITICAL")
    audit_core.write(db, tenant_id=tenant_id, action="audit.chain_verified", outcome="SUCCESS" if res["ok"] else "FAILURE",
                     actor_label=triggered_by, payload={k: v for k, v in res.items() if k != "last_hash"})
    db.flush()
    return {**res, "checkpoint_id": str(cp.id), "verified_at": datetime.now(UTC).isoformat()}


def checkpoints(ctx, limit: int = 20) -> list[dict]:
    rows = ctx.db.execute(select(AuditCheckpoint).order_by(AuditCheckpoint.verified_at.desc()).limit(limit)).scalars()
    return [{"id": str(c.id), "verified_at": iso(c.verified_at), "last_seq": c.last_seq, "events_checked": c.events_checked,
             "ok": c.ok, "error": c.error, "triggered_by": c.triggered_by} for c in rows]
