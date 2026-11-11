"""Profile completion: share of client-approved material fields present (FR-STU-02, FR-STU-06)."""
from sqlalchemy import func, select

from app.models.students import AcademicRecord, EmploymentRecord, Student, StudentAddress, StudentContact

GRADUATE_STATES = {"GRADUATED", "EMPLOYED", "SELF_EMPLOYED", "UNEMPLOYED", "FURTHER_STUDY", "UNKNOWN"}


def completion_checks(db, s: Student) -> list[dict]:
    has = lambda stmt: bool(db.execute(stmt).scalar())  # noqa: E731
    checks = [
        {"key": "dob", "label": "Date of birth", "ok": s.dob is not None},
        {"key": "mobile", "label": "Mobile number", "ok": has(select(func.count()).where(
            StudentContact.student_id == s.id, StudentContact.kind == "MOBILE", StudentContact.superseded_at.is_(None)))},
        {"key": "email", "label": "Email address", "ok": has(select(func.count()).where(
            StudentContact.student_id == s.id, StudentContact.kind == "EMAIL", StudentContact.superseded_at.is_(None)))},
        {"key": "permanent_address", "label": "Permanent address", "ok": has(select(func.count()).where(
            StudentAddress.student_id == s.id, StudentAddress.kind == "PERMANENT", StudentAddress.is_current.is_(True)))},
        {"key": "verified_address", "label": "Verified address", "ok": has(select(func.count()).where(
            StudentAddress.student_id == s.id, StudentAddress.is_current.is_(True),
            StudentAddress.verification == "VERIFIED"))},
        {"key": "academic", "label": "Academic record", "ok": has(select(func.count()).where(
            AcademicRecord.student_id == s.id, AcademicRecord.is_current.is_(True)))},
        {"key": "kyc_ref", "label": "KYC reference (last 4)", "ok": bool(s.kyc_ref_last4)},
    ]
    if s.lifecycle_status in GRADUATE_STATES:
        checks.append({"key": "post_study", "label": "Post-study status", "ok": has(select(func.count()).where(
            EmploymentRecord.student_id == s.id, EmploymentRecord.is_current.is_(True)))})
    return checks


def recompute(db, s: Student) -> int:
    checks = completion_checks(db, s)
    s.profile_completion = round(100 * sum(c["ok"] for c in checks) / len(checks))
    return s.profile_completion
