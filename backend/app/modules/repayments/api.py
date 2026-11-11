"""Repayment monitoring routes."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.repayments import service

router = APIRouter(prefix="/repayments", tags=["repayments"])


@router.get("/overview")
def overview(ctx: RequestContext = Depends(require("repayment:read"))):
    return service.overview(ctx)


@router.get("/accounts")
def accounts(page: int = 1, size: int = 25, due_from: date | None = None, due_to: date | None = None,
             bucket: str | None = None, college_org_id: UUID | None = None, branch_unit_id: UUID | None = None,
             bank_org_id: UUID | None = None, cohort: int | None = None, owner_id: UUID | None = None,
             repayment_status: str | None = None, sync_state: str | None = None, q: str | None = None,
             sort: str | None = None, dpd_bucket: str | None = None,
             ctx: RequestContext = Depends(require("repayment:read"))):
    f = dict(due_from=due_from, due_to=due_to, bucket=bucket or dpd_bucket, college_org_id=college_org_id,
             branch_unit_id=branch_unit_id, bank_org_id=bank_org_id, cohort=cohort, owner_id=owner_id,
             repayment_status=repayment_status, sync_state=sync_state, q=q)
    return service.accounts(ctx, f, page, size, sort)
