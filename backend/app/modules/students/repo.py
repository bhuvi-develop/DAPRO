"""Student queries (repository layer)."""
from sqlalchemy import and_, asc, desc, exists, or_, select

from app.core.context import RequestContext
from app.core.errors import NotFound
from app.core.scope import student_clause
from app.models.loans import LoanAccount
from app.models.students import AcademicRecord, Student

SORTS = {"name": Student.full_name, "created": Student.created_at, "ref": Student.dapro_ref,
         "completion": Student.profile_completion, "status": Student.lifecycle_status,
         "full_name": Student.full_name, "created_at": Student.created_at, "dapro_ref": Student.dapro_ref,
         "profile_completion": Student.profile_completion, "lifecycle_status": Student.lifecycle_status,
         "updated_at": Student.updated_at, "college_student_id": Student.college_student_id}


def get_scoped(ctx: RequestContext, student_id) -> Student:
    try:
        s = ctx.db.execute(select(Student).where(Student.id == student_id, student_clause(ctx))).scalar()
    except Exception as exc:  # malformed uuid
        raise NotFound("Student") from exc
    if s is None:
        raise NotFound("Student")
    return s


def list_stmt(ctx: RequestContext, f: dict):
    stmt = select(Student).where(student_clause(ctx), Student.record_status != "MERGED")
    if f.get("q"):
        q = f"%{f['q'].strip()}%"
        stmt = stmt.where(or_(Student.full_name.ilike(q), Student.dapro_ref.ilike(q),
                              Student.college_student_id.ilike(q)))
    if f.get("college_org_id"):
        stmt = stmt.where(Student.college_org_id == f["college_org_id"])
    if f.get("lifecycle_status"):
        stmt = stmt.where(Student.lifecycle_status == f["lifecycle_status"])
    if f.get("verification_status"):
        stmt = stmt.where(Student.verification_status == f["verification_status"])
    if f.get("completion_below") is not None:
        stmt = stmt.where(Student.profile_completion < f["completion_below"])
    if f.get("has_loan") is not None:
        cond = exists().where(and_(LoanAccount.student_id == Student.id))
        stmt = stmt.where(cond if f["has_loan"] else ~cond)
    if f.get("cohort"):
        stmt = stmt.where(exists().where(and_(AcademicRecord.student_id == Student.id,
                                              AcademicRecord.cohort_year == f["cohort"])))
    if f.get("created_after"):
        stmt = stmt.where(Student.created_at >= f["created_after"])
    col = SORTS.get((f.get("sort") or "name").lstrip("-"), Student.full_name)
    return stmt.order_by(desc(col) if (f.get("sort") or "").startswith("-") else asc(col), Student.id)
