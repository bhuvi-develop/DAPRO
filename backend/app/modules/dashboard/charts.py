"""Dashboard chart series computed with aggregate SQL from stored records."""
from datetime import date

from sqlalchemy import and_, func, select
from sqlalchemy.orm import aliased

from app.common.policy import get_policy
from app.models.iam import Organization
from app.models.loans import LoanAccount, RepaymentSchedule, RepaymentTransaction, ScheduleInstalment
from app.models.ops import Case, RiskIndicator
from app.models.students import Student


def _month_start(d: date, back: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 - back, 12)
    return date(y, m + 1, 1)


def charts(db, sc, today: date) -> dict:
    linked = and_(sc.loans, LoanAccount.link_status == "LINKED")
    bank, col = aliased(Organization), aliased(Organization)
    port = db.execute(select(bank.name, col.name, func.count(), func.count().filter(LoanAccount.link_status == "LINKED"),
                             func.sum(LoanAccount.disbursed_amount))
                      .join(bank, bank.id == LoanAccount.bank_org_id).outerjoin(col, col.id == LoanAccount.college_org_id)
                      .where(sc.loans).group_by(bank.name, col.name).order_by(bank.name, col.name)).all()
    status = db.execute(select(LoanAccount.repayment_status, func.count()).where(linked)
                        .group_by(LoanAccount.repayment_status)).all()
    pol = get_policy(db, "DPD_BUCKETS")
    agg = {b: (n, a) for b, n, a in db.execute(select(LoanAccount.dpd_bucket, func.count(), func.sum(LoanAccount.overdue_amount))
                                               .where(linked, LoanAccount.repayment_status == "OVERDUE")
                                               .group_by(LoanAccount.dpd_bucket)).all()}
    ageing = [{"code": b["code"], "label": b["label"], "min": b["min"], "max": b["max"],
               "count": agg.get(b["code"], (0, None))[0], "amount": sc.money(agg.get(b["code"], (0, None))[1])}
              for b in pol["value"]["buckets"] if b["code"] != "CURRENT"]
    start = _month_start(today, 11)
    month = func.date_trunc("month", RepaymentTransaction.posted_on)
    tx = {r[0].date(): r for r in db.execute(
        select(month, func.sum(RepaymentTransaction.amount).filter(RepaymentTransaction.kind == "PAYMENT"),
               func.sum(func.abs(RepaymentTransaction.amount)).filter(RepaymentTransaction.kind == "REVERSAL"),
               func.count().filter(RepaymentTransaction.kind == "PAYMENT"))
        .join(LoanAccount, LoanAccount.id == RepaymentTransaction.loan_id)
        .where(linked, RepaymentTransaction.posted_on >= start).group_by(month)).all()}
    imonth = func.date_trunc("month", ScheduleInstalment.due_date)
    ins = {r[0].date(): r for r in db.execute(
        select(imonth, func.count(), func.count().filter(ScheduleInstalment.status == "PAID"))
        .join(RepaymentSchedule, and_(RepaymentSchedule.id == ScheduleInstalment.schedule_id, RepaymentSchedule.is_current))
        .join(LoanAccount, LoanAccount.id == ScheduleInstalment.loan_id)
        .where(linked, ScheduleInstalment.due_date >= start, ScheduleInstalment.due_date <= today).group_by(imonth)).all()}
    trend = []
    for k in range(11, -1, -1):
        m = _month_start(today, k)
        t, i = tx.get(m), ins.get(m)
        collected, reversed_ = (t[1], t[2]) if t else (None, None)
        net = (collected or 0) - (reversed_ or 0) if t else None
        trend.append({"month": m.strftime("%Y-%m"), "label": m.strftime("%b %Y"),
                      "collected": sc.money(collected) if t else (None if not sc.financial else "0.00"),
                      "reversed": sc.money(reversed_) if t else (None if not sc.financial else "0.00"),
                      "net": sc.money(net) if t else (None if not sc.financial else "0.00"),
                      "payments": t[3] if t else 0, "instalments_due": i[1] if i else 0,
                      "instalments_paid": i[2] if i else 0})
    cases = db.execute(select(Case.status, func.count()).where(sc.cases).group_by(Case.status)).all()
    risk = db.execute(select(RiskIndicator.category, RiskIndicator.severity, func.count())
                      .where(RiskIndicator.student_id.in_(select(Student.id).where(sc.students)),
                             RiskIndicator.status.in_(["OPEN", "IN_REVIEW"]))
                      .group_by(RiskIndicator.category, RiskIndicator.severity)).all()
    life = db.execute(select(Student.lifecycle_status, func.count()).where(sc.students)
                      .group_by(Student.lifecycle_status)).all()
    return {
        "portfolio_by_bank_college": [{"bank": b, "college": c or "Unlinked", "loans": n, "linked": lk,
                                       "disbursed": sc.money(d)} for b, c, n, lk, d in port],
        "repayment_status_distribution": [{"status": s, "count": n} for s, n in sorted(status, key=lambda x: -x[1])],
        "overdue_ageing": {"approval_label": pol["approval_label"], "policy_version": pol["version"],
                           "buckets": ageing},
        "monthly_repayment_trend": trend,
        "case_status_distribution": [{"status": s, "count": n} for s, n in cases],
        "risk_indicator_distribution": [{"category": c, "severity": s, "count": n} for c, s, n in risk],
        "lifecycle_distribution": [{"status": s, "count": n} for s, n in sorted(life, key=lambda x: -x[1])],
    }
