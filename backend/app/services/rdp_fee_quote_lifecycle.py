"""Lifecycle and financial-term locking rules for RDP fee quotes."""

from datetime import datetime, timezone


ALLOWED_TRANSITIONS = {
    "draft": frozenset({"offered"}),
    "offered": frozenset({
        "accepted",
        "expired",
        "superseded",
    }),
    "accepted": frozenset(),
    "expired": frozenset(),
    "superseded": frozenset(),
}


def _normalize_utc(value: datetime) -> datetime:
    """Convert aware datetimes to naive UTC for backend compatibility."""
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def validate_quote_transition(
    *,
    current_status: str,
    new_status: str,
    now: datetime,
    expires_at: datetime | None = None,
) -> None:
    """Validate a proposed quote status change."""

    if current_status not in ALLOWED_TRANSITIONS:
        raise ValueError("Unknown current quote status")

    if new_status not in ALLOWED_TRANSITIONS:
        raise ValueError("Unknown target quote status")

    if new_status not in ALLOWED_TRANSITIONS[current_status]:
        raise ValueError(
            f"Quote cannot transition from "
            f"{current_status} to {new_status}"
        )

    if (
        new_status in {"offered", "accepted"}
        and expires_at is not None
        and _normalize_utc(now) >= _normalize_utc(expires_at)
    ):
        raise ValueError(
            "An expired quotation cannot be issued or accepted"
        )


def assert_quote_terms_editable(status: str) -> None:
    """Prevent modification of issued financial terms."""

    if status not in ALLOWED_TRANSITIONS:
        raise ValueError("Unknown quote status")

    if status != "draft":
        raise ValueError(
            "Issued quotation terms are locked. "
            "Create a new quote version instead."
        )
