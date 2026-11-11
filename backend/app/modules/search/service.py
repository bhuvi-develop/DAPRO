"""Global search across permitted, scope-filtered records. Max 6 hits per section."""
from sqlalchemy import or_, select

from app.core.context import RequestContext
from app.core.scope import case_clause, loan_clause, student_clause
from app.models.engagement import Grievance
from app.models.loans import LoanAccount
from app.models.ops import Case
from app.models.students import Student

LIMIT = 6


def search(ctx: RequestContext, q: str) -> dict:
    q = (q or "").strip()
    out: dict = {"students": [], "loans": [], "cases": [], "grievances": []}
    if len(q) < 2:
        return out
    like = f"%{q}%"
    db = ctx.db
    if ctx.can("student:read"):
        rows = db.execute(select(Student).where(student_clause(ctx), Student.record_status != "MERGED",
                                                or_(Student.full_name.ilike(like), Student.dapro_ref.ilike(like),
                                                    Student.college_student_id.ilike(like)))
                          .order_by(Student.full_name).limit(LIMIT)).scalars()
        out["students"] = [{"id": str(s.id), "title": s.full_name,
                            "subtitle": f"{s.dapro_ref} | {s.college_student_id} | {s.lifecycle_status}",
                            "link": f"/students/{s.id}"} for s in rows]
    if ctx.can("loan:read"):
        rows = db.execute(select(LoanAccount, Student.full_name).outerjoin(Student, Student.id == LoanAccount.student_id)
                          .where(loan_clause(ctx), LoanAccount.bank_loan_ref.ilike(like))
                          .order_by(LoanAccount.bank_loan_ref).limit(LIMIT)).all()
        out["loans"] = [{"id": str(lo.id), "title": lo.bank_loan_ref,
                         "subtitle": f"{name or 'Unlinked'} | {lo.link_status} | {lo.repayment_status}",
                         "link": f"/loans/{lo.id}"} for lo, name in rows]
    if ctx.can("case:read"):
        rows = db.execute(select(Case, Student.full_name).join(Student, Student.id == Case.student_id)
                          .where(case_clause(ctx), or_(Case.case_ref.ilike(like), Student.full_name.ilike(like)))
                          .order_by(Case.created_at.desc()).limit(LIMIT)).all()
        out["cases"] = [{"id": str(c.id), "title": c.case_ref, "subtitle": f"{name} | {c.status} | {c.priority}",
                         "link": f"/cases/{c.id}"} for c, name in rows]
    if ctx.can("grievance:read"):
        rows = db.execute(select(Grievance, Student.full_name).join(Student, Student.id == Grievance.student_id)
                          .where(student_clause(ctx), or_(Grievance.ref.ilike(like), Grievance.subject.ilike(like)))
                          .order_by(Grievance.created_at.desc()).limit(LIMIT)).all()
        out["grievances"] = [{"id": str(g.id), "title": g.ref, "subtitle": f"{name} | {g.category} | {g.status}",
                              "link": f"/grievances/{g.id}"} for g, name in rows]
    return out
