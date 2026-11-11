"""Enterprise administration and IAM routes (Module 01)."""
from fastapi import APIRouter, Depends

from app.core.authz import require
from app.core.context import RequestContext
from app.modules.admin import orgs, settings, users
from app.modules.admin.schemas import (
    AgreementIn,
    DemoResetIn,
    IntegrationPatch,
    InviteIn,
    OrgIn,
    OrgPatch,
    PolicyProposal,
    ReasonIn,
    RolesIn,
    UnitIn,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/organizations")
def list_orgs(type: str | None = None, ctx: RequestContext = Depends(require("org:read"))):
    return orgs.list_orgs(ctx, type)


@router.post("/organizations", status_code=201)
def create_org(body: OrgIn, ctx: RequestContext = Depends(require("org:manage"))):
    return orgs.create_org(ctx, body)


@router.patch("/organizations/{org_id}")
def update_org(org_id: str, body: OrgPatch, ctx: RequestContext = Depends(require("org:manage"))):
    return orgs.update_org(ctx, org_id, body)


@router.get("/org-units")
def list_units(org_id: str | None = None, ctx: RequestContext = Depends(require("org:read"))):
    return orgs.list_units(ctx, org_id)


@router.post("/org-units", status_code=201)
def create_unit(body: UnitIn, ctx: RequestContext = Depends(require("org:manage", "user:manage", any_of=True))):
    return orgs.create_unit(ctx, body)


@router.get("/sharing-agreements")
def list_agreements(ctx: RequestContext = Depends(require("org:read"))):
    return orgs.list_agreements(ctx)


@router.post("/sharing-agreements", status_code=201)
def create_agreement(body: AgreementIn, ctx: RequestContext = Depends(require("org:manage"))):
    return orgs.create_agreement(ctx, body)


@router.get("/users")
def list_users(page: int = 1, size: int = 25, q: str | None = None, status: str | None = None,
               org_id: str | None = None, role: str | None = None, sort: str | None = None,
               ctx: RequestContext = Depends(require("user:read"))):
    return users.list_users(ctx, {"q": q, "status": status, "org_id": org_id, "role": role, "sort": sort}, page, size)


@router.post("/users/invite", status_code=201)
def invite(body: InviteIn, ctx: RequestContext = Depends(require("user:manage"))):
    return users.invite(ctx, body)


@router.get("/users/{user_id}")
def get_user(user_id: str, ctx: RequestContext = Depends(require("user:read"))):
    return users._single(ctx, users.get_user(ctx, user_id))


@router.post("/users/{user_id}/resend-invitation")
def resend(user_id: str, ctx: RequestContext = Depends(require("user:manage"))):
    return users.resend_invitation(ctx, user_id)


@router.post("/users/{user_id}/suspend")
def suspend(user_id: str, body: ReasonIn, ctx: RequestContext = Depends(require("user:manage"))):
    return users.change_status(ctx, user_id, "suspend", body.reason)


@router.post("/users/{user_id}/activate")
def activate(user_id: str, body: ReasonIn, ctx: RequestContext = Depends(require("user:manage"))):
    return users.change_status(ctx, user_id, "activate", body.reason)


@router.post("/users/{user_id}/revoke")
def revoke(user_id: str, body: ReasonIn, ctx: RequestContext = Depends(require("user:manage"))):
    return users.change_status(ctx, user_id, "revoke", body.reason)


@router.post("/users/{user_id}/unlock")
def unlock(user_id: str, ctx: RequestContext = Depends(require("user:manage"))):
    return users.unlock(ctx, user_id)


@router.put("/users/{user_id}/roles")
def set_roles(user_id: str, body: RolesIn, ctx: RequestContext = Depends(require("user:manage"))):
    return users.set_roles(ctx, user_id, body.role_codes, body.reason)


@router.get("/roles")
def list_roles(ctx: RequestContext = Depends(require("role:read"))):
    return settings.list_roles(ctx)


@router.get("/permissions")
def permissions(ctx: RequestContext = Depends(require("role:read"))):
    return settings.permission_catalogue()


@router.get("/sessions")
def list_sessions(ctx: RequestContext = Depends(require("session:manage"))):
    return users.list_sessions(ctx)


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: str, ctx: RequestContext = Depends(require("session:manage"))):
    return users.revoke_session(ctx, session_id)


@router.get("/integrations")
def list_integrations(ctx: RequestContext = Depends(require("integration:read"))):
    return settings.list_integrations(ctx)


@router.patch("/integrations/{integration_id}")
def update_integration(integration_id: str, body: IntegrationPatch,
                       ctx: RequestContext = Depends(require("integration:manage"))):
    return settings.update_integration(ctx, integration_id, body)


@router.get("/policies")
def list_policies(ctx: RequestContext = Depends(require("policy:read"))):
    return settings.list_policies(ctx)


@router.post("/policies", status_code=201)
def propose_policy(body: PolicyProposal, ctx: RequestContext = Depends(require("policy:manage"))):
    return settings.propose_policy(ctx, body)


@router.post("/policies/{policy_id}/approve")
def approve_policy(policy_id: str, body: ReasonIn, ctx: RequestContext = Depends(require("policy:manage"))):
    return settings.decide_policy(ctx, policy_id, True, body.reason)


@router.post("/policies/{policy_id}/reject")
def reject_policy(policy_id: str, body: ReasonIn, ctx: RequestContext = Depends(require("policy:manage"))):
    return settings.decide_policy(ctx, policy_id, False, body.reason)


@router.post("/demo/reset", status_code=202)
def demo_reset(body: DemoResetIn, ctx: RequestContext = Depends(require("demo:reset"))):
    return settings.demo_reset(ctx, body.confirm)
