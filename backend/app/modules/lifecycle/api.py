"""Lifecycle routes: addresses, verification, contacts, academic, employment, consents, preferences (Module 05)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.lifecycle import service
from app.modules.lifecycle.schemas import (
    AcademicIn,
    AddressIn,
    ConsentIn,
    ContactIn,
    DisputeIn,
    EmploymentIn,
    PreferenceIn,
    VerificationOutcomeIn,
    VerificationRequestIn,
)

router = APIRouter(tags=["lifecycle"])


class NotesIn(BaseModel):
    notes: str = Field(min_length=3, max_length=500)


@router.get("/students/{student_id}/addresses")
def list_addresses(student_id: str, history: bool = False, ctx: RequestContext = Depends(require("address:read"))):
    return service.list_addresses(ctx, student_id, history)


@router.post("/students/{student_id}/addresses", status_code=201)
def add_address(student_id: str, body: AddressIn, ctx: RequestContext = Depends(require("address:write"))):
    return service.add_address(ctx, student_id, body)


@router.post("/addresses/{address_id}/verification-requests", status_code=201)
def request_verification(address_id: str, body: VerificationRequestIn,
                         ctx: RequestContext = Depends(require("address:write", "address:verify", any_of=True))):
    return service.request_verification(ctx, address_id, body)


@router.post("/addresses/{address_id}/dispute")
def dispute(address_id: str, body: DisputeIn, ctx: RequestContext = Depends(require("address:write"))):
    return service.dispute_address(ctx, address_id, body.reason)


@router.get("/address-verifications")
def verification_queue(status: str = "PENDING", ctx: RequestContext = Depends(require("address:verify"))):
    return service.verification_queue(ctx, status)


@router.post("/address-verifications/{verification_id}/outcome")
def record_outcome(verification_id: str, body: VerificationOutcomeIn,
                   ctx: RequestContext = Depends(require("address:verify"))):
    return service.record_outcome(ctx, verification_id, body)


@router.post("/students/{student_id}/contacts", status_code=201)
def add_contact(student_id: str, body: ContactIn, ctx: RequestContext = Depends(require("address:write"))):
    return service.add_contact(ctx, student_id, body)


@router.post("/students/{student_id}/academic", status_code=201)
def add_academic(student_id: str, body: AcademicIn, ctx: RequestContext = Depends(require("academic:write"))):
    return service.add_academic(ctx, student_id, body)


@router.get("/students/{student_id}/employment")
def list_employment(student_id: str, ctx: RequestContext = Depends(require("student:read"))):
    return service.list_employment(ctx, student_id)


@router.post("/students/{student_id}/employment", status_code=201)
def add_employment(student_id: str, body: EmploymentIn, ctx: RequestContext = Depends(require("employment:write"))):
    return service.add_employment(ctx, student_id, body)


@router.post("/employment/{record_id}/verify")
def verify_employment(record_id: str, body: NotesIn, ctx: RequestContext = Depends(require("employment:write"))):
    return service.verify_employment(ctx, record_id, body.notes)


@router.get("/students/{student_id}/consents")
def list_consents(student_id: str, ctx: RequestContext = Depends(require("student:read"))):
    return service.list_consents(ctx, student_id)


@router.post("/students/{student_id}/consents", status_code=201)
def add_consent(student_id: str, body: ConsentIn, ctx: RequestContext = Depends(require("student:write"))):
    return service.add_consent(ctx, student_id, body)


@router.post("/consents/{consent_id}/withdraw")
def withdraw_consent(consent_id: str, ctx: RequestContext = Depends(require("student:write"))):
    return service.withdraw_consent(ctx, consent_id)


@router.get("/students/{student_id}/contact-preferences")
def get_preferences(student_id: str, ctx: RequestContext = Depends(require("student:read"))):
    return service.get_preferences(ctx, student_id)


@router.put("/students/{student_id}/contact-preferences")
def set_preference(student_id: str, body: PreferenceIn, ctx: RequestContext = Depends(require("student:write"))):
    return service.set_preference(ctx, student_id, body)
