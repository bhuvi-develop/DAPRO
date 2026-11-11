"""Policy configuration, exports, audit chain, in-app notifications and reference counters."""
import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Identity, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, created, fk, pk, rls, scol


@rls
class PolicyConfig(Base, TenantMixin):
    """Versioned, effective-dated policy (BR-02, BR-12). DEMO_FIXTURE values are not bank-approved."""
    __tablename__ = "policy_configs"
    __table_args__ = (UniqueConstraint("tenant_id", "key", "version"),)
    id: Mapped[uuid.UUID] = pk()
    key: Mapped[str] = mapped_column(String(60))
    version: Mapped[int] = mapped_column(Integer)
    value: Mapped[dict]
    status: Mapped[str] = scol(20, default="ACTIVE")
    approval_label: Mapped[str] = scol(30, default="DEMO_FIXTURE")
    description: Mapped[str]
    effective_from: Mapped[date]
    created_by: Mapped[uuid.UUID | None]
    approved_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class ExportJob(Base, TenantMixin):
    __tablename__ = "export_jobs"
    id: Mapped[uuid.UUID] = pk()
    report_code: Mapped[str] = scol(40, index=True)
    title: Mapped[str]
    filters: Mapped[dict] = mapped_column(default=dict)
    purpose: Mapped[str]
    format: Mapped[str] = scol(10, default="CSV")
    status: Mapped[str] = scol(20, default="QUEUED")
    row_count: Mapped[int | None] = mapped_column(Integer)
    file_name: Mapped[str | None]
    sha256: Mapped[str | None] = scol(64, nullable=True)
    storage_key: Mapped[str | None]
    as_of: Mapped[datetime | None]
    error: Mapped[str | None]
    requested_by: Mapped[uuid.UUID]
    completed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created()


@rls
class AuditEvent(Base):
    """Append-only, SHA-256 hash-chained per tenant (LLD section 7). UPDATE/DELETE blocked by trigger and grants."""
    __tablename__ = "audit_events"
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True, nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(index=True, nullable=False)
    actor_id: Mapped[uuid.UUID | None]
    actor_label: Mapped[str | None]
    actor_role: Mapped[str | None] = scol(40, nullable=True)
    org_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = scol(80, index=True)
    target_type: Mapped[str | None] = scol(40, nullable=True, index=True)
    target_id: Mapped[str | None] = mapped_column(String(80), index=True)
    target_label: Mapped[str | None]
    outcome: Mapped[str] = scol(20)
    purpose: Mapped[str | None] = scol(40, nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64))
    ip: Mapped[str | None]
    payload: Mapped[dict] = mapped_column(default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


@rls
class AuditCheckpoint(Base, TenantMixin):
    __tablename__ = "audit_checkpoints"
    id: Mapped[uuid.UUID] = pk()
    verified_at: Mapped[datetime] = created()
    last_seq: Mapped[int] = mapped_column(BigInteger)
    last_hash: Mapped[str | None]
    events_checked: Mapped[int] = mapped_column(Integer)
    ok: Mapped[bool] = mapped_column(Boolean)
    error: Mapped[str | None]
    triggered_by: Mapped[str] = scol(20, default="SCHEDULE")


@rls
class InAppNotification(Base, TenantMixin):
    __tablename__ = "in_app_notifications"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = fk("users.id")
    kind: Mapped[str] = scol(40)
    title: Mapped[str]
    body: Mapped[str | None]
    link: Mapped[str | None]
    severity: Mapped[str] = scol(10, default="INFO")
    read_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created()


@rls
class RefCounter(Base, TenantMixin):
    __tablename__ = "ref_counters"
    __table_args__ = (UniqueConstraint("tenant_id", "name"),)
    id: Mapped[uuid.UUID] = pk()
    name: Mapped[str] = mapped_column(String(40))
    value: Mapped[int] = mapped_column(BigInteger, default=0)
