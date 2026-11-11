"""Audit routes. There is deliberately no route that updates or deletes audit events (FR-AUD-03)."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.audit import service
from app.modules.audit.reconstruct import reconstruct

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
def events(page: int = 1, size: int = 50, actor_id: UUID | None = None, action: str | None = None,
           target_type: str | None = None, target_id: str | None = None, outcome: str | None = None,
           date_from: datetime | None = None, date_to: datetime | None = None, q: str | None = None,
           ctx: RequestContext = Depends(require("audit:read"))):
    f = dict(actor_id=actor_id, action=action, target_type=target_type, target_id=target_id, outcome=outcome,
             date_from=date_from, date_to=date_to, q=q)
    return service.search(ctx, f, page, size)


@router.get("/verify")
def verify(ctx: RequestContext = Depends(require("audit:verify"))):
    res = service.run_verification(ctx.db, ctx.tenant_id, triggered_by="MANUAL")
    ctx.commit()
    return res


@router.get("/checkpoints")
def checkpoints(ctx: RequestContext = Depends(require("audit:verify"))):
    return service.checkpoints(ctx)


@router.get("/cases/{case_id}/reconstruction")
def case_reconstruction(case_id: UUID, ctx: RequestContext = Depends(require("audit:read"))):
    return reconstruct(ctx, case_id)
