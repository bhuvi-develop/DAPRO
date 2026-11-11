"""User administration: invite, activate, suspend, revoke, roles with SoD checks, sessions (FR-IAM-04)."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select

from app.common.pagination import paginate
from app.core.context import RequestContext
from app.core.errors import BusinessError, Forbidden, NotFound, ValidationFailed
from app.core.permissions import PRIVILEGED_ROLES, sod_violations
from app.core.security import new_token, sha256_hex
from app.models.iam import Organization, OrgUnit, Role, User, UserInvitation, UserRole, UserSession
from app.modules.admin.orgs import get_org


def roles_of(db, user_ids) -> dict:
    out: dict = {}
    for uid, code in db.execute(select(UserRole.user_id, Role.code).join(Role, Role.id == UserRole.role_id)
                                .where(UserRole.user_id.in_(user_ids))).all():
        out.setdefault(uid, []).append(code)
    return out


def user_dict(u: User, roles: list[str], orgs: dict, units: dict) -> dict:
    now = datetime.now(UTC)
    return {"id": str(u.id), "email": u.email, "full_name": u.full_name, "title": u.title, "status": u.status,
            "org_id": str(u.org_id), "org_name": orgs.get(u.org_id),
            "org_unit_id": str(u.org_unit_id) if u.org_unit_id else None, "unit_name": units.get(u.org_unit_id),
            "roles": roles, "mfa_enabled": u.mfa_enabled,
            "mfa_required": bool(set(roles) & PRIVILEGED_ROLES) and not u.mfa_enabled,
            "locked": bool(u.locked_until and u.locked_until > now), "failed_logins": u.failed_logins,
            "last_login_at": u.last_login_at, "activated_at": u.activated_at, "created_at": u.created_at}


def _scope(ctx, stmt):
    if ctx.org_type != "PLATFORM":
        stmt = stmt.where(User.org_id == ctx.org_id)
    return stmt


def list_users(ctx: RequestContext, f: dict, page: int, size: int) -> dict:
    stmt = _scope(ctx, select(User).where(User.tenant_id == ctx.tenant_id))
    if f.get("q"):
        q = f"%{f['q']}%"
        stmt = stmt.where(or_(User.full_name.ilike(q), User.email.ilike(q)))
    if f.get("status"):
        stmt = stmt.where(User.status == f["status"])
    if f.get("org_id"):
        stmt = stmt.where(User.org_id == f["org_id"])
    if f.get("role"):
        stmt = stmt.where(User.id.in_(select(UserRole.user_id).join(Role, Role.id == UserRole.role_id)
                                      .where(Role.code == f["role"])))
    sort = f.get("sort") or "full_name"
    col = {"full_name": User.full_name, "email": User.email, "created_at": User.created_at,
           "last_login_at": User.last_login_at, "status": User.status}.get(sort.lstrip("-"), User.full_name)
    stmt = stmt.order_by(col.desc() if sort.startswith("-") else col.asc(), User.id)
    rows, total, page, size = paginate(ctx.db, stmt, page, size)
    roles = roles_of(ctx.db, [u.id for u in rows])
    orgs = {o.id: o.name for o in ctx.db.execute(select(Organization)).scalars()}
    units = {u.id: u.name for u in ctx.db.execute(select(OrgUnit)).scalars()}
    return {"items": [user_dict(u, roles.get(u.id, []), orgs, units) for u in rows], "total": total,
            "page": page, "size": size}


def get_user(ctx: RequestContext, user_id) -> User:
    try:
        u = ctx.db.get(User, user_id)
    except Exception:
        u = None
    if u is None or u.tenant_id != ctx.tenant_id or (ctx.org_type != "PLATFORM" and u.org_id != ctx.org_id):
        raise NotFound("User")
    return u


def _single(ctx, u: User) -> dict:
    orgs = {u.org_id: get_org(ctx, u.org_id).name}
    unit = ctx.db.get(OrgUnit, u.org_unit_id) if u.org_unit_id else None
    return user_dict(u, roles_of(ctx.db, [u.id]).get(u.id, []), orgs, {unit.id: unit.name} if unit else {})


def _check_roles(ctx, codes: list[str], org: Organization) -> list[Role]:
    roles = ctx.db.execute(select(Role).where(Role.tenant_id == ctx.tenant_id, Role.code.in_(codes))).scalars().all()
    if len(roles) != len(set(codes)):
        raise ValidationFailed("Unknown role.", [{"field": "role_codes", "message": "Unknown role code"}])
    for r in roles:
        if org.type not in r.org_types or r.code == "BORROWER":
            raise ValidationFailed(f"Role {r.code} cannot be held by a {org.type} user.",
                                   [{"field": "role_codes", "message": "Role not valid for this organization"}])
    perms: set[str] = set()
    for r in roles:
        perms.update(r.permissions)
    bad = sod_violations(perms)
    if bad:
        raise BusinessError("SOD_CONFLICT", "This role combination breaks segregation of duties: " + "; ".join(bad),
                            "Assign these duties to different users (RD 6.1).", 409)
    return roles


def _issue_invitation(ctx, u: User) -> dict:
    token = new_token()
    ctx.db.add(UserInvitation(tenant_id=ctx.tenant_id, user_id=u.id, token_hash=sha256_hex(token),
                              expires_at=datetime.now(UTC) + timedelta(days=7), created_by=ctx.user_id))
    return {"invitation_token": token, "invite_url": f"/accept-invite?token={token}",
            "expires_in_days": 7,
            "delivery": "DEMO: shown once to the administrator. No email is sent to real people."}


def invite(ctx: RequestContext, body) -> dict:
    org = get_org(ctx, body.org_id or ctx.org_id)
    if ctx.org_type != "PLATFORM" and org.id != ctx.org_id:
        raise Forbidden("You can only invite users into your own organization.")
    email = str(body.email).lower()
    if ctx.db.execute(select(User.id).where(User.tenant_id == ctx.tenant_id, User.email == email)).scalar():
        raise BusinessError("DUPLICATE_EMAIL", "A user with this email already exists.", "Search for the existing user.")
    if body.role_code == "PLATFORM_ADMIN" and ctx.org_type != "PLATFORM":
        raise Forbidden("Only platform administrators can create platform administrators.")
    roles = _check_roles(ctx, [body.role_code], org)
    if body.org_unit_id:
        unit = ctx.db.get(OrgUnit, body.org_unit_id)
        if unit is None or unit.org_id != org.id:
            raise ValidationFailed("Unit must belong to the organization.")
    u = User(tenant_id=ctx.tenant_id, org_id=org.id, org_unit_id=body.org_unit_id, email=email,
             full_name=body.full_name, title=body.title, status="INVITED", created_by=ctx.user_id)
    ctx.db.add(u)
    ctx.db.flush()
    ctx.db.add(UserRole(user_id=u.id, role_id=roles[0].id))
    inv = _issue_invitation(ctx, u)
    ctx.audit("user.invited", target_type="user", target_id=u.id, target_label=u.full_name,
              payload={"role": body.role_code, "org": org.code})
    ctx.commit()
    return {"user": _single(ctx, u), **inv}


def resend_invitation(ctx: RequestContext, user_id) -> dict:
    u = get_user(ctx, user_id)
    if u.status != "INVITED":
        raise BusinessError("INVALID_STATE", "Only invited users can receive a new invitation.", None)
    ctx.db.execute(delete(UserInvitation).where(UserInvitation.user_id == u.id, UserInvitation.accepted_at.is_(None)))
    inv = _issue_invitation(ctx, u)
    ctx.audit("user.invitation_reissued", target_type="user", target_id=u.id, target_label=u.full_name)
    ctx.commit()
    return {"user": _single(ctx, u), **inv}


def _revoke_sessions(ctx, user_id, reason: str) -> int:
    n = 0
    for s in ctx.db.execute(select(UserSession).where(UserSession.user_id == user_id,
                                                      UserSession.revoked_at.is_(None))).scalars():
        s.revoked_at, s.revoked_reason = datetime.now(UTC), reason
        n += 1
    return n


TRANSITIONS = {"suspend": ({"ACTIVE"}, "SUSPENDED"), "activate": ({"SUSPENDED"}, "ACTIVE"),
               "revoke": ({"ACTIVE", "SUSPENDED", "INVITED"}, "REVOKED")}


def change_status(ctx: RequestContext, user_id, action: str, reason: str) -> dict:
    u = get_user(ctx, user_id)
    if u.id == ctx.user_id:
        raise BusinessError("NOT_ALLOWED", "You cannot change your own account status.", "Ask another administrator.")
    allowed, target = TRANSITIONS[action]
    if u.status not in allowed:
        hint = "Invited users activate themselves by accepting the invitation." if u.status == "INVITED" else None
        raise BusinessError("INVALID_TRANSITION", f"Cannot {action} a user who is {u.status}.", hint)
    u.status = target
    revoked = _revoke_sessions(ctx, u.id, f"USER_{target}") if target != "ACTIVE" else 0
    ctx.audit(f"user.{action}", target_type="user", target_id=u.id, target_label=u.full_name,
              payload={"reason": reason, "sessions_revoked": revoked})
    ctx.commit()
    return _single(ctx, u)


def unlock(ctx: RequestContext, user_id) -> dict:
    u = get_user(ctx, user_id)
    u.failed_logins, u.locked_until = 0, None
    ctx.audit("user.unlocked", target_type="user", target_id=u.id, target_label=u.full_name)
    ctx.commit()
    return _single(ctx, u)


def set_roles(ctx: RequestContext, user_id, codes: list[str], reason: str) -> dict:
    u = get_user(ctx, user_id)
    if u.id == ctx.user_id:
        raise BusinessError("NOT_ALLOWED", "You cannot change your own roles.", "Ask another administrator.")
    if "PLATFORM_ADMIN" in codes and ctx.org_type != "PLATFORM":
        raise Forbidden("Only platform administrators can grant platform administration.")
    roles = _check_roles(ctx, codes, get_org(ctx, u.org_id))
    before = roles_of(ctx.db, [u.id]).get(u.id, [])
    ctx.db.execute(delete(UserRole).where(UserRole.user_id == u.id))
    for r in roles:
        ctx.db.add(UserRole(user_id=u.id, role_id=r.id))
    _revoke_sessions(ctx, u.id, "ROLES_CHANGED")
    ctx.audit("user.roles_changed", target_type="user", target_id=u.id, target_label=u.full_name,
              payload={"before": before, "after": sorted(codes), "reason": reason})
    ctx.commit()
    return _single(ctx, u)


def list_sessions(ctx: RequestContext) -> list[dict]:
    stmt = select(UserSession, User).join(User, User.id == UserSession.user_id).where(
        User.tenant_id == ctx.tenant_id, UserSession.revoked_at.is_(None), UserSession.expires_at > datetime.now(UTC))
    stmt = _scope(ctx, stmt)
    return [{"id": str(s.id), "user_id": str(u.id), "user_name": u.full_name, "email": u.email, "ip": s.ip,
             "user_agent": s.user_agent, "created_at": s.created_at, "last_seen_at": s.last_seen_at,
             "mfa_passed": s.mfa_passed, "current": s.id == ctx.session_id}
            for s, u in ctx.db.execute(stmt.order_by(UserSession.last_seen_at.desc()).limit(300)).all()]


def revoke_session(ctx: RequestContext, session_id) -> dict:
    s = ctx.db.get(UserSession, session_id)
    if s is None:
        raise NotFound("Session")
    u = get_user(ctx, s.user_id)
    if not s.revoked_at:
        s.revoked_at, s.revoked_reason = datetime.now(UTC), "ADMIN_REVOKED"
    ctx.audit("session.revoked", target_type="user", target_id=u.id, target_label=u.full_name,
              payload={"session_id": str(s.id)})
    ctx.commit()
    return {"id": str(s.id), "revoked": True}
