"""Student request schemas. Responses are built as dicts in the service (role-masked)."""
from datetime import date

from pydantic import BaseModel, EmailStr, Field


class StudentCreate(BaseModel):
    college_org_id: str | None = None
    campus_unit_id: str | None = None
    college_student_id: str = Field(min_length=2, max_length=60)
    first_name: str = Field(min_length=1, max_length=80)
    last_name: str = Field(min_length=1, max_length=80)
    dob: date | None = None
    gender: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None
    mobile: str | None = Field(default=None, pattern=r"^\+?[0-9 ]{8,16}$")
    kyc_ref_last4: str | None = Field(default=None, pattern=r"^[0-9A-Za-z]{4}$")
    programme: str | None = None
    course: str | None = None
    cohort_year: int | None = Field(default=None, ge=1990, le=2100)
    expected_completion: date | None = None
    confirm_not_duplicate: bool = False


class StudentPatch(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    last_name: str | None = Field(default=None, min_length=1, max_length=80)
    dob: date | None = None
    gender: str | None = None
    kyc_ref_last4: str | None = Field(default=None, pattern=r"^[0-9A-Za-z]{4}$")
    reason: str = Field(min_length=5, max_length=500)


class DuplicateResolve(BaseModel):
    decision: str = Field(pattern="^(NOT_DUPLICATE|CONFIRMED_DUPLICATE)$")
    notes: str = Field(min_length=3, max_length=500)
