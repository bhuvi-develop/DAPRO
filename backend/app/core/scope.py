"""Row-scope filters applied inside services (organization, branch and assignment scope).

Tenant isolation is enforced by PostgreSQL RLS; these filters enforce organization-level
purpose limitation within a tenant (FR-ORG-03/04, FR-FLD-01, RD section 6.2).
"""
from sqlalchemy import false, or_, select

from app.core.context import RequestContext


def loan_clause(ctx: RequestContext):
    from app.models.loans import LoanAccount
    from app.models.ops import Case

    if ctx.is_borrower:
        return LoanAccount.student_id == ctx.student_id
    if ctx.is_field_officer:
        return LoanAccount.id.in_(select(Case.loan_id).where(Case.owner_id == ctx.user_id))
    if ctx.is_bank:
        clause = LoanAccount.bank_org_id == ctx.org_id
        if ctx.unit_ids:
            clause = clause & LoanAccount.branch_unit_id.in_(ctx.unit_ids)
        return clause
    if ctx.is_college:
        return LoanAccount.college_org_id == ctx.org_id
    return false()


def student_clause(ctx: RequestContext):
    from app.models.loans import LoanAccount
    from app.models.ops import Case
    from app.models.students import Student

    if ctx.is_borrower:
        return Student.id == ctx.student_id
    if ctx.is_field_officer:
        return Student.id.in_(select(Case.student_id).where(Case.owner_id == ctx.user_id))
    if ctx.is_bank:
        return Student.id.in_(select(LoanAccount.student_id).where(loan_clause(ctx)))
    if ctx.is_college:
        return Student.college_org_id == ctx.org_id
    return false()


def case_clause(ctx: RequestContext):
    from app.models.loans import LoanAccount
    from app.models.ops import Case

    if ctx.is_field_officer:
        return Case.owner_id == ctx.user_id
    if ctx.is_bank:
        clause = Case.bank_org_id == ctx.org_id
        if ctx.unit_ids:
            clause = clause & or_(Case.loan_id.is_(None),
                                  Case.loan_id.in_(select(LoanAccount.id).where(loan_clause(ctx))))
        return clause
    if ctx.is_college:
        return Case.college_org_id == ctx.org_id
    return false()
