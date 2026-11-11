"""Guarantor and witness records (FR-GUA-01..07, BR-07, BR-13, AC-09).

Guarantors and witnesses live in separate tables with separate permissions. A witness record carries no
liability, guarantee or communication fields and is never treated as an obligor. Guarantor changes go
through maker-checker when the MAKER_CHECKER policy enables it (FR-GUA-07, RD 6.1).
"""
from datetime import UTC, date, datetime

from sqlalchemy import select

from app.common.policy import get_policy
from app.core import masking
from app.core.context import RequestContext
from app.core.errors import BusinessError, NotFound, ValidationFailed
from app.core.scope import loan_clause
from app.models.loans import Guarantor, LoanAccount, Witness

G_FIELDS = ["full_name", "relationship_to_borrower", "mobile", "email", "address_text", "city", "state",
            "agreement_ref", "agreement_executed_on", "guarantee_scope", "guarantee_status", "verification",
            "communication_permitted", "communication_basis"]


def scoped_loan(ctx: RequestContext, loan_id) -> LoanAccount:
    try:
        lo = ctx.db.execute(select(LoanAccount).where(LoanAccount.id == loan_id, loan_clause(ctx))).scalar()
    except Exception as exc:
        raise NotFound("Loan") from exc
    if lo is None:
        raise NotFound("Loan")
    return lo


def _maker_checker(ctx) -> bool:
    return bool(get_policy(ctx.db, "MAKER_CHECKER")["value"].get("guarantor_change_approval", True))


def guarantor_dict(ctx, g: Guarantor) -> dict:
    return {"id": str(g.id), "loan_id": str(g.loan_id), "full_name": g.full_name,
            "relationship_to_borrower": g.relationship_to_borrower,
            "mobile": masking.contact(ctx, "MOBILE", g.mobile), "email": masking.contact(ctx, "EMAIL", g.email),
            "address_text": g.address_text, "city": g.city, "state": g.state, "agreement_ref": g.agreement_ref,
            "agreement_executed_on": g.agreement_executed_on, "guarantee_scope": g.guarantee_scope,
            "guarantee_status": g.guarantee_status, "verification": g.verification, "verified_at": g.verified_at,
            "communication_permitted": g.communication_permitted, "communication_basis": g.communication_basis,
            "source": g.source, "approval_status": g.approval_status, "pending_change": g.pending_change,
            "pending_by": str(g.pending_by) if g.pending_by else None, "version": g.version,
            "role": "GUARANTOR", "created_at": g.created_at, "updated_at": g.updated_at}


def witness_dict(w: Witness) -> dict:
    return {"id": str(w.id), "loan_id": str(w.loan_id), "full_name": w.full_name, "document_ref": w.document_ref,
            "witnessed_on": w.witnessed_on, "address_city": w.address_city, "source": w.source,
            "verification": w.verification, "notes": w.notes, "role": "WITNESS",
            "liability": "NONE - a witness is not a guarantor or obligor (BR-07)", "created_at": w.created_at}


def _check_basis(permitted: bool | None, basis: str | None) -> None:
    if permitted and not (basis or "").strip():
        raise ValidationFailed("Guarantor communication needs a documented lawful basis (BR-13).",
                               [{"field": "communication_basis", "message": "Required when communication is permitted"}])


def list_guarantors(ctx: RequestContext, loan_id) -> list[dict]:
    lo = scoped_loan(ctx, loan_id)
    return [guarantor_dict(ctx, g) for g in ctx.db.execute(select(Guarantor).where(Guarantor.loan_id == lo.id)
                                                            .order_by(Guarantor.created_at)).scalars()]


def create_guarantor(ctx: RequestContext, loan_id, body) -> dict:
    lo = scoped_loan(ctx, loan_id)
    _check_basis(body.communication_permitted, body.communication_basis)
    mc = _maker_checker(ctx)
    g = Guarantor(tenant_id=ctx.tenant_id, loan_id=lo.id, **body.model_dump(), source="BANK_PROVIDED",
                  approval_status="PENDING_APPROVAL" if mc else "APPROVED", pending_by=ctx.user_id if mc else None,
                  pending_change={"action": "CREATE"} if mc else None, created_by=ctx.user_id)
    ctx.db.add(g)
    ctx.db.flush()
    ctx.audit("guarantor.created", target_type="loan", target_id=lo.id, target_label=lo.bank_loan_ref,
              payload={"guarantor_id": str(g.id), "maker_checker": mc})
    ctx.commit()
    return guarantor_dict(ctx, g)


def _guarantor(ctx, gid) -> Guarantor:
    g = ctx.db.get(Guarantor, gid)
    if g is None:
        raise NotFound("Guarantor")
    scoped_loan(ctx, g.loan_id)
    return g


def update_guarantor(ctx: RequestContext, gid, body) -> dict:
    g = _guarantor(ctx, gid)
    changes = {k: v for k, v in body.model_dump(exclude={"reason"}).items()
               if v is not None and k in G_FIELDS and v != getattr(g, k)}
    if not changes:
        raise ValidationFailed("Nothing changed.")
    _check_basis(changes.get("communication_permitted", g.communication_permitted),
                 changes.get("communication_basis", g.communication_basis))
    if g.approval_status == "PENDING_APPROVAL":
        raise BusinessError("PENDING_APPROVAL", "Another change is awaiting approval.",
                            "Ask an approver to approve or reject it first.")
    if _maker_checker(ctx):
        g.pending_change = {"action": "UPDATE", "reason": body.reason,
                            "changes": {k: (v.isoformat() if isinstance(v, date) else v) for k, v in changes.items()}}
        g.pending_by, g.approval_status = ctx.user_id, "PENDING_APPROVAL"
        outcome = "PENDING_APPROVAL"
    else:
        _apply(g, changes, ctx)
        outcome = "APPLIED"
    ctx.audit("guarantor.change_submitted", target_type="loan", target_id=g.loan_id,
              payload={"guarantor_id": str(g.id), "fields": sorted(changes), "outcome": outcome, "reason": body.reason})
    ctx.commit()
    return guarantor_dict(ctx, g)


def _apply(g: Guarantor, changes: dict, ctx) -> None:
    for k, v in changes.items():
        if k == "agreement_executed_on" and isinstance(v, str):
            v = date.fromisoformat(v)
        setattr(g, k, v)
    if changes.get("verification") == "VERIFIED":
        g.verified_by, g.verified_at = ctx.user_id, datetime.now(UTC)
    g.version += 1


def decide(ctx: RequestContext, gid, approve: bool, notes: str) -> dict:
    g = _guarantor(ctx, gid)
    if g.approval_status != "PENDING_APPROVAL":
        raise BusinessError("INVALID_STATE", "There is no change awaiting approval.", None)
    if g.pending_by == ctx.user_id:
        raise BusinessError("SOD_MAKER_CHECKER", "You cannot approve a change you submitted.",
                            "A different authorised user must review it (RD 6.1).", 409)
    change = g.pending_change or {}
    if approve:
        if change.get("action") == "UPDATE":
            _apply(g, change.get("changes", {}), ctx)
        g.approval_status, g.approved_by = "APPROVED", ctx.user_id
    else:
        g.approval_status = "REJECTED" if change.get("action") == "CREATE" else "APPROVED"
    g.pending_change, g.pending_by = None, None
    ctx.audit("guarantor.change_approved" if approve else "guarantor.change_rejected", target_type="loan",
              target_id=g.loan_id, payload={"guarantor_id": str(g.id), "action": change.get("action"), "notes": notes})
    ctx.commit()
    return guarantor_dict(ctx, g)


def pending_approvals(ctx: RequestContext) -> list[dict]:
    rows = ctx.db.execute(select(Guarantor, LoanAccount).join(LoanAccount, LoanAccount.id == Guarantor.loan_id)
                          .where(Guarantor.approval_status == "PENDING_APPROVAL", loan_clause(ctx))
                          .order_by(Guarantor.updated_at)).all()
    return [{**guarantor_dict(ctx, g), "bank_loan_ref": lo.bank_loan_ref,
             "can_approve": g.pending_by != ctx.user_id} for g, lo in rows]


def list_witnesses(ctx: RequestContext, loan_id) -> list[dict]:
    lo = scoped_loan(ctx, loan_id)
    return [witness_dict(w) for w in ctx.db.execute(select(Witness).where(Witness.loan_id == lo.id)
                                                    .order_by(Witness.created_at)).scalars()]


def create_witness(ctx: RequestContext, loan_id, body) -> dict:
    lo = scoped_loan(ctx, loan_id)
    w = Witness(tenant_id=ctx.tenant_id, loan_id=lo.id, **body.model_dump(), source="BANK_PROVIDED",
                created_by=ctx.user_id)
    ctx.db.add(w)
    ctx.db.flush()
    ctx.audit("witness.created", target_type="loan", target_id=lo.id, target_label=lo.bank_loan_ref,
              payload={"witness_id": str(w.id)})
    ctx.commit()
    return witness_dict(w)


def update_witness(ctx: RequestContext, wid, body) -> dict:
    w = ctx.db.get(Witness, wid)
    if w is None:
        raise NotFound("Witness")
    scoped_loan(ctx, w.loan_id)
    changes = {k: v for k, v in body.model_dump().items() if v is not None}
    for k, v in changes.items():
        setattr(w, k, v)
    ctx.audit("witness.updated", target_type="loan", target_id=w.loan_id,
              payload={"witness_id": str(w.id), "fields": sorted(changes)})
    ctx.commit()
    return witness_dict(w)
