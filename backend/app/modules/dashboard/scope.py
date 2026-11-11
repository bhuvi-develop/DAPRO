"""Dashboard scope. Platform administrators get tenant-wide operational counts only: no borrower lists,
no financial amounts (RD section 6 role table)."""
from sqlalchemy import true

from app.core import masking
from app.core.scope import case_clause, loan_clause, student_clause


class DashScope:
    def __init__(self, ctx):
        self.ctx = ctx
        self.platform = ctx.org_type == "PLATFORM"
        self.loans = true() if self.platform else loan_clause(ctx)
        self.students = true() if self.platform else student_clause(ctx)
        self.cases = true() if self.platform else case_clause(ctx)
        self.financial = masking.financial_visible(ctx) and not self.platform
        self.borrower_lists = not self.platform
        self.repayments = (ctx.can("repayment:read") or ctx.is_borrower) and not self.platform

    def money(self, v):
        if v is None or not self.financial:
            return None
        return f"{v:.2f}"
