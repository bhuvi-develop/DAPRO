"""Risk review service (FR-RSK-02/05/06/09)."""
from datetime import UTC, date, datetime

from sqlalchemy import or_, select

from app.common.pagination import paginate
from app.core.errors import BusinessError, InvalidTransition, NotFound, ValidationFailed
from app.core.scope import student_clause
from app.models.iam import User
from app.models.loans import LoanAccount
from app.models.ops import RiskIndicator, RiskReview, RiskRule
from app.models.students import Student
from app.modules.cases.service import create_case, user_name
from app.modules.risk import engine
from app.modules.risk.catalog import SEVERITIES

DECISIONS = ("CONFIRM_FOR_FOLLOW_UP", "CREATE_CASE", "DISMISS", "OVERRIDE_SEVERITY")
CASE_CATEGORY = {"FINANCIAL_DELINQUENCY": "REPAYMENT_FOLLOW_UP", "CONTACT_DATA_QUALITY": "ADDRESS_VERIFICATION",
                 "DATA_SYNCHRONIZATION": "DATA_QUALITY", "OPERATIONAL_FOLLOW_UP": "CONTACT_UPDATE"}


def _scope(ctx):
    return RiskIndicator.student_id.in_(select(Student.id).where(student_clause(ctx)))


def get_indicator(ctx, ind_id) -> RiskIndicator:
    ind = ctx.db.execute(select(RiskIndicator).where(RiskIndicator.id == ind_id, _scope(ctx))).scalar()
    if ind is None:
        raise NotFound("Risk indicator")
    return ind


def serialize(ctx, i: RiskIndicator, s: Student | None = None, full=False) -> dict:
    s = s or ctx.db.get(Student, i.student_id)
    loan = ctx.db.get(LoanAccount, i.loan_id) if i.loan_id else None
    out = {"id": str(i.id), "title": i.title, "explanation": i.explanation, "rule_code": i.rule_code,
           "rule_version": i.rule_version, "category": i.category, "severity": i.severity, "status": i.status,
           "generated_at": i.generated_at, "updated_at": i.updated_at, "assigned_to": user_name(ctx.db, i.assigned_to),
           "case_id": str(i.case_id) if i.case_id else None,
           "student": {"id": str(s.id), "name": s.full_name, "dapro_ref": s.dapro_ref},
           "loan": {"id": str(loan.id), "bank_loan_ref": loan.bank_loan_ref} if loan else None,
           "student_name": s.full_name, "dapro_ref": s.dapro_ref, "bank_loan_ref": loan.bank_loan_ref if loan else None,
           "assigned_to_name": (ctx.db.get(User, i.assigned_to).full_name if i.assigned_to else None),
           "not_a_finding": "Risk indicators prioritise human review. They are not legal findings or decisions."}
    if full:
        rule = ctx.db.get(RiskRule, i.rule_id)
        out.update({"evidence": i.evidence, "input_snapshot": i.input_snapshot,
                    "rule": {"code": rule.code, "version": rule.version, "name": rule.name,
                             "description": rule.description, "params": rule.params,
                             "recommended_action": rule.recommended_action, "approval_label": rule.approval_label},
                    "reviews": [{"id": str(r.id), "decision": r.decision, "rationale": r.rationale,
                                 "override_severity": r.override_severity, "evidence_ref": r.evidence_ref,
                                 "case_id": str(r.case_id) if r.case_id else None,
                                 "reviewer": user_name(ctx.db, r.reviewer_id), "created_at": r.created_at}
                                for r in ctx.db.execute(select(RiskReview).where(RiskReview.indicator_id == i.id)
                                                        .order_by(RiskReview.created_at)).scalars()]})
    return out


def list_indicators(ctx, status=None, category=None, severity=None, rule=None, q=None, mine=False, page=1, size=25,
                    sort=None):
    stmt = select(RiskIndicator, Student).join(Student, Student.id == RiskIndicator.student_id).where(_scope(ctx))
    if status == "open":
        stmt = stmt.where(RiskIndicator.status.in_(engine.OPEN_STATES))
    elif status:
        stmt = stmt.where(RiskIndicator.status.in_(status.split(",")))
    if category:
        stmt = stmt.where(RiskIndicator.category == category)
    if severity:
        stmt = stmt.where(RiskIndicator.severity.in_(severity.split(",")))
    if rule:
        stmt = stmt.where(RiskIndicator.rule_code == rule)
    if mine:
        stmt = stmt.where(RiskIndicator.assigned_to == ctx.user_id)
    if q:
        stmt = stmt.where(or_(Student.full_name.ilike(f"%{q}%"), Student.dapro_ref.ilike(f"%{q}%")))
    cols = {"generated_at": RiskIndicator.generated_at, "severity": RiskIndicator.severity,
            "status": RiskIndicator.status}
    key = (sort or "-generated_at").lstrip("-")
    col = cols.get(key, RiskIndicator.generated_at)
    stmt = stmt.order_by(col.asc() if sort and not sort.startswith("-") and key in cols else col.desc())
    rows, total, page, size = paginate(ctx.db, stmt, page, size, scalars=False)
    return [serialize(ctx, i, s) for i, s in rows], total, page, size


def assign(ctx, ind: RiskIndicator, user_id) -> RiskIndicator:
    from app.models.iam import User

    u = ctx.db.get(User, user_id)
    if u is None or u.status != "ACTIVE" or u.org_id != ctx.org_id:
        raise ValidationFailed("Reviewer must be an active user of your organization.",
                               [{"field": "user_id", "message": "Invalid reviewer"}])
    ind.assigned_to = u.id
    if ind.status == "OPEN":
        ind.status = "IN_REVIEW"
    ctx.audit("risk.assigned", target_type="risk_indicator", target_id=ind.id, payload={"reviewer": str(u.id)})
    ctx.commit()
    return ind


def decide(ctx, ind: RiskIndicator, decision: str, rationale: str, override_severity=None, evidence_ref=None,
           priority="MEDIUM") -> RiskIndicator:
    if ind.status not in engine.OPEN_STATES:
        raise InvalidTransition(f"This indicator is already {ind.status}.",
                                "Review history is preserved; a new indicator is raised if the condition recurs.")
    if decision not in DECISIONS:
        raise ValidationFailed("Unknown decision.", [{"field": "decision", "message": "Invalid"}])
    if not rationale or len(rationale.strip()) < 15:
        raise ValidationFailed("Explain the decision (at least 15 characters).",
                               [{"field": "rationale", "message": "Too short"}])
    if decision == "OVERRIDE_SEVERITY" and override_severity not in SEVERITIES:
        raise ValidationFailed("Choose the overriding severity.", [{"field": "override_severity", "message": "Required"}])
    case_id = None
    if decision == "CREATE_CASE":
        c = create_case(ctx, student_id=ind.student_id, loan_id=ind.loan_id,
                        category=CASE_CATEGORY.get(ind.category, "DATA_QUALITY"),
                        reason=f"{ind.title} (indicator {ind.rule_code} v{ind.rule_version})", priority=priority,
                        source="RISK_INDICATOR", source_ref=str(ind.id),
                        next_action=(ind.input_snapshot or {}).get("recommended_action"))
        case_id = ind.case_id = c.id
    ctx.db.add(RiskReview(tenant_id=ind.tenant_id, indicator_id=ind.id, reviewer_id=ctx.user_id, decision=decision,
                          rationale=rationale.strip(), override_severity=override_severity,
                          evidence_ref=evidence_ref, case_id=case_id))
    ind.status = {"DISMISS": "DISMISSED", "OVERRIDE_SEVERITY": "OVERRIDDEN"}.get(decision, "ACTIONED")
    ctx.audit("risk.decision", target_type="risk_indicator", target_id=ind.id, target_label=ind.rule_code,
              payload={"decision": decision, "override_severity": override_severity,
                       "case_id": str(case_id) if case_id else None})
    ctx.commit()
    return ind


def rules(ctx) -> list[dict]:
    rows = ctx.db.execute(select(RiskRule).order_by(RiskRule.code, RiskRule.version.desc())).scalars().all()
    return [{"id": str(r.id), "code": r.code, "version": r.version, "name": r.name, "category": r.category,
             "description": r.description, "params": r.params, "severity": r.severity,
             "recommended_action": r.recommended_action, "status": r.status, "approval_label": r.approval_label,
             "effective_from": r.effective_from, "change_reason": r.change_reason,
             "created_by": user_name(ctx.db, r.created_by), "approved_by": user_name(ctx.db, r.approved_by),
             "approved_at": r.approved_at} for r in rows]


def propose(ctx, code: str, params: dict, severity: str, change_reason: str, recommended_action=None) -> RiskRule:
    cur = ctx.db.execute(select(RiskRule).where(RiskRule.code == code).order_by(RiskRule.version.desc())).scalar()
    if cur is None:
        raise NotFound("Risk rule")
    if severity not in SEVERITIES:
        raise ValidationFailed("Unknown severity.", [{"field": "severity", "message": "Invalid"}])
    if not change_reason or len(change_reason.strip()) < 10:
        raise ValidationFailed("Give a reason for the change.", [{"field": "change_reason", "message": "Required"}])
    unknown = set(params) - set(cur.params)
    if unknown:
        raise ValidationFailed("Unknown parameters: " + ", ".join(sorted(unknown)),
                               [{"field": "params", "message": "Unknown parameter"}])
    r = RiskRule(tenant_id=ctx.tenant_id, code=code, version=cur.version + 1, name=cur.name, category=cur.category,
                 description=cur.description, params={**cur.params, **params}, severity=severity,
                 recommended_action=recommended_action or cur.recommended_action, status="DRAFT",
                 approval_label="PENDING_APPROVAL", change_reason=change_reason, created_by=ctx.user_id)
    ctx.db.add(r)
    ctx.db.flush()
    ctx.audit("risk.rule_proposed", target_type="risk_rule", target_id=r.id, target_label=f"{code} v{r.version}",
              payload={"params": r.params, "severity": severity})
    ctx.commit()
    return r


def approve(ctx, r: RiskRule) -> RiskRule:
    if r.status != "DRAFT":
        raise InvalidTransition("Only DRAFT rule versions can be approved.")
    if r.created_by == ctx.user_id:
        raise BusinessError("SOD_CONFLICT", "You proposed this rule version, so you cannot approve it.",
                            "Ask another authorised policy owner to approve.", 409)
    for old in ctx.db.execute(select(RiskRule).where(RiskRule.code == r.code, RiskRule.status == "ACTIVE")).scalars():
        old.status = "RETIRED"
    r.status, r.approved_by, r.approved_at, r.effective_from = "ACTIVE", ctx.user_id, datetime.now(UTC), date.today()
    r.approval_label = "APPROVED_IN_DAPRO"
    ctx.audit("risk.rule_approved", target_type="risk_rule", target_id=r.id, target_label=f"{r.code} v{r.version}")
    ctx.commit()
    return r
