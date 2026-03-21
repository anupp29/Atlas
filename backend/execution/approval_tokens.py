"""
Cryptographic one-time approval tokens for PCI-DSS and SOX dual sign-off.
Every token is time-limited, incident-scoped, and single-use.

Uses HMAC-SHA256 signing with the ATLAS_SECRET_KEY environment variable.
Missing secret key = hard startup failure. No weak defaults. Ever.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Startup validation
# ─────────────────────────────────────────────────────────────────────────────

_SECRET_KEY_ENV = "ATLAS_SECRET_KEY"
_MIN_KEY_LENGTH = 32  # bytes — NIST minimum for HMAC-SHA256


def _load_secret_key() -> bytes:
    """
    Load and validate the signing key from environment.
    Fails immediately with a clear error if missing or too short.
    """
    raw = os.environ.get(_SECRET_KEY_ENV, "")
    if not raw:
        raise RuntimeError(
            f"ATLAS startup failure: environment variable '{_SECRET_KEY_ENV}' is not set. "
            "Approval token generation requires a cryptographic signing key. "
            "Set this variable before starting ATLAS."
        )
    key_bytes = raw.encode("utf-8")
    if len(key_bytes) < _MIN_KEY_LENGTH:
        raise RuntimeError(
            f"ATLAS startup failure: '{_SECRET_KEY_ENV}' is too short "
            f"({len(key_bytes)} bytes). Minimum required: {_MIN_KEY_LENGTH} bytes. "
            "Use a randomly generated key of at least 32 characters."
        )
    return key_bytes


_SIGNING_KEY: bytes = _load_secret_key()

# ─────────────────────────────────────────────────────────────────────────────
# Nonce store — in-memory for MVP, Redis-backed in production
# ─────────────────────────────────────────────────────────────────────────────

# nonce → expiry_unix_timestamp
_USED_NONCES: dict[str, float] = {}

# Prune nonces older than this to prevent unbounded growth
_NONCE_RETENTION_SECONDS = 7200  # 2 hours


def _prune_expired_nonces() -> None:
    """Remove expired nonces from the store. Called on every validation."""
    now = time.time()
    expired = [n for n, exp in _USED_NONCES.items() if now > exp + _NONCE_RETENTION_SECONDS]
    for n in expired:
        del _USED_NONCES[n]


# ─────────────────────────────────────────────────────────────────────────────
# Token format
# ─────────────────────────────────────────────────────────────────────────────
# Token is a URL-safe base64-encoded JSON payload + HMAC-SHA256 signature.
# Format: <base64url(payload_json)>.<hex_signature>
#
# Payload fields:
#   incident_id   — the specific incident this token authorises
#   approver_role — "primary" | "secondary" | "sdm"
#   nonce         — 32-byte random hex string (single-use guarantee)
#   issued_at     — Unix timestamp
#   expires_at    — Unix timestamp
#
# The token is designed to be embeddable in a URL query parameter.
# ─────────────────────────────────────────────────────────────────────────────

import base64


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    # Re-add padding
    padding = 4 - len(s) % 4
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def _sign(payload_b64: str) -> str:
    """Produce HMAC-SHA256 hex signature over the base64-encoded payload."""
    return hmac.new(
        _SIGNING_KEY,
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def generate_approval_token(
    incident_id: str,
    approver_role: str,
    expiry_minutes: int = 30,
) -> str:
    """
    Generate a cryptographic one-time approval token.

    Args:
        incident_id:    The ATLAS incident ID this token authorises.
        approver_role:  "primary" | "secondary" | "sdm"
        expiry_minutes: Token validity window. Default 30 minutes.

    Returns:
        Signed token string safe for URL embedding.

    Raises:
        ValueError: If incident_id is empty or approver_role is invalid.
    """
    if not incident_id:
        raise ValueError("incident_id is required for approval token generation.")

    valid_roles = {"primary", "secondary", "sdm", "l1", "l2", "l3"}
    if approver_role not in valid_roles:
        raise ValueError(
            f"Invalid approver_role '{approver_role}'. Must be one of: {valid_roles}"
        )

    now = time.time()
    nonce = secrets.token_hex(32)  # 256-bit random nonce

    payload: dict[str, Any] = {
        "incident_id": incident_id,
        "approver_role": approver_role,
        "nonce": nonce,
        "issued_at": now,
        "expires_at": now + (expiry_minutes * 60),
    }

    payload_json = json.dumps(payload, separators=(",", ":"), sort_keys=True)
    payload_b64 = _b64url_encode(payload_json.encode("utf-8"))
    signature = _sign(payload_b64)
    token = f"{payload_b64}.{signature}"

    logger.info(
        "approval_tokens.generated",
        incident_id=incident_id,
        approver_role=approver_role,
        expires_at=datetime.fromtimestamp(payload["expires_at"], tz=timezone.utc).isoformat(),
        nonce_prefix=nonce[:8],  # Log prefix only — never log full nonce
    )
    return token


def validate_approval_token(token: str) -> tuple[bool, str, str, str]:
    """
    Validate a cryptographic approval token.

    Checks:
    1. Token format is valid (two parts separated by '.')
    2. HMAC signature is correct (constant-time comparison)
    3. Token has not expired
    4. Nonce has not been used before (one-time use)

    Args:
        token: The token string to validate.

    Returns:
        Tuple of (valid: bool, incident_id: str, approver_role: str, reason: str)
        On failure: valid=False, incident_id="", approver_role="", reason=<explanation>
        On success: valid=True, incident_id=<id>, approver_role=<role>, reason="ok"
    """
    _prune_expired_nonces()

    # ── 1. Parse structure ────────────────────────────────────────────────────
    parts = token.split(".")
    if len(parts) != 2:
        logger.warning("approval_tokens.invalid_format", token_preview=token[:20])
        return False, "", "", "invalid_token_format"

    payload_b64, provided_signature = parts[0], parts[1]

    # ── 2. Verify signature (constant-time) ───────────────────────────────────
    expected_signature = _sign(payload_b64)
    if not hmac.compare_digest(expected_signature, provided_signature):
        logger.warning("approval_tokens.signature_invalid", token_preview=token[:20])
        return False, "", "", "invalid_signature"

    # ── 3. Decode payload ─────────────────────────────────────────────────────
    try:
        payload_json = _b64url_decode(payload_b64).decode("utf-8")
        payload: dict[str, Any] = json.loads(payload_json)
    except Exception as exc:
        logger.warning("approval_tokens.decode_failed", error=str(exc))
        return False, "", "", "payload_decode_failed"

    incident_id: str = payload.get("incident_id", "")
    approver_role: str = payload.get("approver_role", "")
    nonce: str = payload.get("nonce", "")
    expires_at: float = payload.get("expires_at", 0.0)

    # ── 4. Check expiry ───────────────────────────────────────────────────────
    now = time.time()
    if now > expires_at:
        logger.warning(
            "approval_tokens.expired",
            incident_id=incident_id,
            expired_at=datetime.fromtimestamp(expires_at, tz=timezone.utc).isoformat(),
        )
        return False, incident_id, approver_role, "token_expired"

    # ── 5. Check one-time use ─────────────────────────────────────────────────
    if nonce in _USED_NONCES:
        logger.warning(
            "approval_tokens.replay_attempt",
            incident_id=incident_id,
            approver_role=approver_role,
            nonce_prefix=nonce[:8],
        )
        return False, incident_id, approver_role, "token_already_used"

    # ── 6. Mark nonce as used ─────────────────────────────────────────────────
    _USED_NONCES[nonce] = expires_at

    logger.info(
        "approval_tokens.validated",
        incident_id=incident_id,
        approver_role=approver_role,
        nonce_prefix=nonce[:8],
    )
    return True, incident_id, approver_role, "ok"


def store_nonce(nonce: str, expires_at: float) -> None:
    """
    Explicitly mark a nonce as used.
    Called when a token is consumed outside the normal validate flow
    (e.g. after recording the approval in the audit database).

    Args:
        nonce:      The nonce string from the token payload.
        expires_at: Unix timestamp when the token expires.
    """
    _USED_NONCES[nonce] = expires_at
    logger.debug("approval_tokens.nonce_stored", nonce_prefix=nonce[:8])


def decode_token_payload(token: str) -> dict[str, Any] | None:
    """
    Decode the payload of a token WITHOUT validating it.
    Used for logging and display purposes only — never for authorisation.

    Returns:
        Payload dict or None if the token cannot be decoded.
    """
    parts = token.split(".")
    if len(parts) != 2:
        return None
    try:
        payload_json = _b64url_decode(parts[0]).decode("utf-8")
        return json.loads(payload_json)
    except Exception:
        return None
