"""Authentication and server-side authorization (FR-IAM-01/02/05, NFR-SEC-03).

Every route except the public auth/health routes must depend on require(...). A test enumerates
all routes and fails if one is missing (LLD section 4).
"""
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, Request
from sqlalchemy import select

from app.core import audit
from app.core.config import get_settings
from app.core.context import RequestContext
from app.core.db import SessionLocal, bind_tenant, get_session
from app.core.errors import BusinessError, Forbidden
from app.core.security import decode_token


class Unauthenticated(BusinessError):
    def __init__(self, message: str = "Your session is missing or has expired.") -> None:
        super().__init__("UNAUTHENTICATED", message, "Sign in again to continue.", 401)


def _unit_scope(db, user) -> set | None:
    from app.models.iam import OrgUnit

    if not user.org_unit_id:
        return None
    unit = db.get(OrgUnit, user.org_unit_id)
    if unit is None or unit.kind not in ("BRANCH", "REGION", "CAMPUS"):
        return None
    ids = {unit.id}
    frontier = [unit.id]
    while frontier:
        children = db.execute(select(OrgUnit.id).where(OrgUnit.parent_id.in_(frontier))).scalars().all()
        frontier = [c for c in children if c not in ids]
        ids.update(frontier)
    return ids


def build_context(db, user, session_id=None, request: Request | None = None) -> RequestContext:
    from app.models.iam import Organization, Role, UserRole

    org = db.get(Organization, user.org_id)
    roles = db.execute(select(Role).join(UserRole, UserRole.role_id == Role.id)
                       .where(UserRole.user_id == user.id)).scalars().all()
    perms: set[str] = set()
    for r in roles:
        perms.update(r.permissions)
    bind_tenant(db, user.tenant_id)
    corr = getattr(request.state, "correlation_id", None) if request else None
    return RequestContext(
        db=db, tenant_id=user.tenant_id, user_id=user.id, user_name=user.full_name, org_id=user.org_id,
        org_type=org.type if org else "UNKNOWN", org_name=org.name if org else "", roles=[r.code for r in roles],
        permissions=perms, correlation_id=corr or "", unit_ids=_unit_scope(db, user), student_id=user.student_id,
        session_id=session_id, ip=request.client.host if request and request.client else None,
        purpose=request.headers.get("X-Purpose") if request else None,
    )


def current_context(request: Request, db=Depends(get_session)) -> RequestContext:
    from app.models.iam import User, UserSession

    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise Unauthenticated()
    try:
        claims = decode_token(header[7:])
    except jwt.ExpiredSignatureError as exc:
        raise Unauthenticated("Your access token has expired.") from exc
    except jwt.PyJWTError as exc:
        raise Unauthenticated("Your access token is invalid.") from exc
    if claims.get("typ") != "access":
        raise Unauthenticated("Wrong token type.")
    sess = db.get(UserSession, claims["sid"])
    now = datetime.now(UTC)
    s = get_settings()
    if sess is None or sess.revoked_at is not None or sess.expires_at < now:
        raise Unauthenticated("Your session has ended. Sign in again.")
    if sess.last_seen_at + timedelta(minutes=s.session_idle_minutes) < now:
        sess.revoked_at, sess.revoked_reason = now, "IDLE_TIMEOUT"
        db.commit()
        raise Unauthenticated("Your session timed out after inactivity.")
    user = db.get(User, claims["sub"])
    if user is None or user.status != "ACTIVE":
        raise Unauthenticated("Your account is not active.")
    if (now - sess.last_seen_at).total_seconds() > 60:
        sess.last_seen_at = now
        db.commit()
    return build_context(db, user, sess.id, request)


def _record_denial(ctx: RequestContext, permission: str, path: str) -> None:
    """Refused access is audited in its own transaction so it survives the request rollback (FR-IAM-05)."""
    db = SessionLocal()
    try:
        bind_tenant(db, ctx.tenant_id)
        audit.write(db, tenant_id=ctx.tenant_id, action="access.denied", outcome="DENIED", actor_id=ctx.user_id,
                    actor_label=ctx.user_name, actor_role=ctx.role, org_id=ctx.org_id, target_type="route",
                    target_id=path[:80], correlation_id=ctx.correlation_id, ip=ctx.ip,
                    payload={"permission": permission})
        db.commit()
    finally:
        db.close()


def require(*permissions: str, any_of: bool = False):
    """FastAPI dependency: authenticate, check permission(s), bind tenant."""

    def dep(request: Request, ctx: RequestContext = Depends(current_context)) -> RequestContext:
        held = [p in ctx.permissions for p in permissions]
        ok = any(held) if any_of else all(held)
        if not ok:
            _record_denial(ctx, ",".join(permissions), request.url.path)
            needed = " or ".join(permissions)
            raise Forbidden(f"Your role ({ctx.role}) does not include permission {needed}.")
        return ctx

    dep.__dapro_permission__ = permissions
    return dep


def require_authenticated():
    def dep(ctx: RequestContext = Depends(current_context)) -> RequestContext:
        return ctx

    dep.__dapro_permission__ = ("authenticated",)
    return dep
