"""Risk intelligence, cases, follow-ups, evidence, commitments and field visits (Modules 07, 08, 09)."""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Money, TenantMixin, created, fk, pk, rls, scol, updated


@rls
class RiskRule(Base, TenantMixin):
    __tablename__ = "risk_rules"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "version"),)
    id: Mapped[uuid.UUID] = pk()
    code: Mapped[str] = mapped_column(String(40))
    version: Mapped[int] = mapped_column(Integer)
    name: Mapped[str]
    category: Mapped[str] = scol(40)
    description: Mapped[str]
    params: Mapped[dict] = mapped_column(default=dict)
    severity: Mapped[str] = scol(20)
    recommended_action: Mapped[str]
    status: Mapped[str] = scol(20, default="DRAFT")  # DRAFT | ACTIVE | RETIRED | REJECTED
    approval_label: Mapped[str] = scol(30, default="DEMO_FIXTURE")
    effective_from: Mapped[date | None]
    change_reason: Mapped[str | None]
    created_by: Mapped[uuid.UUID | None]
    approved_by: Mapped[uuid.UUID | None]
    approved_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created()


@rls
class RiskIndicator(Base, TenantMixin):
    __tablename__ = "risk_indicators"
    id: Mapped[uuid.UUID] = pk()
    student_id: Mapped[uuid.UUID] = fk("students.id")
    loan_id: Mapped[uuid.UUID | None] = fk("loan_accounts.id", nullable=True)
    bank_org_id: Mapped[uuid.UUID | None] = fk("organizations.id", nullable=True)
    rule_id: Mapped[uuid.UUID] = fk("risk_rules.id")
    rule_code: Mapped[str] = scol(40, index=True)
    rule_version: Mapped[int] = mapped_column(Integer)
    category: Mapped[str] = scol(40, index=True)
    severity: Mapped[str] = scol(20, index=True)
    title: Mapped[str]
    explanation: Mapped[str]
    evidence: Mapped[list] = mapped_column(default=list)
    input_snapshot: Mapped[dict] = mapped_column(default=dict)
    status: Mapped[str] = scol(20, default="OPEN", index=True)
    assigned_to: Mapped[uuid.UUID | None]
    case_id: Mapped[uuid.UUID | None]
    dedupe_key: Mapped[str] = mapped_column(String(200), index=True)
    generated_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


@rls
class RiskReview(Base, TenantMixin):
    """Append-only review history (FR-RSK-05, FR-RSK-06)."""
    __tablename__ = "risk_reviews"
    id: Mapped[uuid.UUID] = pk()
    indicator_id: Mapped[uuid.UUID] = fk("risk_indicators.id")
    reviewer_id: Mapped[uuid.UUID]
    decision: Mapped[str] = scol(30)  # CONFIRM_FOR_FOLLOW_UP | CREATE_CASE | DISMISS | OVERRIDE_SEVERITY
    rationale: Mapped[str]
    override_severity: Mapped[str | None] = scol(20, nullable=True)
    evidence_ref: Mapped[str | None]
    case_id: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class Case(Base, TenantMixin):
    __tablename__ = "cases"
    __table_args__ = (UniqueConstraint("tenant_id", "case_ref"),)
    id: Mapped[uuid.UUID] = pk()
    case_ref: Mapped[str] = mapped_column(String(30))
    student_id: Mapped[uuid.UUID] = fk("students.id")
    loan_id: Mapped[uuid.UUID | None] = fk("loan_accounts.id", nullable=True)
    bank_org_id: Mapped[uuid.UUID | None] = fk("organizations.id", nullable=True)
    college_org_id: Mapped[uuid.UUID | None] = fk("organizations.id", nullable=True)
    category: Mapped[str] = scol(40, index=True)
    reason: Mapped[str]
    source: Mapped[str] = scol(30, default="MANUAL")
    source_ref: Mapped[str | None]
    priority: Mapped[str] = scol(10, default="MEDIUM", index=True)
    status: Mapped[str] = scol(30, default="NEW", index=True)
    previous_status: Mapped[str | None] = scol(30, nullable=True)
    owner_id: Mapped[uuid.UUID | None] = fk("users.id", nullable=True)
    team_unit_id: Mapped[uuid.UUID | None] = fk("org_units.id", nullable=True)
    next_action: Mapped[str | None]
    due_on: Mapped[date | None] = mapped_column(index=True)
    opened_by: Mapped[uuid.UUID | None]
    resolution_type: Mapped[str | None] = scol(40, nullable=True)
    resolution_notes: Mapped[str | None]
    resolution_evidence: Mapped[dict | None]
    resolved_at: Mapped[datetime | None]
    closed_at: Mapped[datetime | None]
    closed_by: Mapped[uuid.UUID | None]
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


@rls
class CaseEvent(Base, TenantMixin):
    __tablename__ = "case_events"
    id: Mapped[uuid.UUID] = pk()
    case_id: Mapped[uuid.UUID] = fk("cases.id")
    event_type: Mapped[str] = scol(40)
    from_status: Mapped[str | None] = scol(30, nullable=True)
    to_status: Mapped[str | None] = scol(30, nullable=True)
    summary: Mapped[str]
    data: Mapped[dict] = mapped_column(default=dict, server_default="{}")
    actor_id: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class CaseFollowUp(Base, TenantMixin):
    __tablename__ = "case_follow_ups"
    id: Mapped[uuid.UUID] = pk()
    case_id: Mapped[uuid.UUID] = fk("cases.id")
    channel: Mapped[str] = scol(20)
    outcome: Mapped[str] = scol(40)
    notes: Mapped[str]
    contacted_at: Mapped[datetime]
    next_follow_up_on: Mapped[date | None]
    actor_id: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class Evidence(Base, TenantMixin):
    __tablename__ = "evidence"
    id: Mapped[uuid.UUID] = pk()
    case_id: Mapped[uuid.UUID] = fk("cases.id")
    visit_id: Mapped[uuid.UUID | None]
    kind: Mapped[str] = scol(30)  # DOCUMENT | PHOTO | BANK_CONFIRMATION | NOTE
    title: Mapped[str]
    description: Mapped[str | None]
    file_name: Mapped[str | None]
    mime_type: Mapped[str | None]
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    sha256: Mapped[str | None] = scol(64, nullable=True)
    storage_key: Mapped[str | None]
    classification: Mapped[str] = scol(20, default="RESTRICTED")
    evidence_quality: Mapped[str] = scol(30, default="OFFICER_OBSERVATION")
    uploaded_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class PaymentCommitment(Base, TenantMixin):
    """Borrower-reported promise. Never a payment (BR-08, FR-FLD-06, AC-12)."""
    __tablename__ = "payment_commitments"
    id: Mapped[uuid.UUID] = pk()
    case_id: Mapped[uuid.UUID] = fk("cases.id")
    loan_id: Mapped[uuid.UUID | None] = fk("loan_accounts.id", nullable=True)
    visit_id: Mapped[uuid.UUID | None]
    amount: Mapped[Decimal] = mapped_column(Money)
    promised_date: Mapped[date]
    source: Mapped[str] = scol(30, default="BORROWER_REPORTED")
    status: Mapped[str] = scol(20, default="OPEN")  # OPEN | BANK_CONFIRMED | LAPSED | WITHDRAWN
    bank_txn_ref: Mapped[str | None]
    notes: Mapped[str | None]
    recorded_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


@rls
class FieldVisit(Base, TenantMixin):
    __tablename__ = "field_visits"
    __table_args__ = (UniqueConstraint("tenant_id", "client_draft_id"),)
    id: Mapped[uuid.UUID] = pk()
    case_id: Mapped[uuid.UUID] = fk("cases.id")
    officer_id: Mapped[uuid.UUID] = fk("users.id")
    status: Mapped[str] = scol(20, default="SCHEDULED", index=True)  # DRAFT | SCHEDULED | SUBMITTED | CANCELLED
    purpose: Mapped[str]
    scheduled_for: Mapped[datetime | None]
    check_in_at: Mapped[datetime | None]
    check_out_at: Mapped[datetime | None]
    visited_at: Mapped[datetime | None]
    outcome: Mapped[str | None] = scol(30, nullable=True)
    address_id: Mapped[uuid.UUID | None]
    notes: Mapped[str | None]
    borrower_present: Mapped[bool | None]
    safety_incident: Mapped[bool] = mapped_column(Boolean, default=False)
    incident_notes: Mapped[str | None]
    location_captured: Mapped[bool] = mapped_column(Boolean, default=False)
    review_status: Mapped[str] = scol(20, default="NOT_REQUIRED", index=True)
    reviewer_id: Mapped[uuid.UUID | None]
    reviewed_at: Mapped[datetime | None]
    review_notes: Mapped[str | None]
    client_draft_id: Mapped[str | None] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
