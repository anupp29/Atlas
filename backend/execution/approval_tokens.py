"""
Cryptographic one-time approval tokens for PCI-DSS and SOX dual sign-off.
Every token is time-limited, incident-scoped, and single-use.

Uses HMAC-SHA256 signing with the ATLAS_SECRET_KEY environment variable.
Missing secret key = hard startup failure. No weak defaults. Ever.

Nonces are persisted to SQLite so replay attacks are blocked across server restarts.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator

import structlog

logger = structlog.get_logger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Startup validation
# ─────────────────────────────────────────────────────────────────────────────

_SECRET_KEY_ENV = "ATLAS_SECRET_KEY"
_MIN_KEY_LENGTH = 32  # bytes — NIST minimum for HMAC-SHA256
_NONCE_DB_ENV = "ATLAS_AUDIT_DB_PATH"  # reuse audit DB path for nonce store
_NONCE_RETENTION_SECONDS = 7200  # 2 hours


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
# Persistent nonce store — SQLite-backed, survives server restarts
# ─────────────────────────────────────────────────────────────────────────────

def _get_nonce_db_path() -> str:
    """Derive nonce DB path from environment. Stored alongside the audit DB."""
    audit_path = os.environ.get(_NONCE_DB_ENV, "")
    if not audit_path:
        raise RuntimeError(
            f"Environment variable '{_NONCE_DB_ENV}' is not set. "
            "Cannot initialise nonce store for approval tokens."
        )
    # Store nonces in a sibling file to the audit DB
    return str(Path(audit_path).parent / "atlas_nonces.db")


@contextmanager
def _nonce_conn() -> Generator[sqlite3.Connection, None, None]:
    """Open a WAL-mode SQLite connection to the nonce store."""
    path = _get_nonce_db_path()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
    finally:
        conn.close()


def _initialise_nonce_db() -> None:
    """Create the nonces table if it does not exist. Called at module load."""
    with _nonce_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS used_nonces (
                nonce TEXT PRIMARY KEY,
                expires_at REAL NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nonces_expires ON used_nonces(expires_at)")
        conn.commit()


def _is_nonce_used(nonce: str) -> bool:
    """Return True if the nonce exists in the persistent store."""
    with _nonce_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM used_nonces WHERE nonce = ?", (nonce,)
        ).fetchone()
        return row is not None


def _mark_nonce_used(nonce: str, expires_at: float) -> None:
    """Persist a nonce as used. Idempotent."""
    with _nonce_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO used_nonces (nonce, expires_at) VALUES (?, ?)",
            (nonce, expires_at),
        )
        conn.commit()


def _prune_expired_nonces() -> None:
    """Delete nonces that expired more than _NONCE_RETENTION_SECONDS ago."""
    cutoff = time.time() - _NONCE_RETENTION_SECONDS
    with _nonce_conn() as conn:
        conn.execute("DELETE FROM used_nonces WHERE expires_at < ?", (cutoff,))
        conn.commit()


# Initialise on module load — safe to call multiple times
_initialise_nonce_db()


# ─────────────────────────────────────────────────────────────────────────────
# Token format
# ─────────────────────────────────────────────────────────────────────────────


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

    # ── 5. Check one-time use (persistent — survives restarts) ────────────────
    if _is_nonce_used(nonce):
        logger.warning(
            "approval_tokens.replay_attempt",
            incident_id=incident_id,
            approver_role=approver_role,
            nonce_prefix=nonce[:8],
        )
        return False, incident_id, approver_role, "token_already_used"

    # ── 6. Mark nonce as used (persisted to SQLite) ───────────────────────────
    _mark_nonce_used(nonce, expires_at)

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
    Called when a token is consumed outside the normal validate flow.

    Args:
        nonce:      The nonce string from the token payload.
        expires_at: Unix timestamp when the token expires.
    """
    _mark_nonce_used(nonce, expires_at)
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
