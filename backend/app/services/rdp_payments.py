"""Provider-agnostic payment gateway support for the RDP programme.

Paystack and Stripe both use hosted checkout. Secret-key operations remain on
FastAPI. CMS-managed credentials are encrypted at rest; environment variables
remain a bootstrap/fallback path for existing deployments.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.rdp import RDPPaymentPlatformSettings, RDPPaymentProviderConfig
from app.services.credential_crypto import decrypt_credentials

PAYSTACK_BASE = "https://api.paystack.co"
STRIPE_BASE = "https://api.stripe.com/v1"
SUPPORTED_PROVIDERS = {"paystack", "stripe"}
DEFAULTS = {
    "paystack": {"display_name": "Paystack", "currencies": ["NGN", "USD"], "priority": 10},
    "stripe": {"display_name": "Stripe", "currencies": ["USD", "GBP", "EUR"], "priority": 20},
}


class PaymentGatewayError(RuntimeError):
    pass


# Backwards-compatible exception alias used by older endpoint code.
PaystackError = PaymentGatewayError


@dataclass
class GatewayConfig:
    provider: str
    environment: str
    display_name: str
    is_enabled: bool
    public_key: str | None
    secret_key: str
    webhook_secret: str | None
    supported_currencies: list[str]
    priority: int
    source: str = "database"


@dataclass
class GatewayInitResult:
    authorization_url: str
    access_code: str | None
    reference: str
    provider_session_id: str | None = None


@dataclass
class GatewayVerification:
    status: str
    reference: str
    amount_subunit: int
    currency: str
    provider_id: str | None
    provider_session_id: str | None
    paid_at: datetime | None
    raw: dict[str, Any]


@dataclass
class WebhookEnvelope:
    event_id: str | None
    event_type: str | None
    reference: str | None
    environment: str
    verification: GatewayVerification | None


def _json_currencies(value: str | None, fallback: list[str]) -> list[str]:
    if not value:
        return list(fallback)
    try:
        raw = json.loads(value)
    except json.JSONDecodeError:
        return list(fallback)
    if not isinstance(raw, list):
        return list(fallback)
    result = []
    for item in raw:
        code = str(item).upper().strip()
        if len(code) == 3 and code.isalpha() and code not in result:
            result.append(code)
    return result or list(fallback)


def infer_environment_from_key(provider: str, secret_key: str) -> str | None:
    if provider == "paystack":
        if secret_key.startswith("sk_test_"):
            return "test"
        if secret_key.startswith("sk_live_"):
            return "live"
    if provider == "stripe":
        if secret_key.startswith(("sk_test_", "rk_test_")):
            return "test"
        if secret_key.startswith(("sk_live_", "rk_live_")):
            return "live"
    return None


def validate_key_environment(provider: str, environment: str, secret_key: str | None, public_key: str | None = None) -> None:
    if secret_key:
        inferred = infer_environment_from_key(provider, secret_key)
        if inferred and inferred != environment:
            raise PaymentGatewayError(f"{provider.title()} secret key appears to be a {inferred} key, not {environment}")
    if public_key:
        if provider == "paystack":
            expected = "pk_test_" if environment == "test" else "pk_live_"
            if public_key.startswith("pk_") and not public_key.startswith(expected):
                raise PaymentGatewayError(f"Paystack public key does not match the {environment} environment")
        elif provider == "stripe":
            expected = "pk_test_" if environment == "test" else "pk_live_"
            if public_key.startswith("pk_") and not public_key.startswith(expected):
                raise PaymentGatewayError(f"Stripe publishable key does not match the {environment} environment")


async def get_platform_settings(db: AsyncSession) -> RDPPaymentPlatformSettings:
    obj = await db.get(RDPPaymentPlatformSettings, 1)
    if obj:
        return obj
    obj = RDPPaymentPlatformSettings(
        id=1,
        active_environment=(settings.PAYMENT_ACTIVE_ENVIRONMENT or "test").lower(),
        allow_provider_selection=True,
    )
    db.add(obj)
    await db.flush()
    return obj


def _fallback_config(provider: str, environment: str) -> GatewayConfig | None:
    default = DEFAULTS[provider]
    if provider == "paystack":
        secret = settings.PAYSTACK_SECRET_KEY.strip()
        public = settings.PAYSTACK_PUBLIC_KEY.strip() or None
        webhook_secret = None  # Paystack signs with the API secret key itself.
    else:
        secret = settings.STRIPE_SECRET_KEY.strip()
        public = settings.STRIPE_PUBLISHABLE_KEY.strip() or None
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET.strip() or None
    if not secret:
        return None
    inferred = infer_environment_from_key(provider, secret)
    if inferred and inferred != environment:
        return None
    return GatewayConfig(
        provider=provider,
        environment=environment,
        display_name=str(default["display_name"]),
        is_enabled=True,
        public_key=public,
        secret_key=secret,
        webhook_secret=webhook_secret,
        supported_currencies=list(default["currencies"]),
        priority=int(default["priority"]),
        source="environment",
    )


async def load_gateway_config(
    db: AsyncSession,
    provider: str,
    environment: str,
    *,
    include_disabled: bool = False,
    allow_env_fallback: bool = True,
) -> GatewayConfig | None:
    provider = provider.lower()
    environment = environment.lower()
    if provider not in SUPPORTED_PROVIDERS or environment not in {"test", "live"}:
        return None
    row = (await db.execute(select(RDPPaymentProviderConfig).where(
        RDPPaymentProviderConfig.provider == provider,
        RDPPaymentProviderConfig.environment == environment,
    ))).scalar_one_or_none()
    if row:
        if not row.is_enabled and not include_disabled:
            return None
        credentials = decrypt_credentials(row.encrypted_credentials)
        secret = str(credentials.get("secret_key") or "")
        if not secret:
            return None if not include_disabled else GatewayConfig(
                provider=provider,
                environment=environment,
                display_name=row.display_name,
                is_enabled=row.is_enabled,
                public_key=row.public_key,
                secret_key="",
                webhook_secret=str(credentials.get("webhook_secret") or "") or None,
                supported_currencies=_json_currencies(row.supported_currencies_json, DEFAULTS[provider]["currencies"]),
                priority=row.priority,
                source="database",
            )
        return GatewayConfig(
            provider=provider,
            environment=environment,
            display_name=row.display_name,
            is_enabled=row.is_enabled,
            public_key=row.public_key,
            secret_key=secret,
            webhook_secret=str(credentials.get("webhook_secret") or "") or None,
            supported_currencies=_json_currencies(row.supported_currencies_json, DEFAULTS[provider]["currencies"]),
            priority=row.priority,
            source="database",
        )
    return _fallback_config(provider, environment) if allow_env_fallback else None


async def available_gateway_configs(db: AsyncSession, currency: str) -> tuple[str, bool, list[GatewayConfig]]:
    platform = await get_platform_settings(db)
    environment = (platform.active_environment or "test").lower()
    currency = currency.upper()
    found: list[GatewayConfig] = []
    for provider in ("paystack", "stripe"):
        config = await load_gateway_config(db, provider, environment)
        if config and config.is_enabled and currency in config.supported_currencies:
            found.append(config)
    found.sort(key=lambda item: (item.priority, item.provider))
    return environment, platform.allow_provider_selection, found


def _auth_headers(secret_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {secret_key}"}


async def initialize_gateway_transaction(
    config: GatewayConfig,
    *,
    email: str,
    amount_subunit: int,
    currency: str,
    reference: str,
    callback_url: str,
    cancel_url: str,
    metadata: dict[str, Any],
    description: str,
) -> GatewayInitResult:
    validate_key_environment(config.provider, config.environment, config.secret_key, config.public_key)
    if config.provider == "paystack":
        payload = {
            "email": email,
            "amount": str(amount_subunit),
            "currency": currency.upper(),
            "reference": reference,
            "callback_url": callback_url,
            "metadata": json.dumps(metadata, separators=(",", ":")),
        }
        headers = {**_auth_headers(config.secret_key), "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(f"{PAYSTACK_BASE}/transaction/initialize", headers=headers, json=payload)
        try:
            body = response.json()
        except ValueError as exc:
            raise PaymentGatewayError("Paystack returned an unreadable response") from exc
        if response.status_code >= 400 or not body.get("status"):
            raise PaymentGatewayError(body.get("message") or "Unable to initialize Paystack transaction")
        data = body["data"]
        return GatewayInitResult(
            authorization_url=data["authorization_url"],
            access_code=data.get("access_code"),
            reference=data.get("reference") or reference,
        )

    if config.provider == "stripe":
        success_url = callback_url
        form = {
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": reference,
            "customer_email": email,
            "line_items[0][price_data][currency]": currency.lower(),
            "line_items[0][price_data][unit_amount]": str(amount_subunit),
            "line_items[0][price_data][product_data][name]": description[:120],
            "line_items[0][quantity]": "1",
            "metadata[reference]": reference,
            "metadata[invoice_id]": str(metadata.get("invoice_id", "")),
            "payment_intent_data[metadata][reference]": reference,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{STRIPE_BASE}/checkout/sessions",
                headers=_auth_headers(config.secret_key),
                data=form,
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise PaymentGatewayError("Stripe returned an unreadable response") from exc
        if response.status_code >= 400 or not body.get("url"):
            message = body.get("error", {}).get("message") if isinstance(body, dict) else None
            raise PaymentGatewayError(message or "Unable to initialize Stripe Checkout")
        return GatewayInitResult(
            authorization_url=body["url"],
            access_code=None,
            reference=reference,
            provider_session_id=body.get("id"),
        )

    raise PaymentGatewayError("Unsupported payment provider")


async def verify_gateway_transaction(
    config: GatewayConfig,
    *,
    reference: str,
    provider_session_id: str | None = None,
) -> GatewayVerification:
    if config.provider == "paystack":
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{PAYSTACK_BASE}/transaction/verify/{quote(reference, safe='')}",
                headers=_auth_headers(config.secret_key),
            )
        body = response.json()
        if response.status_code >= 400 or not body.get("status"):
            raise PaymentGatewayError(body.get("message") or "Unable to verify Paystack transaction")
        data = body["data"]
        paid_at = _parse_datetime(data.get("paid_at"))
        return GatewayVerification(
            status="success" if data.get("status") == "success" else str(data.get("status") or "failed"),
            reference=str(data.get("reference") or reference),
            amount_subunit=int(data.get("amount") or 0),
            currency=str(data.get("currency") or "").upper(),
            provider_id=str(data.get("id") or "") or None,
            provider_session_id=None,
            paid_at=paid_at,
            raw=data,
        )

    if config.provider == "stripe":
        session_id = provider_session_id
        if not session_id:
            raise PaymentGatewayError("Stripe Checkout session ID is missing")
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                f"{STRIPE_BASE}/checkout/sessions/{quote(session_id, safe='')}",
                headers=_auth_headers(config.secret_key),
            )
        body = response.json()
        if response.status_code >= 400:
            message = body.get("error", {}).get("message") if isinstance(body, dict) else None
            raise PaymentGatewayError(message or "Unable to verify Stripe Checkout session")
        metadata = body.get("metadata") or {}
        actual_ref = str(metadata.get("reference") or body.get("client_reference_id") or reference)
        return GatewayVerification(
            status="success" if body.get("payment_status") == "paid" else str(body.get("payment_status") or "failed"),
            reference=actual_ref,
            amount_subunit=int(body.get("amount_total") or 0),
            currency=str(body.get("currency") or "").upper(),
            provider_id=str(body.get("payment_intent") or "") or None,
            provider_session_id=str(body.get("id") or session_id),
            paid_at=datetime.utcnow() if body.get("payment_status") == "paid" else None,
            raw=body,
        )

    raise PaymentGatewayError("Unsupported payment provider")


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


async def test_gateway_connection(config: GatewayConfig) -> str:
    validate_key_environment(config.provider, config.environment, config.secret_key, config.public_key)
    if not config.secret_key:
        raise PaymentGatewayError("Secret key is not configured")
    if config.provider == "paystack":
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{PAYSTACK_BASE}/transaction",
                params={"perPage": 1},
                headers=_auth_headers(config.secret_key),
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise PaymentGatewayError("Paystack returned an unreadable response") from exc
        if response.status_code >= 400 or not body.get("status"):
            raise PaymentGatewayError(body.get("message") or "Paystack credential test failed")
        return "Paystack credentials verified"
    if config.provider == "stripe":
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{STRIPE_BASE}/balance", headers=_auth_headers(config.secret_key))
        try:
            body = response.json()
        except ValueError as exc:
            raise PaymentGatewayError("Stripe returned an unreadable response") from exc
        if response.status_code >= 400:
            message = body.get("error", {}).get("message") if isinstance(body, dict) else None
            raise PaymentGatewayError(message or "Stripe credential test failed")
        return "Stripe credentials verified"
    raise PaymentGatewayError("Unsupported payment provider")


def webhook_environment(provider: str, payload: dict[str, Any]) -> str:
    if provider == "paystack":
        domain = str((payload.get("data") or {}).get("domain") or "").lower()
        return "live" if domain == "live" else "test"
    if provider == "stripe":
        return "live" if bool(payload.get("livemode")) else "test"
    return "test"


def valid_gateway_webhook_signature(
    config: GatewayConfig,
    *,
    raw_body: bytes,
    signature: str | None,
    now: int | None = None,
) -> bool:
    if not signature:
        return False
    if config.provider == "paystack":
        expected = hmac.new(config.secret_key.encode("utf-8"), raw_body, hashlib.sha512).hexdigest()
        return hmac.compare_digest(expected, signature)
    if config.provider == "stripe":
        secret = config.webhook_secret
        if not secret:
            return False
        parts: dict[str, list[str]] = {}
        for item in signature.split(","):
            if "=" not in item:
                continue
            key, value = item.split("=", 1)
            parts.setdefault(key.strip(), []).append(value.strip())
        try:
            timestamp = int((parts.get("t") or [""])[0])
        except ValueError:
            return False
        current = int(time.time()) if now is None else int(now)
        if abs(current - timestamp) > 300:
            return False
        signed_payload = str(timestamp).encode("ascii") + b"." + raw_body
        expected = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
        return any(hmac.compare_digest(expected, candidate) for candidate in parts.get("v1", []))
    return False


def normalize_webhook(provider: str, payload: dict[str, Any], environment: str) -> WebhookEnvelope:
    if provider == "paystack":
        data = payload.get("data") or {}
        reference = str(data.get("reference") or "") or None
        verification = None
        if reference:
            verification = GatewayVerification(
                status="success" if data.get("status") == "success" else str(data.get("status") or "failed"),
                reference=reference,
                amount_subunit=int(data.get("amount") or 0),
                currency=str(data.get("currency") or "").upper(),
                provider_id=str(data.get("id") or "") or None,
                provider_session_id=None,
                paid_at=_parse_datetime(data.get("paid_at")),
                raw=data,
            )
        return WebhookEnvelope(
            event_id=None,
            event_type=str(payload.get("event") or "") or None,
            reference=reference,
            environment=environment,
            verification=verification,
        )
    if provider == "stripe":
        obj = ((payload.get("data") or {}).get("object") or {})
        metadata = obj.get("metadata") or {}
        reference = str(metadata.get("reference") or obj.get("client_reference_id") or "") or None
        payment_status = str(obj.get("payment_status") or "")
        verification = None
        if reference and obj.get("object") == "checkout.session":
            verification = GatewayVerification(
                status="success" if payment_status == "paid" else (payment_status or "pending"),
                reference=reference,
                amount_subunit=int(obj.get("amount_total") or 0),
                currency=str(obj.get("currency") or "").upper(),
                provider_id=str(obj.get("payment_intent") or "") or None,
                provider_session_id=str(obj.get("id") or "") or None,
                paid_at=datetime.utcnow() if payment_status == "paid" else None,
                raw=obj,
            )
        return WebhookEnvelope(
            event_id=str(payload.get("id") or "") or None,
            event_type=str(payload.get("type") or "") or None,
            reference=reference,
            environment=environment,
            verification=verification,
        )
    raise PaymentGatewayError("Unsupported payment provider")


# ── Backwards-compatible Paystack wrappers ──────────────────────────────────

@dataclass
class PaystackInitResult:
    authorization_url: str
    access_code: str | None
    reference: str


async def initialize_transaction(*, email: str, amount_subunit: int, currency: str, reference: str, callback_url: str, metadata: dict[str, Any]) -> PaystackInitResult:
    config = _fallback_config("paystack", infer_environment_from_key("paystack", settings.PAYSTACK_SECRET_KEY) or "test")
    if not config:
        raise PaymentGatewayError("Paystack is not configured")
    result = await initialize_gateway_transaction(
        config,
        email=email,
        amount_subunit=amount_subunit,
        currency=currency,
        reference=reference,
        callback_url=callback_url,
        cancel_url=settings.FRONTEND_URL.rstrip("/") + "/payment-result?status=cancelled",
        metadata=metadata,
        description="Ungozu R & D programme fee",
    )
    return PaystackInitResult(result.authorization_url, result.access_code, result.reference)


async def verify_transaction(reference: str) -> dict[str, Any]:
    config = _fallback_config("paystack", infer_environment_from_key("paystack", settings.PAYSTACK_SECRET_KEY) or "test")
    if not config:
        raise PaymentGatewayError("Paystack is not configured")
    result = await verify_gateway_transaction(config, reference=reference)
    return result.raw


def valid_webhook_signature(raw_body: bytes, signature: str | None) -> bool:
    config = _fallback_config("paystack", infer_environment_from_key("paystack", settings.PAYSTACK_SECRET_KEY) or "test")
    return bool(config and valid_gateway_webhook_signature(config, raw_body=raw_body, signature=signature))
