"""Student identity, contacts, addresses, academic and employment lifecycle (Modules 02 and 05)."""
import uuid
from datetime import date, datetime, time

from sqlalchemy import Boolean, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, created, fk, pk, rls, scol, text_array, updated


@rls
class Student(Base, TenantMixin):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("tenant_id", "dapro_ref"),
                      UniqueConstraint("tenant_id", "college_org_id", "college_student_id"))
    id: Mapped[uuid.UUID] = pk()
    dapro_ref: Mapped[str] = mapped_column(String(30))
    college_org_id: Mapped[uuid.UUID] = fk("organizations.id")
    campus_unit_id: Mapped[uuid.UUID | None] = fk("org_units.id", nullable=True)
    college_student_id: Mapped[str] = mapped_column(String(60))
    first_name: Mapped[str]
    last_name: Mapped[str]
    full_name: Mapped[str] = mapped_column(index=True)
    name_norm: Mapped[str] = mapped_column(index=True)
    dob: Mapped[date | None]
    gender: Mapped[str | None] = scol(20, nullable=True)
    kyc_ref_last4: Mapped[str | None] = scol(4, nullable=True)
    nationality: Mapped[str] = scol(2, default="IN")
    primary_email: Mapped[str | None]
    primary_mobile: Mapped[str | None]
    lifecycle_status: Mapped[str] = scol(20, default="STUDYING", index=True)
    record_status: Mapped[str] = scol(20, default="ACTIVE")
    verification_status: Mapped[str] = scol(20, default="UNVERIFIED")
    source: Mapped[str] = scol(30, default="STAFF_ENTERED")
    source_ref: Mapped[str | None]
    import_batch_id: Mapped[uuid.UUID | None]
    profile_completion: Mapped[int] = mapped_column(Integer, default=0)
    data_origin: Mapped[str] = scol(10, default="LIVE")
    merged_into_id: Mapped[uuid.UUID | None]
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()


@rls
class StudentFieldChange(Base, TenantMixin):
    """Correction history (FR-STU-08, BR-14): prior value, new value, actor and reason are retained."""
    __tablename__ = "student_field_changes"
    id: Mapped[uuid.UUID] = pk()
    student_id: Mapped[uuid.UUID] = fk("students.id")
    field: Mapped[str] = scol(60)
    old_value: Mapped[str | None]
    new_value: Mapped[str | None]
    reason: Mapped[str]
    source: Mapped[str] = scol(30, default="STAFF_ENTERED")
    actor_id: Mapped[uuid.UUID | None]
    approved_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class StudentContact(Base, TenantMixin):
    __tablename__ = "student_contacts"
    id: Mapped[uuid.UUID] = pk()
    student_id: Mapped[uuid.UUID] = fk("students.id")
    kind: Mapped[str] = scol(20)
    value: Mapped[str]
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = scol(30)
    verification: Mapped[str] = scol(20, default="UNVERIFIED")
    effective_from: Mapped[date | None]
    superseded_at: Mapped[datetime | None]
    created_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class StudentAddress(Base, TenantMixin):
    __tablename__ = "student_addresses"
    id: Mapped[uuid.UUID] = pk()
    student_id: Mapped[uuid.UUID] = fk("students.id")
    kind: Mapped[str] = scol(20)
    line1: Mapped[str]
    line2: Mapped[str | None]
    city: Mapped[str]
    district: Mapped[str | None]
    state: Mapped[str | None]
    postal_code: Mapped[str | None] = scol(12, nullable=True)
    country: Mapped[str] = scol(2, default="IN")
    source_type: Mapped[str] = scol(30)
    source_ref: Mapped[str | None]
    verification: Mapped[str] = scol(20, default="UNVERIFIED", index=True)
    verification_method: Mapped[str | None] = scol(30, nullable=True)
    verified_by: Mapped[uuid.UUID | None]
    verified_at: Mapped[datetime | None]
    effective_from: Mapped[date | None]
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    superseded_at: Mapped[datetime | None]
    superseded_by_id: Mapped[uuid.UUID | None]
    notes: Mapped[str | None]
    created_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class AddressVerification(Base, TenantMixin):
    __tablename__ = "address_verifications"
    id: Mapped[uuid.UUID] = pk()
    address_id: Mapped[uuid.UUID] = fk("student_addresses.id")
    student_id: Mapped[uuid.UUID] = fk("students.id")
    method: Mapped[str] = scol(30)
    status: Mapped[str] = scol(20, default="PENDING", index=True)
    requested_by: Mapped[uuid.UUID | None]
    assigned_to: Mapped[uuid.UUID | None]
    outcome_notes: Mapped[str | None]
    performed_by: Mapped[uuid.UUID | None]
    performed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = created()


@rls
class AcademicRecord(Base, TenantMixin):
    __tablename__ = "academic_records"
    id: Mapped[uuid.UUID] = pk()
    student_id: Mapped[uuid.UUID] = fk("students.id")
    college_org_id: Mapped[uuid.UUID] = fk("organizations.id")
    programme: Mapped[str]
    course: Mapped[str]
    specialization: Mapped[str | None]
    cohort_year: Mapped[int] = mapped_column(Integer)
    enrolment_status: Mapped[str] = scol(20)
    start_date: Mapped[date | None]
    expected_completion: Mapped[date | None]
    actual_completion: Mapped[date | None]
    source: Mapped[str] = scol(30, default="COLLEGE_PROVIDED")
    verification: Mapped[str] = scol(20, default="VERIFIED")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    superseded_at: Mapped[datetime | None]
    recorded_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class EmploymentRecord(Base, TenantMixin):
    """Post-study status history (FR-EMP-02..07). No income field: OD-10 is unresolved."""
    __tablename__ = "employment_records"
    id: Mapped[uuid.UUID] = pk()
    student_id: Mapped[uuid.UUID] = fk("students.id")
    status: Mapped[str] = scol(20)
    employer_name: Mapped[str | None]
    job_title: Mapped[str | None]
    sector: Mapped[str | None]
    city: Mapped[str | None]
    country: Mapped[str | None] = scol(2, nullable=True)
    source: Mapped[str] = scol(30)
    verification: Mapped[str] = scol(20, default="UNVERIFIED")
    verified_by: Mapped[uuid.UUID | None]
    verified_at: Mapped[datetime | None]
    reported_on: Mapped[date]
    effective_from: Mapped[date | None]
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)
    superseded_at: Mapped[datetime | None]
    notes: Mapped[str | None]
    recorded_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class DuplicateCandidate(Base, TenantMixin):
    __tablename__ = "duplicate_candidates"
    id: Mapped[uuid.UUID] = pk()
    student_id: Mapped[uuid.UUID] = fk("students.id")
    candidate_student_id: Mapped[uuid.UUID] = fk("students.id")
    match_fields: Mapped[list[str]] = text_array()
    score: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = scol(30, default="OPEN", index=True)
    reviewed_by: Mapped[uuid.UUID | None]
    reviewed_at: Mapped[datetime | None]
    notes: Mapped[str | None]
    created_at: Mapped[datetime] = created()


@rls
class Consent(Base, TenantMixin):
    __tablename__ = "consents"
    id: Mapped[uuid.UUID] = pk()
    student_id: Mapped[uuid.UUID] = fk("students.id")
    basis: Mapped[str] = scol(30)
    purposes: Mapped[list[str]] = text_array()
    notice_version: Mapped[str] = scol(30)
    source: Mapped[str] = scol(30)
    valid_from: Mapped[datetime]
    valid_to: Mapped[datetime | None]
    withdrawn_at: Mapped[datetime | None]
    recorded_by: Mapped[uuid.UUID | None]
    created_at: Mapped[datetime] = created()


@rls
class ContactPreference(Base, TenantMixin):
    __tablename__ = "contact_preferences"
    __table_args__ = (UniqueConstraint("student_id", "channel"),)
    id: Mapped[uuid.UUID] = pk()
    student_id: Mapped[uuid.UUID] = fk("students.id")
    channel: Mapped[str] = scol(10)
    allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    quiet_start: Mapped[time] = mapped_column(Time, default=time(21, 0))
    quiet_end: Mapped[time] = mapped_column(Time, default=time(8, 0))
    timezone: Mapped[str] = scol(40, default="Asia/Kolkata")
    language: Mapped[str] = scol(10, default="en")
    updated_by: Mapped[uuid.UUID | None]
    updated_at: Mapped[datetime] = updated()
