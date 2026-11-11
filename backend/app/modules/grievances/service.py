"""Grievance and correction workflow (FR-GRV-01..03, FR-STU-09, BR-14, UC-33, US-05)."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import or_, select

from app.common.clock import business_today
from app.common.notify import notify
from app.common.pagination import paginate
from app.common.policy import get_policy
from app.common.refs import next_ref
from app.core.errors import BusinessError, InvalidTransition, NotFound, ValidationFailed
from app.core.scope import student_clause
from app.models.engagement import Grievance, GrievanceEvent
from app.models.iam import User
from app.models.loans import LoanAccount
from app.models.ops import Case
from app.models.students import Student, StudentFieldChange
from app.modules.cases import service as cases

CATEGORIES = ("DATA_CORRECTION", "AMOUNT_DISPUTE", "ADDRESS_DISPUTE", "CONDUCT_COMPLAINT",
              "COMMUNICATION_COMPLAINT", "OTHER")
CORRECTABLE = ("primary_email", "primary_mobile", "first_name", "last_name", "dob")
OPEN = ("SUBMITTED", "ACKNOWLEDGED", "UNDER_REVIEW", "AWAITING_INFORMATION")
TRANSITIONS = {("SUBMITTED", "ACKNOWLEDGED"), ("ACKNOWLEDGED", "UNDER_REVIEW"), ("SUBMITTED", "UNDER_REVIEW"),
               ("UNDER_REVIEW", "AWAITING_INFORMATION"), ("AWAITING_INFORMATION", "UNDER_REVIEW"),
               ("UNDER_REVIEW", "RESOLVED"), ("RESOLVED", "CLOSED")} | {(s, "REJECTED") for s in OPEN}


def _event(ctx, g, etype, message, visibility="BORROWER", frm=None, to=None):
    ctx.db.add(GrievanceEvent(tenant_id=g.tenant_id, grievance_id=g.id, event_type=etype, visibility=visibility,
                              message=message, from_status=frm, to_status=to, actor_id=ctx.user_id))


def _student(ctx, student_id) -> Student:
    if ctx.is_borrower:
        if str(student_id) != str(ctx.student_id):
            raise NotFound("Student")
        return ctx.db.get(Student, ctx.student_id)
    s = ctx.db.execute(select(Student).where(Student.id == student_id, student_clause(ctx))).scalar()
    if s is None:
        raise NotFound("Student")
    return s


def create(ctx, *, student_id, category, subject, description, loan_id=None, case_id=None, channel="STAFF",
           subject_user_id=None, correction_field=None, correction_requested_value=None, priority="MEDIUM"):
    db = ctx.db
    s = _student(ctx, student_id)
    if category not in CATEGORIES:
        raise ValidationFailed("Unknown category.", [{"field": "category", "message": "Invalid"}])
    if category == "DATA_CORRECTION" and (correction_field not in CORRECTABLE or not correction_requested_value):
        raise ValidationFailed("Say which field should be corrected and the correct value.",
                               [{"field": "correction_field", "message": "One of " + ", ".join(CORRECTABLE)}])
    loan = db.get(LoanAccount, loan_id) if loan_id else None
    if loan is not None and loan.student_id != s.id:
        raise ValidationFailed("The loan does not belong to this borrower.", [{"field": "loan_id", "message": "Invalid"}])
    case = None
    if case_id and not ctx.is_borrower:
        case = cases.get_case(ctx, case_id)
        if case.student_id != s.id:
            raise ValidationFailed("The case belongs to another borrower.", [{"field": "case_id", "message": "Invalid"}])
    if case is None and category in ("AMOUNT_DISPUTE", "ADDRESS_DISPUTE"):
        stmt = select(Case).where(Case.student_id == s.id, Case.status.notin_(["RESOLVED", "CLOSED"]))
        if loan is not None:
            stmt = stmt.where(Case.loan_id == loan.id)
        case = db.execute(stmt.order_by(Case.created_at.desc()).limit(1)).scalar()
    sla = int(get_policy(db, "GRIEVANCE_SLA")["value"].get("days", 15))
    owning = loan.bank_org_id if loan else (case.bank_org_id if case and case.bank_org_id else s.college_org_id)
    g = Grievance(tenant_id=ctx.tenant_id, ref=next_ref(db, ctx.tenant_id, "grievance", "GRV"), student_id=s.id,
                  loan_id=loan.id if loan else (case.loan_id if case else None), case_id=case.id if case else None,
                  category=category, subject=subject, description=description,
                  channel="PORTAL" if ctx.is_borrower else channel, submitted_by_user_id=ctx.user_id,
                  subject_user_id=subject_user_id, owning_org_id=owning, status="SUBMITTED", priority=priority,
                  due_on=business_today() + timedelta(days=sla), correction_field=correction_field,
                  correction_requested_value=correction_requested_value)
    db.add(g)
    db.flush()
    _event(ctx, g, "SUBMITTED", f"Request received: {subject}", to="SUBMITTED")
    if case is not None:
        cases.mark_disputed(ctx, case, g.ref)
    ctx.audit("grievance.submitted", target_type="grievance", target_id=g.id, target_label=g.ref,
              payload={"category": category, "channel": g.channel, "case_id": str(case.id) if case else None})
    try:
        from app.modules.comms.service import send
        send(ctx, student_id=s.id, template_code="GRIEVANCE_ACK", now=getattr(ctx, "clock", None),
             variables={"ref": g.ref, "due_date": g.due_on.isoformat()}, commit=False)
    except BusinessError:
        pass
    ctx.commit()
    return g


def get(ctx, gid) -> Grievance:
    g = ctx.db.get(Grievance, gid)
    if g is None:
        raise NotFound("Grievance")
    if ctx.is_borrower:
        if g.student_id != ctx.student_id:
            raise NotFound("Grievance")
    elif not ctx.db.execute(select(Student.id).where(Student.id == g.student_id, student_clause(ctx))).scalar():
        raise NotFound("Grievance")
    return g


def _name(db, uid):
    u = db.get(User, uid) if uid else None
    return u.full_name if u else None


def out(ctx, g: Grievance, s: Student | None = None, full=False) -> dict:
    s = s or ctx.db.get(Student, g.student_id)
    d = {"id": str(g.id), "ref": g.ref, "category": g.category, "subject": g.subject, "status": g.status,
         "priority": g.priority, "channel": g.channel, "due_on": g.due_on,
         "overdue": bool(g.due_on and g.due_on < business_today() and g.status in OPEN),
         "student_id": str(s.id), "student_name": s.full_name, "dapro_ref": s.dapro_ref,
         "owner_id": str(g.owner_id) if g.owner_id else None, "owner_name": _name(ctx.db, g.owner_id),
         "case_id": str(g.case_id) if g.case_id else None, "loan_id": str(g.loan_id) if g.loan_id else None,
         "created_at": g.created_at, "updated_at": g.updated_at, "resolved_at": g.resolved_at}
    if full:
        vis = ["BORROWER"] if ctx.is_borrower else ["BORROWER", "INTERNAL"]
        case = ctx.db.get(Case, g.case_id) if g.case_id else None
        d.update({"description": g.description, "resolution": g.resolution, "closed_at": g.closed_at,
                  "correction_field": g.correction_field,
                  "correction_requested_value": g.correction_requested_value,
                  "case_ref": case.case_ref if case else None, "case_status": case.status if case else None,
                  "events": [{"id": str(e.id), "type": e.event_type, "visibility": e.visibility, "message": e.message,
                              "from": e.from_status, "to": e.to_status,
                              "actor_name": _name(ctx.db, e.actor_id) if not ctx.is_borrower else None,
                              "at": e.created_at}
                             for e in ctx.db.execute(select(GrievanceEvent).where(
                                 GrievanceEvent.grievance_id == g.id, GrievanceEvent.visibility.in_(vis))
                                 .order_by(GrievanceEvent.created_at)).scalars()]})
        if not ctx.is_borrower:
            d["subject_user_name"] = _name(ctx.db, g.subject_user_id)
            d["subject_user_id"] = str(g.subject_user_id) if g.subject_user_id else None
            d["allowed_transitions"] = [to for (frm, to) in sorted(TRANSITIONS) if frm == g.status]
    return d


def list_grievances(ctx, *, status=None, category=None, owner_id=None, q=None, page=1, size=25, sort=None):
    stmt = select(Grievance, Student).join(Student, Student.id == Grievance.student_id)
    stmt = stmt.where(Grievance.student_id == ctx.student_id) if ctx.is_borrower else stmt.where(student_clause(ctx))
    if status == "open":
        stmt = stmt.where(Grievance.status.in_(OPEN))
    elif status:
        stmt = stmt.where(Grievance.status.in_(status.split(",")))
    if category:
        stmt = stmt.where(Grievance.category == category)
    if owner_id == "me":
        stmt = stmt.where(Grievance.owner_id == ctx.user_id)
    elif owner_id:
        stmt = stmt.where(Grievance.owner_id == owner_id)
    if q:
        stmt = stmt.where(or_(Grievance.ref.ilike(f"%{q}%"), Student.full_name.ilike(f"%{q}%")))
    col = {"due_on": Grievance.due_on, "created_at": Grievance.created_at}.get((sort or "").lstrip("-"),
                                                                              Grievance.created_at)
    stmt = stmt.order_by(col.asc() if sort and not sort.startswith("-") else col.desc())
    rows, total, page, size = paginate(ctx.db, stmt, page, size, scalars=False)
    return [out(ctx, g, s) for g, s in rows], total, page, size


def _no_conflict(ctx, g: Grievance, user_id) -> None:
    if g.subject_user_id and str(g.subject_user_id) == str(user_id):
        raise BusinessError("CONFLICT_OF_INTEREST", "The person this grievance is about cannot handle it.",
                            "Assign a different reviewer (FR-GRV-03).", 409)


def assign(ctx, g: Grievance, owner_id) -> Grievance:
    from app.modules.cases.service import user_perms

    _no_conflict(ctx, g, owner_id)
    _no_conflict(ctx, g, ctx.user_id)
    u = ctx.db.get(User, owner_id)
    if u is None or u.status != "ACTIVE" or u.tenant_id != ctx.tenant_id or "grievance:manage" not in user_perms(ctx.db, u.id):
        raise ValidationFailed("Owner must be an active user who can manage grievances.",
                               [{"field": "owner_id", "message": "Invalid owner"}])
    if g.status not in OPEN:
        raise InvalidTransition("Only open grievances can be reassigned.")
    g.owner_id = u.id
    g.version += 1
    _event(ctx, g, "ASSIGNED", f"Assigned to {u.full_name}", "INTERNAL")
    ctx.audit("grievance.assigned", target_type="grievance", target_id=g.id, target_label=g.ref,
              payload={"owner_id": str(u.id)})
    notify(ctx.db, ctx.tenant_id, u.id, "GRIEVANCE_ASSIGNED", f"Grievance {g.ref} assigned to you", g.subject,
           f"/grievances/{g.id}", "INFO")
    ctx.commit()
    return g


def respond(ctx, g: Grievance, message: str, visibility: str = "BORROWER") -> Grievance:
    _no_conflict(ctx, g, ctx.user_id)
    if visibility not in ("BORROWER", "INTERNAL"):
        raise ValidationFailed("Visibility must be BORROWER or INTERNAL.", [{"field": "visibility", "message": "Invalid"}])
    if not message or len(message.strip()) < 3:
        raise ValidationFailed("Write a response.", [{"field": "message", "message": "Required"}])
    _event(ctx, g, "RESPONSE" if visibility == "BORROWER" else "INTERNAL_NOTE", message.strip(), visibility)
    g.version += 1
    ctx.audit("grievance.responded", target_type="grievance", target_id=g.id, target_label=g.ref,
              payload={"visibility": visibility})
    ctx.commit()
    return g


def transition(ctx, g: Grievance, to: str, reason: str | None = None, approve_correction: bool = False) -> Grievance:
    _no_conflict(ctx, g, ctx.user_id)
    if (g.status, to) not in TRANSITIONS:
        raise InvalidTransition(f"A grievance cannot move from {g.status} to {to}.",
                                "Use one of the allowed transitions shown on the grievance.")
    if to in ("RESOLVED", "REJECTED") and not (reason and len(reason.strip()) >= 5):
        raise ValidationFailed("Explain the outcome to the borrower.", [{"field": "reason", "message": "Required"}])
    prev = g.status
    now = datetime.now(UTC)
    if to == "RESOLVED":
        g.resolution, g.resolved_at = reason.strip(), now
        if g.category == "DATA_CORRECTION" and approve_correction:
            _apply_correction(ctx, g)
        if g.case_id:
            case = ctx.db.get(Case, g.case_id)
            if case is not None:
                cases.restore_from_dispute(ctx, case, g.ref)
    if to == "REJECTED":
        g.resolution = reason.strip()
        if g.case_id:
            case = ctx.db.get(Case, g.case_id)
            if case is not None:
                cases.restore_from_dispute(ctx, case, g.ref)
    if to == "CLOSED":
        g.closed_at = now
    g.status = to
    g.version += 1
    _event(ctx, g, "STATUS_CHANGED", reason or f"Status changed to {to.replace('_', ' ').lower()}", "BORROWER", prev, to)
    ctx.audit("grievance.transition", target_type="grievance", target_id=g.id, target_label=g.ref,
              payload={"from": prev, "to": to, "correction_applied": bool(approve_correction)})
    ctx.commit()
    return g


def _apply_correction(ctx, g: Grievance) -> None:
    from datetime import date

    s = ctx.db.get(Student, g.student_id)
    field = g.correction_field
    old = getattr(s, field)
    new = g.correction_requested_value
    value = date.fromisoformat(new) if field == "dob" else new
    ctx.db.add(StudentFieldChange(tenant_id=s.tenant_id, student_id=s.id, field=field,
                                  old_value=None if old is None else str(old), new_value=str(value),
                                  reason=f"Borrower correction request {g.ref}", source="BORROWER_REPORTED",
                                  actor_id=g.submitted_by_user_id, approved_by=ctx.user_id))
    setattr(s, field, value)
    if field in ("first_name", "last_name"):
        s.full_name = f"{s.first_name} {s.last_name}"
        s.name_norm = " ".join(sorted(s.full_name.upper().replace(".", " ").split()))
    s.version += 1
    ctx.audit("student.corrected", target_type="student", target_id=s.id, target_label=s.dapro_ref,
              payload={"field": field, "via": g.ref})
