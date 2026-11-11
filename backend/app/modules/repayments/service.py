"""Repayment monitoring views (FR-REP-03/06/07/08/10). Unknown or stale data is never shown as zero or paid."""
from datetime import timedelta

from sqlalchemy import func, select

from app.common.clock import business_today
from app.common.pagination import paginate
from app.core import masking
from app.core.scope import loan_clause
from app.models.loans import LoanAccount, ReconciliationItem, RepaymentTransaction, ScheduleInstalment
from app.models.ops import Case
from app.models.students import AcademicRecord, Student
from app.modules.loans.service import iso, loan_row, order_by

CLOSED_CASE = ("RESOLVED", "CLOSED")


def _freshness_summary(ctx) -> dict:
    row = ctx.db.execute(select(func.min(LoanAccount.last_synced_at), func.max(LoanAccount.last_synced_at))
                         .where(loan_clause(ctx), LoanAccount.link_status == "LINKED")).one()
    return {"source": "MOCK_BANK_FEED", "oldest_as_of": iso(row[0]), "latest_as_of": iso(row[1])}


def _inst(ctx, r) -> dict:
    m = lambda v: masking.money(ctx, v)  # noqa: E731
    return {"loan_id": str(r[2]), "bank_loan_ref": r[1], "student_name": r[3], "student_id": str(r[4]),
            "instalment_no": r[0].instalment_no, "due_date": iso(r[0].due_date), "amount_due": m(r[0].amount_due),
            "bank_allocated": m(r[0].bank_allocated_amount), "status": r[0].status, "dpd": r[0].dpd}


def overview(ctx) -> dict:
    db = ctx.db
    today = business_today()
    linked = (loan_clause(ctx)) & (LoanAccount.link_status == "LINKED")
    by_status = dict(db.execute(select(LoanAccount.repayment_status, func.count()).where(linked)
                                .group_by(LoanAccount.repayment_status)).all())
    by_bucket = dict(db.execute(select(LoanAccount.dpd_bucket, func.count())
                                .where(linked, LoanAccount.dpd_bucket.isnot(None)).group_by(LoanAccount.dpd_bucket)).all())
    base = (select(ScheduleInstalment, LoanAccount.bank_loan_ref, LoanAccount.id, Student.full_name, Student.id)
            .join(LoanAccount, LoanAccount.id == ScheduleInstalment.loan_id)
            .join(Student, Student.id == LoanAccount.student_id).where(linked, LoanAccount.sync_state == "CURRENT"))
    upcoming = db.execute(base.where(ScheduleInstalment.due_date >= today,
                                     ScheduleInstalment.due_date <= today + timedelta(days=30),
                                     ScheduleInstalment.status != "PAID").order_by(ScheduleInstalment.due_date).limit(25)).all()
    partial = db.execute(base.where(ScheduleInstalment.status == "PARTIALLY_PAID")
                         .order_by(ScheduleInstalment.due_date.desc()).limit(25)).all()
    sel = select(LoanAccount, Student.full_name, Student.dapro_ref).join(Student, Student.id == LoanAccount.student_id)
    rec_over = db.execute(sel.where(linked, LoanAccount.repayment_status == "OVERDUE").order_by(LoanAccount.dpd).limit(25)).all()
    stale = db.execute(sel.where(linked, LoanAccount.sync_state != "CURRENT").order_by(LoanAccount.last_synced_at).limit(25)).all()
    reversals = db.execute(select(RepaymentTransaction, LoanAccount.bank_loan_ref)
                           .join(LoanAccount, LoanAccount.id == RepaymentTransaction.loan_id)
                           .where(linked, RepaymentTransaction.kind == "REVERSAL")
                           .order_by(RepaymentTransaction.posted_on.desc()).limit(25)).all()
    scope = (ReconciliationItem.bank_org_id == ctx.org_id) if ctx.is_bank else ReconciliationItem.loan_id.in_(
        select(LoanAccount.id).where(loan_clause(ctx)))
    recon = db.execute(select(func.count()).select_from(ReconciliationItem)
                       .where(ReconciliationItem.status == "OPEN", scope)).scalar()
    return {
        "as_of_date": today.isoformat(), "freshness": _freshness_summary(ctx),
        "status_counts": by_status, "bucket_counts": by_bucket,
        "unknown_note": "UNKNOWN means bank data is stale, failed or incomplete. It is not zero, paid or current.",
        "upcoming": [_inst(ctx, r) for r in upcoming], "partial_payments": [_inst(ctx, r) for r in partial],
        "recently_overdue": [loan_row(ctx, lo, n, d) for lo, n, d in rec_over],
        "stale": [loan_row(ctx, lo, n, d) for lo, n, d in stale],
        "reversals": [{"loan_id": str(t.loan_id), "bank_loan_ref": ref, "bank_txn_ref": t.bank_txn_ref,
                       "reverses": t.reverses_txn_ref, "posted_on": iso(t.posted_on),
                       "amount": masking.money(ctx, t.amount), "reason": t.payment_reference} for t, ref in reversals],
        "reconciliation_open": recon,
    }


def accounts(ctx, f: dict, page: int, size: int, sort: str | None = None) -> dict:
    cohort = (select(AcademicRecord.cohort_year).where(AcademicRecord.student_id == LoanAccount.student_id,
                                                       AcademicRecord.is_current.is_(True)).limit(1).scalar_subquery())
    stmt = (select(LoanAccount, Student.full_name, Student.dapro_ref, cohort.label("cohort"))
            .join(Student, Student.id == LoanAccount.student_id)
            .where(loan_clause(ctx), LoanAccount.link_status == "LINKED"))
    if f.get("due_from"):
        stmt = stmt.where(LoanAccount.next_due_date >= f.get("due_from"))
    if f.get("due_to"):
        stmt = stmt.where(LoanAccount.next_due_date <= f.get("due_to"))
    for key, col in (("bucket", LoanAccount.dpd_bucket), ("college_org_id", LoanAccount.college_org_id),
                     ("branch_unit_id", LoanAccount.branch_unit_id), ("repayment_status", LoanAccount.repayment_status),
                     ("sync_state", LoanAccount.sync_state), ("bank_org_id", LoanAccount.bank_org_id)):
        if f.get(key):
            stmt = stmt.where(col == f.get(key))
    if f.get("cohort"):
        stmt = stmt.where(cohort == int(f.get("cohort")))
    if f.get("owner_id"):
        stmt = stmt.where(LoanAccount.id.in_(select(Case.loan_id).where(Case.owner_id == f.get("owner_id"),
                                                                         Case.status.notin_(CLOSED_CASE))))
    if f.get("q"):
        q = "%" + f.get("q") + "%"
        stmt = stmt.where(LoanAccount.bank_loan_ref.ilike(q) | Student.full_name.ilike(q))
    stmt = stmt.order_by(*order_by(sort, (LoanAccount.dpd.desc().nullslast(), LoanAccount.next_due_date)))
    rows, total, page, size = paginate(ctx.db, stmt, page, size, scalars=False)
    items = []
    for lo, n, d, c in rows:
        r = loan_row(ctx, lo, n, d)
        r["cohort"] = c
        items.append(r)
    return {"items": items, "total": total, "page": page, "size": size, "freshness": _freshness_summary(ctx)}
