"""Report query implementations. Each returns (columns, rows) using real stored data within caller scope."""
from datetime import UTC, datetime

from sqlalchemy import and_, func, select
from sqlalchemy.orm import aliased

from app.common.clock import business_today
from app.core import masking
from app.core.scope import case_clause, loan_clause, student_clause
from app.models.engagement import Grievance
from app.models.iam import Organization, User
from app.models.loans import Integration, LoanAccount, LoanSnapshot
from app.models.ops import Case, CaseFollowUp, FieldVisit, RiskIndicator, RiskReview
from app.models.platform import AuditEvent
from app.models.students import Student
from app.modules.audit.service import scope_clause as audit_scope


def iso(v):
    return v.isoformat() if v else None


def cols(*pairs):
    return [{"key": k, "label": label} for k, label in pairs]


def _scoped_loans(ctx, f):
    w = [loan_clause(ctx)]
    for k, c in (("bank_org_id", LoanAccount.bank_org_id), ("college_org_id", LoanAccount.college_org_id),
                 ("link_status", LoanAccount.link_status), ("repayment_status", LoanAccount.repayment_status),
                 ("dpd_bucket", LoanAccount.dpd_bucket)):
        if f.get(k):
            w.append(c == f.get(k))
    return and_(*w)


def _period(col, f):
    w = []
    if f.get("date_from"):
        w.append(col >= f.get("date_from"))
    if f.get("date_to"):
        w.append(col <= f.get("date_to"))
    return w


def portfolio_summary(ctx, f):
    bank, col = aliased(Organization), aliased(Organization)
    m = lambda v: masking.money(ctx, v)  # noqa: E731
    rows = ctx.db.execute(
        select(bank.name, col.name, func.count(), func.count().filter(LoanAccount.link_status == "LINKED"),
               func.count().filter(LoanAccount.repayment_status == "CURRENT"),
               func.count().filter(LoanAccount.repayment_status == "OVERDUE"),
               func.count().filter(LoanAccount.repayment_status == "UNKNOWN"),
               func.sum(LoanAccount.overdue_amount).filter(LoanAccount.sync_state == "CURRENT"))
        .join(bank, bank.id == LoanAccount.bank_org_id).outerjoin(col, col.id == LoanAccount.college_org_id)
        .where(_scoped_loans(ctx, f)).group_by(bank.name, col.name).order_by(bank.name, col.name)).all()
    return (cols(("bank", "Bank"), ("college", "College"), ("loans", "Loans"), ("linked", "Linked"),
                 ("current", "Current"), ("overdue", "Overdue"), ("unknown", "Unknown"), ("overdue_amount", "Overdue (INR)")),
            [dict(bank=b, college=c, loans=n, linked=lk, current=cu, overdue=o, unknown=u, overdue_amount=m(a))
             for b, c, n, lk, cu, o, u, a in rows])


def student_register(ctx, f):
    col = aliased(Organization)
    w = [student_clause(ctx), Student.record_status == "ACTIVE"] + _period(Student.created_at, f)
    if f.get("college_org_id"):
        w.append(Student.college_org_id == f.get("college_org_id"))
    if f.get("lifecycle_status"):
        w.append(Student.lifecycle_status == f.get("lifecycle_status"))
    rows = ctx.db.execute(select(Student, col.name).join(col, col.id == Student.college_org_id).where(*w)
                          .order_by(Student.dapro_ref)).all()
    return (cols(("dapro_ref", "DAPRO ID"), ("college_student_id", "College ID"), ("full_name", "Name"),
                 ("college", "College"), ("lifecycle_status", "Lifecycle"), ("profile_completion", "Completion %"),
                 ("verification_status", "Verification"), ("source", "Source"), ("created_at", "Registered")),
            [dict(dapro_ref=s.dapro_ref, college_student_id=s.college_student_id, full_name=s.full_name, college=c,
                  lifecycle_status=s.lifecycle_status, profile_completion=s.profile_completion,
                  verification_status=s.verification_status, source=s.source, created_at=iso(s.created_at))
             for s, c in rows])


def _loan_rows(ctx, f, extra_where=()):
    bank = aliased(Organization)
    return ctx.db.execute(select(LoanAccount, Student.full_name, Student.dapro_ref, bank.name)
                          .outerjoin(Student, Student.id == LoanAccount.student_id)
                          .join(bank, bank.id == LoanAccount.bank_org_id)
                          .where(_scoped_loans(ctx, f), *extra_where).order_by(LoanAccount.bank_loan_ref)).all()


def loan_linkage(ctx, f):
    rows = _loan_rows(ctx, f)
    return (cols(("bank_loan_ref", "Bank loan ref"), ("bank", "Bank"), ("student", "Student"), ("dapro_ref", "DAPRO ID"),
                 ("link_status", "Link status"), ("method", "Validation"), ("linked_at", "Linked at")),
            [dict(bank_loan_ref=lo.bank_loan_ref, bank=b, student=n, dapro_ref=d, link_status=lo.link_status,
                  method=(lo.link_validation or {}).get("method"), linked_at=iso(lo.linked_at)) for lo, n, d, b in rows])


def repayment_status(ctx, f):
    rows = _loan_rows(ctx, f, [LoanAccount.link_status == "LINKED"])
    fin = masking.financial_visible(ctx)
    return (cols(("bank_loan_ref", "Bank loan ref"), ("student", "Student"), ("bank", "Bank"),
                 ("repayment_status", "Status"), ("dpd", "DPD"), ("next_due_date", "Next due"),
                 ("next_due_amount", "Next due (INR)"), ("sync_state", "Sync"), ("as_of", "As of")),
            [dict(bank_loan_ref=lo.bank_loan_ref, student=n, bank=b, repayment_status=lo.repayment_status,
                  dpd=lo.dpd if fin else None, next_due_date=iso(lo.next_due_date),
                  next_due_amount=masking.money(ctx, lo.next_due_amount), sync_state=lo.sync_state,
                  as_of=iso(lo.last_synced_at)) for lo, n, d, b in rows])


def overdue_ageing(ctx, f):
    from app.common.policy import get_policy

    pol = get_policy(ctx.db, "DPD_BUCKETS")
    agg = {b: (n, a) for b, n, a in ctx.db.execute(
        select(LoanAccount.dpd_bucket, func.count(), func.sum(LoanAccount.overdue_amount))
        .where(_scoped_loans(ctx, f), LoanAccount.link_status == "LINKED", LoanAccount.repayment_status == "OVERDUE")
        .group_by(LoanAccount.dpd_bucket)).all()}
    return (cols(("bucket", "Bucket"), ("label", "Label"), ("range", "DPD range"), ("accounts", "Accounts"),
                 ("overdue_amount", "Overdue (INR)"), ("approval", "Definition status")),
            [dict(bucket=b["code"], label=b["label"], range=f"{b['min']}-{b['max'] if b['max'] is not None else '+'}",
                  accounts=agg.get(b["code"], (0, None))[0], overdue_amount=masking.money(ctx, agg.get(b["code"], (0, None))[1]),
                  approval=pol["approval_label"]) for b in pol["value"]["buckets"] if b["code"] != "CURRENT"])


def dpd_detail(ctx, f):
    snap = (select(LoanSnapshot.bank_dpd).where(LoanSnapshot.loan_id == LoanAccount.id)
            .order_by(LoanSnapshot.as_of.desc()).limit(1).scalar_subquery())
    bank = aliased(Organization)
    rows = ctx.db.execute(select(LoanAccount, Student.full_name, bank.name, snap)
                          .join(Student, Student.id == LoanAccount.student_id).join(bank, bank.id == LoanAccount.bank_org_id)
                          .where(_scoped_loans(ctx, f), LoanAccount.repayment_status == "OVERDUE")
                          .order_by(LoanAccount.dpd.desc())).all()
    return (cols(("bank_loan_ref", "Bank loan ref"), ("student", "Student"), ("bank", "Bank"), ("dpd", "DAPRO DPD"),
                 ("bank_dpd", "Bank DPD"), ("dpd_bucket", "Bucket"), ("overdue_amount", "Overdue (INR)"),
                 ("as_of", "As of")),
            [dict(bank_loan_ref=lo.bank_loan_ref, student=n, bank=b, dpd=lo.dpd, bank_dpd=bd, dpd_bucket=lo.dpd_bucket,
                  overdue_amount=masking.money(ctx, lo.overdue_amount), as_of=iso(lo.last_synced_at))
             for lo, n, b, bd in rows])


def data_freshness(ctx, f):
    now = datetime.now(UTC)
    rows = _loan_rows(ctx, f, [LoanAccount.link_status == "LINKED"])
    return (cols(("bank_loan_ref", "Bank loan ref"), ("bank", "Bank"), ("sync_state", "Sync state"),
                 ("last_synced_at", "Last synced"), ("age_hours", "Age (hours)"), ("source", "Source")),
            [dict(bank_loan_ref=lo.bank_loan_ref, bank=b, sync_state=lo.sync_state, last_synced_at=iso(lo.last_synced_at),
                  age_hours=round((now - lo.last_synced_at).total_seconds() / 3600, 1) if lo.last_synced_at else None,
                  source=lo.source_system) for lo, n, d, b in rows])


def case_ageing(ctx, f):
    today = business_today()
    w = [case_clause(ctx), ~Case.status.in_(["RESOLVED", "CLOSED"])]
    for k in ("priority", "status"):
        if f.get(k):
            w.append(getattr(Case, k) == f.get(k))
    rows = ctx.db.execute(select(Case, Student.full_name, User.full_name).join(Student, Student.id == Case.student_id)
                          .outerjoin(User, User.id == Case.owner_id).where(*w).order_by(Case.created_at)).all()
    return (cols(("case_ref", "Case"), ("student", "Student"), ("category", "Category"), ("priority", "Priority"),
                 ("status", "Status"), ("owner", "Owner"), ("age_days", "Age (days)"), ("due_on", "Due"),
                 ("overdue", "Past due")),
            [dict(case_ref=c.case_ref, student=n, category=c.category, priority=c.priority, status=c.status, owner=o,
                  age_days=(today - c.created_at.date()).days, due_on=iso(c.due_on),
                  overdue=bool(c.due_on and c.due_on < today)) for c, n, o in rows])


def followup_productivity(ctx, f):
    in_cases = select(Case.id).where(case_clause(ctx))
    fu = ctx.db.execute(select(CaseFollowUp.actor_id, func.count(),
                               func.count().filter(CaseFollowUp.outcome == "CONTACT_ESTABLISHED"))
                        .where(CaseFollowUp.case_id.in_(in_cases), *_period(CaseFollowUp.contacted_at, f))
                        .group_by(CaseFollowUp.actor_id)).all()
    vi = dict(ctx.db.execute(select(FieldVisit.officer_id, func.count()).where(
        FieldVisit.case_id.in_(in_cases), FieldVisit.status == "SUBMITTED", *_period(FieldVisit.created_at, f))
        .group_by(FieldVisit.officer_id)).all())
    ids = {a for a, _, _ in fu} | set(vi)
    names = {u.id: u.full_name for u in ctx.db.execute(select(User).where(User.id.in_(ids))).scalars()} if ids else {}
    fumap = {a: (n, e) for a, n, e in fu}
    return (cols(("officer", "Officer"), ("follow_ups", "Follow-ups"), ("contacts_established", "Contact established"),
                 ("visits", "Visits submitted")),
            [dict(officer=names.get(i, "Unknown"), follow_ups=fumap.get(i, (0, 0))[0],
                  contacts_established=fumap.get(i, (0, 0))[1], visits=vi.get(i, 0)) for i in ids])


def risk_review(ctx, f):
    w = [RiskIndicator.student_id.in_(select(Student.id).where(student_clause(ctx)))] + _period(RiskIndicator.generated_at, f)
    if f.get("status"):
        w.append(RiskIndicator.status == f.get("status"))
    last = (select(RiskReview.decision).where(RiskReview.indicator_id == RiskIndicator.id)
            .order_by(RiskReview.created_at.desc()).limit(1).scalar_subquery())
    rows = ctx.db.execute(select(RiskIndicator, Student.full_name, last).join(Student, Student.id == RiskIndicator.student_id)
                          .where(*w).order_by(RiskIndicator.generated_at.desc())).all()
    return (cols(("rule", "Rule"), ("rule_version", "Version"), ("category", "Category"), ("severity", "Severity"),
                 ("student", "Student"), ("status", "Status"), ("decision", "Latest decision"), ("generated_at", "Generated")),
            [dict(rule=i.rule_code, rule_version=i.rule_version, category=i.category, severity=i.severity, student=n,
                  status=i.status, decision=d, generated_at=iso(i.generated_at)) for i, n, d in rows])


def field_visits(ctx, f):
    rows = ctx.db.execute(select(FieldVisit, Case.case_ref, User.full_name).join(Case, Case.id == FieldVisit.case_id)
                          .join(User, User.id == FieldVisit.officer_id)
                          .where(case_clause(ctx), *_period(FieldVisit.created_at, f))
                          .order_by(FieldVisit.created_at.desc())).all()
    return (cols(("case_ref", "Case"), ("officer", "Officer"), ("status", "Status"), ("outcome", "Outcome"),
                 ("visited_at", "Visited"), ("review_status", "Review"), ("safety_incident", "Safety incident")),
            [dict(case_ref=r, officer=o, status=v.status, outcome=v.outcome, visited_at=iso(v.visited_at),
                  review_status=v.review_status, safety_incident=v.safety_incident) for v, r, o in rows])


def grievances(ctx, f):
    today = business_today()
    w = [Grievance.student_id.in_(select(Student.id).where(student_clause(ctx)))] + _period(Grievance.created_at, f)
    if f.get("status"):
        w.append(Grievance.status == f.get("status"))
    rows = ctx.db.execute(select(Grievance).where(*w).order_by(Grievance.created_at.desc())).scalars().all()
    open_ = lambda g: g.status not in ("RESOLVED", "REJECTED", "CLOSED")  # noqa: E731
    return (cols(("ref", "Reference"), ("category", "Category"), ("status", "Status"), ("priority", "Priority"),
                 ("created_at", "Submitted"), ("due_on", "Due"), ("resolved_at", "Resolved"), ("sla_breached", "SLA breached")),
            [dict(ref=g.ref, category=g.category, status=g.status, priority=g.priority, created_at=iso(g.created_at),
                  due_on=iso(g.due_on), resolved_at=iso(g.resolved_at),
                  sla_breached=bool(open_(g) and g.due_on and g.due_on < today)) for g in rows])


def integration_health(ctx, f):
    w = [] if ctx.org_type == "PLATFORM" else [(Integration.org_id.is_(None)) | (Integration.org_id == ctx.org_id)]
    rows = ctx.db.execute(select(Integration, Organization.name).outerjoin(Organization, Organization.id == Integration.org_id)
                          .where(*w).order_by(Integration.kind)).all()
    return (cols(("name", "Integration"), ("organization", "Organization"), ("kind", "Kind"), ("mode", "Mode"),
                 ("health", "Health"), ("last_success_at", "Last success"), ("last_failure_at", "Last failure"),
                 ("consecutive_failures", "Consecutive failures")),
            [dict(name=i.name, organization=n, kind=i.kind, mode=i.mode, health=i.health,
                  last_success_at=iso(i.last_success_at), last_failure_at=iso(i.last_failure_at),
                  consecutive_failures=i.consecutive_failures) for i, n in rows])


def audit_log(ctx, f):
    rows = ctx.db.execute(select(AuditEvent).where(audit_scope(ctx), *_period(AuditEvent.occurred_at, f))
                          .order_by(AuditEvent.seq.desc()).limit(5000)).scalars().all()
    return (cols(("seq", "Seq"), ("occurred_at", "Time"), ("actor", "Actor"), ("role", "Role"), ("action", "Action"),
                 ("target", "Target"), ("outcome", "Outcome"), ("purpose", "Purpose"), ("hash", "Hash")),
            [dict(seq=e.seq, occurred_at=iso(e.occurred_at), actor=e.actor_label, role=e.actor_role, action=e.action,
                  target=e.target_label or e.target_id, outcome=e.outcome, purpose=e.purpose, hash=e.hash[:16])
             for e in rows])


RUNNERS = {"PORTFOLIO_SUMMARY": portfolio_summary, "STUDENT_REGISTER": student_register, "LOAN_LINKAGE": loan_linkage,
           "REPAYMENT_STATUS": repayment_status, "OVERDUE_AGEING": overdue_ageing, "DPD_DETAIL": dpd_detail,
           "DATA_FRESHNESS": data_freshness, "CASE_AGEING": case_ageing, "FOLLOWUP_PRODUCTIVITY": followup_productivity,
           "RISK_REVIEW": risk_review, "FIELD_VISITS": field_visits, "GRIEVANCES": grievances,
           "INTEGRATION_HEALTH": integration_health, "AUDIT_LOG": audit_log}
