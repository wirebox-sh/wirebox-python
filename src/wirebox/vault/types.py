"""Vault types.

Secret payloads are JSON-encoded, encrypted client-side, and stored as opaque
ciphertext. Field names are the canonical on-the-wire keys shared across all
Wirebox SDKs, so an encrypted payload written by one SDK decodes in another.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from wirebox.vault.totp import TOTPConfig


class VaultSecretType(StrEnum):
    LOGIN = "login"
    API_KEY = "api_key"
    OTHER = "other"


@dataclass
class LoginPayload:
    username: str | None = None
    email: str | None = None
    password: str | None = None
    service_url: str | None = None
    totp: TOTPConfig | None = None

    def to_wire(self) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if self.username is not None:
            out["username"] = self.username
        if self.email is not None:
            out["email"] = self.email
        if self.password is not None:
            out["password"] = self.password
        if self.service_url is not None:
            out["service_url"] = self.service_url
        if self.totp is not None:
            out["totp"] = {
                "secret": self.totp.secret,
                "algorithm": self.totp.algorithm,
                "digits": self.totp.digits,
                "period": self.totp.period,
            }
        return out

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> LoginPayload:
        totp = data.get("totp")
        return cls(
            username=data.get("username"),
            email=data.get("email"),
            password=data.get("password"),
            service_url=data.get("service_url"),
            totp=TOTPConfig(
                secret=totp["secret"],
                algorithm=totp.get("algorithm", "sha1"),
                digits=totp.get("digits", 6),
                period=totp.get("period", 30),
            )
            if totp
            else None,
        )


@dataclass
class ApiKeyPayload:
    key: str
    service_url: str | None = None

    def to_wire(self) -> dict[str, Any]:
        out: dict[str, Any] = {"key": self.key}
        if self.service_url is not None:
            out["service_url"] = self.service_url
        return out

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> ApiKeyPayload:
        return cls(key=data["key"], service_url=data.get("service_url"))


@dataclass
class OtherPayload:
    data: str

    def to_wire(self) -> dict[str, Any]:
        return {"data": self.data}

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> OtherPayload:
        return cls(data=data["data"])


SecretPayload = LoginPayload | ApiKeyPayload | OtherPayload


def payload_to_wire(payload: SecretPayload | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    return payload.to_wire()


def payload_from_wire(secret_type: str, data: dict[str, Any]) -> SecretPayload:
    if secret_type == VaultSecretType.LOGIN:
        return LoginPayload.from_wire(data)
    if secret_type == VaultSecretType.API_KEY:
        return ApiKeyPayload.from_wire(data)
    return OtherPayload.from_wire(data)


@dataclass
class VaultInfo:
    initialized: bool
    id: str | None = None
    kdf_salt: str | None = None
    kdf_params: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> VaultInfo:
        return cls(
            initialized=bool(data.get("initialized")),
            id=data.get("id"),
            kdf_salt=data.get("kdf_salt"),
            kdf_params=data.get("kdf_params") or {},
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )


@dataclass
class VaultSecretSummary:
    id: str
    type: str
    name: str
    description: str | None
    created_at: str
    updated_at: str

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> VaultSecretSummary:
        return cls(
            id=data["id"],
            type=data["type"],
            name=data["name"],
            description=data.get("description"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )


@dataclass
class DecryptedSecret:
    id: str
    type: str
    name: str
    description: str | None
    created_at: str
    updated_at: str
    payload: SecretPayload


@dataclass
class VaultAccessGrant:
    id: str
    secret_id: str
    identity_id: str
    created_at: str

    @classmethod
    def from_wire(cls, data: dict[str, Any]) -> VaultAccessGrant:
        return cls(
            id=data["id"],
            secret_id=data["secret_id"],
            identity_id=data["identity_id"],
            created_at=data["created_at"],
        )


@dataclass
class VaultInitializeResult:
    vault_key: str
    info: VaultInfo
    warning: str


__all__ = [
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
    "payload_to_wire",
    "payload_from_wire",
]
