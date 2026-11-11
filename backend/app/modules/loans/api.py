"""Loan, bank sync, import and reconciliation routes."""
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.loans import service
from app.modules.loans.schemas import LinkIn, ResolveIn

router = APIRouter(tags=["loans"])


@router.get("/loans")
def list_loans(page: int = 1, size: int = 25, q: str | None = None, bank_org_id: UUID | None = None,
               branch_unit_id: UUID | None = None, college_org_id: UUID | None = None, link_status: str | None = None,
               repayment_status: str | None = None, dpd_bucket: str | None = None, sync_state: str | None = None,
               student_id: UUID | None = None, sort: str | None = None,
               ctx: RequestContext = Depends(require("loan:read"))):
    f = {"q": q, "bank_org_id": bank_org_id, "branch_unit_id": branch_unit_id, "college_org_id": college_org_id,
         "link_status": link_status, "repayment_status": repayment_status, "dpd_bucket": dpd_bucket,
         "sync_state": sync_state, "student_id": student_id}
    return service.list_loans(ctx, f, page, size, sort)


@router.post("/loans/link")
def link_loan(body: LinkIn, ctx: RequestContext = Depends(require("loan:link"))):
    return service.link(ctx, body.student_id, body.bank_org_id, body.bank_loan_ref)


@router.get("/loans/{loan_id}")
def get_loan(loan_id: UUID, ctx: RequestContext = Depends(require("loan:read"))):
    return service.loan_detail(ctx, loan_id)


@router.get("/loans/{loan_id}/schedule")
def get_schedule(loan_id: UUID, ctx: RequestContext = Depends(require("loan:read", "repayment:read"))):
    return service.schedule(ctx, loan_id)


@router.get("/loans/{loan_id}/transactions")
def get_transactions(loan_id: UUID, ctx: RequestContext = Depends(require("loan:read", "repayment:read"))):
    return service.transactions(ctx, loan_id)


@router.get("/loans/{loan_id}/snapshots")
def get_snapshots(loan_id: UUID, ctx: RequestContext = Depends(require("loan:read", "loan:financial"))):
    return service.snapshots(ctx, loan_id)


@router.post("/banks/{bank_org_id}/sync", status_code=202)
def sync_bank(bank_org_id: UUID, ctx: RequestContext = Depends(require("bank:sync"))):
    return service.trigger_sync(ctx, bank_org_id)


@router.get("/imports")
def list_imports(page: int = 1, size: int = 25, status: str | None = None, kind: str | None = None,
                 ctx: RequestContext = Depends(require("bank:sync", "student:import", "integration:read", any_of=True))):
    return service.list_imports(ctx, page, size, status, kind)


@router.get("/imports/{batch_id}")
def get_import(batch_id: UUID,
               ctx: RequestContext = Depends(require("bank:sync", "student:import", "integration:read", any_of=True))):
    return service.get_import(ctx, batch_id)


@router.get("/reconciliation")
def list_reconciliation(page: int = 1, size: int = 25, kind: str | None = None, status: str | None = "OPEN",
                        severity: str | None = None, ctx: RequestContext = Depends(require("loan:reconcile"))):
    return service.list_recon(ctx, page, size, kind, None if status in (None, "", "ALL") else status, severity)


@router.post("/reconciliation/{item_id}/resolve")
def resolve_item(item_id: UUID, body: ResolveIn, ctx: RequestContext = Depends(require("loan:reconcile"))):
    return service.resolve(ctx, item_id, body.action, body.resolution, body.student_id)
