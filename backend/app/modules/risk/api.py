"""Risk intelligence routes (Module 07)."""
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.authz import require
from app.core.context import RequestContext
from app.core.errors import NotFound
from app.models.ops import RiskRule
from app.modules.risk import engine, service
from app.modules.risk.catalog import CATEGORIES, SEVERITIES

router = APIRouter(prefix="/risk", tags=["risk"])


class DecisionIn(BaseModel):
    decision: str
    rationale: str = Field(min_length=15, max_length=2000)
    override_severity: str | None = None
    evidence_ref: str | None = None
    priority: str = "MEDIUM"


class AssignIn(BaseModel):
    user_id: UUID


class RuleVersionIn(BaseModel):
    params: dict = {}
    severity: str
    change_reason: str
    recommended_action: str | None = None


@router.get("/meta")
def meta(ctx: RequestContext = Depends(require("risk:read", "policy:read", any_of=True))):
    return {"categories": CATEGORIES, "severities": SEVERITIES, "decisions": service.DECISIONS}


@router.get("/indicators")
def indicators(status: str | None = None, category: str | None = None, severity: str | None = None,
               rule: str | None = None, rule_code: str | None = None, q: str | None = None, mine: bool = False,
               page: int = 1, size: int = 25, sort: str | None = None,
               ctx: RequestContext = Depends(require("risk:read"))):
    items, total, page, size = service.list_indicators(ctx, status, category, severity, rule_code or rule, q, mine,
                                                       page, size, sort)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/indicators/{ind_id}")
def indicator(ind_id: UUID, ctx: RequestContext = Depends(require("risk:read"))):
    return service.serialize(ctx, service.get_indicator(ctx, ind_id), full=True)


@router.post("/indicators/{ind_id}/assign")
def assign(ind_id: UUID, body: AssignIn, ctx: RequestContext = Depends(require("risk:decide"))):
    return service.serialize(ctx, service.assign(ctx, service.get_indicator(ctx, ind_id), body.user_id), full=True)


@router.post("/indicators/{ind_id}/decision")
def decision(ind_id: UUID, body: DecisionIn, ctx: RequestContext = Depends(require("risk:decide"))):
    ind = service.decide(ctx, service.get_indicator(ctx, ind_id), body.decision, body.rationale,
                         body.override_severity, body.evidence_ref, body.priority)
    return service.serialize(ctx, ind, full=True)


@router.get("/rules")
def rules(ctx: RequestContext = Depends(require("risk:read", "policy:read", any_of=True))):
    return service.rules(ctx)


@router.post("/rules/{code}/versions", status_code=201)
def propose(code: str, body: RuleVersionIn, ctx: RequestContext = Depends(require("risk:rules"))):
    r = service.propose(ctx, code, body.params, body.severity, body.change_reason, body.recommended_action)
    return {"id": str(r.id), "code": r.code, "version": r.version, "status": r.status}


def _rule(ctx, rule_id) -> RiskRule:
    r = ctx.db.get(RiskRule, rule_id)
    if r is None:
        raise NotFound("Risk rule")
    return r


@router.post("/rules/{rule_id}/approve")
def approve(rule_id: UUID, ctx: RequestContext = Depends(require("risk:approve_rules"))):
    r = service.approve(ctx, _rule(ctx, rule_id))
    return {"id": str(r.id), "code": r.code, "version": r.version, "status": r.status}


@router.post("/rules/{rule_id}/test")
def test_rule(rule_id: UUID, ctx: RequestContext = Depends(require("risk:rules", "risk:approve_rules", any_of=True))):
    return engine.dry_run(ctx.db, _rule(ctx, rule_id))


@router.post("/run")
def run(ctx: RequestContext = Depends(require("risk:decide"))):
    stats = engine.evaluate_tenant(ctx.db, ctx.tenant_id)
    ctx.audit("risk.evaluated", payload=stats)
    ctx.commit()
    return stats
