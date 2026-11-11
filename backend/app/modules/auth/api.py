"""Auth routes. login/refresh/mfa-verify/invitation-accept are the only public routes (besides health)."""
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select

from app.core.authz import require_authenticated
from app.core.config import get_settings
from app.core.context import RequestContext
from app.core.db import get_session
from app.models.iam import OrgUnit, Tenant, User, UserSession
from app.modules.auth import service
from app.modules.auth.schemas import AcceptInviteIn, ChangePasswordIn, CodeIn, LoginIn, MfaVerifyIn, TokenOut

router = APIRouter(prefix="/auth", tags=["auth"])
PUBLIC_PATHS = {"/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/mfa/verify",
                "/api/v1/auth/invitations/accept", "/api/v1/auth/logout-cookie"}
COOKIE = "dapro_refresh"


def _set_cookie(resp: Response, token: str | None) -> None:
    if token:
        s = get_settings()
        resp.set_cookie(COOKIE, token, httponly=True, secure=s.cookie_secure, samesite="strict",
                        path="/api/v1/auth", max_age=s.refresh_token_hours * 3600)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, request: Request, response: Response, db=Depends(get_session)):
    out, refresh = service.login(db, body.email, body.password, body.tenant_code,
                                 request.client.host if request.client else None, request.headers.get("user-agent"))
    _set_cookie(response, refresh)
    return out


@router.post("/mfa/verify", response_model=TokenOut)
def mfa_verify(body: MfaVerifyIn, request: Request, response: Response, db=Depends(get_session)):
    out, refresh = service.verify_mfa(db, body.mfa_token, body.code,
                                      request.client.host if request.client else None,
                                      request.headers.get("user-agent"))
    _set_cookie(response, refresh)
    return out


@router.post("/refresh", response_model=TokenOut)
def refresh(request: Request, response: Response, db=Depends(get_session)):
    out, token = service.refresh_session(db, request.cookies.get(COOKIE))
    _set_cookie(response, token)
    return out


@router.post("/logout")
def logout(response: Response, ctx: RequestContext = Depends(require_authenticated())):
    service.logout(ctx)
    response.delete_cookie(COOKIE, path="/api/v1/auth")
    return {"message": "Signed out"}


@router.post("/logout-cookie")
def logout_cookie(response: Response):
    response.delete_cookie(COOKIE, path="/api/v1/auth")
    return {"message": "Cookie cleared"}


@router.post("/invitations/accept")
def accept_invitation(body: AcceptInviteIn, request: Request, db=Depends(get_session)):
    service.accept_invitation(db, body.token, body.password, request.client.host if request.client else None)
    return {"message": "Account activated. You can now sign in."}


@router.get("/me")
def me(ctx: RequestContext = Depends(require_authenticated())):
    db = ctx.db
    user = db.get(User, ctx.user_id)
    tenant = db.get(Tenant, ctx.tenant_id)
    unit = db.get(OrgUnit, user.org_unit_id) if user.org_unit_id else None
    s = get_settings()
    return {
        "id": str(user.id), "email": user.email, "full_name": user.full_name, "title": user.title,
        "roles": ctx.roles, "permissions": sorted(ctx.permissions), "mfa_enabled": user.mfa_enabled,
        "org": {"id": str(ctx.org_id), "name": ctx.org_name, "type": ctx.org_type},
        "unit": {"id": str(unit.id), "name": unit.name, "kind": unit.kind} if unit else None,
        "student_id": str(user.student_id) if user.student_id else None,
        "tenant": {"id": str(tenant.id), "name": tenant.name, "code": tenant.code,
                   "environment": tenant.environment_label},
        "environment": {"env": s.env, "demo": s.env == "demo", "bank_adapter": s.bank_adapter,
                        "email_mode": s.email_mode, "sms_mode": s.sms_mode,
                        "location_capture": s.field_location_capture_enabled},
        "last_login_at": user.last_login_at, "timezone": user.timezone,
    }


@router.get("/sessions")
def my_sessions(ctx: RequestContext = Depends(require_authenticated())):
    rows = ctx.db.execute(select(UserSession).where(UserSession.user_id == ctx.user_id, UserSession.revoked_at.is_(None),
                                                    UserSession.expires_at > datetime.now(UTC))
                          .order_by(UserSession.created_at.desc())).scalars().all()
    return [{"id": str(r.id), "created_at": r.created_at, "last_seen_at": r.last_seen_at, "ip": r.ip,
             "user_agent": r.user_agent, "current": r.id == ctx.session_id, "mfa_passed": r.mfa_passed}
            for r in rows]


@router.delete("/sessions/{session_id}")
def revoke_my_session(session_id: str, ctx: RequestContext = Depends(require_authenticated())):
    sess = ctx.db.get(UserSession, session_id)
    if sess and sess.user_id == ctx.user_id and not sess.revoked_at:
        sess.revoked_at, sess.revoked_reason = datetime.now(UTC), "USER_REVOKED"
        ctx.audit("auth.session_revoked", target_type="session", target_id=sess.id)
        ctx.commit()
    return {"message": "Session revoked"}


@router.post("/mfa/setup")
def mfa_setup(ctx: RequestContext = Depends(require_authenticated())):
    return service.mfa_setup(ctx)


@router.post("/mfa/enable")
def mfa_enable(body: CodeIn, ctx: RequestContext = Depends(require_authenticated())):
    service.mfa_enable(ctx, body.code)
    return {"message": "Two-factor authentication enabled"}


@router.post("/password")
def change_password(body: ChangePasswordIn, ctx: RequestContext = Depends(require_authenticated())):
    service.change_password(ctx, body.current_password, body.new_password)
    return {"message": "Password changed"}
