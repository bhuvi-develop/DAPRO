"""KPI cards with previous-period comparison where the stored history allows it."""
from datetime import datetime

from sqlalchemy import and_, exists, func, select

from app.models.loans import LoanAccount, LoanSnapshot
from app.models.ops import Case, FieldVisit, RiskIndicator, RiskReview
from app.models.students import Student

OPEN_CASE = ~Case.status.in_(["RESOLVED", "CLOSED"])
OPEN_IND = RiskIndicator.status.in_(["OPEN", "IN_REVIEW"])


def _count(db, stmt):
    return db.execute(stmt).scalar() or 0


def _snapshot_overdue_at(db, sc, at: datetime):
    """Overdue position from the latest bank snapshot per loan as of a past instant; None if no history."""
    latest = (select(LoanSnapshot.loan_id, func.max(LoanSnapshot.as_of).label("mx"))
              .join(LoanAccount, LoanAccount.id == LoanSnapshot.loan_id)
              .where(sc.loans, LoanSnapshot.as_of <= at).group_by(LoanSnapshot.loan_id).subquery())
    row = db.execute(select(func.count(), func.count().filter(LoanSnapshot.overdue_amount > 0),
                            func.sum(LoanSnapshot.overdue_amount))
                     .join(latest, and_(latest.c.loan_id == LoanSnapshot.loan_id, latest.c.mx == LoanSnapshot.as_of))).one()
    if not row[0]:
        return None, None
    return row[1], row[2]


def kpis(db, sc, start: datetime, end: datetime) -> list[dict]:
    linked = and_(sc.loans, LoanAccount.link_status == "LINKED")
    stu = _count(db, select(func.count()).select_from(Student).where(sc.students, Student.record_status == "ACTIVE"))
    stu_prev = _count(db, select(func.count()).select_from(Student).where(sc.students, Student.created_at <= start))
    lk = _count(db, select(func.count()).select_from(LoanAccount).where(linked))
    lk_prev = _count(db, select(func.count()).select_from(LoanAccount).where(linked, LoanAccount.linked_at <= start))
    active = _count(db, select(func.count()).select_from(LoanAccount).where(linked, LoanAccount.repayment_status != "CLOSED"))
    current = _count(db, select(func.count()).select_from(LoanAccount).where(linked, LoanAccount.repayment_status == "CURRENT"))
    overdue = _count(db, select(func.count()).select_from(LoanAccount).where(linked, LoanAccount.repayment_status == "OVERDUE"))
    amount = db.execute(select(func.sum(LoanAccount.overdue_amount)).where(
        linked, LoanAccount.sync_state == "CURRENT", LoanAccount.repayment_status == "OVERDUE")).scalar()
    od_prev, amt_prev = _snapshot_overdue_at(db, sc, start)
    oc = _count(db, select(func.count()).select_from(Case).where(sc.cases, OPEN_CASE))
    oc_prev = _count(db, select(func.count()).select_from(Case).where(
        sc.cases, Case.created_at <= start, (Case.closed_at.is_(None)) | (Case.closed_at > start)))
    ind_scope = RiskIndicator.student_id.in_(select(Student.id).where(sc.students))
    pr = _count(db, select(func.count()).select_from(RiskIndicator).where(ind_scope, OPEN_IND))
    pr += _count(db, select(func.count()).select_from(FieldVisit).where(
        FieldVisit.review_status == "PENDING", FieldVisit.case_id.in_(select(Case.id).where(sc.cases))))
    reviewed_before = exists().where(RiskReview.indicator_id == RiskIndicator.id, RiskReview.created_at <= start)
    pr_prev = _count(db, select(func.count()).select_from(RiskIndicator).where(
        ind_scope, RiskIndicator.generated_at <= start, ~reviewed_before))
    unknown = _count(db, select(func.count()).select_from(LoanAccount).where(linked, LoanAccount.repayment_status == "UNKNOWN"))
    out = [
        dict(key="total_students", label="Total students", value=stu, previous_value=stu_prev, unit="count",
             status="neutral", link="/students", hint="Active DAPRO student identities in your scope"),
        dict(key="linked_loans", label="Linked loan accounts", value=lk, previous_value=lk_prev, unit="count",
             status="neutral", link="/loans?link_status=LINKED", hint="Validated bank loan references"),
        dict(key="active_monitoring", label="Active monitoring", value=active, previous_value=None, unit="count",
             status="neutral", link="/repayments", hint=f"Linked loans not closed; {unknown} with UNKNOWN status"),
        dict(key="current_repayment", label="Current repayment", value=current, previous_value=None, unit="count",
             status="good", link="/repayments?repayment_status=CURRENT", hint="No bank-confirmed overdue instalment"),
        dict(key="overdue_accounts", label="Overdue accounts", value=overdue, previous_value=od_prev, unit="count",
             status="critical" if overdue else "good", link="/loans?repayment_status=OVERDUE",
             hint="Bank-confirmed overdue (current data only)"),
    ]
    if sc.financial:
        out.append(dict(key="total_overdue_amount", label="Total overdue amount", value=sc.money(amount or 0),
                        previous_value=sc.money(amt_prev) if amt_prev is not None else None, unit="INR",
                        status="critical" if amount else "good", link="/repayments?repayment_status=OVERDUE",
                        hint="Sum of latest bank snapshots; stale loans excluded"))
    out += [
        dict(key="open_cases", label="Open cases", value=oc, previous_value=oc_prev, unit="count",
             status="warning" if oc else "good", link="/cases?status=open", hint="Cases not resolved or closed"),
        dict(key="pending_reviews", label="Pending reviews", value=pr, previous_value=pr_prev, unit="count",
             status="warning" if pr else "good", link="/risk?status=OPEN",
             hint="Risk indicators awaiting review and field reports awaiting supervision"),
    ]
    return out
