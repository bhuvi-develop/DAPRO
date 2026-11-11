"""Field operations routes (Module 09)."""
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.field import service

router = APIRouter(tags=["field"])


class VisitIn(BaseModel):
    purpose: str = Field(min_length=3, max_length=300)
    scheduled_for: datetime | None = None
    draft: bool = False
    client_draft_id: str | None = Field(None, max_length=64)


class DraftIn(BaseModel):
    scheduled_for: datetime | None = None
    outcome: str | None = None
    notes: str | None = None
    borrower_present: bool | None = None
    safety_incident: bool | None = None
    incident_notes: str | None = None


class SubmitIn(BaseModel):
    outcome: str
    notes: str
    borrower_present: bool | None = None
    safety_incident: bool = False
    incident_notes: str | None = None
    client_draft_id: str | None = Field(None, max_length=64)


class ReviewIn(BaseModel):
    decision: str
    notes: str


@router.get("/field/my-cases")
def my_cases(ctx: RequestContext = Depends(require("visit:record"))):
    items = service.my_cases(ctx)
    return {"items": items, "total": len(items), "page": 1, "size": len(items), "settings": service.settings_info()}


@router.get("/field/meta")
def meta(ctx: RequestContext = Depends(require("visit:record", "visit:review", any_of=True))):
    return {"outcomes": service.OUTCOMES, **service.settings_info()}


@router.post("/cases/{case_id}/visits", status_code=201)
def create(case_id: UUID, body: VisitIn, ctx: RequestContext = Depends(require("visit:record"))):
    return service.visit_out(ctx.db, service.create_visit(ctx, case_id, **body.model_dump()))


@router.get("/visits/{visit_id}")
def get(visit_id: UUID, ctx: RequestContext = Depends(require("visit:record", "visit:review", any_of=True))):
    return service.visit_out(ctx.db, service.get_visit(ctx, visit_id))


@router.patch("/visits/{visit_id}")
def save(visit_id: UUID, body: DraftIn, if_match: str | None = Header(None),
         ctx: RequestContext = Depends(require("visit:record"))):
    v = service.save_draft(ctx, visit_id, int(if_match) if if_match and if_match.isdigit() else None,
                           **body.model_dump())
    return service.visit_out(ctx.db, v)


@router.post("/visits/{visit_id}/check-in")
def check_in(visit_id: UUID, ctx: RequestContext = Depends(require("visit:record"))):
    return service.visit_out(ctx.db, service.check(ctx, visit_id, "in"))


@router.post("/visits/{visit_id}/check-out")
def check_out(visit_id: UUID, ctx: RequestContext = Depends(require("visit:record"))):
    return service.visit_out(ctx.db, service.check(ctx, visit_id, "out"))


@router.post("/visits/{visit_id}/submit")
def submit(visit_id: UUID, body: SubmitIn, ctx: RequestContext = Depends(require("visit:record"))):
    return service.visit_out(ctx.db, service.submit(ctx, visit_id, **body.model_dump()))


@router.get("/field/review-queue")
def queue(ctx: RequestContext = Depends(require("visit:review"))):
    items = service.review_queue(ctx)
    return {"items": items, "total": len(items), "page": 1, "size": len(items)}


@router.post("/visits/{visit_id}/review")
def review(visit_id: UUID, body: ReviewIn, ctx: RequestContext = Depends(require("visit:review"))):
    return service.visit_out(ctx.db, service.review(ctx, visit_id, body.decision, body.notes))
