"""Borrower self-service (FR-BRW-01, FR-ADR-02, FR-EMP-03, FR-GRV-01). Own records only."""
from datetime import UTC, date, datetime

from sqlalchemy import select

from app.core.errors import Forbidden, ValidationFailed
from app.models.engagement import Communication
from app.models.iam import Organization
from app.models.loans import LoanAccount, RepaymentTransaction
from app.models.students import (
    AcademicRecord,
    ContactPreference,
    EmploymentRecord,
    Student,
    StudentAddress,
    StudentFieldChange,
)
from app.modules.students.completion import recompute

EMP_STATES = ("STUDYING", "GRADUATED", "FURTHER_STUDY", "EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "UNKNOWN")


def me(ctx) -> Student:
    if not ctx.is_borrower or not ctx.student_id:
        raise Forbidden("The borrower portal is only for borrower accounts.")
    return ctx.db.get(Student, ctx.student_id)


def _m(v):
    return None if v is None else f"{v:.2f}"


def overview(ctx) -> dict:
    s = me(ctx)
    loans = []
    for lo in ctx.db.execute(select(LoanAccount).where(LoanAccount.student_id == s.id,
                                                       LoanAccount.link_status == "LINKED")).scalars():
        bank = ctx.db.get(Organization, lo.bank_org_id)
        txns = ctx.db.execute(select(RepaymentTransaction).where(RepaymentTransaction.loan_id == lo.id)
                              .order_by(RepaymentTransaction.posted_on.desc()).limit(6)).scalars().all()
        loans.append({
            "id": str(lo.id), "bank_name": bank.name, "bank_loan_ref": lo.bank_loan_ref, "product": lo.product_name,
            "bank_status": lo.bank_status, "repayment_status": lo.repayment_status, "dpd": lo.dpd,
            "sanctioned_amount": _m(lo.sanctioned_amount), "disbursed_amount": _m(lo.disbursed_amount),
            "principal_outstanding": _m(lo.principal_outstanding), "overdue_amount": _m(lo.overdue_amount),
            "emi_amount": _m(lo.emi_amount), "next_due_date": lo.next_due_date, "next_due_amount": _m(lo.next_due_amount),
            "moratorium_end": lo.moratorium_end, "repayment_start": lo.repayment_start, "tenure_months": lo.tenure_months,
            "currency": lo.currency,
            "freshness": {"source": lo.source_system, "as_of": lo.last_synced_at, "sync_state": lo.sync_state},
            "recent_transactions": [{"bank_txn_ref": t.bank_txn_ref, "posted_on": t.posted_on, "amount": _m(t.amount),
                                     "kind": t.kind, "channel": t.channel} for t in txns],
            "note": ("Amounts are a read-only copy of bank records. If anything looks wrong, raise a correction "
                     "request; the bank remains the source of truth."),
        })
    return {"student": {"id": str(s.id), "name": s.full_name, "dapro_ref": s.dapro_ref,
                        "lifecycle_status": s.lifecycle_status}, "loans": loans}


def _addr(a):
    return {"id": str(a.id), "kind": a.kind, "line1": a.line1, "line2": a.line2, "city": a.city, "state": a.state,
            "postal_code": a.postal_code, "country": a.country, "verification": a.verification,
            "source": a.source_type, "effective_from": a.effective_from, "is_current": a.is_current,
            "created_at": a.created_at}


def profile(ctx) -> dict:
    s = me(ctx)
    db = ctx.db
    addrs = db.execute(select(StudentAddress).where(StudentAddress.student_id == s.id, StudentAddress.is_current.is_(True))
                       .order_by(StudentAddress.kind)).scalars()
    ac = db.execute(select(AcademicRecord).where(AcademicRecord.student_id == s.id,
                                                 AcademicRecord.is_current.is_(True))).scalar()
    emp = db.execute(select(EmploymentRecord).where(EmploymentRecord.student_id == s.id,
                                                    EmploymentRecord.is_current.is_(True))).scalar()
    prefs = db.execute(select(ContactPreference).where(ContactPreference.student_id == s.id)).scalars()
    return {"id": str(s.id), "dapro_ref": s.dapro_ref, "first_name": s.first_name, "last_name": s.last_name,
            "dob": s.dob, "email": s.primary_email, "mobile": s.primary_mobile, "lifecycle_status": s.lifecycle_status,
            "college": db.get(Organization, s.college_org_id).name,
            "addresses": [_addr(a) for a in addrs],
            "academic": {"programme": ac.programme, "course": ac.course, "cohort_year": ac.cohort_year,
                         "enrolment_status": ac.enrolment_status, "expected_completion": ac.expected_completion,
                         "actual_completion": ac.actual_completion} if ac else None,
            "employment": {"status": emp.status, "employer_name": emp.employer_name, "job_title": emp.job_title,
                           "city": emp.city, "country": emp.country, "verification": emp.verification,
                           "source": emp.source, "reported_on": emp.reported_on} if emp else None,
            "preferences": [{"channel": p.channel, "allowed": p.allowed} for p in prefs],
            "correctable_fields": ["primary_email", "primary_mobile", "first_name", "last_name", "dob"]}


def submit_address(ctx, kind, line1, line2, city, state, postal_code, country, effective_from=None) -> dict:
    s = me(ctx)
    if kind not in ("CURRENT", "CORRESPONDENCE"):
        raise ValidationFailed("You can update your current or correspondence address.",
                               [{"field": "kind", "message": "CURRENT or CORRESPONDENCE"}])
    now = datetime.now(UTC)
    a = StudentAddress(tenant_id=s.tenant_id, student_id=s.id, kind=kind, line1=line1, line2=line2, city=city,
                       state=state, postal_code=postal_code, country=(country or "IN").upper()[:2],
                       source_type="BORROWER_REPORTED", verification="UNVERIFIED",
                       effective_from=effective_from or date.today(), is_current=True, created_by=ctx.user_id)
    ctx.db.add(a)
    ctx.db.flush()
    for old in ctx.db.execute(select(StudentAddress).where(StudentAddress.student_id == s.id,
                                                           StudentAddress.kind == kind, StudentAddress.id != a.id,
                                                           StudentAddress.is_current.is_(True))).scalars():
        old.is_current, old.superseded_at, old.superseded_by_id = False, now, a.id
    ctx.audit("address.submitted", target_type="student", target_id=s.id, target_label=s.dapro_ref,
              payload={"kind": kind, "source": "BORROWER_REPORTED", "country": a.country})
    recompute(ctx.db, s)
    ctx.commit()
    return _addr(a)


def submit_employment(ctx, status, employer_name=None, job_title=None, city=None, country=None,
                      effective_from=None) -> dict:
    s = me(ctx)
    if status not in EMP_STATES:
        raise ValidationFailed("Choose a status.", [{"field": "status", "message": "Invalid"}])
    now = datetime.now(UTC)
    for old in ctx.db.execute(select(EmploymentRecord).where(EmploymentRecord.student_id == s.id,
                                                             EmploymentRecord.is_current.is_(True))).scalars():
        old.is_current, old.superseded_at = False, now
    e = EmploymentRecord(tenant_id=s.tenant_id, student_id=s.id, status=status, employer_name=employer_name,
                         job_title=job_title, city=city, country=(country or "IN").upper()[:2],
                         source="BORROWER_REPORTED", verification="UNVERIFIED", reported_on=date.today(),
                         effective_from=effective_from or date.today(), recorded_by=ctx.user_id)
    ctx.db.add(e)
    if s.lifecycle_status != status:
        ctx.db.add(StudentFieldChange(tenant_id=s.tenant_id, student_id=s.id, field="lifecycle_status",
                                      old_value=s.lifecycle_status, new_value=status,
                                      reason="Borrower-reported post-study update", source="BORROWER_REPORTED",
                                      actor_id=ctx.user_id))
        s.lifecycle_status = status
    ctx.audit("employment.submitted", target_type="student", target_id=s.id, target_label=s.dapro_ref,
              payload={"status": status, "source": "BORROWER_REPORTED"})
    ctx.db.flush()
    recompute(ctx.db, s)
    ctx.commit()
    return {"id": str(e.id), "status": e.status, "verification": e.verification, "source": e.source,
            "note": "Self-reported and voluntary. It is never used on its own to assess repayment (FR-EMP-07)."}


def communications(ctx) -> list[dict]:
    s = me(ctx)
    rows = ctx.db.execute(select(Communication).where(Communication.student_id == s.id,
                                                      Communication.recipient_type == "BORROWER",
                                                      Communication.status.in_(["SENT", "DELIVERED", "QUEUED"]))
                          .order_by(Communication.created_at.desc())).scalars()
    return [{"id": str(c.id), "channel": c.channel, "purpose": c.purpose, "subject": c.rendered_subject,
             "body": c.rendered_body, "status": c.status, "created_at": c.created_at,
             "provider_mode": c.provider_mode} for c in rows]
