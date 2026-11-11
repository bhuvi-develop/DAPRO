"""Case management service (FR-CAS-01..04, FR-FLD-06/07, BR-08, BR-11)."""
import hashlib
import os
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select

from app.common.clock import business_today
from app.common.notify import notify
from app.common.pagination import paginate
from app.common.policy import get_policy
from app.common.refs import next_ref
from app.core.config import get_settings
from app.core.errors import BusinessError, Forbidden, InvalidTransition, NotFound, ValidationFailed, VersionMismatch
from app.core.scope import case_clause, loan_clause, student_clause
from app.models.iam import Role, User, UserRole
from app.models.loans import LoanAccount, RepaymentTransaction
from app.models.ops import Case, CaseEvent, CaseFollowUp, Evidence, PaymentCommitment
from app.models.students import Student
from app.modules.cases.machine import RESOLUTION_TYPES, TRANSITIONS

NO_CONTACT = ("NO_ANSWER", "WRONG_NUMBER", "MESSAGE_LEFT", "UNREACHABLE")
CONTACT = ("CONTACT_ESTABLISHED", "BORROWER_UPDATE_RECEIVED", "CALLBACK_REQUESTED", "DISPUTE_RAISED")
CHANNELS = ("PHONE", "EMAIL", "SMS", "VISIT", "IN_PERSON", "LETTER")
CATEGORIES = ("REPAYMENT_FOLLOW_UP", "CONTACT_UPDATE", "DATA_QUALITY", "ADDRESS_VERIFICATION",
              "GRIEVANCE_FOLLOW_UP", "MORATORIUM_ENGAGEMENT")
PRIORITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
ALLOWED_MIME = {"application/pdf": b"%PDF", "image/png": b"\x89PNG", "image/jpeg": b"\xff\xd8"}


def event(ctx, case, etype, summary, frm=None, to=None, data=None):
    ctx.db.add(CaseEvent(tenant_id=case.tenant_id, case_id=case.id, event_type=etype, from_status=frm,
                         to_status=to, summary=summary, data=data or {}, actor_id=ctx.user_id))


def get_case(ctx, case_id) -> Case:
    c = ctx.db.execute(select(Case).where(Case.id == case_id, case_clause(ctx))).scalar()
    if c is None:
        raise NotFound("Case")
    return c


def user_name(db, uid):
    if not uid:
        return None
    u = db.get(User, uid)
    return {"id": str(u.id), "name": u.full_name} if u else None


def user_perms(db, uid) -> set[str]:
    perms = set()
    for r in db.execute(select(Role).join(UserRole, UserRole.role_id == Role.id)
                        .where(UserRole.user_id == uid)).scalars():
        perms.update(r.permissions)
    return perms


def create_case(ctx, *, student_id, loan_id=None, category, reason, priority="MEDIUM", due_on=None,
                next_action=None, owner_id=None, source="MANUAL", source_ref=None) -> Case:
    db = ctx.db
    if category not in CATEGORIES or priority not in PRIORITIES:
        raise ValidationFailed("Unknown category or priority.", [{"field": "category", "message": "Invalid value"}])
    s = db.execute(select(Student).where(Student.id == student_id, student_clause(ctx))).scalar()
    if s is None:
        raise NotFound("Student")
    loan = None
    if loan_id:
        loan = db.execute(select(LoanAccount).where(LoanAccount.id == loan_id, loan_clause(ctx))).scalar()
        if loan is None or loan.student_id != s.id:
            raise ValidationFailed("The loan does not belong to this student or is outside your scope.",
                                   [{"field": "loan_id", "message": "Invalid loan"}])
    if due_on is None:
        days = get_policy(db, "CASE_DEFAULTS")["value"].get("due_days", {}).get(priority, 10)
        due_on = business_today() + timedelta(days=int(days))
    c = Case(tenant_id=ctx.tenant_id, case_ref=next_ref(db, ctx.tenant_id, "case", "CASE"), student_id=s.id,
             loan_id=loan.id if loan else None,
             bank_org_id=loan.bank_org_id if loan else (ctx.org_id if ctx.is_bank else None),
             college_org_id=s.college_org_id, category=category, reason=reason, source=source,
             source_ref=source_ref, priority=priority, status="NEW", due_on=due_on,
             next_action=next_action or "Assign an owner and review bank data", opened_by=ctx.user_id)
    db.add(c)
    db.flush()
    event(ctx, c, "CREATED", f"Case opened: {reason}", to="NEW", data={"source": source, "source_ref": source_ref})
    ctx.audit("case.created", target_type="case", target_id=c.id, target_label=c.case_ref,
              payload={"category": category, "priority": priority, "source": source})
    if owner_id:
        assign(ctx, c, owner_id, commit=False)
    return c


SORTS = {"created_at": Case.created_at, "due_on": Case.due_on, "updated_at": Case.updated_at,
         "case_ref": Case.case_ref, "status": Case.status}


def list_cases(ctx, *, status=None, priority=None, owner=None, category=None, overdue=None, q=None,
               page=1, size=25, sort=None):
    stmt = select(Case, Student).join(Student, Student.id == Case.student_id).where(case_clause(ctx))
    if status == "open":
        stmt = stmt.where(Case.status.notin_(["RESOLVED", "CLOSED"]))
    elif status:
        stmt = stmt.where(Case.status.in_(status.split(",")))
    if priority:
        stmt = stmt.where(Case.priority.in_(priority.split(",")))
    if owner == "me":
        stmt = stmt.where(Case.owner_id == ctx.user_id)
    elif owner == "unassigned":
        stmt = stmt.where(Case.owner_id.is_(None))
    elif owner:
        stmt = stmt.where(Case.owner_id == owner)
    if category:
        stmt = stmt.where(Case.category == category)
    if overdue:
        stmt = stmt.where(Case.due_on < business_today(), Case.status.notin_(["RESOLVED", "CLOSED"]))
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Case.case_ref.ilike(like), Student.full_name.ilike(like), Student.dapro_ref.ilike(like)))
    if sort and sort.lstrip("-") in SORTS:
        col = SORTS[sort.lstrip("-")]
        stmt = stmt.order_by(col.desc().nullslast() if sort.startswith("-") else col.asc().nullslast())
    else:
        stmt = stmt.order_by(func.array_position(list(PRIORITIES), Case.priority), Case.due_on.asc().nullslast())
    rows, total, page, size = paginate(ctx.db, stmt, page, size, scalars=False)
    return [summary(ctx, c, s) for c, s in rows], total, page, size


def summary(ctx, c: Case, s: Student) -> dict:
    loan = ctx.db.get(LoanAccount, c.loan_id) if c.loan_id else None
    return {"id": str(c.id), "case_ref": c.case_ref, "status": c.status, "priority": c.priority,
            "category": c.category, "reason": c.reason, "source": c.source, "due_on": c.due_on,
            "overdue": bool(c.due_on and c.due_on < business_today() and c.status not in ("RESOLVED", "CLOSED")),
            "next_action": c.next_action, "owner": (own := user_name(ctx.db, c.owner_id)),
            "owner_id": str(c.owner_id) if c.owner_id else None, "owner_name": own["name"] if own else None,
            "student_name": s.full_name, "dapro_ref": s.dapro_ref, "student_id": str(s.id),
            "bank_loan_ref": loan.bank_loan_ref if loan else None,
            "student": {"id": str(s.id), "name": s.full_name, "dapro_ref": s.dapro_ref},
            "loan": {"id": str(loan.id), "bank_loan_ref": loan.bank_loan_ref, "repayment_status": loan.repayment_status,
                     "dpd": loan.dpd, "sync_state": loan.sync_state} if loan else None,
            "version": c.version, "created_at": c.created_at, "updated_at": c.updated_at}


def assign(ctx, c: Case, owner_id, commit=True) -> Case:
    ctx.require("case:assign", "assigning cases")
    owner = ctx.db.get(User, owner_id)
    if owner is None or owner.status != "ACTIVE" or owner.tenant_id != ctx.tenant_id:
        raise ValidationFailed("Owner must be an active user.", [{"field": "owner_id", "message": "Invalid user"}])
    allowed_org = c.bank_org_id or ctx.org_id
    if owner.org_id != allowed_org or "case:read" not in user_perms(ctx.db, owner.id):
        raise ValidationFailed("Owner must belong to the case organization and be able to work cases.",
                               [{"field": "owner_id", "message": "Outside scope"}],
                               "Choose a follow-up officer or field officer from your organization.")
    prev_owner, prev = c.owner_id, c.status
    c.owner_id = owner.id
    if c.status == "NEW":
        c.status = "ASSIGNED"
    c.version += 1
    event(ctx, c, "ASSIGNED", f"Assigned to {owner.full_name}", prev, c.status,
          {"from_owner": str(prev_owner) if prev_owner else None, "to_owner": str(owner.id)})
    ctx.audit("case.assigned", target_type="case", target_id=c.id, target_label=c.case_ref,
              payload={"owner_id": str(owner.id)})
    notify(ctx.db, ctx.tenant_id, owner.id, "CASE_ASSIGNED", f"Case {c.case_ref} assigned to you",
           c.next_action, f"/cases/{c.id}", "INFO")
    if commit:
        ctx.commit()
    return c


def patch(ctx, c: Case, version: int | None, priority=None, due_on=None, next_action=None) -> Case:
    if version is not None and version != c.version:
        raise VersionMismatch()
    if c.status in ("RESOLVED", "CLOSED"):
        raise InvalidTransition("Resolved or closed cases cannot be edited.", "Reopen the case first.")
    changes = {}
    if priority and priority != c.priority:
        if priority not in PRIORITIES:
            raise ValidationFailed("Unknown priority.", [{"field": "priority", "message": "Invalid"}])
        changes["priority"] = [c.priority, priority]
        c.priority = priority
    if due_on and due_on != c.due_on:
        changes["due_on"] = [str(c.due_on), str(due_on)]
        c.due_on = due_on
    if next_action is not None and next_action.strip() and next_action != c.next_action:
        changes["next_action"] = [c.next_action, next_action]
        c.next_action = next_action
    if changes:
        c.version += 1
        event(ctx, c, "UPDATED", "Updated " + ", ".join(changes), data=changes)
        ctx.audit("case.updated", target_type="case", target_id=c.id, target_label=c.case_ref, payload=changes)
    ctx.commit()
    return c


def followup_count(db, case_id) -> int:
    return db.execute(select(func.count()).where(CaseFollowUp.case_id == case_id)).scalar()


def _bank_txn(db, c: Case, ref: str | None):
    if not ref or not c.loan_id:
        return None
    return db.execute(select(RepaymentTransaction).where(RepaymentTransaction.loan_id == c.loan_id,
                                                         RepaymentTransaction.bank_txn_ref == ref.strip(),
                                                         RepaymentTransaction.kind == "PAYMENT")).scalar()


def transition(ctx, c: Case, to: str, note: str | None = None, resolution_type: str | None = None,
               bank_txn_ref: str | None = None) -> Case:
    key = (c.status, to)
    if key not in TRANSITIONS:
        raise InvalidTransition(f"A case cannot move from {c.status} to {to}.",
                                "Use one of the allowed transitions shown on the case.")
    perm = TRANSITIONS[key][0]
    if not ctx.can(perm):
        raise Forbidden(f"Moving a case to {to} requires {perm}.")
    if ctx.is_field_officer and to in ("RESOLVED", "CLOSED"):
        raise Forbidden("Field officers cannot resolve or close cases.", "Ask your manager to review the case.")
    evidence = {}
    if to == "ESCALATED" and followup_count(ctx.db, c.id) == 0:
        raise BusinessError("EVIDENCE_REQUIRED", "A case must show recorded follow-up before it can be escalated.",
                            "Record the contact attempts or visit first.", 409)
    if to in ("ESCALATED", "CLOSED") and not (note and note.strip()):
        raise ValidationFailed("Add a note explaining this step.", [{"field": "note", "message": "Required"}])
    if to == "RESOLVED":
        if resolution_type not in RESOLUTION_TYPES:
            raise ValidationFailed("Choose a resolution type.", [{"field": "resolution_type", "message": "Required"}])
        if resolution_type == "PAYMENT_CONFIRMED":
            txn = _bank_txn(ctx.db, c, bank_txn_ref)
            if txn is None:
                raise BusinessError("BANK_CONFIRMATION_REQUIRED",
                                    "A case can be resolved as paid only with a bank-confirmed transaction.",
                                    "Enter the bank transaction reference received in the bank feed. "
                                    "A borrower commitment is not a payment.", 409)
            evidence = {"bank_txn_ref": txn.bank_txn_ref, "amount": str(txn.amount),
                        "posted_on": txn.posted_on.isoformat(), "source": txn.source_system}
        if not (note and note.strip()):
            raise ValidationFailed("Add a resolution note.", [{"field": "note", "message": "Required"}])
    if to == "CLOSED":
        mc = get_policy(ctx.db, "MAKER_CHECKER")["value"]
        if mc.get("case_closure_review", True) and c.priority in ("HIGH", "CRITICAL") and c.owner_id == ctx.user_id:
            raise BusinessError("SOD_CONFLICT", "The owner of a HIGH or CRITICAL case cannot close it.",
                                "Ask another manager to review and close the case.", 409)
    prev = c.status
    c.status = to
    c.version += 1
    now = datetime.now(UTC)
    if to == "RESOLVED":
        c.resolution_type, c.resolution_notes, c.resolution_evidence, c.resolved_at = (
            resolution_type, note, evidence, now)
        c.next_action = "Review resolution and close"
    elif to == "CLOSED":
        c.closed_at, c.closed_by, c.next_action = now, ctx.user_id, None
    elif to == "ASSIGNED" and prev == "RESOLVED":
        c.resolution_type = c.resolved_at = None
        c.next_action = note or "Reopened: review the case"
    event(ctx, c, "STATUS_CHANGED", note or f"{prev} to {to}", prev, to,
          {"resolution_type": resolution_type, **evidence})
    ctx.audit("case.transition", target_type="case", target_id=c.id, target_label=c.case_ref,
              payload={"from": prev, "to": to, "resolution_type": resolution_type, **evidence})
    if to == "ESCALATED":
        for uid in ctx.db.execute(select(User.id).join(UserRole, UserRole.user_id == User.id)
                                  .join(Role, Role.id == UserRole.role_id)
                                  .where(User.org_id == c.bank_org_id, Role.code == "COLLECTIONS_MANAGER")).scalars():
            notify(ctx.db, ctx.tenant_id, uid, "CASE_ESCALATED", f"Case {c.case_ref} escalated", note,
                   f"/cases/{c.id}", "WARNING")
    ctx.commit()
    return c


def add_follow_up(ctx, c: Case, channel, outcome, notes, contacted_at=None, next_follow_up_on=None):
    if c.status in ("RESOLVED", "CLOSED"):
        raise InvalidTransition("This case is no longer active.", "Reopen the case to record follow-up.")
    if channel not in CHANNELS or outcome not in NO_CONTACT + CONTACT:
        raise ValidationFailed("Unknown channel or outcome.", [{"field": "outcome", "message": "Invalid value"}])
    f = CaseFollowUp(tenant_id=c.tenant_id, case_id=c.id, channel=channel, outcome=outcome, notes=notes,
                     contacted_at=contacted_at or datetime.now(UTC), next_follow_up_on=next_follow_up_on,
                     actor_id=ctx.user_id)
    ctx.db.add(f)
    prev = c.status
    if c.status in ("ASSIGNED", "CONTACT_ATTEMPTED", "NEW") and c.owner_id:
        c.status = "CONTACT_ESTABLISHED" if outcome in CONTACT else "CONTACT_ATTEMPTED"
    if next_follow_up_on:
        c.next_action = f"Follow up by {channel.lower()} on {next_follow_up_on.isoformat()}"
    c.version += 1
    event(ctx, c, "FOLLOW_UP", f"{channel} - {outcome.replace('_', ' ').lower()}", prev,
          c.status if c.status != prev else None, {"channel": channel, "outcome": outcome})
    ctx.audit("case.follow_up", target_type="case", target_id=c.id, target_label=c.case_ref,
              payload={"channel": channel, "outcome": outcome})
    ctx.commit()
    return f


def add_evidence(ctx, c: Case, *, title, kind, description, file_name, mime, content: bytes, visit_id=None):
    s = get_settings()
    if mime not in ALLOWED_MIME or not content.startswith(ALLOWED_MIME[mime]):
        raise ValidationFailed("Only PDF, PNG or JPEG files are accepted, and the content must match the type.",
                               [{"field": "file", "message": "Unsupported file"}])
    if len(content) > s.max_upload_mb * 1024 * 1024:
        raise ValidationFailed(f"File exceeds {s.max_upload_mb} MB.", [{"field": "file", "message": "Too large"}])
    digest = hashlib.sha256(content).hexdigest()
    folder = os.path.join(s.storage_dir, str(ctx.tenant_id), "evidence")
    os.makedirs(folder, exist_ok=True)
    key = os.path.join(str(ctx.tenant_id), "evidence", digest)
    with open(os.path.join(s.storage_dir, key), "wb") as fh:
        fh.write(content)
    ev = Evidence(tenant_id=c.tenant_id, case_id=c.id, visit_id=visit_id, kind=kind or "DOCUMENT", title=title,
                  description=description, file_name=os.path.basename(file_name or "upload")[:120], mime_type=mime,
                  size_bytes=len(content), sha256=digest, storage_key=key,
                  evidence_quality="OFFICER_OBSERVATION" if ctx.is_field_officer else "STAFF_UPLOADED",
                  uploaded_by=ctx.user_id)
    ctx.db.add(ev)
    ctx.db.flush()
    event(ctx, c, "EVIDENCE_ADDED", f"Evidence added: {title}", data={"evidence_id": str(ev.id), "sha256": digest})
    ctx.audit("case.evidence_added", target_type="case", target_id=c.id, target_label=c.case_ref,
              payload={"evidence_id": str(ev.id), "sha256": digest, "size": len(content)})
    ctx.commit()
    return ev


def add_commitment(ctx, c: Case, amount: Decimal, promised_date: date, notes=None, visit_id=None):
    if amount <= 0:
        raise ValidationFailed("Amount must be positive.", [{"field": "amount", "message": "Must be > 0"}])
    if promised_date < business_today():
        raise ValidationFailed("Promised date cannot be in the past.", [{"field": "promised_date", "message": "Past"}])
    pc = PaymentCommitment(tenant_id=c.tenant_id, case_id=c.id, loan_id=c.loan_id, visit_id=visit_id, amount=amount,
                           promised_date=promised_date, source="BORROWER_REPORTED", status="OPEN", notes=notes,
                           recorded_by=ctx.user_id)
    ctx.db.add(pc)
    ctx.db.flush()
    event(ctx, c, "COMMITMENT", f"Borrower-reported commitment of INR {amount:.2f} by {promised_date} (not a payment)",
          data={"commitment_id": str(pc.id)})
    ctx.audit("case.commitment_recorded", target_type="case", target_id=c.id, target_label=c.case_ref,
              payload={"amount": f"{amount:.2f}", "promised_date": promised_date.isoformat()})
    ctx.commit()
    return pc


def confirm_commitment(ctx, pc: PaymentCommitment, bank_txn_ref: str):
    c = get_case(ctx, pc.case_id)
    txn = _bank_txn(ctx.db, c, bank_txn_ref)
    if txn is None:
        raise BusinessError("BANK_CONFIRMATION_REQUIRED", "No bank-confirmed payment with this reference exists "
                            "for the loan.", "Wait for the bank feed to include the payment, then retry.", 409)
    pc.status, pc.bank_txn_ref = "BANK_CONFIRMED", txn.bank_txn_ref
    event(ctx, c, "COMMITMENT", f"Commitment matched to bank transaction {txn.bank_txn_ref}",
          data={"commitment_id": str(pc.id), "bank_txn_ref": txn.bank_txn_ref})
    ctx.audit("case.commitment_confirmed", target_type="case", target_id=c.id, target_label=c.case_ref,
              payload={"bank_txn_ref": txn.bank_txn_ref})
    ctx.commit()
    return pc


def mark_disputed(ctx, c: Case, grievance_ref: str) -> None:
    if c.status in ("RESOLVED", "CLOSED", "DISPUTED"):
        return
    c.previous_status, prev = c.status, c.status
    c.status = "DISPUTED"
    c.version += 1
    event(ctx, c, "DISPUTED", f"Dispute raised ({grievance_ref}); outreach paused", prev, "DISPUTED",
          {"grievance_ref": grievance_ref})
    ctx.audit("case.disputed", target_type="case", target_id=c.id, target_label=c.case_ref,
              payload={"grievance_ref": grievance_ref})


def restore_from_dispute(ctx, c: Case, grievance_ref: str) -> None:
    if c.status != "DISPUTED":
        return
    to = c.previous_status or "ASSIGNED"
    c.status, c.previous_status = to, None
    c.version += 1
    event(ctx, c, "DISPUTE_RESOLVED", f"Dispute {grievance_ref} resolved; case resumed", "DISPUTED", to,
          {"grievance_ref": grievance_ref})
    ctx.audit("case.dispute_resolved", target_type="case", target_id=c.id, target_label=c.case_ref,
              payload={"grievance_ref": grievance_ref})


def detail(ctx, c: Case) -> dict:
    from app.core import masking
    from app.models.engagement import Grievance
    from app.models.ops import FieldVisit, RiskIndicator
    from app.modules.cases.machine import allowed

    db = ctx.db
    s = db.get(Student, c.student_id)
    out = summary(ctx, c, s)
    loan = db.get(LoanAccount, c.loan_id) if c.loan_id else None
    if loan:
        out["loan"].update({"bank_status": loan.bank_status, "overdue_amount": masking.money(ctx, loan.overdue_amount),
                            "last_synced_at": loan.last_synced_at, "source": loan.source_system,
                            "dpd_bucket": loan.dpd_bucket})
    out["student"].update({"mobile": masking.contact(ctx, "MOBILE", s.primary_mobile),
                           "email": masking.contact(ctx, "EMAIL", s.primary_email),
                           "lifecycle_status": s.lifecycle_status})
    out.update({
        "previous_status": c.previous_status, "resolution_type": c.resolution_type,
        "resolution_notes": c.resolution_notes, "resolution_evidence": c.resolution_evidence,
        "resolved_at": c.resolved_at, "closed_at": c.closed_at, "opened_by": user_name(db, c.opened_by),
        "source_ref": c.source_ref,
        "timeline": [{"id": str(e.id), "type": e.event_type, "summary": e.summary, "from": e.from_status,
                      "to": e.to_status, "data": e.data, "actor": user_name(db, e.actor_id), "at": e.created_at}
                     for e in db.execute(select(CaseEvent).where(CaseEvent.case_id == c.id)
                                         .order_by(CaseEvent.created_at.desc())).scalars()],
        "follow_ups": [{"id": str(f.id), "channel": f.channel, "outcome": f.outcome, "notes": f.notes,
                        "contacted_at": f.contacted_at, "next_follow_up_on": f.next_follow_up_on,
                        "actor": user_name(db, f.actor_id)}
                       for f in db.execute(select(CaseFollowUp).where(CaseFollowUp.case_id == c.id)
                                           .order_by(CaseFollowUp.contacted_at.desc())).scalars()],
        "evidence": [{"id": str(e.id), "kind": e.kind, "title": e.title, "file_name": e.file_name,
                      "mime_type": e.mime_type, "size_bytes": e.size_bytes, "sha256": e.sha256,
                      "evidence_quality": e.evidence_quality, "uploaded_by": user_name(db, e.uploaded_by),
                      "created_at": e.created_at}
                     for e in db.execute(select(Evidence).where(Evidence.case_id == c.id)
                                         .order_by(Evidence.created_at.desc())).scalars()],
        "commitments": [{"id": str(p.id), "amount": f"{p.amount:.2f}", "promised_date": p.promised_date,
                         "source": p.source, "status": p.status, "bank_txn_ref": p.bank_txn_ref, "notes": p.notes,
                         "is_payment": False, "recorded_by": user_name(db, p.recorded_by), "created_at": p.created_at}
                        for p in db.execute(select(PaymentCommitment).where(PaymentCommitment.case_id == c.id)
                                            .order_by(PaymentCommitment.created_at.desc())).scalars()],
        "visits": [{"id": str(v.id), "status": v.status, "purpose": v.purpose, "scheduled_for": v.scheduled_for,
                    "visited_at": v.visited_at, "outcome": v.outcome, "review_status": v.review_status,
                    "safety_incident": v.safety_incident, "officer": user_name(db, v.officer_id)}
                   for v in db.execute(select(FieldVisit).where(FieldVisit.case_id == c.id)
                                       .order_by(FieldVisit.created_at.desc())).scalars()],
        "indicators": [{"id": str(i.id), "rule_code": i.rule_code, "rule_version": i.rule_version, "title": i.title,
                        "severity": i.severity, "status": i.status, "generated_at": i.generated_at}
                       for i in db.execute(select(RiskIndicator).where(
                           (RiskIndicator.case_id == c.id) | ((RiskIndicator.student_id == c.student_id)
                                                               & RiskIndicator.status.in_(["OPEN", "IN_REVIEW"])))
                           .order_by(RiskIndicator.generated_at.desc())).scalars()],
        "grievances": [{"id": str(g.id), "ref": g.ref, "category": g.category, "status": g.status,
                        "subject": g.subject}
                       for g in db.execute(select(Grievance).where(Grievance.case_id == c.id)).scalars()],
        "allowed_transitions": allowed(ctx, c, followup_count(db, c.id)),
        "resolution_types": RESOLUTION_TYPES,
        "can": {"assign": ctx.can("case:assign"), "update": ctx.can("case:update"),
                "record_visit": ctx.can("visit:record") and c.owner_id == ctx.user_id,
                "follow_up": ctx.can("case:update") and c.status not in ("RESOLVED", "CLOSED")},
    })
    return out
