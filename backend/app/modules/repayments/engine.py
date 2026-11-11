"""Display-level repayment status and DPD evaluation (FR-REP-03/04/06, BR-02/03/04).

Inputs are bank-confirmed only: the bank schedule and the bank-supplied allocation per instalment.
DAPRO never allocates payments itself. Stale or failed data yields UNKNOWN, never zero or paid.
Calculation inputs (grace days, buckets) come from versioned policy configuration.
"""
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.common.clock import business_today
from app.common.policy import get_policy
from app.models.loans import LoanAccount, LoanSnapshot, ReconciliationItem, RepaymentSchedule, ScheduleInstalment

ZERO = Decimal("0.00")


def bucket_for(dpd: int | None, buckets: list[dict]) -> str | None:
    if dpd is None:
        return None
    for b in buckets:
        if dpd >= b["min"] and (b["max"] is None or dpd <= b["max"]):
            return b["code"]
    return None


def classify_instalment(inst: ScheduleInstalment, today: date, grace_days: int) -> tuple[str, int | None]:
    allocated = inst.bank_allocated_amount
    if inst.bank_status == "DEFERRED":
        return "DEFERRED", None
    if inst.due_date > today:
        if allocated is not None and allocated >= inst.amount_due:
            return "PAID", 0
        return "UPCOMING", None
    if allocated is None:
        return "UNKNOWN", None  # past due but the bank supplied no allocation: do not assume
    if allocated >= inst.amount_due:
        return "PAID", 0
    overdue_days = (today - inst.due_date).days - grace_days
    if overdue_days <= 0:
        return "IN_GRACE", 0
    if allocated > ZERO:
        return "PARTIALLY_PAID", overdue_days
    return "OVERDUE", overdue_days


def evaluate_loan(db: Session, loan: LoanAccount, today: date | None = None, raise_recon: bool = True) -> None:
    rules = get_policy(db, "REPAYMENT_RULES")["value"]
    today = today or business_today(rules.get("business_timezone"))
    now = datetime.now(UTC)
    buckets = get_policy(db, "DPD_BUCKETS")["value"]["buckets"]
    grace = int(rules.get("grace_days", 0))

    snap = db.execute(select(LoanSnapshot).where(LoanSnapshot.loan_id == loan.id)
                      .order_by(LoanSnapshot.as_of.desc()).limit(1)).scalar()
    loan.overdue_amount = snap.overdue_amount if snap else None
    loan.principal_outstanding = snap.principal_outstanding if snap else None
    loan.status_evaluated_at = now

    if loan.link_status != "LINKED":
        loan.repayment_status, loan.dpd, loan.dpd_bucket = "UNKNOWN", None, None
        return
    if loan.sync_state != "CURRENT":
        # BR-03 / FR-REP-06: no delinquency finding from stale, failed or missing data.
        loan.repayment_status, loan.dpd, loan.dpd_bucket = "UNKNOWN", None, None
        return
    if loan.bank_status == "CLOSED":
        loan.repayment_status, loan.dpd, loan.dpd_bucket = "CLOSED", 0, None
        loan.next_due_date = loan.next_due_amount = None
        return

    schedule = db.execute(select(RepaymentSchedule).where(RepaymentSchedule.loan_id == loan.id,
                                                          RepaymentSchedule.is_current.is_(True))).scalar()
    if schedule is None:
        in_moratorium = loan.bank_status in ("MORATORIUM", "SANCTIONED", "DISBURSED") or (
            loan.repayment_start and loan.repayment_start > today)
        loan.repayment_status = "NOT_STARTED" if in_moratorium else "UNKNOWN"
        loan.dpd, loan.dpd_bucket = (0, "CURRENT") if in_moratorium else (None, None)
        loan.next_due_date = loan.repayment_start
        loan.next_due_amount = loan.emi_amount
        return

    insts = db.execute(select(ScheduleInstalment).where(ScheduleInstalment.schedule_id == schedule.id)
                       .order_by(ScheduleInstalment.instalment_no)).scalars().all()
    max_dpd, unknown, any_due = 0, False, False
    next_due = None
    for inst in insts:
        status, dpd = classify_instalment(inst, today, grace)
        inst.status, inst.dpd, inst.evaluated_at = status, dpd, now
        if inst.due_date <= today:
            any_due = True
        if status == "UNKNOWN":
            unknown = True
        if dpd:
            max_dpd = max(max_dpd, dpd)
        if next_due is None and inst.due_date >= today and status != "PAID":
            next_due = inst
    loan.next_due_date = next_due.due_date if next_due else None
    loan.next_due_amount = next_due.amount_due if next_due else None

    if unknown:
        loan.repayment_status, loan.dpd, loan.dpd_bucket = "UNKNOWN", None, None
    elif max_dpd > 0:
        loan.repayment_status, loan.dpd = "OVERDUE", max_dpd
        loan.dpd_bucket = bucket_for(max_dpd, buckets)
    else:
        loan.repayment_status = "CURRENT" if any_due else "NOT_STARTED"
        loan.dpd, loan.dpd_bucket = 0, "CURRENT"

    # AC-06 / BR-02: reconcile against bank-supplied DPD when available.
    if raise_recon and snap and snap.bank_dpd is not None and loan.dpd is not None and snap.bank_dpd != loan.dpd:
        key = f"DPD_MISMATCH:{loan.id}:{snap.id}"
        exists = db.execute(select(ReconciliationItem.id).where(ReconciliationItem.dedupe_key == key)).scalar()
        if not exists:
            db.add(ReconciliationItem(
                tenant_id=loan.tenant_id, bank_org_id=loan.bank_org_id, loan_id=loan.id, student_id=loan.student_id,
                kind="DPD_MISMATCH", severity="MEDIUM", dedupe_key=key,
                summary=f"Bank DPD {snap.bank_dpd} differs from DAPRO display DPD {loan.dpd}",
                details={"bank_dpd": snap.bank_dpd, "dapro_dpd": loan.dpd, "snapshot_as_of": snap.as_of.isoformat(),
                         "grace_days": grace, "note": "Bank allocation and grace rules govern. Confirm with bank."}))
