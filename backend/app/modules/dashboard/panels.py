"""Dashboard lists: repayment intelligence, case operations, student intelligence."""
from datetime import date, timedelta

from sqlalchemy import and_, func, select

from app.models.loans import Guarantor, LoanAccount, ReconciliationItem, ScheduleInstalment, Witness
from app.models.ops import Case, CaseEvent, FieldVisit
from app.models.students import AcademicRecord, AddressVerification, Student
from app.modules.loans.service import iso

OPEN = ~Case.status.in_(["RESOLVED", "CLOSED"])


def repayment_lists(db, sc, today: date) -> dict:
    if not sc.borrower_lists:
        return {"upcoming_repayments": [], "recently_overdue": [], "repayment_exceptions": [], "stale_records": []}
    linked = and_(sc.loans, LoanAccount.link_status == "LINKED")
    up = []
    if sc.repayments:
        up = db.execute(select(ScheduleInstalment, LoanAccount.id, LoanAccount.bank_loan_ref, Student.full_name, Student.id)
                        .join(LoanAccount, LoanAccount.id == ScheduleInstalment.loan_id)
                        .join(Student, Student.id == LoanAccount.student_id)
                        .where(linked, LoanAccount.sync_state == "CURRENT", ScheduleInstalment.due_date >= today,
                               ScheduleInstalment.due_date <= today + timedelta(days=30),
                               ScheduleInstalment.status != "PAID").order_by(ScheduleInstalment.due_date).limit(8)).all()
    sel = select(LoanAccount, Student.full_name).join(Student, Student.id == LoanAccount.student_id)
    od = db.execute(sel.where(linked, LoanAccount.repayment_status == "OVERDUE")
                    .order_by(LoanAccount.dpd.asc().nullslast()).limit(8)).all()
    st = db.execute(sel.where(sc.loans, (LoanAccount.sync_state != "CURRENT") | (LoanAccount.link_status != "LINKED"))
                    .order_by(LoanAccount.last_synced_at.asc().nullsfirst()).limit(8)).all()
    rscope = (ReconciliationItem.bank_org_id == sc.ctx.org_id) if sc.ctx.is_bank else \
        ReconciliationItem.loan_id.in_(select(LoanAccount.id).where(sc.loans))
    rec = db.execute(select(ReconciliationItem).where(rscope, ReconciliationItem.status == "OPEN")
                     .order_by(ReconciliationItem.created_at.desc()).limit(8)).scalars().all()
    loan = lambda lo, n: {"loan_id": str(lo.id), "bank_loan_ref": lo.bank_loan_ref, "student_id": str(lo.student_id) if lo.student_id else None,  # noqa: E731
                          "student_name": n, "repayment_status": lo.repayment_status,
                          "dpd": lo.dpd if sc.financial else None, "dpd_bucket": lo.dpd_bucket if sc.financial else None,
                          "overdue_amount": sc.money(lo.overdue_amount), "sync_state": lo.sync_state,
                          "link_status": lo.link_status,
                          "freshness": {"source": lo.source_system, "as_of": iso(lo.last_synced_at), "sync_state": lo.sync_state}}
    return {
        "upcoming_repayments": [{"loan_id": str(lid), "bank_loan_ref": ref, "student_name": n, "student_id": str(sid),
                                 "instalment_no": i.instalment_no, "due_date": iso(i.due_date),
                                 "amount_due": sc.money(i.amount_due), "status": i.status} for i, lid, ref, n, sid in up],
        "recently_overdue": [loan(lo, n) for lo, n in od],
        "repayment_exceptions": [{"id": str(r.id), "kind": r.kind, "severity": r.severity, "summary": r.summary,
                                  "loan_id": str(r.loan_id) if r.loan_id else None, "created_at": iso(r.created_at)}
                                 for r in rec],
        "stale_records": [loan(lo, n) for lo, n in st],
    }


def case_ops(db, sc, today: date) -> dict:
    cnt = lambda *w: db.execute(select(func.count()).select_from(Case).where(sc.cases, *w)).scalar()  # noqa: E731
    in_cases = FieldVisit.case_id.in_(select(Case.id).where(sc.cases))
    vcount = lambda *w: db.execute(select(func.count()).select_from(FieldVisit).where(in_cases, *w)).scalar()  # noqa: E731
    recent = []
    if sc.borrower_lists:
        recent = db.execute(select(CaseEvent, Case.case_ref, Case.id).join(Case, Case.id == CaseEvent.case_id)
                            .where(sc.cases).order_by(CaseEvent.created_at.desc()).limit(8)).all()
    return {
        "open": cnt(OPEN), "high_priority": cnt(OPEN, Case.priority.in_(["CRITICAL", "HIGH"])),
        "escalated": cnt(Case.status == "ESCALATED"),
        "awaiting_review": vcount(FieldVisit.review_status == "PENDING"),
        "assigned_field_visits": vcount(FieldVisit.status == "SCHEDULED"),
        "overdue_follow_ups": cnt(OPEN, Case.due_on < today),
        "recent_activity": [{"case_id": str(cid), "case_ref": ref, "event_type": e.event_type, "summary": e.summary,
                             "at": iso(e.created_at)} for e, ref, cid in recent],
    }


def student_intel(db, sc) -> dict:
    s_ids = select(Student.id).where(sc.students)
    recent = []
    if sc.borrower_lists:
        recent = db.execute(select(Student).where(sc.students).order_by(Student.created_at.desc()).limit(6)).scalars().all()
    avg, missing = db.execute(select(func.avg(Student.profile_completion),
                                     func.count().filter(Student.profile_completion < 80)).where(sc.students)).one()
    pend = db.execute(select(func.count()).select_from(AddressVerification)
                      .where(AddressVerification.student_id.in_(s_ids), AddressVerification.status == "PENDING")).scalar()
    acad = db.execute(select(AcademicRecord.enrolment_status, func.count())
                      .where(AcademicRecord.student_id.in_(s_ids), AcademicRecord.is_current,
                             AcademicRecord.enrolment_status.in_(["DISCONTINUED", "ON_LEAVE"]))
                      .group_by(AcademicRecord.enrolment_status)).all()
    linked = and_(sc.loans, LoanAccount.link_status == "LINKED")
    n_loans = db.execute(select(func.count()).select_from(LoanAccount).where(linked)).scalar()
    with_g = db.execute(select(func.count(func.distinct(Guarantor.loan_id)))
                        .where(Guarantor.loan_id.in_(select(LoanAccount.id).where(linked)))).scalar()
    with_w = db.execute(select(func.count(func.distinct(Witness.loan_id)))
                        .where(Witness.loan_id.in_(select(LoanAccount.id).where(linked)))).scalar()
    return {
        "recently_added": [{"id": str(s.id), "dapro_ref": s.dapro_ref, "full_name": s.full_name,
                            "created_at": iso(s.created_at), "profile_completion": s.profile_completion,
                            "verification_status": s.verification_status} for s in recent],
        "avg_profile_completion": round(float(avg), 1) if avg is not None else None,
        "missing_information": missing,
        "pending_address_verification": pend,
        "academic_exceptions": [{"status": s, "count": n} for s, n in acad],
        "guarantor_witness_completion": {"linked_loans": n_loans, "with_guarantor": with_g, "with_witness": with_w,
                                         "guarantor_pct": round(100 * with_g / n_loans, 1) if n_loans else None},
    }
