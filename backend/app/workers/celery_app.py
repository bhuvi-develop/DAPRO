"""Celery application and beat schedule (LLD section 7 background jobs).

Task modules (each owned by one module group):
  app.workers.tasks_core       imports.process_student_csv, demo.reset
  app.workers.tasks_financial  bank.sync_all, bank.sync_bank, bank.mark_stale, audit.verify_chain, reports.export
  app.workers.tasks_ops        risk.nightly, risk.evaluate_tenant, comms.dispatch
Every task binds the tenant (RLS) before touching business tables.
"""
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

s = get_settings()
celery = Celery("dapro", broker=s.redis_url, backend=s.redis_url,
                include=["app.workers.tasks_core", "app.workers.tasks_financial", "app.workers.tasks_ops"])
celery.conf.update(
    task_always_eager=s.celery_eager, task_eager_propagates=True, timezone="Asia/Kolkata", enable_utc=True,
    task_acks_late=True, worker_prefetch_multiplier=1, task_default_queue="default",
    task_routes={"dapro.bank.*": {"queue": "default"}, "dapro.reports.*": {"queue": "default"}},
    beat_schedule={
        "bank-sync-daily": {"task": "dapro.bank.sync_all", "schedule": crontab(hour=2, minute=0)},
        "bank-mark-stale-hourly": {"task": "dapro.bank.mark_stale", "schedule": crontab(minute=15)},
        "risk-nightly": {"task": "dapro.risk.nightly", "schedule": crontab(hour=1, minute=0)},
        "audit-verify-nightly": {"task": "dapro.audit.verify_chain", "schedule": crontab(hour=2, minute=30)},
        "comms-dispatch": {"task": "dapro.comms.dispatch", "schedule": 60.0},
    },
)
app = celery


def tenant_ids() -> list:
    from sqlalchemy import select

    from app.core.db import SessionLocal
    from app.models.iam import Tenant

    db = SessionLocal()
    try:
        return list(db.execute(select(Tenant.id).where(Tenant.status == "ACTIVE")).scalars())
    finally:
        db.close()


def tenant_session(tenant_id):
    from app.core.db import SessionLocal, bind_tenant

    db = SessionLocal()
    bind_tenant(db, tenant_id)
    return db
