"""Student registration, update with correction history, duplicate detection (FR-STU-01..08)."""
from datetime import UTC, date, datetime

from sqlalchemy import or_, select

from app.common.pagination import paginate
from app.common.refs import next_ref
from app.core import masking
from app.core.context import RequestContext
from app.core.errors import BusinessError, Forbidden, NotFound, ValidationFailed, VersionMismatch
from app.models.iam import Organization, OrgUnit
from app.models.loans import LoanAccount
from app.models.students import AcademicRecord, DuplicateCandidate, Student, StudentContact, StudentFieldChange
from app.modules.students import repo
from app.modules.students.completion import recompute
from app.seed.data import norm_name


def org_names(db) -> dict:
    return {o.id: o.name for o in db.execute(select(Organization)).scalars()}


def serialize(ctx: RequestContext, s: Student, names: dict | None = None, loan_count: int | None = None) -> dict:
    names = names or {}
    return {
        "id": str(s.id), "dapro_ref": s.dapro_ref, "college_student_id": s.college_student_id,
        "full_name": s.full_name, "first_name": s.first_name, "last_name": s.last_name,
        "dob": s.dob.isoformat() if s.dob and (ctx.can("student:pii_full") or ctx.is_bank) else None,
        "dob_masked": s.dob is not None and not (ctx.can("student:pii_full") or ctx.is_bank),
        "gender": s.gender, "kyc_ref_last4": s.kyc_ref_last4,
        "email": masking.contact(ctx, "EMAIL", s.primary_email),
        "mobile": masking.contact(ctx, "MOBILE", s.primary_mobile),
        "college_org_id": str(s.college_org_id), "college_name": names.get(s.college_org_id),
        "campus_unit_id": str(s.campus_unit_id) if s.campus_unit_id else None,
        "lifecycle_status": s.lifecycle_status, "record_status": s.record_status,
        "verification_status": s.verification_status, "source": s.source, "source_ref": s.source_ref,
        "profile_completion": s.profile_completion, "data_origin": s.data_origin, "version": s.version,
        "loan_count": loan_count, "created_at": s.created_at, "updated_at": s.updated_at,
    }


def list_students(ctx: RequestContext, filters: dict, page: int, size: int) -> dict:
    rows, total, page, size = paginate(ctx.db, repo.list_stmt(ctx, filters), page, size)
    ids = [r.id for r in rows]
    counts: dict = {}
    if ids:
        for sid in ctx.db.execute(select(LoanAccount.student_id).where(LoanAccount.student_id.in_(ids))).scalars():
            counts[sid] = counts.get(sid, 0) + 1
    names = org_names(ctx.db)
    return {"items": [serialize(ctx, r, names, counts.get(r.id, 0)) for r in rows], "total": total, "page": page,
            "size": size}


def find_duplicates(ctx: RequestContext, college_org_id, college_student_id: str, full_name: str,
                    dob: date | None) -> list[Student]:
    conds = [(Student.college_org_id == college_org_id) & (Student.college_student_id == college_student_id)]
    if dob:
        conds.append((Student.name_norm == norm_name(full_name)) & (Student.dob == dob))
    return list(ctx.db.execute(select(Student).where(or_(*conds), Student.record_status != "MERGED")).scalars())


def resolve_college(ctx: RequestContext, college_org_id: str | None):
    if ctx.is_college:
        if college_org_id and str(college_org_id) != str(ctx.org_id):
            raise Forbidden("College users can only register students for their own college.")
        return ctx.org_id
    if not college_org_id:
        raise ValidationFailed("College is required.", [{"field": "college_org_id", "message": "Required"}])
    org = ctx.db.get(Organization, college_org_id)
    if org is None or org.type != "COLLEGE":
        raise ValidationFailed("Unknown college.", [{"field": "college_org_id", "message": "Not a college"}])
    return org.id


def create_student(ctx: RequestContext, body, source: str = "STAFF_ENTERED", batch_id=None, commit: bool = True):
    db = ctx.db
    college_id = resolve_college(ctx, body.college_org_id)
    full = f"{body.first_name.strip()} {body.last_name.strip()}"
    sid = body.college_student_id.strip()
    dups = find_duplicates(ctx, college_id, sid, full, body.dob)
    same_id = [d for d in dups if d.college_org_id == college_id and d.college_student_id == sid]
    if same_id:
        raise BusinessError("DUPLICATE_STUDENT_ID", "A student with this college student ID already exists.",
                            "Open the existing record instead of creating a new one.", 409,
                            [{"id": str(d.id), "dapro_ref": d.dapro_ref, "full_name": d.full_name} for d in same_id])
    if dups and not body.confirm_not_duplicate:
        raise BusinessError("POSSIBLE_DUPLICATE", "A student with the same name and date of birth already exists.",
                            "Review the candidates. If this is a different person, confirm and submit again.", 409,
                            [{"id": str(d.id), "dapro_ref": d.dapro_ref, "full_name": d.full_name,
                              "college_student_id": d.college_student_id} for d in dups])
    campus = None
    if body.campus_unit_id:
        unit = db.get(OrgUnit, body.campus_unit_id)
        if unit is None or unit.org_id != college_id:
            raise ValidationFailed("Campus does not belong to the college.",
                                   [{"field": "campus_unit_id", "message": "Invalid campus"}])
        campus = unit.id
    s = Student(tenant_id=ctx.tenant_id, dapro_ref=next_ref(db, ctx.tenant_id, "student", "DAP"),
                college_org_id=college_id, campus_unit_id=campus, college_student_id=sid,
                first_name=body.first_name.strip(), last_name=body.last_name.strip(), full_name=full,
                name_norm=norm_name(full), dob=body.dob, gender=body.gender, kyc_ref_last4=body.kyc_ref_last4,
                primary_email=str(body.email).lower() if body.email else None, primary_mobile=body.mobile,
                source=source, source_ref=str(batch_id) if batch_id else None, import_batch_id=batch_id,
                data_origin="LIVE", created_by=ctx.user_id, verification_status="UNVERIFIED")
    db.add(s)
    db.flush()
    for kind, value in (("EMAIL", s.primary_email), ("MOBILE", s.primary_mobile)):
        if value:
            db.add(StudentContact(tenant_id=ctx.tenant_id, student_id=s.id, kind=kind, value=value, is_primary=True,
                                  source="COLLEGE_PROVIDED", verification="UNVERIFIED", effective_from=date.today(),
                                  created_by=ctx.user_id))
    if body.programme and body.course and body.cohort_year:
        db.add(AcademicRecord(tenant_id=ctx.tenant_id, student_id=s.id, college_org_id=college_id,
                              programme=body.programme, course=body.course, cohort_year=body.cohort_year,
                              enrolment_status="ENROLLED", start_date=date(body.cohort_year, 7, 1),
                              expected_completion=body.expected_completion, source="COLLEGE_PROVIDED",
                              verification="VERIFIED", recorded_by=ctx.user_id))
    for d in dups:
        db.add(DuplicateCandidate(tenant_id=ctx.tenant_id, student_id=s.id, candidate_student_id=d.id,
                                  match_fields=["full_name", "dob"], score=90, status="OPEN"))
    db.flush()
    recompute(db, s)
    ctx.audit("student.registered", target_type="student", target_id=s.id, target_label=s.dapro_ref,
              payload={"source": source, "possible_duplicates": len(dups)})
    if commit:
        ctx.commit()
    return s


EDITABLE = ("first_name", "last_name", "dob", "gender", "kyc_ref_last4")


def update_student(ctx: RequestContext, student_id, version: int | None, body) -> Student:
    s = repo.get_scoped(ctx, student_id)
    if not ctx.is_college:
        raise Forbidden("Only the owning college can change student identity fields.")
    if version is None:
        raise BusinessError("VERSION_REQUIRED", "If-Match header with the record version is required.",
                            "Reload the record and resend with If-Match.", 428)
    if version != s.version:
        raise VersionMismatch()
    changed = []
    for f in EDITABLE:
        new = getattr(body, f)
        if new is None or new == getattr(s, f):
            continue
        old = getattr(s, f)
        ctx.db.add(StudentFieldChange(tenant_id=ctx.tenant_id, student_id=s.id, field=f,
                                      old_value=None if old is None else str(old), new_value=str(new),
                                      reason=body.reason, source="STAFF_ENTERED", actor_id=ctx.user_id))
        setattr(s, f, new)
        changed.append(f)
    if not changed:
        raise ValidationFailed("Nothing changed.", next_step="Change at least one field.")
    s.full_name = f"{s.first_name} {s.last_name}"
    s.name_norm = norm_name(s.full_name)
    s.version += 1
    recompute(ctx.db, s)
    ctx.audit("student.updated", target_type="student", target_id=s.id, target_label=s.dapro_ref,
              payload={"fields": changed, "reason": body.reason})
    ctx.commit()
    return s


def field_history(ctx: RequestContext, student_id) -> list[dict]:
    s = repo.get_scoped(ctx, student_id)
    rows = ctx.db.execute(select(StudentFieldChange).where(StudentFieldChange.student_id == s.id)
                          .order_by(StudentFieldChange.created_at.desc())).scalars()
    return [{"id": str(r.id), "field": r.field, "old_value": r.old_value, "new_value": r.new_value,
             "reason": r.reason, "source": r.source, "actor_id": str(r.actor_id) if r.actor_id else None,
             "created_at": r.created_at} for r in rows]


def list_duplicates(ctx: RequestContext, status: str = "OPEN") -> list[dict]:
    from app.core.scope import student_clause
    rows = ctx.db.execute(select(DuplicateCandidate).where(DuplicateCandidate.status == status)
                          .order_by(DuplicateCandidate.created_at.desc())).scalars().all()
    visible = set(ctx.db.execute(select(Student.id).where(student_clause(ctx))).scalars())
    out = []
    for r in rows:
        if r.student_id not in visible:
            continue
        a, b = ctx.db.get(Student, r.student_id), ctx.db.get(Student, r.candidate_student_id)
        out.append({"id": str(r.id), "status": r.status, "score": r.score, "match_fields": r.match_fields,
                    "created_at": r.created_at, "notes": r.notes,
                    "student": {"id": str(a.id), "dapro_ref": a.dapro_ref, "full_name": a.full_name,
                                "college_student_id": a.college_student_id},
                    "candidate": {"id": str(b.id), "dapro_ref": b.dapro_ref, "full_name": b.full_name,
                                  "college_student_id": b.college_student_id}})
    return out


def resolve_duplicate(ctx: RequestContext, dup_id, decision: str, notes: str) -> dict:
    r = ctx.db.get(DuplicateCandidate, dup_id)
    if r is None or r.status != "OPEN":
        raise NotFound("Open duplicate candidate")
    s = repo.get_scoped(ctx, r.student_id)
    r.status, r.reviewed_by, r.reviewed_at, r.notes = decision, ctx.user_id, datetime.now(UTC), notes
    if decision == "CONFIRMED_DUPLICATE":
        s.record_status, s.merged_into_id = "MERGED", r.candidate_student_id
    ctx.audit("student.duplicate_resolved", target_type="student", target_id=s.id, target_label=s.dapro_ref,
              payload={"decision": decision, "candidate": str(r.candidate_student_id)})
    ctx.commit()
    return {"id": str(r.id), "status": r.status}
