"""Zero-knowledge credential vault for Wirebox agents.

All encryption and decryption happen client-side; the Wirebox API only ever
stores ciphertext.
"""

from wirebox.vault.client import UnlockedVault, VaultClient
from wirebox.vault.crypto import generate_vault_key
from wirebox.vault.totp import TOTPCode, TOTPConfig, generate_totp, parse_totp_uri
from wirebox.vault.types import (
    ApiKeyPayload,
    DecryptedSecret,
    LoginPayload,
    OtherPayload,
    SecretPayload,
    VaultAccessGrant,
    VaultInfo,
    VaultInitializeResult,
    VaultSecretSummary,
    VaultSecretType,
)

__all__ = [
    "VaultClient",
    "UnlockedVault",
    "generate_vault_key",
    "generate_totp",
    "parse_totp_uri",
    "TOTPConfig",
    "TOTPCode",
    "VaultSecretType",
    "LoginPayload",
    "ApiKeyPayload",
    "OtherPayload",
    "SecretPayload",
    "VaultInfo",
    "VaultSecretSummary",
    "DecryptedSecret",
    "VaultAccessGrant",
    "VaultInitializeResult",
]
