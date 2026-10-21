"""Synchronous vault client.

Two layers:
  - ``VaultClient``:   metadata/admin operations that do not need the vault key.
  - ``UnlockedVault``: returned by ``unlock()``, holds the Organization
                       Encryption Key in memory and performs payload crypto.

The server filters ciphertext by the caller's identity, so an agent key's
``unlock()`` returns only the secrets granted to it.
"""

from __future__ import annotations

import os
import secrets as _secrets
from typing import Any

from wirebox.vault import crypto
from wirebox.vault.totp import TOTPCode, generate_totp
from wirebox.vault.types import (
    DecryptedSecret,
    SecretPayload,
    VaultAccessGrant,
    VaultInfo,
    VaultInitializeResult,
    VaultSecretSummary,
    VaultSecretType,
    payload_from_wire,
    payload_to_wire,
)

_BASE = "/v1/vault"


def _generate_secret_id() -> str:
    return "vsec_" + _secrets.token_hex(16)


class VaultClient:
    """Admin/metadata vault operations. Obtain decryption via :meth:`unlock`."""

    def __init__(self, transport: Any) -> None:
        self._http = transport

    def info(self) -> VaultInfo:
        """Vault metadata for the caller's organization (never returns ciphertext)."""
        return VaultInfo.from_wire(self._http.get(_BASE))

    def initialize(
        self, vault_key: str | None = None, kdf_params: dict[str, Any] | None = None
    ) -> VaultInitializeResult:
        """Initialize the organization vault.

        All cryptographic material is produced client-side. When ``vault_key`` is
        omitted a strong key is generated and returned — the vault has no recovery
        codes, so store it securely.
        """
        key = vault_key or crypto.generate_vault_key()
        material, _ = crypto.create_vault_init_material(key, kdf_params)
        info = self._http.post(
            f"{_BASE}/initialize",
            json={
                "kdf_salt": material.kdf_salt,
                "kdf_params": material.kdf_params,
                "wrapped_org_key": material.wrapped_org_key,
                "auth_hash": material.auth_hash,
            },
        )
        return VaultInitializeResult(
            vault_key=key,
            info=VaultInfo.from_wire(info),
            warning=(
                "Store this vault key securely. It cannot be recovered; losing it "
                "requires re-initializing the vault."
            ),
        )

    def unlock(self, vault_key: str | None = None) -> UnlockedVault:
        """Unlock the vault and return a crypto-enabled handle.

        ``vault_key`` falls back to the ``WIREBOX_VAULT_KEY`` environment variable.
        """
        key = vault_key or os.environ.get("WIREBOX_VAULT_KEY")
        if not key:
            raise ValueError(
                "A vault key is required. Pass it to unlock() or set WIREBOX_VAULT_KEY."
            )

        info = self.info()
        if not info.initialized or not info.kdf_salt:
            raise ValueError("No vault exists for this organization.")

        master_key = crypto.derive_master_key(
            key, crypto.from_base64(info.kdf_salt), info.kdf_params
        )
        auth_hash = crypto.compute_auth_hash(master_key)
        data = self._http.get(f"{_BASE}/unlock", params={"auth_hash": auth_hash})

        try:
            org_key = crypto.unwrap_org_key(master_key, data["wrapped_org_key"])
        except Exception as exc:  # noqa: BLE001
            raise ValueError("The vault key did not match. Unlock failed.") from exc

        decrypted: list[DecryptedSecret] = []
        for raw in data.get("secrets", []):
            payload = payload_from_wire(
                raw["type"], crypto.decrypt_payload(org_key, raw["encrypted_payload"], raw["id"])
            )
            decrypted.append(
                DecryptedSecret(
                    id=raw["id"],
                    type=raw["type"],
                    name=raw["name"],
                    description=raw.get("description"),
                    created_at=raw["created_at"],
                    updated_at=raw["updated_at"],
                    payload=payload,
                )
            )
        return UnlockedVault(self._http, org_key, decrypted)

    def list_secrets(self, *, type: str | None = None) -> list[VaultSecretSummary]:
        """List secret metadata (no ciphertext). Scoped keys see only their grants."""
        params = {"type": type} if type else None
        res = self._http.get(f"{_BASE}/secrets", params=params)
        return [VaultSecretSummary.from_wire(s) for s in res.get("secrets", [])]

    def _resolve_secret_id(self, name_or_id: str) -> str:
        """Resolve a secret name to its id (ids starting with ``vsec_`` pass through)."""
        if name_or_id.startswith("vsec_"):
            return name_or_id
        matches = [s for s in self.list_secrets() if s.name.lower() == name_or_id.lower()]
        if len(matches) == 1:
            return matches[0].id
        if len(matches) > 1:
            raise ValueError(
                f"Multiple secrets are named '{name_or_id}'. Use the secret id (vsec_...)."
            )
        raise KeyError(f"No secret named or identified by '{name_or_id}'.")

    def list_access(self, secret: str) -> list[VaultAccessGrant]:
        """List the identities granted access to a secret (by name or id). Admin only."""
        res = self._http.get(f"{_BASE}/secrets/{self._resolve_secret_id(secret)}/access")
        return [VaultAccessGrant.from_wire(a) for a in res.get("access", [])]

    def grant_access(self, secret: str, identity_id: str) -> VaultAccessGrant:
        """Grant an agent identity access to a secret (by name or id). Admin only."""
        return VaultAccessGrant.from_wire(
            self._http.post(
                f"{_BASE}/secrets/{self._resolve_secret_id(secret)}/access",
                json={"identity_id": identity_id},
            )
        )

    def revoke_access(self, secret: str, identity_id: str) -> None:
        """Revoke an identity's access to a secret (by name or id). Admin only."""
        self._http.delete(f"{_BASE}/secrets/{self._resolve_secret_id(secret)}/access/{identity_id}")

    def delete_secret(self, secret: str) -> None:
        """Permanently delete a secret (by name or id), and its access grants. Admin only."""
        self._http.delete(f"{_BASE}/secrets/{self._resolve_secret_id(secret)}")


class UnlockedVault:
    """A vault unlocked with a valid vault key. Holds the OEK in memory."""

    def __init__(self, transport: Any, org_key: bytes, secrets: list[DecryptedSecret]) -> None:
        self._http = transport
        self._org_key = org_key
        self._by_id: dict[str, DecryptedSecret] = {s.id: s for s in secrets}

    @property
    def secrets(self) -> list[DecryptedSecret]:
        """All secrets decrypted at unlock (for an agent key, only its grants)."""
        return list(self._by_id.values())

    def get_secret(self, name_or_id: str) -> DecryptedSecret:
        """Get a decrypted secret by id, or by name (case-insensitive)."""
        if name_or_id in self._by_id:
            return self._by_id[name_or_id]
        lower = name_or_id.lower()
        matches = [s for s in self._by_id.values() if s.name.lower() == lower]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise ValueError(
                f"Multiple secrets are named '{name_or_id}'. Use the secret id (vsec_...)."
            )
        raise KeyError(f"No secret named or identified by '{name_or_id}' in the unlocked vault.")

    def get_by_name(self, name: str) -> DecryptedSecret:
        return self.get_secret(name)

    def _get_typed(self, name_or_id: str, type_: str) -> SecretPayload:
        secret = self.get_secret(name_or_id)
        if secret.type != type_:
            raise TypeError(f"Secret '{secret.name}' is of type '{secret.type}', not '{type_}'.")
        return secret.payload

    def get_login(self, name_or_id: str):  # -> LoginPayload
        return self._get_typed(name_or_id, VaultSecretType.LOGIN)

    def get_api_key(self, name_or_id: str):  # -> ApiKeyPayload
        return self._get_typed(name_or_id, VaultSecretType.API_KEY)

    def get_other(self, name_or_id: str):  # -> OtherPayload
        return self._get_typed(name_or_id, VaultSecretType.OTHER)

    def get_totp_code(self, name_or_id: str) -> TOTPCode:
        """Current TOTP code for a ``login`` secret that has TOTP configured."""
        login = self.get_login(name_or_id)
        if getattr(login, "totp", None) is None:
            raise ValueError(f"Secret '{name_or_id}' has no TOTP configured.")
        return generate_totp(login.totp)

    def create_secret(
        self,
        *,
        type: str,
        name: str,
        payload: SecretPayload | dict[str, Any],
        description: str | None = None,
    ) -> DecryptedSecret:
        """Create a new secret: encrypts the payload client-side, then stores it."""
        secret_id = _generate_secret_id()
        encrypted = crypto.encrypt_payload(self._org_key, payload_to_wire(payload), secret_id)
        body: dict[str, Any] = {
            "id": secret_id,
            "type": type,
            "name": name,
            "encrypted_payload": encrypted,
        }
        if description is not None:
            body["description"] = description
        summary = self._http.post(f"{_BASE}/secrets", json=body)
        secret = DecryptedSecret(
            id=summary["id"],
            type=summary["type"],
            name=summary["name"],
            description=summary.get("description"),
            created_at=summary["created_at"],
            updated_at=summary["updated_at"],
            payload=payload_from_wire(type, payload_to_wire(payload)),
        )
        self._by_id[secret.id] = secret
        return secret

    def update_secret(
        self,
        name_or_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        payload: SecretPayload | dict[str, Any] | None = None,
    ) -> DecryptedSecret:
        """Update a secret's metadata and/or payload (re-encrypts when given)."""
        target = self.get_secret(name_or_id)
        body: dict[str, Any] = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if payload is not None:
            body["encrypted_payload"] = crypto.encrypt_payload(
                self._org_key, payload_to_wire(payload), target.id
            )

        summary = self._http.patch(f"{_BASE}/secrets/{target.id}", json=body)
        new_payload = (
            payload_from_wire(target.type, payload_to_wire(payload))
            if payload is not None
            else target.payload
        )
        secret = DecryptedSecret(
            id=summary["id"],
            type=summary["type"],
            name=summary["name"],
            description=summary.get("description"),
            created_at=summary["created_at"],
            updated_at=summary["updated_at"],
            payload=new_payload,
        )
        self._by_id[secret.id] = secret
        return secret

    def delete_secret(self, name_or_id: str) -> None:
        """Delete a secret (and its access grants), by id or name."""
        target = self.get_secret(name_or_id)
        self._http.delete(f"{_BASE}/secrets/{target.id}")
        self._by_id.pop(target.id, None)
