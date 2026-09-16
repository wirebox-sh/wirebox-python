"""Wirebox Python SDK — Cryptographic Webhook Verification.

Implements HMAC-SHA256 signature verification adhering to docs/api/webhook/events.md.
Uses constant-time comparison (hmac.compare_digest) to prevent timing attacks and
enforces timestamp freshness to protect against replay attacks.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping
from typing import Any


def _get_header(headers: Mapping[str, Any], name: str) -> str | None:
    """Retrieves a header value case-insensitively."""
    lower_name = name.lower()
    for k, v in headers.items():
        if k.lower() == lower_name:
            return str(v) if v is not None else None
    return None


def verify_webhook(
    *,
    payload: bytes | str,
    headers: Mapping[str, Any],
    secret: str,
    tolerance_seconds: int = 300,
) -> bool:
    """Verifies that an incoming HTTP webhook request was authentically dispatched by Wirebox.

    Args:
        payload: Exact, raw request body as bytes or UTF-8 string.
                 Do NOT parse into a JSON object and re-serialize, as key ordering
                 or whitespace differences will invalidate the HMAC digest.
        headers: Request headers dictionary/mapping (keys are matched case-insensitively).
        secret:  The webhook HMAC signing secret ('whsec_...').
        tolerance_seconds: Maximum allowed clock drift in seconds (default: 300 / 5 minutes).
                           Set to 0 to disable timestamp validation (e.g. for offline replay testing).

    Returns:
        True if the signature is authentic and the request timestamp is fresh; False otherwise.

    Example:
        >>> from wirebox import verify_webhook
        >>> is_valid = verify_webhook(
        ...     payload=raw_body,
        ...     headers=request.headers,
        ...     secret="whsec_xxxxxxxx",
        ... )
    """
    if not secret:
        return False

    raw_body_bytes: bytes = payload.encode("utf-8") if isinstance(payload, str) else payload

    raw_sig = _get_header(headers, "x-wirebox-signature") or ""
    request_id = _get_header(headers, "x-wirebox-request-id") or ""
    timestamp_str = _get_header(headers, "x-wirebox-timestamp") or ""

    # Support compound format: `t=...,v1=...` or `t=...,req=...,v1=...`
    if "t=" in raw_sig and ("v1=" in raw_sig or "sha256=" in raw_sig):
        for part in raw_sig.split(","):
            trimmed = part.strip()
            if "=" in trimmed:
                k, v = trimmed.split("=", 1)
                k = k.strip().lower()
                v = v.strip()
                if k == "t" and not timestamp_str:
                    timestamp_str = v
                elif k == "req" and not request_id:
                    request_id = v
                elif (k in ("v1", "sha256")) and not raw_sig.startswith("sha256="):
                    raw_sig = v

    if not raw_sig or not timestamp_str:
        return False

    received_hex = raw_sig[7:] if raw_sig.startswith("sha256=") else raw_sig

    # 1. Anti-Replay Timestamp Freshness Verification
    try:
        timestamp = float(timestamp_str)
    except (ValueError, TypeError):
        return False

    if tolerance_seconds > 0:
        now = time.time()
        if abs(now - timestamp) > tolerance_seconds:
            return False

    # 2. Reconstruct Canonical Signed Payload String
    # Format: `${requestId ? f"{requestId}." : ""}${timestamp}.${rawBody}`
    prefix = f"{request_id}." if request_id else ""
    header_part = f"{prefix}{timestamp_str}.".encode()
    signed_data = header_part + raw_body_bytes

    # 3. Compute HMAC-SHA256 Digest using the full signing secret
    computed_hex = hmac.new(
        key=secret.encode("utf-8"),
        msg=signed_data,
        digestmod=hashlib.sha256,
    ).hexdigest()

    # 4. Constant-Time Timing-Safe Comparison
    return hmac.compare_digest(computed_hex.lower(), received_hex.lower())
