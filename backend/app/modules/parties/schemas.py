from datetime import date

from pydantic import BaseModel, Field


class GuarantorIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    relationship_to_borrower: str | None = Field(default=None, max_length=60)
    mobile: str | None = Field(default=None, pattern=r"^\+?[0-9 ]{8,16}$")
    email: str | None = Field(default=None, max_length=254)
    address_text: str | None = Field(default=None, max_length=300)
    city: str | None = None
    state: str | None = None
    agreement_ref: str = Field(min_length=2, max_length=80)
    agreement_executed_on: date | None = None
    guarantee_scope: str | None = Field(default=None, max_length=300)
    communication_permitted: bool = False
    communication_basis: str | None = Field(default=None, max_length=300)


class GuarantorPatch(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    relationship_to_borrower: str | None = None
    mobile: str | None = Field(default=None, pattern=r"^\+?[0-9 ]{8,16}$")
    email: str | None = None
    address_text: str | None = None
    city: str | None = None
    state: str | None = None
    agreement_ref: str | None = None
    agreement_executed_on: date | None = None
    guarantee_scope: str | None = None
    guarantee_status: str | None = Field(default=None, pattern="^(ACTIVE|RELEASED|EXPIRED|UNDER_REVIEW)$")
    verification: str | None = Field(default=None, pattern="^(UNVERIFIED|VERIFIED|FAILED)$")
    communication_permitted: bool | None = None
    communication_basis: str | None = None
    reason: str = Field(min_length=5, max_length=500)


class DecisionIn(BaseModel):
    notes: str = Field(min_length=3, max_length=500)


class WitnessIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    document_ref: str = Field(min_length=2, max_length=80)
    witnessed_on: date | None = None
    address_city: str | None = None
    notes: str | None = Field(default=None, max_length=500)


class WitnessPatch(BaseModel):
    full_name: str | None = None
    document_ref: str | None = None
    witnessed_on: date | None = None
    address_city: str | None = None
    verification: str | None = Field(default=None, pattern="^(UNVERIFIED|VERIFIED|FAILED)$")
    notes: str | None = None
