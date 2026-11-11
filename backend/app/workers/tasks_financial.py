"""Financial and audit background jobs (LLD section 7): bank sync, stale marking, audit chain, exports."""
import logging

from sqlalchemy import select

from app.workers.celery_app import celery, tenant_ids, tenant_session

log = logging.getLogger("dapro.worker")


@celery.task(name="dapro.bank.sync_bank", autoretry_for=(ConnectionError,), retry_backoff=True, max_retries=3)
def sync_bank(tenant_id, bank_org_id, actor_id=None, actor_label="Scheduler", actor_role="SYSTEM", correlation_id=None):
    from app.modules.loans.sync import run_bank_sync

    db = tenant_session(tenant_id)
    try:
        batch = run_bank_sync(db, tenant_id, bank_org_id, actor_id=actor_id, actor_label=actor_label,
                              actor_role=actor_role, correlation_id=correlation_id)
        db.commit()
        return str(batch.id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery.task(name="dapro.bank.sync_all")
def sync_all():
    from app.models.loans import Integration

    out = []
    for tid in tenant_ids():
        db = tenant_session(tid)
        try:
            banks = db.execute(select(Integration.org_id).where(Integration.kind == "BANK_LOAN_FEED",
                                                                Integration.org_id.isnot(None))).scalars().all()
        finally:
            db.close()
        for bank in banks:
            out.append(sync_bank(str(tid), str(bank)))
    return out


@celery.task(name="dapro.bank.mark_stale")
def mark_stale_all():
    from app.modules.loans.sync import mark_stale

    total = 0
    for tid in tenant_ids():
        db = tenant_session(tid)
        try:
            total += mark_stale(db)
            db.commit()
        finally:
            db.close()
    return total


@celery.task(name="dapro.audit.verify_chain")
def verify_chain_all(triggered_by="SCHEDULE"):
    from app.modules.audit.service import run_verification

    results = []
    for tid in tenant_ids():
        db = tenant_session(tid)
        try:
            results.append(run_verification(db, tid, triggered_by))
            db.commit()
        finally:
            db.close()
    return results


@celery.task(name="dapro.reports.export")
def export_report(tenant_id, job_id):
    from app.modules.reports.service import execute_export

    db = tenant_session(tenant_id)
    try:
        execute_export(db, job_id)
        db.commit()
    finally:
        db.close()
    return str(job_id)
