"""Case and investigation workspace routes (Module 08)."""
import os
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.config import get_settings
from app.core.context import RequestContext
from app.core.errors import NotFound
from app.models.ops import Evidence, PaymentCommitment
from app.modules.cases import service
from app.modules.cases.machine import RESOLUTION_TYPES, STATUSES

router = APIRouter(tags=["cases"])


class CaseIn(BaseModel):
    student_id: UUID
    loan_id: UUID | None = None
    category: str
    reason: str = Field(min_length=5, max_length=500)
    priority: str = "MEDIUM"
    due_on: date | None = None
    next_action: str | None = None
    owner_id: UUID | None = None


class CasePatch(BaseModel):
    priority: str | None = None
    due_on: date | None = None
    next_action: str | None = None


class AssignIn(BaseModel):
    owner_id: UUID


class TransitionIn(BaseModel):
    to: str
    note: str | None = None
    resolution_type: str | None = None
    bank_txn_ref: str | None = None


class FollowUpIn(BaseModel):
    channel: str
    outcome: str
    notes: str = Field(min_length=3, max_length=2000)
    contacted_at: datetime | None = None
    next_follow_up_on: date | None = None


class CommitmentIn(BaseModel):
    amount: Decimal = Field(gt=0, decimal_places=2)
    promised_date: date
    notes: str | None = None


class ConfirmIn(BaseModel):
    bank_txn_ref: str = Field(min_length=3)


@router.get("/cases/meta")
def meta(ctx: RequestContext = Depends(require("case:read"))):
    return {"statuses": STATUSES, "priorities": service.PRIORITIES, "categories": service.CATEGORIES,
            "channels": service.CHANNELS, "outcomes": {"no_contact": service.NO_CONTACT, "contact": service.CONTACT},
            "resolution_types": RESOLUTION_TYPES}


@router.get("/cases")
def list_cases(status: str | None = None, priority: str | None = None, owner: str | None = None,
               owner_id: str | None = None, category: str | None = None, overdue: bool | None = None,
               q: str | None = None, page: int = 1, size: int = 25, sort: str | None = None,
               ctx: RequestContext = Depends(require("case:read"))):
    items, total, page, size = service.list_cases(ctx, status=status, priority=priority, owner=owner_id or owner,
                                                  category=category, overdue=overdue, q=q, page=page, size=size,
                                                  sort=sort)
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("/cases", status_code=201)
def create(body: CaseIn, ctx: RequestContext = Depends(require("case:create"))):
    c = service.create_case(ctx, **body.model_dump())
    ctx.commit()
    return service.detail(ctx, c)


@router.get("/cases/{case_id}")
def get(case_id: UUID, ctx: RequestContext = Depends(require("case:read"))):
    return service.detail(ctx, service.get_case(ctx, case_id))


@router.patch("/cases/{case_id}")
def patch(case_id: UUID, body: CasePatch, if_match: str | None = Header(None),
          ctx: RequestContext = Depends(require("case:update", "case:assign", any_of=True))):
    c = service.get_case(ctx, case_id)
    service.patch(ctx, c, int(if_match) if if_match and if_match.isdigit() else None, **body.model_dump())
    return service.detail(ctx, c)


@router.post("/cases/{case_id}/assign")
def assign(case_id: UUID, body: AssignIn, ctx: RequestContext = Depends(require("case:assign"))):
    c = service.assign(ctx, service.get_case(ctx, case_id), body.owner_id)
    return service.detail(ctx, c)


@router.post("/cases/{case_id}/transition")
def transition(case_id: UUID, body: TransitionIn, ctx: RequestContext = Depends(require("case:read"))):
    c = service.transition(ctx, service.get_case(ctx, case_id), body.to, body.note, body.resolution_type,
                           body.bank_txn_ref)
    return service.detail(ctx, c)


@router.post("/cases/{case_id}/follow-ups", status_code=201)
def follow_up(case_id: UUID, body: FollowUpIn, ctx: RequestContext = Depends(require("case:update"))):
    c = service.get_case(ctx, case_id)
    service.add_follow_up(ctx, c, **body.model_dump())
    return service.detail(ctx, c)


@router.post("/cases/{case_id}/evidence", status_code=201)
async def evidence(case_id: UUID, file: UploadFile = File(...), title: str = Form(...), kind: str = Form("DOCUMENT"),
                   description: str | None = Form(None), visit_id: UUID | None = Form(None),
                   ctx: RequestContext = Depends(require("case:update"))):
    content = await file.read()
    c = service.get_case(ctx, case_id)
    ev = service.add_evidence(ctx, c, title=title, kind=kind, description=description, file_name=file.filename,
                              mime=file.content_type, content=content, visit_id=visit_id)
    return {"id": str(ev.id), "sha256": ev.sha256, "size_bytes": ev.size_bytes}


@router.get("/evidence/{evidence_id}/download")
def download(evidence_id: UUID, ctx: RequestContext = Depends(require("case:read"))):
    ev = ctx.db.get(Evidence, evidence_id)
    if ev is None:
        raise NotFound("Evidence")
    c = service.get_case(ctx, ev.case_id)
    ctx.audit("evidence.downloaded", target_type="evidence", target_id=ev.id, target_label=c.case_ref,
              payload={"sha256": ev.sha256})
    ctx.commit()
    return FileResponse(os.path.join(get_settings().storage_dir, ev.storage_key), media_type=ev.mime_type,
                        filename=ev.file_name)


@router.post("/cases/{case_id}/commitments", status_code=201)
def commitment(case_id: UUID, body: CommitmentIn, ctx: RequestContext = Depends(require("case:update"))):
    c = service.get_case(ctx, case_id)
    pc = service.add_commitment(ctx, c, body.amount, body.promised_date, body.notes)
    return {"id": str(pc.id), "status": pc.status, "source": pc.source, "is_payment": False}


@router.post("/commitments/{commitment_id}/confirm")
def confirm(commitment_id: UUID, body: ConfirmIn,
            ctx: RequestContext = Depends(require("case:update", "case:close", any_of=True))):
    pc = ctx.db.get(PaymentCommitment, commitment_id)
    if pc is None:
        raise NotFound("Commitment")
    pc = service.confirm_commitment(ctx, pc, body.bank_txn_ref)
    return {"id": str(pc.id), "status": pc.status, "bank_txn_ref": pc.bank_txn_ref}
