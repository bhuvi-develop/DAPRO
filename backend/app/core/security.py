"""Password hashing, JWT access tokens and refresh-token helpers."""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher

from app.core.config import get_settings

_ph = PasswordHasher()


def hash_password(raw: str) -> str:
    return _ph.hash(raw)


def verify_password(hashed: str, raw: str) -> bool:
    try:
        return _ph.verify(hashed, raw)
    except Exception:
        return False


def new_token() -> str:
    return secrets.token_urlsafe(48)


def sha256_hex(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def create_access_token(user_id: str, tenant_id: str, session_id: str, kind: str = "access",
                        minutes: int | None = None) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    payload = {"sub": user_id, "tid": tenant_id, "sid": session_id, "typ": kind, "iat": now,
               "exp": now + timedelta(minutes=minutes or s.access_token_minutes)}
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])
