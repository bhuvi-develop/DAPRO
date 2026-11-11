"""Grievance and correction routes (Module 10)."""
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.grievances import service

router = APIRouter(prefix="/grievances", tags=["grievances"])


class GrievanceIn(BaseModel):
    student_id: UUID
    category: str
    subject: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    loan_id: UUID | None = None
    case_id: UUID | None = None
    channel: Literal["STAFF", "PHONE", "EMAIL", "IN_PERSON", "LETTER"] = "STAFF"
    subject_user_id: UUID | None = None
    correction_field: str | None = None
    correction_requested_value: str | None = None
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"


class AssignIn(BaseModel):
    owner_id: UUID


class RespondIn(BaseModel):
    message: str = Field(min_length=3, max_length=4000)
    visibility: Literal["BORROWER", "INTERNAL"] = "BORROWER"


class TransitionIn(BaseModel):
    to: Literal["ACKNOWLEDGED", "UNDER_REVIEW", "AWAITING_INFORMATION", "RESOLVED", "REJECTED", "CLOSED"]
    reason: str | None = Field(None, max_length=2000)
    approve_correction: bool = False


@router.get("/meta")
def meta(ctx: RequestContext = Depends(require("grievance:read"))):
    return {"categories": service.CATEGORIES, "correctable_fields": service.CORRECTABLE,
            "statuses": ["SUBMITTED", "ACKNOWLEDGED", "UNDER_REVIEW", "AWAITING_INFORMATION", "RESOLVED",
                         "REJECTED", "CLOSED"]}


@router.get("")
def list_grievances(status: str | None = None, category: str | None = None, owner_id: str | None = None,
                    q: str | None = None, page: int = 1, size: int = 25, sort: str | None = None,
                    ctx: RequestContext = Depends(require("grievance:read"))):
    items, total, page, size = service.list_grievances(ctx, status=status, category=category, owner_id=owner_id,
                                                       q=q, page=page, size=size, sort=sort)
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("", status_code=201)
def create(body: GrievanceIn, ctx: RequestContext = Depends(require("grievance:create"))):
    return service.out(ctx, service.create(ctx, **body.model_dump()), full=True)


@router.get("/{gid}")
def get(gid: UUID, ctx: RequestContext = Depends(require("grievance:read"))):
    return service.out(ctx, service.get(ctx, gid), full=True)


@router.post("/{gid}/assign")
def assign(gid: UUID, body: AssignIn, ctx: RequestContext = Depends(require("grievance:manage"))):
    return service.out(ctx, service.assign(ctx, service.get(ctx, gid), body.owner_id), full=True)


@router.post("/{gid}/respond")
def respond(gid: UUID, body: RespondIn, ctx: RequestContext = Depends(require("grievance:manage"))):
    return service.out(ctx, service.respond(ctx, service.get(ctx, gid), body.message, body.visibility), full=True)


@router.post("/{gid}/transition")
def transition(gid: UUID, body: TransitionIn, ctx: RequestContext = Depends(require("grievance:manage"))):
    g = service.transition(ctx, service.get(ctx, gid), body.to, body.reason, body.approve_correction)
    return service.out(ctx, g, full=True)
