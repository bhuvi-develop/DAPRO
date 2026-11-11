"""Communications with consent, preference, quiet-hour, frequency and lawful-basis checks (FR-COM-01..04,
FR-REP-09, BR-13, FR-GUA-06, INT-MSG-01). Every refusal is stored as BLOCKED with its reason."""
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, or_, select

from app.common.pagination import paginate
from app.common.policy import get_policy
from app.core import masking
from app.core.config import get_settings
from app.core.errors import BusinessError, Forbidden, InvalidTransition, NotFound, ValidationFailed
from app.core.ids import uuid7
from app.core.scope import student_clause
from app.models.engagement import Communication, Grievance, NotificationTemplate
from app.models.iam import Organization, User
from app.models.loans import Guarantor, LoanAccount
from app.models.students import Consent, ContactPreference, Student

PURPOSES = ("REMINDER", "UPDATE_REQUEST", "GRIEVANCE_ACK", "GUARANTOR_NOTICE", "GENERAL")
OPEN_GRV = ("SUBMITTED", "ACKNOWLEDGED", "UNDER_REVIEW", "AWAITING_INFORMATION")


def approved_template(db, code: str) -> NotificationTemplate | None:
    return db.execute(select(NotificationTemplate).where(NotificationTemplate.code == code,
                                                         NotificationTemplate.status == "APPROVED")
                      .order_by(NotificationTemplate.version.desc()).limit(1)).scalar()


def _in_quiet(now_local: time, start: time, end: time) -> bool:
    return (now_local >= start or now_local < end) if start > end else (start <= now_local < end)


def _hm(v: str) -> time:
    h, m = v.split(":")
    return time(int(h), int(m))


def has_consent(db, student_id, purpose: str, now) -> bool:
    return bool(db.execute(select(func.count()).where(
        Consent.student_id == student_id, Consent.purposes.any(purpose), Consent.withdrawn_at.is_(None),
        Consent.valid_from <= now, or_(Consent.valid_to.is_(None), Consent.valid_to > now))).scalar())


def _render(text: str | None, values: dict) -> str | None:
    if text is None:
        return None
    d = defaultdict(lambda: "-", {k: str(v) for k, v in values.items()})
    return text.format_map(d)


def _values(db, s: Student, extra: dict | None) -> dict:
    loan = db.execute(select(LoanAccount).where(LoanAccount.student_id == s.id, LoanAccount.link_status == "LINKED")
                      .order_by(LoanAccount.next_due_date.asc().nullslast()).limit(1)).scalar()
    bank = db.get(Organization, loan.bank_org_id).name if loan else "your bank"
    v = {"name": s.first_name, "bank": bank,
         "amount": f"{loan.next_due_amount:.2f}" if loan and loan.next_due_amount else "-",
         "due_date": loan.next_due_date.isoformat() if loan and loan.next_due_date else "-"}
    v.update(extra or {})
    return v


def send(ctx, *, student_id, template_code, channel=None, case_id=None, recipient_type="BORROWER",
         guarantor_id=None, variables=None, now=None, commit=True) -> Communication:
    db = ctx.db
    now = now or datetime.now(UTC)
    s = db.execute(select(Student).where(Student.id == student_id, student_clause(ctx))).scalar()
    if s is None:
        raise NotFound("Student")
    tpl = approved_template(db, template_code)
    comm = Communication(id=uuid7(), tenant_id=ctx.tenant_id, student_id=s.id, case_id=case_id,
                         guarantor_id=guarantor_id, recipient_type=recipient_type, template_code=template_code,
                         channel=channel or (tpl.channel if tpl else "EMAIL"),
                         purpose=tpl.purpose if tpl else "GENERAL", created_by=ctx.user_id, created_at=now)
    if tpl:
        comm.template_id, comm.template_version = tpl.id, tpl.version
    block = _check(ctx, s, tpl, comm, now)
    recipient = None
    if not block:
        recipient, block = _recipient(db, s, comm)
    mode = get_settings().email_mode if comm.channel == "EMAIL" else get_settings().sms_mode
    if not block and mode == "disabled":
        block = "CHANNEL_DISABLED: no provider is configured for this channel"
    if recipient:
        comm.recipient_masked = masking.mask_email(recipient) if comm.channel == "EMAIL" else masking.mask_mobile(recipient)
    if tpl:
        vals = _values(db, s, variables)
        comm.rendered_subject, comm.rendered_body = _render(tpl.subject, vals), _render(tpl.body, vals)
    comm.provider = "MOCK_EMAIL" if comm.channel == "EMAIL" else "MOCK_SMS"
    comm.provider_mode = "MOCK"
    comm.status = "BLOCKED" if block else "QUEUED"
    comm.block_reason = block
    db.add(comm)
    db.flush()
    ctx.audit("comm.blocked" if block else "comm.queued", target_type="communication", target_id=comm.id,
              target_label=template_code, outcome="DENIED" if block else "SUCCESS",
              payload={"student": s.dapro_ref, "channel": comm.channel, "purpose": comm.purpose,
                       "recipient_type": recipient_type, "block_reason": block})
    if commit:
        ctx.commit()
    return comm


def _check(ctx, s: Student, tpl, comm: Communication, now) -> str | None:
    db = ctx.db
    if tpl is None:
        return "TEMPLATE_NOT_APPROVED: no approved version of this template exists"
    if comm.channel != tpl.channel:
        return f"CHANNEL_MISMATCH: template is for {tpl.channel}"
    if comm.recipient_type == "GUARANTOR":
        if not ctx.can("comm:guarantor"):
            raise Forbidden("Guarantor communication requires comm:guarantor.")
        g = db.get(Guarantor, comm.guarantor_id) if comm.guarantor_id else None
        loan = db.get(LoanAccount, g.loan_id) if g else None
        if g is None or loan is None or loan.student_id != s.id:
            raise ValidationFailed("Guarantor does not belong to this borrower.",
                                   [{"field": "guarantor_id", "message": "Invalid"}])
        if tpl.purpose != "GUARANTOR_NOTICE":
            return "GUARANTOR_TEMPLATE_REQUIRED: only an approved guarantor notice template may be used"
        if not g.communication_permitted:
            return "NO_LAWFUL_BASIS: the executed agreement does not permit guarantor communication (BR-13)"
        return None
    purpose = "FOLLOW_UP" if comm.case_id else "ENGAGEMENT"
    if not has_consent(db, s.id, purpose, now) and not (purpose == "FOLLOW_UP" and has_consent(db, s.id, "ENGAGEMENT", now)):
        return f"NO_ACTIVE_CONSENT: no active consent or lawful basis covers {purpose}"
    pref = db.execute(select(ContactPreference).where(ContactPreference.student_id == s.id,
                                                      ContactPreference.channel == comm.channel)).scalar()
    if pref is not None and not pref.allowed:
        return f"CHANNEL_NOT_PERMITTED: borrower has opted out of {comm.channel}"
    window = get_policy(db, "COMMUNICATION_WINDOW")["value"]
    tz = ZoneInfo(pref.timezone if pref else "Asia/Kolkata")
    start = pref.quiet_start if pref else _hm(window.get("quiet_start", "21:00"))
    end = pref.quiet_end if pref else _hm(window.get("quiet_end", "08:00"))
    local = now.astimezone(tz)
    ack = tpl.purpose == "GRIEVANCE_ACK" and comm.channel == "EMAIL"  # reply to the borrower request itself
    if not ack and _in_quiet(local.time(), start, end):
        return f"QUIET_HOURS: {local.strftime('%H:%M')} {tz.key} is inside quiet hours; retry after {end.strftime('%H:%M')}"
    cap = int(window.get("max_per_week", 3))
    sent = db.execute(select(func.count()).where(Communication.student_id == s.id,
                                                 Communication.recipient_type == "BORROWER",
                                                 Communication.status.in_(["QUEUED", "SENT", "DELIVERED"]),
                                                 Communication.created_at >= now - timedelta(days=7))).scalar()
    if sent >= cap:
        return f"FREQUENCY_CAP: {sent} messages in the last 7 days (cap {cap})"
    if tpl.purpose == "REMINDER":
        disputed = db.execute(select(func.count()).where(Grievance.student_id == s.id,
                                                         Grievance.category == "AMOUNT_DISPUTE",
                                                         Grievance.status.in_(OPEN_GRV))).scalar()
        if disputed:
            return "DISPUTE_PAUSE: reminders are paused while an amount dispute is open"
    return None


def _recipient(db, s: Student, comm: Communication):
    if comm.recipient_type == "GUARANTOR":
        g = db.get(Guarantor, comm.guarantor_id)
        r = g.email if comm.channel == "EMAIL" else g.mobile
    else:
        r = s.primary_email if comm.channel == "EMAIL" else s.primary_mobile
    return (r, None) if r else (None, f"NO_RECIPIENT: no {comm.channel.lower()} contact on record")


def dispatch(db, limit: int = 500) -> dict:
    """MOCK provider: QUEUED -> SENT -> DELIVERED, or FAILED for .invalid recipients. Delivery is not receipt."""
    now = datetime.now(UTC)
    stats = {"sent": 0, "delivered": 0, "failed": 0}
    for c in db.execute(select(Communication).where(Communication.status == "QUEUED")
                        .order_by(Communication.created_at).limit(limit)).scalars():
        c.provider_message_id = f"mock-{uuid7().hex[:16]}"
        c.sent_at = now
        if (c.recipient_masked or "").endswith(".invalid"):
            c.status, c.error = "FAILED", "MOCK provider: recipient domain does not accept mail"
            stats["failed"] += 1
        else:
            c.status, c.delivered_at = "DELIVERED", now
            stats["sent"] += 1
            stats["delivered"] += 1
    db.flush()
    return stats


def _name(db, uid):
    u = db.get(User, uid) if uid else None
    return u.full_name if u else None


def comm_out(db, c: Communication, s: Student | None = None) -> dict:
    s = s or db.get(Student, c.student_id)
    return {"id": str(c.id), "student_id": str(c.student_id), "student_name": s.full_name, "dapro_ref": s.dapro_ref,
            "case_id": str(c.case_id) if c.case_id else None, "recipient_type": c.recipient_type,
            "template_code": c.template_code, "template_version": c.template_version, "channel": c.channel,
            "recipient_masked": c.recipient_masked, "purpose": c.purpose, "status": c.status,
            "block_reason": c.block_reason, "provider": c.provider, "provider_mode": c.provider_mode,
            "provider_message_id": c.provider_message_id, "error": c.error, "subject": c.rendered_subject,
            "body": c.rendered_body, "created_by_name": _name(db, c.created_by), "created_at": c.created_at,
            "sent_at": c.sent_at, "delivered_at": c.delivered_at,
            "delivery_note": "Delivery status from a MOCK provider; delivery is not proof of receipt or action."}


def list_comms(ctx, *, status=None, channel=None, purpose=None, student_id=None, case_id=None, q=None,
               page=1, size=25, sort=None):
    stmt = select(Communication, Student).join(Student, Student.id == Communication.student_id).where(
        student_clause(ctx))
    if status:
        stmt = stmt.where(Communication.status.in_(status.split(",")))
    if channel:
        stmt = stmt.where(Communication.channel == channel)
    if purpose:
        stmt = stmt.where(Communication.purpose == purpose)
    if student_id:
        stmt = stmt.where(Communication.student_id == student_id)
    if case_id:
        stmt = stmt.where(Communication.case_id == case_id)
    if q:
        stmt = stmt.where(or_(Student.full_name.ilike(f"%{q}%"), Student.dapro_ref.ilike(f"%{q}%")))
    order = Communication.created_at.asc() if sort == "created_at" else Communication.created_at.desc()
    rows, total, page, size = paginate(ctx.db, stmt.order_by(order), page, size, scalars=False)
    return [comm_out(ctx.db, c, s) for c, s in rows], total, page, size


def tpl_out(db, t: NotificationTemplate) -> dict:
    return {"id": str(t.id), "code": t.code, "version": t.version, "name": t.name, "channel": t.channel,
            "purpose": t.purpose, "language": t.language, "subject": t.subject, "body": t.body, "status": t.status,
            "approval_label": t.approval_label, "org_id": str(t.org_id) if t.org_id else None,
            "created_by_name": _name(db, t.created_by), "approved_by_name": _name(db, t.approved_by),
            "approved_at": t.approved_at, "created_at": t.created_at}


def templates(ctx) -> list[dict]:
    rows = ctx.db.execute(select(NotificationTemplate).order_by(NotificationTemplate.code,
                                                                NotificationTemplate.version.desc())).scalars()
    return [tpl_out(ctx.db, t) for t in rows]


def create_template(ctx, *, code, name, channel, purpose, subject, body, language="en", shared=False):
    if channel not in ("EMAIL", "SMS") or purpose not in PURPOSES:
        raise ValidationFailed("Unknown channel or purpose.", [{"field": "purpose", "message": "Invalid"}])
    if channel == "EMAIL" and not subject:
        raise ValidationFailed("Email templates need a subject.", [{"field": "subject", "message": "Required"}])
    code = code.strip().upper().replace(" ", "_")
    ver = (ctx.db.execute(select(func.max(NotificationTemplate.version)).where(
        NotificationTemplate.code == code)).scalar() or 0) + 1
    t = NotificationTemplate(tenant_id=ctx.tenant_id, org_id=None if shared else ctx.org_id, code=code, version=ver,
                             name=name, channel=channel, purpose=purpose, language=language, subject=subject,
                             body=body, status="DRAFT", approval_label="PENDING_APPROVAL", created_by=ctx.user_id)
    ctx.db.add(t)
    ctx.db.flush()
    ctx.audit("template.created", target_type="template", target_id=t.id, target_label=f"{code} v{ver}")
    ctx.commit()
    return t


def approve_template(ctx, t: NotificationTemplate):
    if t.status != "DRAFT":
        raise InvalidTransition("Only DRAFT templates can be approved.")
    if t.created_by == ctx.user_id:
        raise BusinessError("SOD_CONFLICT", "You authored this template version, so you cannot approve it.",
                            "Ask another template approver to review it.", 409)
    if t.org_id and t.org_id != ctx.org_id:
        raise Forbidden("This template belongs to another organization.")
    for old in ctx.db.execute(select(NotificationTemplate).where(NotificationTemplate.code == t.code,
                                                                 NotificationTemplate.status == "APPROVED")).scalars():
        old.status = "RETIRED"
    t.status, t.approved_by, t.approved_at = "APPROVED", ctx.user_id, datetime.now(UTC)
    t.approval_label = "APPROVED_IN_DAPRO"
    ctx.audit("template.approved", target_type="template", target_id=t.id, target_label=f"{t.code} v{t.version}")
    ctx.commit()
    return t
