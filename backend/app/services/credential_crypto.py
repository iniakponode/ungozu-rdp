"""Encryption helpers for CMS-managed third-party credentials.

Provider secrets are encrypted at rest with Fernet.  The encryption material is
kept outside the database.  A dedicated CREDENTIAL_ENCRYPTION_KEY is preferred;
for backwards-compatible deployments the already-required application SECRET_KEY
is used as a fallback.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CredentialEncryptionError(RuntimeError):
    pass


def _fernet() -> Fernet:
    material = (settings.CREDENTIAL_ENCRYPTION_KEY or settings.SECRET_KEY or "").strip()
    if not material:
        raise CredentialEncryptionError("Credential encryption key is not configured")
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_credentials(data: dict[str, Any]) -> str:
    clean = {k: v for k, v in data.items() if v not in (None, "")}
    raw = json.dumps(clean, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _fernet().encrypt(raw).decode("ascii")


def decrypt_credentials(token: str | None) -> dict[str, Any]:
    if not token:
        return {}
    try:
        raw = _fernet().decrypt(token.encode("ascii"))
        value = json.loads(raw.decode("utf-8"))
        return value if isinstance(value, dict) else {}
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise CredentialEncryptionError("Stored payment credentials could not be decrypted") from exc


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 8:
        return "•" * len(value)
    prefix = value[: min(8, max(3, value.find("_") + 1))]
    return f"{prefix}{'•' * 12}{value[-4:]}"
