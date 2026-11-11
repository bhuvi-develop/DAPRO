"""Roles, integrations, versioned policy configuration and demo reset (FR-ADM-01/02, BR-12)."""
from datetime import UTC, datetime

from sqlalchemy import func, or_, select

from app.common.policy import DEFAULTS
from app.core.config import get_settings
from app.core.context import RequestContext
from app.core.errors import BusinessError, Forbidden, NotFound, ValidationFailed
from app.core.permissions import PERMISSIONS, ROLE_MATRIX, SOD_CONFLICTS
from app.models.iam import Organization, Role, UserRole
from app.models.loans import Integration
from app.models.platform import PolicyConfig

RESET_PHRASE = "RESET DEMO DATA"


def list_roles(ctx: RequestContext) -> list[dict]:
    counts = dict(ctx.db.execute(select(UserRole.role_id, func.count()).group_by(UserRole.role_id)).all())
    rows = ctx.db.execute(select(Role).where(Role.tenant_id == ctx.tenant_id).order_by(Role.name)).scalars()
    return [{"id": str(r.id), "code": r.code, "name": r.name, "description": r.description, "org_types": r.org_types,
             "permissions": sorted(r.permissions), "is_system": r.is_system, "version": r.version,
             "user_count": counts.get(r.id, 0)} for r in rows]


def permission_catalogue() -> dict:
    return {"permissions": [{"code": k, "description": v} for k, v in PERMISSIONS.items()],
            "matrix": {k: sorted(v["permissions"]) for k, v in ROLE_MATRIX.items()},
            "sod_conflicts": [list(p) for p in SOD_CONFLICTS],
            "approval_status": "PROPOSED - the client must approve the final role matrix (RD section 6)"}


def integration_status(i: Integration) -> str:
    if i.mode in ("NOT_CONFIGURED", "DISABLED"):
        return i.mode
    if i.health == "FAILED":
        return "FAILED"
    if i.health == "DEGRADED":
        return "DEGRADED"
    return i.mode


def integration_dict(i: Integration, names: dict) -> dict:
    return {"id": str(i.id), "org_id": str(i.org_id) if i.org_id else None, "org_name": names.get(i.org_id),
            "kind": i.kind, "name": i.name, "provider": i.provider, "mode": i.mode, "health": i.health,
            "status": integration_status(i), "last_success_at": i.last_success_at,
            "last_failure_at": i.last_failure_at, "last_error": i.last_error,
            "consecutive_failures": i.consecutive_failures, "refresh_interval_hours": i.refresh_interval_hours,
            "simulate_failure": i.simulate_failure, "config": i.config, "is_mock": i.mode == "MOCK",
            "updated_at": i.updated_at}


def list_integrations(ctx: RequestContext) -> list[dict]:
    stmt = select(Integration)
    if ctx.org_type != "PLATFORM":
        stmt = stmt.where(or_(Integration.org_id == ctx.org_id, Integration.org_id.is_(None)))
    names = {o.id: o.name for o in ctx.db.execute(select(Organization)).scalars()}
    return [integration_dict(i, names) for i in ctx.db.execute(stmt.order_by(Integration.kind, Integration.name)).scalars()]


def update_integration(ctx: RequestContext, integration_id, body) -> dict:
    i = ctx.db.get(Integration, integration_id)
    if i is None or (ctx.org_type != "PLATFORM" and i.org_id != ctx.org_id):
        raise NotFound("Integration")
    changes = body.model_dump(exclude_none=True)
    if changes.get("mode") == "LIVE" and i.provider.startswith("MOCK"):
        raise BusinessError("LIVE_NOT_AVAILABLE", "No live provider is contracted for this integration.",
                            "LIVE needs an approved provider and credentials in the secrets manager (OD-06, OD-16).")
    if "simulate_failure" in changes and not get_settings().is_demo:
        raise Forbidden("Failure simulation is available only in the DEMO environment.")
    for k, v in changes.items():
        setattr(i, k, v)
    if changes.get("mode") in ("NOT_CONFIGURED", "DISABLED"):
        i.health = "UNKNOWN"
    ctx.audit("integration.updated", target_type="integration", target_id=i.id, target_label=i.name,
              payload=changes)
    ctx.commit()
    return integration_dict(i, {})


def policy_dict(p: PolicyConfig) -> dict:
    return {"id": str(p.id), "key": p.key, "version": p.version, "value": p.value, "status": p.status,
            "approval_label": p.approval_label, "description": p.description, "effective_from": p.effective_from,
            "created_by": str(p.created_by) if p.created_by else None,
            "approved_by": str(p.approved_by) if p.approved_by else None, "created_at": p.created_at}


def list_policies(ctx: RequestContext) -> list[dict]:
    rows = ctx.db.execute(select(PolicyConfig).order_by(PolicyConfig.key, PolicyConfig.version.desc())).scalars()
    return [policy_dict(p) for p in rows]


def _validate_policy(key: str, value: dict) -> None:
    if key not in DEFAULTS:
        raise ValidationFailed("Unknown policy key.", [{"field": "key", "message": "Not a configurable policy"}])
    missing = [k for k in DEFAULTS[key] if k not in value]
    if missing:
        raise ValidationFailed("Policy value is incomplete.", [{"field": "value", "message": "Missing " + ", ".join(missing)}])
    if key == "DPD_BUCKETS":
        prev_max = -1
        for b in value["buckets"]:
            if b.get("min") != prev_max + 1:
                raise ValidationFailed("DPD buckets must be contiguous from 0.", [{"field": "value", "message": b.get("code")}])
            prev_max = b["max"] if b.get("max") is not None else 10**9


def propose_policy(ctx: RequestContext, body) -> dict:
    _validate_policy(body.key, body.value)
    last = ctx.db.execute(select(func.max(PolicyConfig.version)).where(PolicyConfig.key == body.key)).scalar() or 0
    cur = ctx.db.execute(select(PolicyConfig).where(PolicyConfig.key == body.key, PolicyConfig.status == "ACTIVE")
                         .order_by(PolicyConfig.version.desc())).scalar()
    p = PolicyConfig(tenant_id=ctx.tenant_id, key=body.key, version=last + 1, value=body.value, status="DRAFT",
                     approval_label="PENDING_APPROVAL",
                     description=body.description or (cur.description if cur else body.key),
                     effective_from=body.effective_from, created_by=ctx.user_id)
    ctx.db.add(p)
    ctx.db.flush()
    ctx.audit("policy.proposed", target_type="policy", target_id=p.id, target_label=f"{p.key} v{p.version}",
              payload={"reason": body.reason})
    ctx.commit()
    return policy_dict(p)


def decide_policy(ctx: RequestContext, policy_id, approve: bool, reason: str) -> dict:
    p = ctx.db.get(PolicyConfig, policy_id)
    if p is None:
        raise NotFound("Policy version")
    if p.status != "DRAFT":
        raise BusinessError("INVALID_STATE", f"Policy version is {p.status}.", None)
    if p.created_by == ctx.user_id:
        raise BusinessError("SOD_MAKER_CHECKER", "You cannot approve a policy version you proposed.",
                            "A different authorised user must approve it (BR-12).", 409)
    if approve:
        for old in ctx.db.execute(select(PolicyConfig).where(PolicyConfig.key == p.key,
                                                             PolicyConfig.status == "ACTIVE")).scalars():
            old.status = "SUPERSEDED"
        p.status, p.approved_by = "ACTIVE", ctx.user_id
        p.approval_label = "DEMO_FIXTURE" if get_settings().is_demo else "CLIENT_APPROVED"
    else:
        p.status = "REJECTED"
    ctx.audit("policy.approved" if approve else "policy.rejected", target_type="policy", target_id=p.id,
              target_label=f"{p.key} v{p.version}", payload={"reason": reason})
    ctx.commit()
    return policy_dict(p)


def demo_reset(ctx: RequestContext, confirm: str) -> dict:
    if confirm != RESET_PHRASE:
        raise ValidationFailed("Confirmation phrase does not match.",
                               [{"field": "confirm", "message": f"Type {RESET_PHRASE} exactly"}])
    s = get_settings()
    if not s.is_demo:
        raise BusinessError("NOT_DEMO", "Demo reset is disabled outside the DEMO environment.", None, 409)
    from app.workers.tasks_core import demo_reset as task

    ctx.audit("demo.reset_requested", target_type="tenant", target_id=ctx.tenant_id)
    ctx.commit()
    res = task.delay(str(ctx.user_id), ctx.user_name)
    return {"status": "QUEUED", "task_id": getattr(res, "id", None), "requested_at": datetime.now(UTC),
            "note": "The DEMO dataset is being rebuilt. Audit history is preserved. Sign in again afterwards."}
