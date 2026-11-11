"""Notifications, communications and grievances (Module 10)."""
import uuid
from datetime import date, datetime

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, created, fk, pk, rls, scol, updated


@rls
class NotificationTemplate(Base, TenantMixin):
    __tablename__ = "notification_templates"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "version"),)
    id: Mapped[uuid.UUID] = pk()
    org_id: Mapped[uuid.UUID | None] = fk("organizations.id", nullable=True)
    code: Mapped[str] = mapped_column(String(60))
    version: Mapped[int] = mapped_column(Integer, default=1)
    name: Mapped[str]
    channel: Mapped[str] = scol(10)
    purpose: Mapped[str] = scol(30)  # REMINDER | UPDATE_REQUEST | GRIEVANCE_ACK | GUARANTOR_NOTICE | GENERAL
    language: Mapped[str] = scol(10, default="en")
    subject: Mapped[str | None]
    body: Mapped[str]
    status: Mapped[str] = scol(20, default="DRAFT")
    approval_label: Mapped[str] = scol(30, default="DEMO_FIXTURE")
    created_by: Mapped[uuid.UUID | None]
    approved_by: Mapped[uuid.UUID | None]
    approved_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created()


@rls
class Communication(Base, TenantMixin):
    __tablename__ = "communications"
    id: Mapped[uuid.UUID] = pk()
    student_id: Mapped[uuid.UUID] = fk("students.id")
    case_id: Mapped[uuid.UUID | None] = fk("cases.id", nullable=True)
    guarantor_id: Mapped[uuid.UUID | None] = fk("guarantors.id", nullable=True)
    recipient_type: Mapped[str] = scol(20, default="BORROWER")
    template_id: Mapped[uuid.UUID | None]
    template_code: Mapped[str | None]
    template_version: Mapped[int | None] = mapped_column(Integer)
    channel: Mapped[str] = scol(10)
    recipient_masked: Mapped[str | None]
    purpose: Mapped[str] = scol(30)
    status: Mapped[str] = scol(20, default="QUEUED", index=True)
    block_reason: Mapped[str | None]
    provider: Mapped[str | None]
    provider_mode: Mapped[str] = scol(20, default="MOCK")
    provider_message_id: Mapped[str | None]
    error: Mapped[str | None]
    rendered_subject: Mapped[str | None]
    rendered_body: Mapped[str | None]
    created_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()
    sent_at: Mapped[datetime | None]
    delivered_at: Mapped[datetime | None]


@rls
class Grievance(Base, TenantMixin):
    __tablename__ = "grievances"
    __table_args__ = (UniqueConstraint("tenant_id", "ref"),)
    id: Mapped[uuid.UUID] = pk()
    ref: Mapped[str] = mapped_column(String(30))
    student_id: Mapped[uuid.UUID] = fk("students.id")
    loan_id: Mapped[uuid.UUID | None] = fk("loan_accounts.id", nullable=True)
    case_id: Mapped[uuid.UUID | None] = fk("cases.id", nullable=True)
    category: Mapped[str] = scol(30, index=True)
    subject: Mapped[str]
    description: Mapped[str]
    channel: Mapped[str] = scol(20)
    submitted_by_user_id: Mapped[uuid.UUID | None]
    subject_user_id: Mapped[uuid.UUID | None]
    owner_id: Mapped[uuid.UUID | None] = fk("users.id", nullable=True)
    owning_org_id: Mapped[uuid.UUID | None] = fk("organizations.id", nullable=True)
    status: Mapped[str] = scol(30, default="SUBMITTED", index=True)
    priority: Mapped[str] = scol(10, default="MEDIUM")
    due_on: Mapped[date | None]
    correction_field: Mapped[str | None]
    correction_requested_value: Mapped[str | None]
    resolution: Mapped[str | None]
    resolved_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


@rls
class GrievanceEvent(Base, TenantMixin):
    __tablename__ = "grievance_events"
    id: Mapped[uuid.UUID] = pk()
    grievance_id: Mapped[uuid.UUID] = fk("grievances.id")
    event_type: Mapped[str] = scol(30)
    visibility: Mapped[str] = scol(20, default="BORROWER")  # BORROWER | INTERNAL
    message: Mapped[str]
    from_status: Mapped[str | None] = scol(30, nullable=True)
    to_status: Mapped[str | None] = scol(30, nullable=True)
    actor_id: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()
