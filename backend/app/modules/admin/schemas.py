from datetime import date

from pydantic import BaseModel, EmailStr, Field


class OrgIn(BaseModel):
    type: str = Field(pattern="^(COLLEGE|BANK|NBFC|AGENCY)$")
    code: str = Field(pattern=r"^[A-Z0-9_-]{2,40}$")
    name: str = Field(min_length=3, max_length=160)
    legal_name: str | None = None
    city: str | None = None
    state: str | None = None
    contact_email: EmailStr | None = None


class OrgPatch(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=160)
    legal_name: str | None = None
    city: str | None = None
    state: str | None = None
    contact_email: EmailStr | None = None
    status: str | None = Field(default=None, pattern="^(ACTIVE|SUSPENDED|INACTIVE)$")


class UnitIn(BaseModel):
    org_id: str
    parent_id: str | None = None
    kind: str = Field(pattern="^(CAMPUS|BRANCH|REGION|DEPARTMENT|TEAM)$")
    code: str = Field(pattern=r"^[A-Z0-9_-]{2,40}$")
    name: str = Field(min_length=2, max_length=160)
    city: str | None = None
    state: str | None = None


class AgreementIn(BaseModel):
    reference: str = Field(min_length=3, max_length=60)
    college_org_id: str
    bank_org_id: str
    purposes: list[str] = Field(min_length=1)
    shared_fields: list[str] = Field(default_factory=list)
    effective_from: date
    effective_to: date | None = None
    notes: str | None = None


class InviteIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    title: str | None = None
    role_code: str
    org_id: str | None = None
    org_unit_id: str | None = None


class RolesIn(BaseModel):
    role_codes: list[str] = Field(min_length=1)
    reason: str = Field(min_length=5, max_length=300)


class ReasonIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


class IntegrationPatch(BaseModel):
    mode: str | None = Field(default=None, pattern="^(LIVE|MOCK|NOT_CONFIGURED|DISABLED)$")
    refresh_interval_hours: int | None = Field(default=None, ge=1, le=168)
    simulate_failure: bool | None = None


class PolicyProposal(BaseModel):
    key: str
    value: dict
    description: str | None = None
    effective_from: date
    reason: str = Field(min_length=5, max_length=500)


class DemoResetIn(BaseModel):
    confirm: str
