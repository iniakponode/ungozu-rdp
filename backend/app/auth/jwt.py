"""
JWT creation and verification utilities.
Uses PyJWT with HS256 signing.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt import PyJWTError as JWTError

from app.core.config import settings

ALGORITHM = "HS256"


def create_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a signed JWT token.

    Args:
        subject: Token subject — typically the user's email or id (stored as `sub`).
        expires_delta: Optional custom expiry window; falls back to settings.
        extra_claims: Optional extra payload fields.
    """
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {"sub": str(subject), "exp": expire}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(
    subject: str | Any,
    *,
    token_type: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed, purpose-bound JWT access token."""
    if token_type not in {"admin_access", "student_access", "rdp_access"}:
        raise ValueError("Unsupported access-token type")
    return create_token(
        subject=subject,
        expires_delta=expires_delta,
        extra_claims={"type": token_type},
    )


def create_password_reset_token(email: str) -> str:
    """Create a short-lived JWT used for student password resets."""
    return create_token(
        subject=email,
        expires_delta=timedelta(minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES),
        extra_claims={"type": "password_reset"},
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT, returning the payload dict.

    Raises:
        JWTError: if the token is invalid or expired.
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])


def decode_password_reset_token(token: str) -> str:
    """Decode a password-reset token and return the email subject."""
    payload = decode_access_token(token)
    if payload.get("type") != "password_reset":
        raise JWTError("Invalid token type")
    email = payload.get("sub")
    if not isinstance(email, str) or not email:
        raise JWTError("Missing token subject")
    return email
