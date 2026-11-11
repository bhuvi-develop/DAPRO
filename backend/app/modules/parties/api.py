"""Guarantor and witness routes (Module 06). Separate permissions for each role (AC-09)."""
from fastapi import APIRouter, Depends

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.parties import service
from app.modules.parties.schemas import DecisionIn, GuarantorIn, GuarantorPatch, WitnessIn, WitnessPatch

router = APIRouter(tags=["guarantors-witnesses"])


@router.get("/loans/{loan_id}/guarantors")
def list_guarantors(loan_id: str, ctx: RequestContext = Depends(require("guarantor:read"))):
    return service.list_guarantors(ctx, loan_id)


@router.post("/loans/{loan_id}/guarantors", status_code=201)
def create_guarantor(loan_id: str, body: GuarantorIn, ctx: RequestContext = Depends(require("guarantor:write"))):
    return service.create_guarantor(ctx, loan_id, body)


@router.get("/guarantor-approvals")
def pending(ctx: RequestContext = Depends(require("guarantor:approve"))):
    return service.pending_approvals(ctx)


@router.patch("/guarantors/{guarantor_id}")
def update_guarantor(guarantor_id: str, body: GuarantorPatch,
                     ctx: RequestContext = Depends(require("guarantor:write"))):
    return service.update_guarantor(ctx, guarantor_id, body)


@router.post("/guarantors/{guarantor_id}/approve")
def approve(guarantor_id: str, body: DecisionIn, ctx: RequestContext = Depends(require("guarantor:approve"))):
    return service.decide(ctx, guarantor_id, True, body.notes)


@router.post("/guarantors/{guarantor_id}/reject")
def reject(guarantor_id: str, body: DecisionIn, ctx: RequestContext = Depends(require("guarantor:approve"))):
    return service.decide(ctx, guarantor_id, False, body.notes)


@router.get("/loans/{loan_id}/witnesses")
def list_witnesses(loan_id: str, ctx: RequestContext = Depends(require("witness:read"))):
    return service.list_witnesses(ctx, loan_id)


@router.post("/loans/{loan_id}/witnesses", status_code=201)
def create_witness(loan_id: str, body: WitnessIn, ctx: RequestContext = Depends(require("witness:write"))):
    return service.create_witness(ctx, loan_id, body)


@router.patch("/witnesses/{witness_id}")
def update_witness(witness_id: str, body: WitnessPatch, ctx: RequestContext = Depends(require("witness:write"))):
    return service.update_witness(ctx, witness_id, body)
