"""Tenancy, organizations, users, roles, sessions (Module 01)."""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, created, fk, pk, rls, scol, text_array, updated


class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[uuid.UUID] = pk()
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str]
    status: Mapped[str] = scol(20, default="ACTIVE")
    environment_label: Mapped[str] = scol(20, default="DEMO")  # DEMO | UAT | LIVE
    created_at: Mapped[datetime] = created()


class Organization(Base, TenantMixin):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)
    id: Mapped[uuid.UUID] = pk()
    type: Mapped[str] = scol(20)  # PLATFORM | COLLEGE | BANK | NBFC | AGENCY
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str]
    legal_name: Mapped[str | None]
    status: Mapped[str] = scol(20, default="ACTIVE")
    city: Mapped[str | None]
    state: Mapped[str | None]
    contact_email: Mapped[str | None]
    settings: Mapped[dict] = mapped_column(default=dict, server_default="{}")
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class OrgUnit(Base, TenantMixin):
    __tablename__ = "org_units"
    __table_args__ = (UniqueConstraint("org_id", "code"),)
    id: Mapped[uuid.UUID] = pk()
    org_id: Mapped[uuid.UUID] = fk("organizations.id")
    parent_id: Mapped[uuid.UUID | None] = fk("org_units.id", nullable=True)
    kind: Mapped[str] = scol(20)  # CAMPUS | BRANCH | REGION | DEPARTMENT | TEAM
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str]
    city: Mapped[str | None]
    state: Mapped[str | None]
    status: Mapped[str] = scol(20, default="ACTIVE")
    created_at: Mapped[datetime] = created()


@rls
class SharingAgreement(Base, TenantMixin):
    __tablename__ = "sharing_agreements"
    id: Mapped[uuid.UUID] = pk()
    reference: Mapped[str]
    college_org_id: Mapped[uuid.UUID] = fk("organizations.id")
    bank_org_id: Mapped[uuid.UUID] = fk("organizations.id")
    purposes: Mapped[list[str]] = text_array()
    shared_fields: Mapped[list[str]] = text_array()
    status: Mapped[str] = scol(20, default="ACTIVE")
    effective_from: Mapped[date]
    effective_to: Mapped[date | None]
    approval_label: Mapped[str] = scol(30, default="DEMO_FIXTURE")
    notes: Mapped[str | None]
    created_at: Mapped[datetime] = created()


class Role(Base, TenantMixin):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)
    id: Mapped[uuid.UUID] = pk()
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str]
    description: Mapped[str | None]
    org_types: Mapped[list[str]] = text_array()
    permissions: Mapped[list[str]] = text_array()
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class User(Base, TenantMixin):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "email"),)
    id: Mapped[uuid.UUID] = pk()
    org_id: Mapped[uuid.UUID] = fk("organizations.id")
    org_unit_id: Mapped[uuid.UUID | None] = fk("org_units.id", nullable=True)
    student_id: Mapped[uuid.UUID | None] = fk("students.id", nullable=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    full_name: Mapped[str]
    title: Mapped[str | None]
    phone: Mapped[str | None]
    password_hash: Mapped[str | None]
    status: Mapped[str] = scol(20, default="INVITED")  # INVITED | ACTIVE | SUSPENDED | REVOKED
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[str | None]
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None]
    last_login_at: Mapped[datetime | None]
    timezone: Mapped[str] = scol(40, default="Asia/Kolkata")
    created_by: Mapped[uuid.UUID | None]
    activated_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
                                               primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id"), primary_key=True)


class UserInvitation(Base, TenantMixin):
    __tablename__ = "user_invitations"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = fk("users.id")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime]
    accepted_at: Mapped[datetime | None]
    created_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


class UserSession(Base, TenantMixin):
    __tablename__ = "user_sessions"
    id: Mapped[uuid.UUID] = pk()
    user_id: Mapped[uuid.UUID] = fk("users.id")
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    ip: Mapped[str | None]
    user_agent: Mapped[str | None]
    mfa_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = created()
    last_seen_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    revoked_reason: Mapped[str | None]
