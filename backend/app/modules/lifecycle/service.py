"""Address, contact, academic and employment lifecycle (FR-ADR-01..08, FR-EMP-01..07, BR-05, BR-10).

History is never overwritten: a new row supersedes the previous current row. No change here sets any
risk, default or absconding flag (BR-05, FR-EMP-07).
"""
import re
from datetime import UTC, date, datetime, time

from sqlalchemy import select

from app.core.context import RequestContext
from app.core.errors import BusinessError, Forbidden, NotFound, ValidationFailed
from app.core.scope import student_clause
from app.models.students import (
    AcademicRecord,
    AddressVerification,
    Consent,
    ContactPreference,
    EmploymentRecord,
    Student,
    StudentAddress,
    StudentContact,
)
from app.modules.students.completion import recompute
from app.modules.students.profile import academic_dict, address_dict, employment_dict
from app.modules.students.repo import get_scoped

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MOBILE = re.compile(r"^\+?[0-9 ]{8,16}$")


def list_addresses(ctx: RequestContext, student_id, history: bool) -> list[dict]:
    s = get_scoped(ctx, student_id)
    stmt = select(StudentAddress).where(StudentAddress.student_id == s.id)
    if history:
        if not ctx.can("address:history"):
            raise Forbidden("Historical addresses need an approved purpose (address:history).",
                            "Ask a bank operations user or manager to review the history.")
        ctx.audit("address.history_viewed", target_type="student", target_id=s.id, target_label=s.dapro_ref)
        ctx.commit()
    else:
        stmt = stmt.where(StudentAddress.is_current.is_(True))
    rows = ctx.db.execute(stmt.order_by(StudentAddress.created_at.desc())).scalars()
    return [address_dict(ctx, a) for a in rows]


def add_address(ctx: RequestContext, student_id, body) -> dict:
    s = get_scoped(ctx, student_id)
    now = datetime.now(UTC)
    a = StudentAddress(tenant_id=ctx.tenant_id, student_id=s.id, kind=body.kind, line1=body.line1, line2=body.line2,
                       city=body.city, district=body.district, state=body.state, postal_code=body.postal_code,
                       country=body.country.upper(), source_type=body.source_type,
                       verification="PENDING" if body.request_verification else "UNVERIFIED",
                       effective_from=body.effective_from or date.today(), notes=body.notes, created_by=ctx.user_id)
    ctx.db.add(a)
    ctx.db.flush()
    prev = ctx.db.execute(select(StudentAddress).where(StudentAddress.student_id == s.id,
                                                       StudentAddress.kind == body.kind,
                                                       StudentAddress.is_current.is_(True),
                                                       StudentAddress.id != a.id)).scalars().all()
    for p in prev:
        p.is_current, p.superseded_at, p.superseded_by_id = False, now, a.id
    if body.request_verification:
        ctx.db.add(AddressVerification(tenant_id=ctx.tenant_id, address_id=a.id, student_id=s.id,
                                       method=body.verification_method or "DOCUMENT", requested_by=ctx.user_id))
    recompute(ctx.db, s)
    ctx.audit("address.added", target_type="student", target_id=s.id, target_label=s.dapro_ref,
              payload={"kind": a.kind, "source": a.source_type, "superseded": len(prev), "address_id": str(a.id)})
    ctx.commit()
    return address_dict(ctx, a)


def _address_scoped(ctx, address_id) -> StudentAddress:
    a = ctx.db.get(StudentAddress, address_id)
    if a is None:
        raise NotFound("Address")
    get_scoped(ctx, a.student_id)
    return a


def request_verification(ctx: RequestContext, address_id, body) -> dict:
    a = _address_scoped(ctx, address_id)
    if not a.is_current:
        raise BusinessError("INVALID_STATE", "Only a current address can be verified.", "Verify the current address.")
    open_req = ctx.db.execute(select(AddressVerification).where(AddressVerification.address_id == a.id,
                                                                AddressVerification.status == "PENDING")).scalar()
    if open_req:
        raise BusinessError("ALREADY_PENDING", "A verification is already pending for this address.",
                            "Record the outcome of the pending request first.")
    v = AddressVerification(tenant_id=ctx.tenant_id, address_id=a.id, student_id=a.student_id, method=body.method,
                            requested_by=ctx.user_id, assigned_to=body.assigned_to)
    ctx.db.add(v)
    a.verification = "PENDING"
    ctx.db.flush()
    ctx.audit("address.verification_requested", target_type="student", target_id=a.student_id,
              payload={"address_id": str(a.id), "method": body.method})
    ctx.commit()
    return verification_dict(ctx, v)


def verification_dict(ctx, v: AddressVerification, a: StudentAddress | None = None, s: Student | None = None) -> dict:
    d = {"id": str(v.id), "address_id": str(v.address_id), "student_id": str(v.student_id), "method": v.method,
         "status": v.status, "outcome_notes": v.outcome_notes, "created_at": v.created_at,
         "performed_at": v.performed_at, "performed_by": str(v.performed_by) if v.performed_by else None}
    if a:
        d["address"] = {"kind": a.kind, "city": a.city, "state": a.state, "country": a.country,
                        "source_type": a.source_type}
    if s:
        d["student"] = {"dapro_ref": s.dapro_ref, "full_name": s.full_name}
    return d


def verification_queue(ctx: RequestContext, status: str = "PENDING") -> list[dict]:
    rows = ctx.db.execute(select(AddressVerification, StudentAddress, Student)
                          .join(StudentAddress, StudentAddress.id == AddressVerification.address_id)
                          .join(Student, Student.id == AddressVerification.student_id)
                          .where(AddressVerification.status == status, student_clause(ctx))
                          .order_by(AddressVerification.created_at).limit(200)).all()
    return [verification_dict(ctx, v, a, s) for v, a, s in rows]


def record_outcome(ctx: RequestContext, verification_id, body) -> dict:
    v = ctx.db.get(AddressVerification, verification_id)
    if v is None:
        raise NotFound("Verification request")
    get_scoped(ctx, v.student_id)
    if v.status != "PENDING":
        raise BusinessError("INVALID_STATE", f"Verification is already {v.status}.", "Raise a new request if needed.")
    now = datetime.now(UTC)
    v.status, v.outcome_notes, v.performed_by, v.performed_at = body.status, body.notes, ctx.user_id, now
    a = ctx.db.get(StudentAddress, v.address_id)
    a.verification, a.verification_method = body.status, v.method
    a.verified_by, a.verified_at = ctx.user_id, now
    recompute(ctx.db, ctx.db.get(Student, v.student_id))
    ctx.audit("address.verification_recorded", target_type="student", target_id=v.student_id,
              payload={"address_id": str(a.id), "outcome": body.status, "method": v.method})
    ctx.commit()
    return verification_dict(ctx, v, a)


def dispute_address(ctx: RequestContext, address_id, reason: str) -> dict:
    a = _address_scoped(ctx, address_id)
    a.verification, a.notes = "DISPUTED", reason
    ctx.audit("address.disputed", target_type="student", target_id=a.student_id, payload={"address_id": str(a.id)})
    ctx.commit()
    return address_dict(ctx, a)


def add_contact(ctx: RequestContext, student_id, body) -> dict:
    s = get_scoped(ctx, student_id)
    value = body.value.strip().lower() if body.kind == "EMAIL" else body.value.strip()
    if (body.kind == "EMAIL" and not EMAIL.match(value)) or (body.kind == "MOBILE" and not MOBILE.match(value)):
        raise ValidationFailed("Contact value is not valid.", [{"field": "value", "message": f"Invalid {body.kind.lower()}"}])
    now = datetime.now(UTC)
    if body.make_primary:
        for old in ctx.db.execute(select(StudentContact).where(StudentContact.student_id == s.id,
                                                               StudentContact.kind == body.kind,
                                                               StudentContact.is_primary.is_(True),
                                                               StudentContact.superseded_at.is_(None))).scalars():
            old.is_primary, old.superseded_at = False, now
        if body.kind == "EMAIL":
            s.primary_email = value
        else:
            s.primary_mobile = value
    c = StudentContact(tenant_id=ctx.tenant_id, student_id=s.id, kind=body.kind, value=value,
                       is_primary=body.make_primary, source=body.source, effective_from=date.today(),
                       created_by=ctx.user_id)
    ctx.db.add(c)
    ctx.db.flush()
    recompute(ctx.db, s)
    ctx.audit("contact.added", target_type="student", target_id=s.id, target_label=s.dapro_ref,
              payload={"kind": body.kind, "primary": body.make_primary, "source": body.source})
    ctx.commit()
    return {"id": str(c.id), "kind": c.kind, "is_primary": c.is_primary, "source": c.source,
            "verification": c.verification}


def add_academic(ctx: RequestContext, student_id, body) -> dict:
    s = get_scoped(ctx, student_id)
    if ctx.is_college and s.college_org_id != ctx.org_id:
        raise NotFound("Student")
    now = datetime.now(UTC)
    for old in ctx.db.execute(select(AcademicRecord).where(AcademicRecord.student_id == s.id,
                                                           AcademicRecord.is_current.is_(True))).scalars():
        old.is_current, old.superseded_at = False, now
    r = AcademicRecord(tenant_id=ctx.tenant_id, student_id=s.id, college_org_id=s.college_org_id, **body.model_dump(),
                       source="COLLEGE_PROVIDED" if ctx.is_college else "STAFF_ENTERED", verification="VERIFIED",
                       recorded_by=ctx.user_id)
    ctx.db.add(r)
    if body.enrolment_status == "COMPLETED" and s.lifecycle_status == "STUDYING":
        s.lifecycle_status = "GRADUATED"
    elif body.enrolment_status == "ENROLLED":
        s.lifecycle_status = "STUDYING"
    ctx.db.flush()
    recompute(ctx.db, s)
    ctx.audit("academic.recorded", target_type="student", target_id=s.id, target_label=s.dapro_ref,
              payload={"enrolment_status": body.enrolment_status, "lifecycle_status": s.lifecycle_status})
    ctx.commit()
    from app.models.iam import Organization
    return academic_dict(r, {s.college_org_id: (ctx.db.get(Organization, s.college_org_id) or Organization()).name})


def list_employment(ctx: RequestContext, student_id) -> list[dict]:
    s = get_scoped(ctx, student_id)
    rows = ctx.db.execute(select(EmploymentRecord).where(EmploymentRecord.student_id == s.id)
                          .order_by(EmploymentRecord.is_current.desc(), EmploymentRecord.reported_on.desc())).scalars()
    return [employment_dict(e) for e in rows]


def add_employment(ctx: RequestContext, student_id, body) -> dict:
    """Records a post-study status. Status is never used to infer default or absconding (FR-EMP-07)."""
    s = get_scoped(ctx, student_id)
    if body.source == "INSTITUTION_VERIFIED":
        raise ValidationFailed("Records cannot be created as verified.",
                               [{"field": "source", "message": "Record it, then use the verify action"}])
    now = datetime.now(UTC)
    for old in ctx.db.execute(select(EmploymentRecord).where(EmploymentRecord.student_id == s.id,
                                                             EmploymentRecord.is_current.is_(True))).scalars():
        old.is_current, old.superseded_at = False, now
    e = EmploymentRecord(tenant_id=ctx.tenant_id, student_id=s.id, status=body.status,
                         employer_name=body.employer_name, job_title=body.job_title, sector=body.sector,
                         city=body.city, country=(body.country or "").upper() or None, source=body.source,
                         verification="UNVERIFIED", reported_on=date.today(),
                         effective_from=body.effective_from or date.today(), notes=body.notes, recorded_by=ctx.user_id)
    ctx.db.add(e)
    if body.status != "STUDYING" or s.lifecycle_status == "STUDYING":
        s.lifecycle_status = body.status
    ctx.db.flush()
    recompute(ctx.db, s)
    ctx.audit("employment.recorded", target_type="student", target_id=s.id, target_label=s.dapro_ref,
              payload={"status": body.status, "source": body.source})
    ctx.commit()
    return employment_dict(e)


def verify_employment(ctx: RequestContext, record_id, notes: str) -> dict:
    e = ctx.db.get(EmploymentRecord, record_id)
    if e is None:
        raise NotFound("Employment record")
    get_scoped(ctx, e.student_id)
    if e.verification == "VERIFIED":
        raise BusinessError("INVALID_STATE", "Record is already verified.", None)
    e.verification, e.verified_by, e.verified_at = "VERIFIED", ctx.user_id, datetime.now(UTC)
    e.notes = ((e.notes + " | ") if e.notes else "") + "Verified: " + notes
    ctx.audit("employment.verified", target_type="student", target_id=e.student_id,
              payload={"record_id": str(e.id), "original_source": e.source})
    ctx.commit()
    return employment_dict(e)


def consent_dict(c: Consent) -> dict:
    return {"id": str(c.id), "basis": c.basis, "purposes": c.purposes, "notice_version": c.notice_version,
            "source": c.source, "valid_from": c.valid_from, "valid_to": c.valid_to, "withdrawn_at": c.withdrawn_at,
            "active": c.withdrawn_at is None}


def list_consents(ctx: RequestContext, student_id) -> list[dict]:
    s = get_scoped(ctx, student_id)
    return [consent_dict(c) for c in ctx.db.execute(select(Consent).where(Consent.student_id == s.id)
                                                    .order_by(Consent.valid_from.desc())).scalars()]


def add_consent(ctx: RequestContext, student_id, body) -> dict:
    s = get_scoped(ctx, student_id)
    allowed = {"MONITORING", "ENGAGEMENT", "FOLLOW_UP"}
    bad = [p for p in body.purposes if p not in allowed]
    if bad:
        raise ValidationFailed("Unknown purpose.", [{"field": "purposes", "message": ", ".join(bad)}])
    c = Consent(tenant_id=ctx.tenant_id, student_id=s.id, basis=body.basis, purposes=body.purposes,
                notice_version=body.notice_version, source=body.source, valid_from=datetime.now(UTC),
                recorded_by=ctx.user_id)
    ctx.db.add(c)
    ctx.db.flush()
    ctx.audit("consent.recorded", target_type="student", target_id=s.id, payload={"basis": c.basis, "purposes": c.purposes})
    ctx.commit()
    return consent_dict(c)


def withdraw_consent(ctx: RequestContext, consent_id) -> dict:
    c = ctx.db.get(Consent, consent_id)
    if c is None:
        raise NotFound("Consent")
    get_scoped(ctx, c.student_id)
    if c.withdrawn_at:
        raise BusinessError("INVALID_STATE", "Consent already withdrawn.", None)
    c.withdrawn_at = datetime.now(UTC)
    ctx.audit("consent.withdrawn", target_type="student", target_id=c.student_id, payload={"consent_id": str(c.id)})
    ctx.commit()
    return consent_dict(c)


def pref_dict(p: ContactPreference) -> dict:
    return {"channel": p.channel, "allowed": p.allowed, "quiet_start": p.quiet_start.strftime("%H:%M"),
            "quiet_end": p.quiet_end.strftime("%H:%M"), "timezone": p.timezone, "language": p.language}


def get_preferences(ctx: RequestContext, student_id) -> list[dict]:
    s = get_scoped(ctx, student_id)
    return [pref_dict(p) for p in ctx.db.execute(select(ContactPreference)
                                                 .where(ContactPreference.student_id == s.id)).scalars()]


def set_preference(ctx: RequestContext, student_id, body) -> dict:
    s = get_scoped(ctx, student_id)
    p = ctx.db.execute(select(ContactPreference).where(ContactPreference.student_id == s.id,
                                                       ContactPreference.channel == body.channel)).scalar()
    if p is None:
        p = ContactPreference(tenant_id=ctx.tenant_id, student_id=s.id, channel=body.channel)
        ctx.db.add(p)
    p.allowed = body.allowed
    if body.quiet_start:
        p.quiet_start = time.fromisoformat(body.quiet_start)
    if body.quiet_end:
        p.quiet_end = time.fromisoformat(body.quiet_end)
    p.timezone = body.timezone or p.timezone or "Asia/Kolkata"
    p.language = body.language or p.language or "en"
    p.updated_by = ctx.user_id
    ctx.db.flush()
    ctx.audit("preference.updated", target_type="student", target_id=s.id,
              payload={"channel": body.channel, "allowed": body.allowed})
    ctx.commit()
    return pref_dict(p)
