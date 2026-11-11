"""Request bodies for loan, sync and reconciliation endpoints."""
from uuid import UUID

from pydantic import BaseModel, Field


class LinkIn(BaseModel):
    student_id: UUID
    bank_org_id: UUID
    bank_loan_ref: str = Field(min_length=3, max_length=60)


class ResolveIn(BaseModel):
    action: str = Field(pattern="^(CONFIRM_LINK|REJECT_LINK|LINK_TO_STUDENT|RESOLVE|DISMISS)$")
    resolution: str = Field(min_length=5, max_length=2000)
    student_id: UUID | None = None
