"""Bank-owned loan mirror, repayment data, parties, imports and reconciliation (Modules 03, 04, 06).

Bank-sourced rows are a read-only mirror (BR-01, INT-BNK-01). repayment_transactions and
loan_snapshots are append-only: the application DB role has no UPDATE/DELETE on them.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Money, TenantMixin, created, fk, pk, rls, scol, updated


@rls
class LoanAccount(Base, TenantMixin):
    __tablename__ = "loan_accounts"
    __table_args__ = (UniqueConstraint("tenant_id", "bank_org_id", "bank_loan_ref"),)
    id: Mapped[uuid.UUID] = pk()
    bank_org_id: Mapped[uuid.UUID] = fk("organizations.id")
    branch_unit_id: Mapped[uuid.UUID | None] = fk("org_units.id", nullable=True)
    student_id: Mapped[uuid.UUID | None] = fk("students.id", nullable=True)
    college_org_id: Mapped[uuid.UUID | None] = fk("organizations.id", nullable=True)
    bank_loan_ref: Mapped[str] = mapped_column(String(60), index=True)
    bank_borrower_ref: Mapped[str | None]
    product_name: Mapped[str | None]
    scheme: Mapped[str | None]
    bank_status: Mapped[str] = scol(20, default="UNKNOWN")
    sanctioned_amount: Mapped[Decimal | None] = mapped_column(Money)
    disbursed_amount: Mapped[Decimal | None] = mapped_column(Money)
    sanction_date: Mapped[date | None]
    first_disbursement_date: Mapped[date | None]
    moratorium_end: Mapped[date | None]
    repayment_start: Mapped[date | None]
    tenure_months: Mapped[int | None] = mapped_column(Integer)
    interest_rate_pct: Mapped[Decimal | None] = mapped_column(Money)
    emi_amount: Mapped[Decimal | None] = mapped_column(Money)
    currency: Mapped[str] = scol(3, default="INR")
    link_status: Mapped[str] = scol(20, default="PENDING_REVIEW", index=True)
    link_validation: Mapped[dict] = mapped_column(default=dict, server_default="{}")
    linked_by: Mapped[uuid.UUID | None]
    linked_at: Mapped[datetime | None]
    sync_state: Mapped[str] = scol(20, default="UNKNOWN", index=True)
    last_synced_at: Mapped[datetime | None]
    last_sync_batch_id: Mapped[uuid.UUID | None]
    source_system: Mapped[str] = scol(40, default="MOCK_BANK_FEED")
    source_record_id: Mapped[str | None]
    data_origin: Mapped[str] = scol(10, default="LIVE")
    repayment_status: Mapped[str] = scol(20, default="UNKNOWN", index=True)
    dpd: Mapped[int | None] = mapped_column(Integer)
    dpd_bucket: Mapped[str | None] = scol(20, nullable=True, index=True)
    overdue_amount: Mapped[Decimal | None] = mapped_column(Money)
    principal_outstanding: Mapped[Decimal | None] = mapped_column(Money)
    next_due_date: Mapped[date | None]
    next_due_amount: Mapped[Decimal | None] = mapped_column(Money)
    status_evaluated_at: Mapped[datetime | None]
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


@rls
class LoanParty(Base, TenantMixin):
    """Applicant / co-applicant relationships. Guarantors and witnesses have their own tables (BR-07)."""
    __tablename__ = "loan_parties"
    id: Mapped[uuid.UUID] = pk()
    loan_id: Mapped[uuid.UUID] = fk("loan_accounts.id")
    student_id: Mapped[uuid.UUID | None] = fk("students.id", nullable=True)
    party_role: Mapped[str] = scol(20)
    full_name: Mapped[str]
    relationship: Mapped[str | None]
    source: Mapped[str] = scol(30, default="BANK_PROVIDED")
    created_at: Mapped[datetime] = created()


@rls
class LoanSnapshot(Base, TenantMixin):
    __tablename__ = "loan_snapshots"
    id: Mapped[uuid.UUID] = pk()
    loan_id: Mapped[uuid.UUID] = fk("loan_accounts.id")
    as_of: Mapped[datetime]
    principal_outstanding: Mapped[Decimal | None] = mapped_column(Money)
    interest_charges: Mapped[Decimal | None] = mapped_column(Money)
    overdue_amount: Mapped[Decimal | None] = mapped_column(Money)
    total_due: Mapped[Decimal | None] = mapped_column(Money)
    bank_dpd: Mapped[int | None] = mapped_column(Integer)
    bank_status: Mapped[str | None] = scol(20, nullable=True)
    source_system: Mapped[str] = scol(40)
    source_batch_id: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class RepaymentSchedule(Base, TenantMixin):
    __tablename__ = "repayment_schedules"
    __table_args__ = (UniqueConstraint("loan_id", "version"),)
    id: Mapped[uuid.UUID] = pk()
    loan_id: Mapped[uuid.UUID] = fk("loan_accounts.id")
    version: Mapped[int] = mapped_column(Integer)
    schedule_ref: Mapped[str]
    reason: Mapped[str] = scol(20, default="ORIGINAL")
    effective_from: Mapped[date]
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    source_system: Mapped[str] = scol(40)
    source_batch_id: Mapped[uuid.UUID | None]
    received_at: Mapped[datetime] = created()


@rls
class ScheduleInstalment(Base, TenantMixin):
    __tablename__ = "schedule_instalments"
    __table_args__ = (UniqueConstraint("schedule_id", "instalment_no"),)
    id: Mapped[uuid.UUID] = pk()
    schedule_id: Mapped[uuid.UUID] = fk("repayment_schedules.id")
    loan_id: Mapped[uuid.UUID] = fk("loan_accounts.id")
    instalment_no: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(index=True)
    amount_due: Mapped[Decimal] = mapped_column(Money)
    principal_component: Mapped[Decimal | None] = mapped_column(Money)
    interest_component: Mapped[Decimal | None] = mapped_column(Money)
    bank_allocated_amount: Mapped[Decimal | None] = mapped_column(Money)
    bank_status: Mapped[str | None] = scol(20, nullable=True)
    status: Mapped[str] = scol(20, default="UNKNOWN", index=True)
    dpd: Mapped[int | None] = mapped_column(Integer)
    evaluated_at: Mapped[datetime | None]


@rls
class RepaymentTransaction(Base, TenantMixin):
    """Bank-confirmed transaction. Corrections arrive as new REVERSAL rows; nothing is overwritten (FR-REP-05)."""
    __tablename__ = "repayment_transactions"
    __table_args__ = (UniqueConstraint("tenant_id", "bank_txn_ref"),)
    id: Mapped[uuid.UUID] = pk()
    loan_id: Mapped[uuid.UUID] = fk("loan_accounts.id")
    bank_txn_ref: Mapped[str] = mapped_column(String(80))
    posted_on: Mapped[date] = mapped_column(index=True)
    value_on: Mapped[date | None]
    amount: Mapped[Decimal] = mapped_column(Money)
    kind: Mapped[str] = scol(20)  # PAYMENT | REVERSAL
    channel: Mapped[str | None] = scol(30, nullable=True)
    payment_reference: Mapped[str | None]
    reverses_txn_ref: Mapped[str | None]
    allocations: Mapped[list] = mapped_column(default=list, server_default="[]")
    source_system: Mapped[str] = scol(40)
    source_batch_id: Mapped[uuid.UUID | None]
    received_at: Mapped[datetime] = created()


@rls
class Guarantor(Base, TenantMixin):
    __tablename__ = "guarantors"
    id: Mapped[uuid.UUID] = pk()
    loan_id: Mapped[uuid.UUID] = fk("loan_accounts.id")
    full_name: Mapped[str]
    relationship_to_borrower: Mapped[str | None]
    mobile: Mapped[str | None]
    email: Mapped[str | None]
    address_text: Mapped[str | None]
    city: Mapped[str | None]
    state: Mapped[str | None]
    agreement_ref: Mapped[str]
    agreement_executed_on: Mapped[date | None]
    guarantee_scope: Mapped[str | None]
    guarantee_status: Mapped[str] = scol(20, default="ACTIVE")
    verification: Mapped[str] = scol(20, default="UNVERIFIED")
    verified_by: Mapped[uuid.UUID | None]
    verified_at: Mapped[datetime | None]
    communication_permitted: Mapped[bool] = mapped_column(Boolean, default=False)
    communication_basis: Mapped[str | None]
    source: Mapped[str] = scol(30, default="BANK_PROVIDED")
    approval_status: Mapped[str] = scol(20, default="APPROVED")
    pending_change: Mapped[dict | None]
    pending_by: Mapped[uuid.UUID | None]
    approved_by: Mapped[uuid.UUID | None]
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


@rls
class Witness(Base, TenantMixin):
    """Witness to a loan document. Deliberately has no liability, guarantee or communication fields (BR-07)."""
    __tablename__ = "witnesses"
    id: Mapped[uuid.UUID] = pk()
    loan_id: Mapped[uuid.UUID] = fk("loan_accounts.id")
    full_name: Mapped[str]
    document_ref: Mapped[str]
    witnessed_on: Mapped[date | None]
    address_city: Mapped[str | None]
    source: Mapped[str] = scol(30, default="BANK_PROVIDED")
    verification: Mapped[str] = scol(20, default="UNVERIFIED")
    notes: Mapped[str | None]
    created_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class ImportBatch(Base, TenantMixin):
    __tablename__ = "import_batches"
    id: Mapped[uuid.UUID] = pk()
    org_id: Mapped[uuid.UUID] = fk("organizations.id")
    kind: Mapped[str] = scol(30)  # STUDENT_CSV | BANK_SYNC | TRANSACTION_CSV
    source: Mapped[str] = scol(30)  # CSV_UPLOAD | MOCK_BANK_FEED | BANK_API
    file_name: Mapped[str | None]
    checksum: Mapped[str | None] = scol(64, nullable=True, index=True)
    status: Mapped[str] = scol(20, default="QUEUED", index=True)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0)
    applied_rows: Mapped[int] = mapped_column(Integer, default=0)
    error_rows: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[list] = mapped_column(default=list, server_default="[]")
    summary: Mapped[dict] = mapped_column(default=dict, server_default="{}")
    storage_key: Mapped[str | None]
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    uploaded_by: Mapped[uuid.UUID | None]
    approved_by: Mapped[uuid.UUID | None]
    approved_at: Mapped[datetime | None]
    correlation_id: Mapped[str | None]
    data_origin: Mapped[str] = scol(10, default="LIVE")
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created()


@rls
class ReconciliationItem(Base, TenantMixin):
    __tablename__ = "reconciliation_items"
    id: Mapped[uuid.UUID] = pk()
    bank_org_id: Mapped[uuid.UUID | None] = fk("organizations.id", nullable=True)
    loan_id: Mapped[uuid.UUID | None] = fk("loan_accounts.id", nullable=True)
    student_id: Mapped[uuid.UUID | None] = fk("students.id", nullable=True)
    batch_id: Mapped[uuid.UUID | None]
    kind: Mapped[str] = scol(30, index=True)
    severity: Mapped[str] = scol(10, default="MEDIUM")
    summary: Mapped[str]
    details: Mapped[dict] = mapped_column(default=dict, server_default="{}")
    status: Mapped[str] = scol(20, default="OPEN", index=True)
    resolution: Mapped[str | None]
    resolved_by: Mapped[uuid.UUID | None]
    resolved_at: Mapped[datetime | None]
    dedupe_key: Mapped[str | None] = mapped_column(String(200), index=True)
    created_at: Mapped[datetime] = created()


@rls
class Integration(Base, TenantMixin):
    __tablename__ = "integrations"
    id: Mapped[uuid.UUID] = pk()
    org_id: Mapped[uuid.UUID | None] = fk("organizations.id", nullable=True)
    kind: Mapped[str] = scol(30)  # BANK_LOAN_FEED | COLLEGE_SIS | EMAIL | SMS | OBJECT_STORAGE
    name: Mapped[str]
    provider: Mapped[str]
    mode: Mapped[str] = scol(20)  # LIVE | MOCK | NOT_CONFIGURED | DISABLED
    health: Mapped[str] = scol(20, default="UNKNOWN")  # HEALTHY | DEGRADED | FAILED | UNKNOWN
    last_success_at: Mapped[datetime | None]
    last_failure_at: Mapped[datetime | None]
    last_error: Mapped[str | None]
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    refresh_interval_hours: Mapped[int] = mapped_column(Integer, default=24)
    simulate_failure: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(default=dict, server_default="{}")
    updated_at: Mapped[datetime] = updated()


@rls
class MockBankRecord(Base, TenantMixin):
    """The MOCK bank's own loan book. Never a live integration; used only when DAPRO_BANK_ADAPTER=mock."""
    __tablename__ = "mock_bank_records"
    __table_args__ = (UniqueConstraint("tenant_id", "bank_org_id", "bank_loan_ref"),)
    id: Mapped[uuid.UUID] = pk()
    bank_org_id: Mapped[uuid.UUID] = fk("organizations.id")
    branch_code: Mapped[str | None]
    bank_loan_ref: Mapped[str] = mapped_column(String(60))
    bank_borrower_ref: Mapped[str]
    borrower_name: Mapped[str]
    borrower_dob: Mapped[date | None]
    terms: Mapped[dict] = mapped_column(default=dict)
    profile: Mapped[str] = scol(20)
    created_at: Mapped[datetime] = created()
