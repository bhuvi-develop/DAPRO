"""Authentication service: login, MFA, refresh rotation, logout, invitations (FR-IAM-01/03/04)."""
import re
from datetime import UTC, datetime, timedelta

import pyotp
import redis
from sqlalchemy import select

from app.core import audit
from app.core.config import get_settings
from app.core.db import bind_tenant
from app.core.errors import BusinessError, ValidationFailed
from app.core.ids import uuid7
from app.core.security import create_access_token, decode_token, hash_password, new_token, sha256_hex, verify_password
from app.models.iam import Tenant, User, UserInvitation, UserSession

_redis = None


def _r():
    global _redis
    if _redis is None:
        _redis = redis.Redis.from_url(get_settings().redis_url, socket_timeout=1)
    return _redis


class AuthFailed(BusinessError):
    def __init__(self, message="Email or password is incorrect.", next_step="Check your details and try again."):
        super().__init__("UNAUTHENTICATED", message, next_step, 401)


def rate_limit(key: str) -> None:
    s = get_settings()
    try:
        k = f"rl:login:{key}:{int(datetime.now(UTC).timestamp() // 60)}"
        n = _r().incr(k)
        _r().expire(k, 90)
    except redis.RedisError:
        return
    if n > s.login_rate_per_minute:
        raise BusinessError("RATE_LIMITED", "Too many sign-in attempts.", "Wait a minute and try again.", 429)


def password_policy(pw: str) -> None:
    if len(pw) < 10 or not re.search(r"[A-Z]", pw) or not re.search(r"[a-z]", pw) or not re.search(r"\d", pw):
        raise ValidationFailed("Password does not meet the policy.",
                               [{"field": "password", "message": "Use 10+ characters with upper, lower and a digit."}])


def _audit(db, user, action, outcome, ip, payload=None):
    bind_tenant(db, user.tenant_id)
    audit.write(db, tenant_id=user.tenant_id, action=action, outcome=outcome, actor_id=user.id,
                actor_label=user.full_name, org_id=user.org_id, target_type="user", target_id=user.id,
                ip=ip, payload=payload or {})


def find_user(db, email: str, tenant_code: str | None) -> User | None:
    stmt = select(User).where(User.email == email.lower().strip())
    if tenant_code:
        stmt = stmt.join(Tenant, Tenant.id == User.tenant_id).where(Tenant.code == tenant_code)
    users = db.execute(stmt).scalars().all()
    if len(users) > 1:
        raise BusinessError("TENANT_REQUIRED", "This email exists in more than one workspace.",
                            "Enter your workspace code.", 400)
    return users[0] if users else None


def start_session(db, user: User, ip: str | None, ua: str | None, mfa_passed: bool) -> tuple[str, str, UserSession]:
    s = get_settings()
    now = datetime.now(UTC)
    refresh = new_token()
    sess = UserSession(id=uuid7(), tenant_id=user.tenant_id, user_id=user.id, refresh_hash=sha256_hex(refresh),
                       ip=ip, user_agent=(ua or "")[:300], mfa_passed=mfa_passed, last_seen_at=now,
                       expires_at=now + timedelta(hours=s.refresh_token_hours))
    db.add(sess)
    user.last_login_at, user.failed_logins, user.locked_until = now, 0, None
    access = create_access_token(str(user.id), str(user.tenant_id), str(sess.id))
    return access, refresh, sess


def login(db, email: str, password: str, tenant_code: str | None, ip: str | None, ua: str | None):
    rate_limit(f"{ip}:{email.lower()}")
    user = find_user(db, email, tenant_code)
    now = datetime.now(UTC)
    if user is None:
        verify_password(hash_password("timing-equaliser"), password)
        raise AuthFailed()
    if user.locked_until and user.locked_until > now:
        _audit(db, user, "auth.login", "DENIED", ip, {"reason": "LOCKED"})
        db.commit()
        raise AuthFailed("This account is temporarily locked after repeated failed attempts.",
                         "Wait 15 minutes or ask an administrator to unlock it.")
    if not user.password_hash or not verify_password(user.password_hash, password):
        s = get_settings()
        user.failed_logins += 1
        if user.failed_logins >= s.max_failed_logins:
            user.locked_until = now + timedelta(minutes=s.lockout_minutes)
        _audit(db, user, "auth.login", "FAILURE", ip, {"reason": "BAD_CREDENTIALS", "attempt": user.failed_logins})
        db.commit()
        raise AuthFailed()
    if user.status != "ACTIVE":
        _audit(db, user, "auth.login", "DENIED", ip, {"reason": f"STATUS_{user.status}"})
        db.commit()
        raise AuthFailed("This account is not active.", "Contact your administrator.")
    if user.mfa_enabled:
        token = create_access_token(str(user.id), str(user.tenant_id), "mfa", kind="mfa", minutes=5)
        _audit(db, user, "auth.mfa_challenge", "SUCCESS", ip)
        db.commit()
        return {"mfa_required": True, "mfa_token": token}, None
    access, refresh, _ = start_session(db, user, ip, ua, mfa_passed=False)
    _audit(db, user, "auth.login", "SUCCESS", ip)
    db.commit()
    return {"access_token": access, "expires_in": get_settings().access_token_minutes * 60}, refresh


def verify_mfa(db, mfa_token: str, code: str, ip, ua):
    try:
        claims = decode_token(mfa_token)
    except Exception as exc:
        raise AuthFailed("The verification step expired.", "Sign in again.") from exc
    if claims.get("typ") != "mfa":
        raise AuthFailed("Invalid verification token.")
    user = db.get(User, claims["sub"])
    if user is None or not user.mfa_secret or not pyotp.TOTP(user.mfa_secret).verify(code, valid_window=1):
        if user:
            _audit(db, user, "auth.mfa_verify", "FAILURE", ip)
            db.commit()
        raise AuthFailed("The verification code is incorrect.", "Enter the current 6-digit code.")
    access, refresh, _ = start_session(db, user, ip, ua, mfa_passed=True)
    _audit(db, user, "auth.login", "SUCCESS", ip, {"mfa": True})
    db.commit()
    return {"access_token": access, "expires_in": get_settings().access_token_minutes * 60}, refresh


def refresh_session(db, refresh_token: str | None):
    if not refresh_token:
        raise AuthFailed("No refresh session.", "Sign in again.")
    sess = db.execute(select(UserSession).where(UserSession.refresh_hash == sha256_hex(refresh_token))).scalar()
    now = datetime.now(UTC)
    if sess is None or sess.revoked_at or sess.expires_at < now:
        raise AuthFailed("Your session has ended.", "Sign in again.")
    if sess.last_seen_at + timedelta(minutes=get_settings().session_idle_minutes) < now:
        sess.revoked_at, sess.revoked_reason = now, "IDLE_TIMEOUT"
        db.commit()
        raise AuthFailed("Your session timed out after inactivity.", "Sign in again.")
    user = db.get(User, sess.user_id)
    if user is None or user.status != "ACTIVE":
        raise AuthFailed("Your account is not active.")
    new_refresh = new_token()
    sess.refresh_hash, sess.last_seen_at = sha256_hex(new_refresh), now
    db.commit()
    access = create_access_token(str(user.id), str(user.tenant_id), str(sess.id))
    return {"access_token": access, "expires_in": get_settings().access_token_minutes * 60}, new_refresh


def logout(ctx) -> None:
    sess = ctx.db.get(UserSession, ctx.session_id)
    if sess and not sess.revoked_at:
        sess.revoked_at, sess.revoked_reason = datetime.now(UTC), "LOGOUT"
    ctx.audit("auth.logout", target_type="user", target_id=ctx.user_id)
    ctx.commit()


def mfa_setup(ctx) -> dict:
    user = ctx.db.get(User, ctx.user_id)
    secret = pyotp.random_base32()
    user.mfa_secret = secret
    user.mfa_enabled = False
    ctx.audit("auth.mfa_setup", target_type="user", target_id=user.id)
    ctx.commit()
    return {"secret": secret, "otpauth_uri": pyotp.TOTP(secret).provisioning_uri(user.email, issuer_name="DAPRO")}


def mfa_enable(ctx, code: str) -> None:
    user = ctx.db.get(User, ctx.user_id)
    if not user.mfa_secret or not pyotp.TOTP(user.mfa_secret).verify(code, valid_window=1):
        raise ValidationFailed("The code does not match.", [{"field": "code", "message": "Invalid code"}])
    user.mfa_enabled = True
    ctx.audit("auth.mfa_enabled", target_type="user", target_id=user.id)
    ctx.commit()


def accept_invitation(db, token: str, password: str, ip) -> None:
    password_policy(password)
    inv = db.execute(select(UserInvitation).where(UserInvitation.token_hash == sha256_hex(token))).scalar()
    now = datetime.now(UTC)
    if inv is None or inv.accepted_at or inv.expires_at < now:
        raise BusinessError("INVITATION_INVALID", "This invitation link is invalid or has expired.",
                            "Ask your administrator to send a new invitation.", 400)
    user = db.get(User, inv.user_id)
    if user.status != "INVITED":
        raise BusinessError("INVITATION_INVALID", "This invitation was already used.", "Sign in instead.", 400)
    user.password_hash, user.status, user.activated_at = hash_password(password), "ACTIVE", now
    inv.accepted_at = now
    _audit(db, user, "user.invitation_accepted", "SUCCESS", ip)
    db.commit()


def change_password(ctx, current: str, new: str) -> None:
    user = ctx.db.get(User, ctx.user_id)
    if not verify_password(user.password_hash or "", current):
        raise ValidationFailed("Current password is incorrect.", [{"field": "current_password", "message": "Incorrect"}])
    password_policy(new)
    user.password_hash = hash_password(new)
    ctx.audit("auth.password_changed", target_type="user", target_id=user.id)
    ctx.commit()
