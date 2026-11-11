"""Operations tasks: nightly risk evaluation and MOCK message dispatch (LLD 7 background jobs)."""
import logging

from app.core import audit
from app.workers.celery_app import celery, tenant_ids, tenant_session

log = logging.getLogger("dapro.tasks.ops")


@celery.task(name="dapro.risk.evaluate_tenant", time_limit=1800)
def evaluate_tenant(tenant_id: str) -> dict:
    from app.modules.risk.engine import evaluate_tenant as run

    db = tenant_session(tenant_id)
    try:
        stats = run(db, tenant_id)
        audit.write(db, tenant_id=tenant_id, action="risk.evaluated", actor_label="Scheduler (Celery beat)",
                    actor_role="SYSTEM", payload=stats)
        db.commit()
        return stats
    except Exception:
        db.rollback()
        log.exception("risk evaluation failed", extra={"tenant": str(tenant_id)})
        raise
    finally:
        db.close()


@celery.task(name="dapro.risk.nightly")
def nightly() -> dict:
    return {str(t): evaluate_tenant(str(t)) for t in tenant_ids()}


@celery.task(name="dapro.comms.dispatch", time_limit=120)
def dispatch() -> dict:
    from app.modules.comms.service import dispatch as run

    out = {}
    for t in tenant_ids():
        db = tenant_session(t)
        try:
            out[str(t)] = run(db)
            db.commit()
        except Exception:
            db.rollback()
            log.exception("dispatch failed")
        finally:
            db.close()
    return out
