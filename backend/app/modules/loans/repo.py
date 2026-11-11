"""Loan queries (repository layer)."""
from sqlalchemy import or_, select

from app.core.scope import loan_clause
from app.models.iam import Organization, OrgUnit
from app.models.loans import ImportBatch, LoanAccount, LoanSnapshot
from app.models.students import Student


def loan_list_stmt(ctx, f: dict):
    stmt = (select(LoanAccount, Student.full_name, Student.dapro_ref, Organization.name, OrgUnit.name)
            .outerjoin(Student, Student.id == LoanAccount.student_id)
            .join(Organization, Organization.id == LoanAccount.bank_org_id)
            .outerjoin(OrgUnit, OrgUnit.id == LoanAccount.branch_unit_id)
            .where(loan_clause(ctx)))
    for key, col in (("bank_org_id", LoanAccount.bank_org_id), ("branch_unit_id", LoanAccount.branch_unit_id),
                     ("college_org_id", LoanAccount.college_org_id), ("link_status", LoanAccount.link_status),
                     ("repayment_status", LoanAccount.repayment_status), ("dpd_bucket", LoanAccount.dpd_bucket),
                     ("sync_state", LoanAccount.sync_state), ("student_id", LoanAccount.student_id)):
        if f.get(key):
            stmt = stmt.where(col == f[key])
    if f.get("q"):
        q = f"%{f['q'].strip()}%"
        stmt = stmt.where(or_(LoanAccount.bank_loan_ref.ilike(q), Student.full_name.ilike(q), Student.dapro_ref.ilike(q)))
    return stmt


def get_scoped(ctx, loan_id):
    return ctx.db.execute(select(LoanAccount).where(LoanAccount.id == loan_id, loan_clause(ctx))).scalar()


def latest_snapshot(db, loan_id):
    return db.execute(select(LoanSnapshot).where(LoanSnapshot.loan_id == loan_id)
                      .order_by(LoanSnapshot.as_of.desc()).limit(1)).scalar()


def batches_for(db, loan):
    ids = {loan.last_sync_batch_id} if loan.last_sync_batch_id else set()
    stmt = select(ImportBatch).where(ImportBatch.org_id == loan.bank_org_id, ImportBatch.kind == "BANK_SYNC") \
        .order_by(ImportBatch.created_at.desc()).limit(10)
    return [b for b in db.execute(stmt).scalars()] or [db.get(ImportBatch, i) for i in ids]
