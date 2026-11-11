"""Notification and communication routes (Module 10)."""
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.errors import NotFound
from app.models.engagement import NotificationTemplate
from app.modules.comms import service

router = APIRouter(tags=["communications"])


class SendIn(BaseModel):
    student_id: UUID
    template_code: str
    channel: str | None = None
    case_id: UUID | None = None
    recipient_type: str = "BORROWER"
    guarantor_id: UUID | None = None
    variables: dict | None = None


class TemplateIn(BaseModel):
    code: str = Field(min_length=3, max_length=60)
    name: str
    channel: str
    purpose: str
    subject: str | None = None
    body: str = Field(min_length=10)
    language: str = "en"
    shared: bool = False


@router.get("/communications")
def list_comms(status: str | None = None, channel: str | None = None, purpose: str | None = None,
               student_id: UUID | None = None, case_id: UUID | None = None, q: str | None = None, page: int = 1,
               size: int = 25, sort: str | None = None, ctx: RequestContext = Depends(require("comm:read"))):
    items, total, page, size = service.list_comms(ctx, status=status, channel=channel, purpose=purpose,
                                                  student_id=student_id, case_id=case_id, q=q, page=page,
                                                  size=size, sort=sort)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/students/{student_id}/communications")
def student_comms(student_id: UUID, page: int = 1, size: int = 50,
                  ctx: RequestContext = Depends(require("comm:read"))):
    items, total, page, size = service.list_comms(ctx, student_id=student_id, page=page, size=size)
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("/communications", status_code=201)
def send(body: SendIn, ctx: RequestContext = Depends(require("comm:send"))):
    return service.comm_out(ctx.db, service.send(ctx, **body.model_dump()))


@router.get("/templates")
def templates(ctx: RequestContext = Depends(require("comm:read", "template:manage", "comm:send", any_of=True))):
    items = service.templates(ctx)
    return {"items": items, "total": len(items), "page": 1, "size": len(items), "purposes": service.PURPOSES}


@router.post("/templates", status_code=201)
def create_template(body: TemplateIn, ctx: RequestContext = Depends(require("template:manage"))):
    return service.tpl_out(ctx.db, service.create_template(ctx, **body.model_dump()))


@router.post("/templates/{template_id}/approve")
def approve(template_id: UUID, ctx: RequestContext = Depends(require("template:manage"))):
    t = ctx.db.get(NotificationTemplate, template_id)
    if t is None:
        raise NotFound("Template")
    return service.tpl_out(ctx.db, service.approve_template(ctx, t))
