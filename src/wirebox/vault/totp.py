"""TOTP (RFC 6238) for ``login`` secrets that carry a TOTP config.

Codes are generated client-side from the decrypted TOTP secret; the Wirebox API
never sees the secret in plaintext. Pure standard library — no extra deps.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

_ALGORITHMS = {"sha1": hashlib.sha1, "sha256": hashlib.sha256, "sha512": hashlib.sha512}


@dataclass
class TOTPConfig:
    """Time-based one-time password configuration (RFC 6238)."""

    secret: str  # base32
    algorithm: str = "sha1"  # sha1 | sha256 | sha512
    digits: int = 6  # 6 | 8
    period: int = 30  # 30 | 60 (seconds)


@dataclass
class TOTPCode:
    code: str
    expires_in_seconds: int
    digits: int
    period: int


def _validate(config: TOTPConfig) -> None:
    if not config.secret:
        raise ValueError("TOTP config requires a 'secret'.")
    if config.algorithm not in _ALGORITHMS:
        raise ValueError(f"Unsupported TOTP algorithm: {config.algorithm}.")
    if config.digits not in (6, 8):
        raise ValueError("TOTP 'digits' must be 6 or 8.")
    if config.period not in (30, 60):
        raise ValueError("TOTP 'period' must be 30 or 60.")


def _base32_decode(secret: str) -> bytes:
    clean = secret.upper().replace(" ", "").rstrip("=")
    # Re-pad to a multiple of 8 for the stdlib decoder.
    padding = "=" * ((8 - len(clean) % 8) % 8)
    try:
        return base64.b32decode(clean + padding)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Invalid base32 TOTP secret.") from exc


def generate_totp(config: TOTPConfig, at_ms: int | None = None) -> TOTPCode:
    """Compute the TOTP code for a config at a given time (defaults to now)."""
    _validate(config)
    now_ms = int(time.time() * 1000) if at_ms is None else at_ms
    counter = int(now_ms / 1000 / config.period)

    message = counter.to_bytes(8, "big")
    digest = hmac.new(_base32_decode(config.secret), message, _ALGORITHMS[config.algorithm]).digest()

    offset = digest[-1] & 0x0F
    binary = (
        ((digest[offset] & 0x7F) << 24)
        | ((digest[offset + 1] & 0xFF) << 16)
        | ((digest[offset + 2] & 0xFF) << 8)
        | (digest[offset + 3] & 0xFF)
    )
    code = str(binary % (10**config.digits)).zfill(config.digits)
    elapsed = int(now_ms / 1000) % config.period
    return TOTPCode(
        code=code,
        expires_in_seconds=config.period - elapsed,
        digits=config.digits,
        period=config.period,
    )


def parse_totp_uri(uri: str) -> TOTPConfig:
    """Parse a standard ``otpauth://totp/...`` provisioning URI into a TOTPConfig."""
    parsed = urlparse(uri)
    if parsed.scheme != "otpauth" or parsed.netloc != "totp":
        raise ValueError("Not an otpauth://totp/ URI.")
    params = parse_qs(parsed.query)

    secret = params.get("secret", [None])[0]
    if not secret:
        raise ValueError("otpauth URI is missing the 'secret' parameter.")

    config = TOTPConfig(secret=secret)
    if "algorithm" in params:
        config.algorithm = params["algorithm"][0].lower()
    if "digits" in params:
        config.digits = int(params["digits"][0])
    if "period" in params:
        config.period = int(params["period"][0])

    _validate(config)
    return config
