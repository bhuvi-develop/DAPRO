"""Core-records Celery tasks: student CSV validation and DEMO reset."""
from sqlalchemy import select

from app.workers.celery_app import celery, tenant_session


@celery.task(name="dapro.imports.process_student_csv")
def process_student_csv(batch_id: str, tenant_id: str) -> str:
    from app.models.loans import ImportBatch
    from app.modules.students.imports import validate_batch

    db = tenant_session(tenant_id)
    try:
        b = db.get(ImportBatch, batch_id)
        if b is None:
            return "missing"
        try:
            validate_batch(db, b)
        except Exception as exc:  # file unreadable: fail visibly
            b.status = "FAILED"
            b.errors = [{"row": None, "field": None, "message": f"Could not read file: {type(exc).__name__}"}]
        db.commit()
        return b.status
    finally:
        db.close()


@celery.task(name="dapro.demo.reset")
def demo_reset(requested_by: str | None = None, requested_label: str | None = None) -> str:
    """Wipe and rebuild the DEMO tenant. Audit events are never deleted (append-only)."""
    from app.core import audit
    from app.core.config import get_settings
    from app.core.db import OwnerSessionLocal
    from app.models.iam import Tenant
    from app.seed.run import seed_all, wipe_tenant

    if get_settings().env not in ("demo", "development", "test"):
        return "refused"
    db = OwnerSessionLocal()
    try:
        demo = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalar()
        if demo is None:
            return "no-demo-tenant"
        wipe_tenant(db, demo.id)
        db.flush()
        seed_all(db, demo)
        audit.write(db, tenant_id=demo.id, action="demo.reset", actor_label=requested_label or "system",
                    actor_role="PLATFORM_ADMIN", target_type="tenant", target_id=demo.id,
                    payload={"requested_by": requested_by})
        db.commit()
        return "ok"
    finally:
        db.close()
