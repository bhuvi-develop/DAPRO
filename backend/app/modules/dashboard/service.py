"""Enterprise cockpit aggregation (one role-scoped endpoint). All values come from PostgreSQL records."""
import time
from datetime import UTC, date, datetime, timedelta
from datetime import time as dtime

from sqlalchemy import and_, func, or_, select, true

from app.common.clock import business_today
from app.core.config import get_settings
from app.models.iam import Organization
from app.models.loans import ImportBatch, Integration, LoanAccount
from app.models.platform import AuditCheckpoint, AuditEvent, ExportJob
from app.modules.audit.service import scope_clause as audit_scope
from app.modules.dashboard.charts import charts
from app.modules.dashboard.kpis import kpis
from app.modules.dashboard.panels import case_ops, repayment_lists, student_intel
from app.modules.dashboard.scope import DashScope
from app.modules.loans.service import iso

SENTENCES = {
    "student.registered": "{a} registered student {t}", "student.created": "{a} registered student {t}",
    "loan.linked": "{a} linked bank loan {t}", "loan.link_pending_review": "{a} sent loan link {t} for identity review",
    "bank.sync": "Bank feed synchronization {o}", "address.updated": "{a} updated an address for {t}",
    "address.submitted": "{a} submitted an address update for {t}", "address.verified": "{a} recorded address verification for {t}",
    "risk.indicator_generated": "Risk indicator generated for {t}", "risk.indicators_generated": "Risk rules evaluated",
    "risk.review_recorded": "{a} completed a risk review", "risk.decision": "{a} completed a risk review",
    "case.created": "{a} opened case {t}", "case.assigned": "{a} assigned case {t}",
    "case.follow_up_recorded": "{a} recorded a follow-up on {t}", "case.transition": "{a} changed status of {t}",
    "visit.recorded": "{a} recorded a field visit on {t}", "visit.reviewed": "{a} reviewed a field visit on {t}",
    "grievance.submitted": "Grievance {t} submitted", "grievance.created": "Grievance {t} submitted",
    "grievance.resolved": "{a} resolved grievance {t}", "reconciliation.resolved": "{a} resolved a reconciliation item",
    "export.created": "{a} exported report data", "audit.chain_verified": "Audit chain verification {o}",
}
HIDDEN = ("auth.", "access.denied", "audit.case_reconstructed", "export.downloaded")


def sentence(e: AuditEvent) -> str:
    tpl = SENTENCES.get(e.action)
    a, t = e.actor_label or "System", e.target_label or (e.target_type or "record")
    o = "succeeded" if e.outcome == "SUCCESS" else "failed"
    if tpl:
        s = tpl.format(a=a, t=t, o=o)
        if e.action == "bank.sync" and e.outcome == "SUCCESS":
            s += f" ({e.payload.get('transactions_new', 0)} new transactions)"
        return s
    return f"{a}: {e.action.replace('.', ' ').replace('_', ' ')} {t}".strip()


def health(db, sc) -> dict:
    ctx = sc.ctx
    org_ok = or_(Integration.org_id.is_(None), Integration.org_id == ctx.org_id) if not sc.platform else true()
    ints = db.execute(select(Integration, Organization.name).outerjoin(Organization, Organization.id == Integration.org_id)
                      .where(org_ok).order_by(Integration.kind, Integration.name)).all()
    org_b = (ImportBatch.org_id == ctx.org_id) if not sc.platform else true()
    since = datetime.now(UTC) - timedelta(days=30)
    failed = db.execute(select(func.count()).select_from(ImportBatch).where(org_b, ImportBatch.status == "FAILED",
                                                                            ImportBatch.created_at >= since)).scalar()
    pend = db.execute(select(func.count()).select_from(ImportBatch).where(org_b, ImportBatch.status.in_(["QUEUED", "RUNNING"]))).scalar()
    pend += db.execute(select(func.count()).select_from(ExportJob).where(ExportJob.status.in_(["QUEUED", "RUNNING"]))).scalar()
    now = datetime.now(UTC)
    age = LoanAccount.last_synced_at
    linked = and_(sc.loans, LoanAccount.link_status == "LINKED")
    f = db.execute(select(func.count().filter(age >= now - timedelta(hours=24)),
                          func.count().filter(and_(age < now - timedelta(hours=24), age >= now - timedelta(hours=48))),
                          func.count().filter(age < now - timedelta(hours=48)), func.count().filter(age.is_(None)))
                   .where(linked)).one()
    cp = db.execute(select(AuditCheckpoint).order_by(AuditCheckpoint.verified_at.desc()).limit(1)).scalar()
    def status(i):
        if i.mode in ("NOT_CONFIGURED", "DISABLED"):
            return i.mode
        return "FAILED" if i.health == "FAILED" else i.mode
    return {
        "integrations": [{"id": str(i.id), "kind": i.kind, "name": i.name, "org_name": n, "provider": i.provider,
                          "mode": i.mode, "health": i.health, "status": status(i), "last_success_at": iso(i.last_success_at),
                          "last_failure_at": iso(i.last_failure_at), "last_error": i.last_error,
                          "consecutive_failures": i.consecutive_failures} for i, n in ints],
        "failed_imports": failed, "pending_jobs": pend,
        "data_freshness": [{"bucket": "UNDER_24H", "label": "Synced < 24h", "count": f[0]},
                           {"bucket": "24_48H", "label": "24-48h", "count": f[1]},
                           {"bucket": "STALE_48H_PLUS", "label": "Older than 48h", "count": f[2]},
                           {"bucket": "NEVER", "label": "Never synchronized", "count": f[3]}],
        "audit_verification": None if cp is None else {"verified_at": iso(cp.verified_at), "ok": cp.ok,
                                                       "events_checked": cp.events_checked, "error": cp.error},
    }


def activity(db, ctx, limit=25) -> list[dict]:
    stmt = select(AuditEvent).where(audit_scope(ctx), *[~AuditEvent.action.startswith(h) for h in HIDDEN])
    rows = db.execute(stmt.order_by(AuditEvent.occurred_at.desc(), AuditEvent.seq.desc()).limit(limit)).scalars()
    return [{"id": str(e.id), "at": iso(e.occurred_at), "action": e.action, "sentence": sentence(e),
             "actor": e.actor_label, "outcome": e.outcome, "target_type": e.target_type, "target_id": e.target_id,
             "target_label": e.target_label} for e in rows]


def summary(ctx, date_from: date | None, date_to: date | None) -> dict:
    t0 = time.perf_counter()
    db = ctx.db
    sc = DashScope(ctx)
    today = business_today()
    end_d = date_to or today
    start_d = date_from or end_d - timedelta(days=30)
    span = end_d - start_d
    start = datetime.combine(start_d, dtime.min, tzinfo=UTC)
    end = datetime.combine(end_d, dtime.max, tzinfo=UTC)
    bank_scope = Integration.org_id == ctx.org_id if ctx.is_bank else true()
    syncs = db.execute(select(Organization.id, Organization.name, Integration.last_success_at, Integration.mode,
                              Integration.health).join(Integration, Integration.org_id == Organization.id)
                       .where(Integration.kind == "BANK_LOAN_FEED", bank_scope)).all()
    s = get_settings()
    out = {
        "header": {
            "title": "DAPRO Enterprise Cockpit", "org": {"id": str(ctx.org_id), "name": ctx.org_name, "type": ctx.org_type},
            "role": ctx.role, "period": {"from": start_d.isoformat(), "to": end_d.isoformat(),
                                         "previous_from": (start_d - span).isoformat(), "previous_to": start_d.isoformat()},
            "business_date": today.isoformat(), "generated_at": datetime.now(UTC).isoformat(),
            "last_sync": [{"bank_org_id": str(i), "bank_name": n, "last_success_at": iso(t), "mode": m, "health": h}
                          for i, n, t, m, h in syncs],
            "data_sources": sorted({f"{n}: {m}" for _, n, _, m, _ in syncs}),
            "demo": s.env in ("demo", "test", "development"), "environment": s.env,
            "financial_visible": sc.financial, "borrower_lists_visible": sc.borrower_lists,
        },
        "kpis": kpis(db, sc, start, end),
        "charts": charts(db, sc, today),
        "lists": repayment_lists(db, sc, today),
        "case_ops": case_ops(db, sc, today),
        "student_intel": student_intel(db, sc),
        "operational_health": health(db, sc),
        "activity": activity(db, ctx),
    }
    out["header"]["compute_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return out
