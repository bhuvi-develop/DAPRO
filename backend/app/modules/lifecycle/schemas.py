from datetime import date

from pydantic import BaseModel, Field

ADDRESS_KINDS = "^(PERMANENT|CURRENT|CORRESPONDENCE)$"
SOURCES = "^(BORROWER_REPORTED|COLLEGE_PROVIDED|BANK_PROVIDED|FIELD_OBSERVED|STAFF_ENTERED)$"
METHODS = "^(DOCUMENT|FIELD_VISIT|POSTAL|PHONE_CONFIRMATION|SELF_DECLARATION)$"
EMP_STATUS = "^(STUDYING|GRADUATED|FURTHER_STUDY|EMPLOYED|SELF_EMPLOYED|UNEMPLOYED|UNKNOWN)$"


class AddressIn(BaseModel):
    kind: str = Field(pattern=ADDRESS_KINDS)
    line1: str = Field(min_length=3, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=2, max_length=80)
    district: str | None = None
    state: str | None = None
    postal_code: str | None = Field(default=None, max_length=12)
    country: str = Field(default="IN", min_length=2, max_length=2)
    source_type: str = Field(default="STAFF_ENTERED", pattern=SOURCES)
    effective_from: date | None = None
    notes: str | None = Field(default=None, max_length=500)
    request_verification: bool = False
    verification_method: str | None = Field(default=None, pattern=METHODS)


class VerificationRequestIn(BaseModel):
    method: str = Field(pattern=METHODS)
    assigned_to: str | None = None


class VerificationOutcomeIn(BaseModel):
    status: str = Field(pattern="^(VERIFIED|FAILED)$")
    notes: str = Field(min_length=3, max_length=1000)


class DisputeIn(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class ContactIn(BaseModel):
    kind: str = Field(pattern="^(MOBILE|EMAIL)$")
    value: str = Field(min_length=5, max_length=254)
    source: str = Field(default="STAFF_ENTERED", pattern=SOURCES)
    make_primary: bool = True


class AcademicIn(BaseModel):
    programme: str = Field(min_length=2, max_length=80)
    course: str = Field(min_length=2, max_length=120)
    specialization: str | None = None
    cohort_year: int = Field(ge=1990, le=2100)
    enrolment_status: str = Field(pattern="^(ENROLLED|ON_LEAVE|COMPLETED|DISCONTINUED|TRANSFERRED)$")
    start_date: date | None = None
    expected_completion: date | None = None
    actual_completion: date | None = None


class EmploymentIn(BaseModel):
    status: str = Field(pattern=EMP_STATUS)
    employer_name: str | None = Field(default=None, max_length=160)
    job_title: str | None = Field(default=None, max_length=120)
    sector: str | None = None
    city: str | None = None
    country: str | None = Field(default=None, min_length=2, max_length=2)
    source: str = Field(default="STAFF_ENTERED", pattern="^(BORROWER_REPORTED|COLLEGE_PROVIDED|INSTITUTION_VERIFIED|STAFF_ENTERED)$")
    effective_from: date | None = None
    notes: str | None = Field(default=None, max_length=500)


class ConsentIn(BaseModel):
    basis: str = Field(pattern="^(CONSENT|CONTRACT|LEGITIMATE_USE|LEGAL_OBLIGATION)$")
    purposes: list[str] = Field(min_length=1)
    notice_version: str = Field(min_length=2, max_length=30)
    source: str = Field(min_length=2, max_length=30)


class PreferenceIn(BaseModel):
    channel: str = Field(pattern="^(EMAIL|SMS)$")
    allowed: bool
    quiet_start: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    quiet_end: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    timezone: str | None = None
    language: str | None = None
