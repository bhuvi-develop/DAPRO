"""Borrower portal routes. portal:self; every query is pinned to the caller student_id."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.grievances import service as grievances
from app.modules.portal import service

router = APIRouter(prefix="/portal", tags=["borrower-portal"])


class AddressIn(BaseModel):
    kind: str = "CURRENT"
    line1: str = Field(min_length=3, max_length=200)
    line2: str | None = None
    city: str = Field(min_length=2, max_length=80)
    state: str | None = None
    postal_code: str | None = Field(None, max_length=12)
    country: str = "IN"
    effective_from: date | None = None


class EmploymentIn(BaseModel):
    status: str
    employer_name: str | None = None
    job_title: str | None = None
    city: str | None = None
    country: str | None = "IN"
    effective_from: date | None = None


class PortalGrievanceIn(BaseModel):
    category: str
    subject: str = Field(min_length=5, max_length=200)
    description: str = Field(min_length=10, max_length=4000)
    loan_id: UUID | None = None
    correction_field: str | None = None
    correction_requested_value: str | None = None


@router.get("/overview")
def overview(ctx: RequestContext = Depends(require("portal:self"))):
    return service.overview(ctx)


@router.get("/profile")
def profile(ctx: RequestContext = Depends(require("portal:self"))):
    return service.profile(ctx)


@router.post("/address", status_code=201)
def address(body: AddressIn, ctx: RequestContext = Depends(require("portal:self"))):
    return service.submit_address(ctx, **body.model_dump())


@router.post("/employment", status_code=201)
def employment(body: EmploymentIn, ctx: RequestContext = Depends(require("portal:self"))):
    return service.submit_employment(ctx, **body.model_dump())


@router.get("/grievances")
def my_grievances(ctx: RequestContext = Depends(require("portal:self"))):
    service.me(ctx)
    items, total, page, size = grievances.list_grievances(ctx, size=100)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/grievances/{gid}")
def my_grievance(gid: UUID, ctx: RequestContext = Depends(require("portal:self"))):
    service.me(ctx)
    return grievances.out(ctx, grievances.get(ctx, gid), full=True)


@router.post("/grievances", status_code=201)
def raise_grievance(body: PortalGrievanceIn, ctx: RequestContext = Depends(require("portal:self"))):
    s = service.me(ctx)
    g = grievances.create(ctx, student_id=s.id, channel="PORTAL", **body.model_dump())
    return grievances.out(ctx, g, full=True)


@router.get("/communications")
def my_comms(ctx: RequestContext = Depends(require("portal:self"))):
    items = service.communications(ctx)
    return {"items": items, "total": len(items), "page": 1, "size": len(items)}
