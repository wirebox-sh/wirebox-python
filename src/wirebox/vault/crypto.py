"""Client-side cryptography for the zero-knowledge vault.

All encryption and decryption happen here; the Wirebox API only ever stores
ciphertext.

    vault key --Argon2id(salt)--> master key
    master key --AES-256-GCM--> wraps the Organization Encryption Key (OEK)
    OEK --AES-256-GCM--> encrypts each secret's JSON payload

The byte formats here match the TypeScript SDK exactly, so a secret encrypted
by one SDK (or the Console) decrypts in the other:

  - KDF:        Argon2id, parameters carried per-vault by the server.
  - Encryption: AES-256-GCM. Each blob is ``[version][algorithm][iv][ct+tag]``,
                base64-encoded. ``iv`` is 12 bytes; the GCM tag is appended to
                the ciphertext (as WebCrypto and ``cryptography`` both do).
  - AAD:        the secret id for payloads; none for the OEK wrap.
  - Salt:       random, stored server-side.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any

from argon2.low_level import Type as _Argon2Type
from argon2.low_level import hash_secret_raw
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Default Argon2id parameters used when initializing a new vault. ``m`` is the
# memory cost in KiB (64 MiB), matching the TypeScript SDK.
DEFAULT_KDF_PARAMS: dict[str, Any] = {"algorithm": "argon2id", "m": 65536, "t": 3, "p": 1}

_MASTER_KEY_BYTES = 32
_OEK_BYTES = 32
_IV_BYTES = 12
_SALT_BYTES = 16
_TAG_BYTES = 16

_BLOB_VERSION = 1
_ALG_AES_256_GCM = 1

# Crockford-ish alphabet (no I, L, O, U) for generated vault keys.
_VK_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def to_base64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def from_base64(value: str) -> bytes:
    return base64.b64decode(value)


# ---------------------------------------------------------------------------
# Versioned blob packing
# ---------------------------------------------------------------------------


def _pack_blob(iv: bytes, ciphertext: bytes) -> str:
    return to_base64(bytes([_BLOB_VERSION, _ALG_AES_256_GCM]) + iv + ciphertext)


def _unpack_blob(value: str) -> tuple[bytes, bytes]:
    blob = from_base64(value)
    if len(blob) < 2 + _IV_BYTES + _TAG_BYTES:
        raise ValueError("Malformed vault ciphertext: blob is too short.")
    version, algorithm = blob[0], blob[1]
    if version != _BLOB_VERSION:
        raise ValueError(f"Unsupported vault ciphertext version: {version}.")
    if algorithm != _ALG_AES_256_GCM:
        raise ValueError(f"Unsupported vault ciphertext algorithm: {algorithm}.")
    return blob[2 : 2 + _IV_BYTES], blob[2 + _IV_BYTES :]


# ---------------------------------------------------------------------------
# AES-256-GCM
# ---------------------------------------------------------------------------


def _aes_gcm_encrypt(key: bytes, plaintext: bytes, aad: bytes | None = None) -> str:
    iv = os.urandom(_IV_BYTES)
    ciphertext = AESGCM(key).encrypt(iv, plaintext, aad)  # ciphertext || tag
    return _pack_blob(iv, ciphertext)


def _aes_gcm_decrypt(key: bytes, blob_b64: str, aad: bytes | None = None) -> bytes:
    iv, ciphertext = _unpack_blob(blob_b64)
    return AESGCM(key).decrypt(iv, ciphertext, aad)


# ---------------------------------------------------------------------------
# Key derivation & material
# ---------------------------------------------------------------------------


def generate_vault_key() -> str:
    """Generate a fresh, high-entropy vault key (~160 bits) for the user to store."""
    raw = os.urandom(20)
    body = "".join(_VK_ALPHABET[b % len(_VK_ALPHABET)] for b in raw)
    groups = [body[i : i + 4] for i in range(0, len(body), 4)]
    return "WBV-" + "-".join(groups)


def generate_salt() -> bytes:
    return os.urandom(_SALT_BYTES)


def generate_org_key() -> bytes:
    return os.urandom(_OEK_BYTES)


def derive_master_key(vault_key: str, salt: bytes, params: dict[str, Any] | None = None) -> bytes:
    """Derive the 32-byte master key from a vault key and salt via Argon2id."""
    p = params or DEFAULT_KDF_PARAMS
    return hash_secret_raw(
        secret=vault_key.encode("utf-8"),
        salt=salt,
        time_cost=int(p.get("t", DEFAULT_KDF_PARAMS["t"])),
        memory_cost=int(p.get("m", DEFAULT_KDF_PARAMS["m"])),
        parallelism=int(p.get("p", DEFAULT_KDF_PARAMS["p"])),
        hash_len=_MASTER_KEY_BYTES,
        type=_Argon2Type.ID,
    )


def compute_auth_hash(master_key: bytes) -> str:
    """The unlock verifier: ``SHA-256(master key)`` as a hex digest."""
    return hashlib.sha256(master_key).hexdigest()


# ---------------------------------------------------------------------------
# OEK wrapping / payload encryption
# ---------------------------------------------------------------------------


def wrap_org_key(master_key: bytes, org_key: bytes) -> str:
    """Wrap (encrypt) the OEK under the master key. No AAD: the vault has one key."""
    return _aes_gcm_encrypt(master_key, org_key)


def unwrap_org_key(master_key: bytes, wrapped_b64: str) -> bytes:
    """Unwrap (decrypt) the OEK. Raises on a wrong vault key."""
    return _aes_gcm_decrypt(master_key, wrapped_b64)


def encrypt_payload(org_key: bytes, payload: Any, secret_id: str) -> str:
    """Encrypt a secret payload with the OEK, binding it to its secret id (AAD)."""
    plaintext = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return _aes_gcm_encrypt(org_key, plaintext, secret_id.encode("utf-8"))


def decrypt_payload(org_key: bytes, blob_b64: str, secret_id: str) -> Any:
    """Decrypt a secret payload blob with the OEK and parse its JSON."""
    plaintext = _aes_gcm_decrypt(org_key, blob_b64, secret_id.encode("utf-8"))
    return json.loads(plaintext.decode("utf-8"))


@dataclass
class VaultInitMaterial:
    """Server-bound material produced client-side at vault initialization."""

    kdf_salt: str  # base64
    kdf_params: dict[str, Any]
    wrapped_org_key: str  # base64 blob
    auth_hash: str  # hex


def create_vault_init_material(
    vault_key: str, params: dict[str, Any] | None = None
) -> tuple[VaultInitMaterial, bytes]:
    """Produce all server-bound material for a new vault, plus the OEK in memory."""
    p = params or DEFAULT_KDF_PARAMS
    salt = generate_salt()
    org_key = generate_org_key()
    master_key = derive_master_key(vault_key, salt, p)
    material = VaultInitMaterial(
        kdf_salt=to_base64(salt),
        kdf_params=p,
        wrapped_org_key=wrap_org_key(master_key, org_key),
        auth_hash=compute_auth_hash(master_key),
    )
    return material, org_key
