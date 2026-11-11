"""Student 360 aggregate (FR-STU-06/07, NFR-USA-01). Every section is permission-gated and masked."""
from sqlalchemy import func, or_, select

from app.core import masking
from app.core.context import RequestContext
from app.core.scope import case_clause, loan_clause
from app.models.engagement import Communication, Grievance
from app.models.iam import Organization, OrgUnit
from app.models.loans import Guarantor, LoanAccount, LoanSnapshot, Witness
from app.models.ops import Case, RiskIndicator
from app.models.platform import AuditEvent
from app.models.students import (
    AcademicRecord,
    AddressVerification,
    Consent,
    DuplicateCandidate,
    EmploymentRecord,
    StudentAddress,
    StudentContact,
    StudentFieldChange,
)
from app.modules.students import repo
from app.modules.students.completion import completion_checks
from app.modules.students.service import serialize


def address_dict(ctx, a: StudentAddress) -> dict:
    return {"id": str(a.id), "kind": a.kind, "line1": a.line1, "line2": a.line2, "city": a.city,
            "district": a.district, "state": a.state, "postal_code": a.postal_code, "country": a.country,
            "source_type": a.source_type, "verification": a.verification,
            "verification_method": a.verification_method, "verified_at": a.verified_at,
            "effective_from": a.effective_from, "is_current": a.is_current, "superseded_at": a.superseded_at,
            "notes": a.notes, "created_at": a.created_at}


def employment_dict(e: EmploymentRecord) -> dict:
    return {"id": str(e.id), "status": e.status, "employer_name": e.employer_name, "job_title": e.job_title,
            "sector": e.sector, "city": e.city, "country": e.country, "source": e.source,
            "verification": e.verification, "verified_at": e.verified_at, "reported_on": e.reported_on,
            "effective_from": e.effective_from, "is_current": e.is_current, "superseded_at": e.superseded_at,
            "notes": e.notes}


def academic_dict(r: AcademicRecord, names: dict) -> dict:
    return {"id": str(r.id), "college_name": names.get(r.college_org_id), "programme": r.programme,
            "course": r.course, "specialization": r.specialization, "cohort_year": r.cohort_year,
            "enrolment_status": r.enrolment_status, "start_date": r.start_date,
            "expected_completion": r.expected_completion, "actual_completion": r.actual_completion,
            "source": r.source, "verification": r.verification, "is_current": r.is_current}


def loan_summary(ctx, lo: LoanAccount, names: dict, snap: LoanSnapshot | None) -> dict:
    return {"id": str(lo.id), "bank_loan_ref": lo.bank_loan_ref, "bank_name": names.get(lo.bank_org_id),
            "product_name": lo.product_name, "bank_status": lo.bank_status, "link_status": lo.link_status,
            "repayment_status": lo.repayment_status, "dpd": lo.dpd if masking.financial_visible(ctx) else None,
            "dpd_bucket": lo.dpd_bucket if masking.financial_visible(ctx) else None,
            "sanctioned_amount": masking.money(ctx, lo.sanctioned_amount),
            "principal_outstanding": masking.money(ctx, lo.principal_outstanding),
            "overdue_amount": masking.money(ctx, lo.overdue_amount),
            "next_due_date": lo.next_due_date, "next_due_amount": masking.money(ctx, lo.next_due_amount),
            "financial_restricted": not masking.financial_visible(ctx), "currency": lo.currency,
            "data_origin": lo.data_origin,
            "freshness": {"source": lo.source_system, "as_of": (snap.as_of.isoformat() if snap else
                                                                (lo.last_synced_at.isoformat() if lo.last_synced_at else None)),
                          "sync_state": lo.sync_state}}


def build_profile(ctx: RequestContext, student_id) -> dict:
    db = ctx.db
    s = repo.get_scoped(ctx, student_id)
    names = {o.id: o.name for o in db.execute(select(Organization)).scalars()}
    out: dict = {"student": serialize(ctx, s, names)}
    campus = db.get(OrgUnit, s.campus_unit_id) if s.campus_unit_id else None
    out["student"]["campus_name"] = campus.name if campus else None
    checks = completion_checks(db, s)
    out["completion"] = {"percent": s.profile_completion, "checks": checks}
    pending = [{"kind": "MISSING_INFO", "label": "Missing: " + c["label"]} for c in checks if not c["ok"]]
    contacts = db.execute(select(StudentContact).where(StudentContact.student_id == s.id,
                                                       StudentContact.superseded_at.is_(None))).scalars().all()
    out["contacts"] = [{"id": str(c.id), "kind": c.kind, "value": masking.contact(ctx, c.kind, c.value),
                        "is_primary": c.is_primary, "source": c.source, "verification": c.verification,
                        "effective_from": c.effective_from} for c in contacts]
    if ctx.can("address:read"):
        addrs = db.execute(select(StudentAddress).where(StudentAddress.student_id == s.id,
                                                        StudentAddress.is_current.is_(True))
                           .order_by(StudentAddress.kind)).scalars().all()
        out["addresses"] = [address_dict(ctx, a) for a in addrs]
        out["address_history_available"] = ctx.can("address:history")
        n_pending = db.execute(select(func.count()).select_from(AddressVerification).where(
            AddressVerification.student_id == s.id, AddressVerification.status == "PENDING")).scalar()
        if n_pending:
            pending.append({"kind": "ADDRESS_VERIFICATION", "label": f"{n_pending} address verification(s) pending"})
        for a in addrs:
            if a.verification in ("FAILED", "DISPUTED"):
                pending.append({"kind": "ADDRESS_" + a.verification,
                                "label": f"{a.kind.title()} address {a.verification.lower()}"})
    acad = db.execute(select(AcademicRecord).where(AcademicRecord.student_id == s.id)
                      .order_by(AcademicRecord.is_current.desc(), AcademicRecord.created_at.desc())).scalars().all()
    out["academic"] = [academic_dict(r, names) for r in acad]
    emp = db.execute(select(EmploymentRecord).where(EmploymentRecord.student_id == s.id)
                     .order_by(EmploymentRecord.is_current.desc(), EmploymentRecord.reported_on.desc())).scalars().all()
    out["employment"] = [employment_dict(e) for e in emp]
    out["consents"] = [{"id": str(c.id), "basis": c.basis, "purposes": c.purposes, "notice_version": c.notice_version,
                        "source": c.source, "valid_from": c.valid_from, "valid_to": c.valid_to,
                        "withdrawn_at": c.withdrawn_at, "active": c.withdrawn_at is None}
                       for c in db.execute(select(Consent).where(Consent.student_id == s.id)).scalars()]
    if ctx.can("student:merge") or ctx.can("student:write"):
        n_dup = db.execute(select(func.count()).select_from(DuplicateCandidate).where(
            or_(DuplicateCandidate.student_id == s.id, DuplicateCandidate.candidate_student_id == s.id),
            DuplicateCandidate.status == "OPEN")).scalar()
        if n_dup:
            pending.append({"kind": "DUPLICATE_REVIEW", "label": "Possible duplicate record awaiting review"})
    loan_ids = _loans_section(ctx, s, names, out, pending)
    _ops_sections(ctx, s, out)
    out["pending_actions"] = pending
    out["timeline"] = timeline(ctx, s, loan_ids)
    ctx.audit("student.profile_viewed", target_type="student", target_id=s.id, target_label=s.dapro_ref)
    ctx.commit()
    return out


def _loans_section(ctx, s, names, out, pending) -> list:
    db = ctx.db
    if not ctx.can("loan:read"):
        return []
    loans = db.execute(select(LoanAccount).where(LoanAccount.student_id == s.id, loan_clause(ctx))).scalars().all()
    out["loans"] = []
    for lo in loans:
        snap = db.execute(select(LoanSnapshot).where(LoanSnapshot.loan_id == lo.id)
                          .order_by(LoanSnapshot.as_of.desc()).limit(1)).scalar()
        item = loan_summary(ctx, lo, names, snap)
        if ctx.can("guarantor:read"):
            item["guarantor_count"] = db.execute(select(func.count()).select_from(Guarantor)
                                                 .where(Guarantor.loan_id == lo.id)).scalar()
        if ctx.can("witness:read"):
            item["witness_count"] = db.execute(select(func.count()).select_from(Witness)
                                               .where(Witness.loan_id == lo.id)).scalar()
        out["loans"].append(item)
        if lo.link_status == "PENDING_REVIEW":
            pending.append({"kind": "LINK_REVIEW", "label": f"Loan {lo.bank_loan_ref} link awaiting review"})
        if lo.sync_state in ("STALE", "FAILED"):
            pending.append({"kind": "STALE_DATA", "label": f"Bank data for {lo.bank_loan_ref} is {lo.sync_state.lower()}"})
    return [lo.id for lo in loans]


def _ops_sections(ctx, s, out) -> None:
    db = ctx.db
    if ctx.can("case:read"):
        cases = db.execute(select(Case).where(Case.student_id == s.id, case_clause(ctx))
                           .order_by(Case.created_at.desc())).scalars().all()
        out["cases"] = [{"id": str(c.id), "case_ref": c.case_ref, "category": c.category, "status": c.status,
                         "priority": c.priority, "due_on": c.due_on, "next_action": c.next_action,
                         "owner_id": str(c.owner_id) if c.owner_id else None} for c in cases]
    if ctx.can("risk:read"):
        inds = db.execute(select(RiskIndicator).where(RiskIndicator.student_id == s.id)
                          .order_by(RiskIndicator.generated_at.desc()).limit(20)).scalars().all()
        out["risk_indicators"] = [{"id": str(i.id), "rule_code": i.rule_code, "rule_version": i.rule_version,
                                   "title": i.title, "category": i.category, "severity": i.severity,
                                   "status": i.status, "explanation": i.explanation, "generated_at": i.generated_at}
                                  for i in inds if not ctx.is_bank or i.bank_org_id in (None, ctx.org_id)]
    if ctx.can("grievance:read"):
        out["grievances"] = [{"id": str(g.id), "ref": g.ref, "category": g.category, "subject": g.subject,
                              "status": g.status, "due_on": g.due_on, "created_at": g.created_at}
                             for g in db.execute(select(Grievance).where(Grievance.student_id == s.id)
                                                 .order_by(Grievance.created_at.desc())).scalars()]
    if ctx.can("comm:read"):
        out["communications"] = [{"id": str(c.id), "channel": c.channel, "purpose": c.purpose, "status": c.status,
                                  "template_code": c.template_code, "recipient_type": c.recipient_type,
                                  "provider_mode": c.provider_mode, "created_at": c.created_at}
                                 for c in db.execute(select(Communication).where(Communication.student_id == s.id)
                                                     .order_by(Communication.created_at.desc()).limit(10)).scalars()]


HIDDEN = ["student.profile_viewed", "address.history_viewed"]


def timeline(ctx: RequestContext, s, loan_ids: list) -> list[dict]:
    db = ctx.db
    targets = [str(s.id)] + [str(i) for i in loan_ids]
    evs = db.execute(select(AuditEvent).where(AuditEvent.target_id.in_(targets), AuditEvent.action.notin_(HIDDEN))
                     .order_by(AuditEvent.occurred_at.desc()).limit(50)).scalars().all()
    items = [{"at": e.occurred_at, "kind": e.action,
              "summary": e.action.replace(".", " ").replace("_", " ").capitalize(),
              "actor": e.actor_label, "outcome": e.outcome, "source": "AUDIT"} for e in evs]
    for c in db.execute(select(StudentFieldChange).where(StudentFieldChange.student_id == s.id)).scalars():
        items.append({"at": c.created_at, "kind": "student.field_changed", "summary": f"{c.field} changed: {c.reason}",
                      "actor": None, "outcome": "SUCCESS", "source": "CORRECTION_HISTORY"})
    items.append({"at": s.created_at, "kind": "student.created", "summary": f"Record created ({s.source})",
                  "actor": None, "outcome": "SUCCESS", "source": "RECORD"})
    return sorted(items, key=lambda x: x["at"], reverse=True)[:50]
