"""Field operations (FR-FLD-01..08, BR-09). No location capture until OD-14 is approved."""
from datetime import UTC, datetime

from sqlalchemy import select

from app.common.clock import business_today
from app.common.notify import notify
from app.core import masking
from app.core.config import get_settings
from app.core.errors import Forbidden, InvalidTransition, NotFound, ValidationFailed, VersionMismatch
from app.core.scope import case_clause
from app.models.iam import Role, User, UserRole
from app.models.loans import LoanAccount
from app.models.ops import Case, FieldVisit
from app.models.students import Student, StudentAddress
from app.modules.cases import service as cases

OUTCOMES = ("ATTEMPTED", "COMPLETED", "NO_CONTACT", "ADDRESS_NOT_FOUND", "BORROWER_UNAVAILABLE",
            "RESCHEDULE_REQUESTED")
FOLLOW_UP_OUTCOME = {"COMPLETED": "CONTACT_ESTABLISHED", "RESCHEDULE_REQUESTED": "CALLBACK_REQUESTED"}


def _address(db, student_id):
    rows = db.execute(select(StudentAddress).where(StudentAddress.student_id == student_id,
                                                   StudentAddress.is_current.is_(True))).scalars().all()
    a = next((r for r in rows if r.kind == "CURRENT"), None) or next(iter(rows), None)
    if not a:
        return None
    return {"id": str(a.id), "kind": a.kind, "text": ", ".join(x for x in [a.line1, a.line2, a.city, a.state,
                                                                            a.postal_code, a.country] if x),
            "verification": a.verification, "source": a.source_type}


def my_cases(ctx) -> list[dict]:
    rows = ctx.db.execute(select(Case, Student).join(Student, Student.id == Case.student_id)
                          .where(Case.owner_id == ctx.user_id, Case.status.notin_(["RESOLVED", "CLOSED"]))
                          .order_by(Case.due_on.asc().nullslast())).all()
    out = []
    for c, s in rows:
        loan = ctx.db.get(LoanAccount, c.loan_id) if c.loan_id else None
        nxt = ctx.db.execute(select(FieldVisit).where(FieldVisit.case_id == c.id,
                                                      FieldVisit.status.in_(["SCHEDULED", "DRAFT"]))
                             .order_by(FieldVisit.scheduled_for.asc().nullslast()).limit(1)).scalar()
        out.append({"case_id": str(c.id), "case_ref": c.case_ref, "status": c.status, "priority": c.priority,
                    "due_on": c.due_on, "overdue": bool(c.due_on and c.due_on < business_today()),
                    "next_action": c.next_action, "student": {"id": str(s.id), "name": s.full_name,
                                                              "dapro_ref": s.dapro_ref,
                                                              "mobile": masking.mask_mobile(s.primary_mobile)},
                    "address": _address(ctx.db, s.id),
                    "loan": {"bank_loan_ref": loan.bank_loan_ref, "repayment_status": loan.repayment_status,
                             "dpd": loan.dpd, "sync_state": loan.sync_state} if loan else None,
                    "next_visit": {"id": str(nxt.id), "status": nxt.status, "scheduled_for": nxt.scheduled_for}
                    if nxt else None})
    return out


def visit_out(db, v: FieldVisit) -> dict:
    return {"id": str(v.id), "case_id": str(v.case_id), "status": v.status, "purpose": v.purpose,
            "scheduled_for": v.scheduled_for, "check_in_at": v.check_in_at, "check_out_at": v.check_out_at,
            "visited_at": v.visited_at, "outcome": v.outcome, "notes": v.notes, "borrower_present": v.borrower_present,
            "safety_incident": v.safety_incident, "incident_notes": v.incident_notes,
            "location_captured": False, "evidence_quality": "OFFICER_OBSERVATION",
            "review_status": v.review_status, "review_notes": v.review_notes,
            "reviewer": cases.user_name(db, v.reviewer_id), "reviewed_at": v.reviewed_at,
            "officer": cases.user_name(db, v.officer_id), "client_draft_id": v.client_draft_id, "version": v.version}


def _own_case(ctx, case_id) -> Case:
    c = cases.get_case(ctx, case_id)
    if c.owner_id != ctx.user_id:
        raise Forbidden("Only the assigned officer can record a visit for this case.",
                        "Ask your manager to assign the case to you.")
    if c.status in ("RESOLVED", "CLOSED"):
        raise InvalidTransition("This case is no longer active.")
    return c


def get_visit(ctx, visit_id) -> FieldVisit:
    v = ctx.db.execute(select(FieldVisit).join(Case, Case.id == FieldVisit.case_id)
                       .where(FieldVisit.id == visit_id, case_clause(ctx))).scalar()
    if v is None:
        raise NotFound("Visit")
    return v


def _own_visit(ctx, visit_id, editable=True) -> FieldVisit:
    v = get_visit(ctx, visit_id)
    if v.officer_id != ctx.user_id:
        raise Forbidden("Only the visiting officer can change this visit.")
    if editable and v.status not in ("DRAFT", "SCHEDULED"):
        raise InvalidTransition(f"A {v.status} visit cannot be changed.")
    return v


def create_visit(ctx, case_id, purpose, scheduled_for=None, draft=False, client_draft_id=None) -> FieldVisit:
    if client_draft_id:
        existing = ctx.db.execute(select(FieldVisit).where(FieldVisit.client_draft_id == client_draft_id)).scalar()
        if existing:
            return existing
    c = _own_case(ctx, case_id)
    v = FieldVisit(tenant_id=ctx.tenant_id, case_id=c.id, officer_id=ctx.user_id,
                   status="DRAFT" if draft else "SCHEDULED", purpose=purpose, scheduled_for=scheduled_for,
                   client_draft_id=client_draft_id)
    ctx.db.add(v)
    ctx.db.flush()
    cases.event(ctx, c, "VISIT_SCHEDULED", f"Visit {v.status.lower()}: {purpose}", data={"visit_id": str(v.id)})
    ctx.audit("visit.created", target_type="field_visit", target_id=v.id, target_label=c.case_ref)
    ctx.commit()
    return v


def save_draft(ctx, visit_id, version, **fields) -> FieldVisit:
    v = _own_visit(ctx, visit_id)
    if version is not None and version != v.version:
        raise VersionMismatch()
    for k, val in fields.items():
        if val is not None:
            if k == "outcome" and val not in OUTCOMES:
                raise ValidationFailed("Unknown outcome.", [{"field": "outcome", "message": "Invalid"}])
            setattr(v, k, val)
    v.version += 1
    ctx.commit()
    return v


def check(ctx, visit_id, which: str) -> FieldVisit:
    v = _own_visit(ctx, visit_id)
    now = datetime.now(UTC)
    if which == "in":
        if v.check_in_at:
            raise InvalidTransition("Already checked in.")
        v.check_in_at = now
    else:
        if not v.check_in_at:
            raise InvalidTransition("Check in before checking out.")
        v.check_out_at = now
    v.location_captured = False
    v.version += 1
    ctx.audit(f"visit.check_{which}", target_type="field_visit", target_id=v.id,
              payload={"location_captured": False, "reason": "Location capture disabled pending OD-14"})
    ctx.commit()
    return v


def settings_info() -> dict:
    return {"location_capture_enabled": get_settings().field_location_capture_enabled,
            "location_capture_note": "Disabled until OD-14 (purpose, consent and retention) is approved.",
            "offline_drafts": "Server-side drafts with idempotent client_draft_id; device storage pending decision."}


def submit(ctx, visit_id, outcome, notes, borrower_present=None, safety_incident=False, incident_notes=None,
           client_draft_id=None) -> FieldVisit:
    v = get_visit(ctx, visit_id)
    if v.status == "SUBMITTED" and client_draft_id and v.client_draft_id == client_draft_id:
        return v  # idempotent re-submit from a retried client
    v = _own_visit(ctx, visit_id)
    if outcome not in OUTCOMES:
        raise ValidationFailed("Choose a structured outcome.", [{"field": "outcome", "message": "Invalid"}])
    if not notes or len(notes.strip()) < 5:
        raise ValidationFailed("Add visit notes.", [{"field": "notes", "message": "Required"}])
    if safety_incident and not (incident_notes and incident_notes.strip()):
        raise ValidationFailed("Describe the safety incident.", [{"field": "incident_notes", "message": "Required"}])
    c = ctx.db.get(Case, v.case_id)
    now = datetime.now(UTC)
    v.outcome, v.notes, v.borrower_present = outcome, notes.strip(), borrower_present
    v.safety_incident, v.incident_notes = bool(safety_incident), incident_notes
    v.status, v.visited_at = "SUBMITTED", v.check_in_at or now
    if client_draft_id:
        v.client_draft_id = client_draft_id
    needs_review = bool(safety_incident) or c.status in ("ESCALATED", "DISPUTED") or c.priority == "CRITICAL"
    v.review_status = "PENDING" if needs_review else "NOT_REQUIRED"
    v.version += 1
    cases.event(ctx, c, "VISIT_SUBMITTED", "Visit outcome: " + outcome.replace("_", " ").lower(),
                data={"visit_id": str(v.id), "outcome": outcome, "review_status": v.review_status,
                      "evidence_quality": "OFFICER_OBSERVATION"})
    ctx.audit("visit.submitted", target_type="field_visit", target_id=v.id, target_label=c.case_ref,
              payload={"outcome": outcome, "safety_incident": bool(safety_incident), "review": v.review_status})
    if needs_review:
        for uid in ctx.db.execute(select(User.id).join(UserRole, UserRole.user_id == User.id)
                                  .join(Role, Role.id == UserRole.role_id)
                                  .where(User.org_id == ctx.org_id, Role.code == "COLLECTIONS_MANAGER")).scalars():
            notify(ctx.db, ctx.tenant_id, uid, "VISIT_REVIEW", f"Visit on {c.case_ref} needs review",
                   "Safety incident reported" if safety_incident else "Sensitive case visit",
                   "/field/review", "CRITICAL" if safety_incident else "WARNING")
    if c.status not in ("DISPUTED", "ESCALATED"):
        cases.add_follow_up(ctx, c, "VISIT", FOLLOW_UP_OUTCOME.get(outcome, "UNREACHABLE"), v.notes)
    ctx.commit()
    return v


def review_queue(ctx) -> list[dict]:
    rows = ctx.db.execute(select(FieldVisit, Case).join(Case, Case.id == FieldVisit.case_id)
                          .where(case_clause(ctx), FieldVisit.review_status == "PENDING")
                          .order_by(FieldVisit.visited_at.desc())).all()
    out = []
    for v, c in rows:
        d = visit_out(ctx.db, v)
        s = ctx.db.get(Student, c.student_id)
        d.update({"case_ref": c.case_ref, "case_status": c.status, "case_priority": c.priority,
                  "student_name": s.full_name, "dapro_ref": s.dapro_ref})
        out.append(d)
    return out


def review(ctx, visit_id, decision, notes) -> FieldVisit:
    v = get_visit(ctx, visit_id)
    if v.review_status != "PENDING":
        raise InvalidTransition("This visit is not awaiting review.")
    if v.officer_id == ctx.user_id:
        raise Forbidden("You cannot review your own visit report (segregation of duties).")
    if decision not in ("APPROVED", "RETURNED"):
        raise ValidationFailed("Decision must be APPROVED or RETURNED.", [{"field": "decision", "message": "Invalid"}])
    if not notes or len(notes.strip()) < 5:
        raise ValidationFailed("Add review notes.", [{"field": "notes", "message": "Required"}])
    v.review_status, v.reviewer_id, v.reviewed_at, v.review_notes = decision, ctx.user_id, datetime.now(UTC), notes
    if decision == "RETURNED":
        v.status = "DRAFT"
        notify(ctx.db, ctx.tenant_id, v.officer_id, "VISIT_RETURNED", "Visit report returned for changes", notes,
               f"/field/visits/{v.id}", "WARNING")
    v.version += 1
    c = ctx.db.get(Case, v.case_id)
    cases.event(ctx, c, "VISIT_REVIEWED", f"Supervisor {decision.lower()} visit report",
                data={"visit_id": str(v.id), "decision": decision})
    ctx.audit("visit.reviewed", target_type="field_visit", target_id=v.id, target_label=c.case_ref,
              payload={"decision": decision})
    ctx.commit()
    return v
