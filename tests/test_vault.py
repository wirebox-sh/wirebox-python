"""Vault tests: crypto round-trips, RFC 6238 TOTP vectors, and a client flow
against an in-memory fake of the vault API."""

from __future__ import annotations

from typing import Any

import pytest
from cryptography.exceptions import InvalidTag

from wirebox.vault import crypto
from wirebox.vault.client import VaultClient
from wirebox.vault.totp import TOTPConfig, generate_totp, parse_totp_uri
from wirebox.vault.types import ApiKeyPayload, LoginPayload, OtherPayload, VaultSecretType

VAULT_KEY = "WBV-TEST-KEY-abc123!"
RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"  # RFC 6238 seed in base32


# --------------------------------------------------------------------------- crypto


def test_derive_is_deterministic_and_auth_hash_matches():
    salt = crypto.generate_salt()
    a = crypto.derive_master_key(VAULT_KEY, salt)
    b = crypto.derive_master_key(VAULT_KEY, salt)
    assert a == b and len(a) == 32
    assert crypto.compute_auth_hash(a) == crypto.compute_auth_hash(b)
    assert len(crypto.compute_auth_hash(a)) == 64


def test_oek_wrap_unwrap_and_wrong_key():
    salt = crypto.generate_salt()
    mk = crypto.derive_master_key(VAULT_KEY, salt)
    oek = crypto.generate_org_key()
    assert crypto.unwrap_org_key(mk, crypto.wrap_org_key(mk, oek)) == oek

    wrong = crypto.derive_master_key("WBV-WRONG-000000!", salt)
    with pytest.raises(InvalidTag):
        crypto.unwrap_org_key(wrong, crypto.wrap_org_key(mk, oek))


def test_payload_round_trip_and_aad():
    oek = crypto.generate_org_key()
    payload = {"username": "eva", "password": "s3cr3t", "service_url": "https://x"}
    blob = crypto.encrypt_payload(oek, payload, "vsec_1")
    assert crypto.decrypt_payload(oek, blob, "vsec_1") == payload
    with pytest.raises(InvalidTag):
        crypto.decrypt_payload(oek, blob, "vsec_2")  # wrong AAD


def test_init_material_unlockable():
    material, oek = crypto.create_vault_init_material(VAULT_KEY)
    mk = crypto.derive_master_key(
        VAULT_KEY, crypto.from_base64(material.kdf_salt), material.kdf_params
    )
    assert crypto.compute_auth_hash(mk) == material.auth_hash
    assert crypto.unwrap_org_key(mk, material.wrapped_org_key) == oek


# --------------------------------------------------------------------------- totp


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (59, "94287082"),
        (1111111109, "07081804"),
        (1111111111, "14050471"),
        (1234567890, "89005924"),
    ],
)
def test_totp_rfc6238_sha1(seconds, expected):
    code = generate_totp(
        TOTPConfig(secret=RFC_SECRET, algorithm="sha1", digits=8, period=30), seconds * 1000
    )
    assert code.code == expected


def test_totp_parse_uri_and_six_digits():
    cfg = parse_totp_uri(f"otpauth://totp/Acme?secret={RFC_SECRET}&digits=8&period=30")
    assert cfg.digits == 8
    six = generate_totp(TOTPConfig(secret=RFC_SECRET), 59 * 1000)
    assert six.code == "287082"


# --------------------------------------------------------------------------- fake server


class FakeVaultTransport:
    """Minimal in-memory fake of the vault API. Stores only ciphertext + metadata."""

    def __init__(self) -> None:
        self.vault: dict[str, Any] | None = None
        self.secrets: list[dict[str, Any]] = []
        self.access: list[dict[str, Any]] = []

    def get(self, path: str, *, params: dict[str, Any] | None = None, **_: Any) -> Any:
        if path == "/v1/vault":
            if not self.vault:
                return {"initialized": False}
            return {
                "initialized": True,
                "id": "vlt_x",
                "kdf_salt": self.vault["kdf_salt"],
                "kdf_params": self.vault["kdf_params"],
            }
        if path == "/v1/vault/unlock":
            assert params and params["auth_hash"] == self.vault["auth_hash"]
            return {
                "wrapped_org_key": self.vault["wrapped_org_key"],
                "kdf_params": self.vault["kdf_params"],
                "secrets": self.secrets,
            }
        if path == "/v1/vault/secrets":
            t = (params or {}).get("type")
            rows = [
                {k: v for k, v in s.items() if k != "encrypted_payload"}
                | {"created_at": "t", "updated_at": "t"}
                for s in self.secrets
                if not t or s["type"] == t
            ]
            return {"secrets": rows}
        if path.endswith("/access"):
            sid = path.split("/")[4]
            return {"access": [a for a in self.access if a["secret_id"] == sid]}
        raise AssertionError(path)

    def post(self, path: str, *, json: Any = None, **_: Any) -> Any:
        if path == "/v1/vault/initialize":
            self.vault = dict(json)
            return {
                "initialized": True,
                "id": "vlt_x",
                "kdf_salt": json["kdf_salt"],
                "kdf_params": json["kdf_params"],
            }
        if path == "/v1/vault/secrets":
            self.secrets.append(
                {
                    "id": json["id"],
                    "type": json["type"],
                    "name": json["name"],
                    "description": json.get("description"),
                    "encrypted_payload": json["encrypted_payload"],
                    "created_at": "t",
                    "updated_at": "t",
                }
            )
            return {
                "id": json["id"],
                "type": json["type"],
                "name": json["name"],
                "description": json.get("description"),
                "created_at": "t",
                "updated_at": "t",
            }
        if path.endswith("/access"):
            sid = path.split("/")[4]
            grant = {
                "id": f"vacc_{len(self.access) + 1}",
                "secret_id": sid,
                "identity_id": json["identity_id"],
                "created_at": "t",
            }
            self.access.append(grant)
            return grant
        raise AssertionError(path)

    def patch(self, path: str, *, json: Any = None, **_: Any) -> Any:
        sid = path.split("/")[4]
        s = next(x for x in self.secrets if x["id"] == sid)
        s.update(
            {k: v for k, v in json.items() if k in ("name", "description", "encrypted_payload")}
        )
        return {
            "id": s["id"],
            "type": s["type"],
            "name": s["name"],
            "description": s.get("description"),
            "created_at": "t",
            "updated_at": "t2",
        }

    def delete(self, path: str, **_: Any) -> Any:
        parts = path.split("/")
        if path.endswith("/access/" + parts[-1]) and len(parts) == 7:
            self.access = [
                a
                for a in self.access
                if not (a["secret_id"] == parts[4] and a["identity_id"] == parts[6])
            ]
        else:
            self.secrets = [s for s in self.secrets if s["id"] != parts[4]]
        return None


def test_client_end_to_end():
    vault_api = VaultClient(FakeVaultTransport())

    assert vault_api.info().initialized is False
    result = vault_api.initialize()
    assert result.vault_key.startswith("WBV-")

    vk = result.vault_key
    unlocked = vault_api.unlock(vk)

    created = unlocked.create_secret(
        type=VaultSecretType.LOGIN,
        name="GitHub",
        payload=LoginPayload(
            username="eva", password="hunter2", totp=TOTPConfig(secret=RFC_SECRET)
        ),
    )
    assert created.id.startswith("vsec_")
    unlocked.create_secret(
        type=VaultSecretType.API_KEY, name="Stripe", payload=ApiKeyPayload(key="sk_live_1")
    )
    unlocked.create_secret(type=VaultSecretType.OTHER, name="Note", payload=OtherPayload(data="x"))

    # ciphertext does not contain the plaintext
    assert "hunter2" not in vault_api._http.secrets[0]["encrypted_payload"]  # type: ignore[attr-defined]

    # name-or-id lookup, decrypted after re-unlock
    reopened = vault_api.unlock(vk)
    assert reopened.get_login("github").username == "eva"
    assert reopened.get_login("GitHub").password == "hunter2"
    assert reopened.get_totp_code("GitHub").code.isdigit()

    # list metadata only
    assert len(vault_api.list_secrets()) == 3
    assert vault_api.list_secrets(type="login")[0].name == "GitHub"

    # update preserves untouched fields
    reopened.update_secret(
        "GitHub",
        name="GitHub2",
        payload=LoginPayload(username="eva", password="new", totp=TOTPConfig(secret=RFC_SECRET)),
    )
    again = vault_api.unlock(vk)
    assert again.get_login("GitHub2").password == "new"

    # access grant / list / revoke
    vault_api.grant_access(created.id, "agt_bot")
    assert len(vault_api.list_access(created.id)) == 1
    vault_api.revoke_access(created.id, "agt_bot")
    assert vault_api.list_access(created.id) == []

    # delete via unlocked
    again.delete_secret("GitHub2")
    with pytest.raises(KeyError):
        again.get_secret("GitHub2")


class AsyncFakeVaultTransport:
    """Async wrapper over the in-memory fake (methods just await the sync logic)."""

    def __init__(self) -> None:
        self._s = FakeVaultTransport()

    async def get(self, path: str, *, params: dict[str, Any] | None = None, **k: Any) -> Any:
        return self._s.get(path, params=params, **k)

    async def post(self, path: str, *, json: Any = None, **k: Any) -> Any:
        return self._s.post(path, json=json, **k)

    async def patch(self, path: str, *, json: Any = None, **k: Any) -> Any:
        return self._s.patch(path, json=json, **k)

    async def delete(self, path: str, **k: Any) -> Any:
        return self._s.delete(path, **k)


async def test_async_client_end_to_end():
    from wirebox.vault.async_client import AsyncVaultClient

    vault_api = AsyncVaultClient(AsyncFakeVaultTransport())
    assert (await vault_api.info()).initialized is False

    vk = (await vault_api.initialize()).vault_key
    unlocked = await vault_api.unlock(vk)
    created = await unlocked.create_secret(
        type=VaultSecretType.LOGIN,
        name="GitHub",
        payload=LoginPayload(
            username="eva", password="hunter2", totp=TOTPConfig(secret=RFC_SECRET)
        ),
    )

    reopened = await vault_api.unlock(vk)
    assert reopened.get_login("github").password == "hunter2"  # name-or-id, sync accessor
    assert reopened.get_totp_code("GitHub").code.isdigit()
    assert len(await vault_api.list_secrets()) == 1

    await reopened.update_secret(
        "GitHub",
        name="GH2",
        payload=LoginPayload(username="eva", password="new", totp=TOTPConfig(secret=RFC_SECRET)),
    )
    again = await vault_api.unlock(vk)
    assert again.get_login("GH2").password == "new"

    await vault_api.grant_access(created.id, "agt_bot")
    assert len(await vault_api.list_access(created.id)) == 1
    await vault_api.revoke_access(created.id, "agt_bot")
    assert await vault_api.list_access(created.id) == []

    await again.delete_secret("GH2")
    with pytest.raises(KeyError):
        again.get_secret("GH2")


def test_grant_access_by_secret_name():
    vault_api = VaultClient(FakeVaultTransport())
    vk = vault_api.initialize().vault_key
    v = vault_api.unlock(vk)
    v.create_secret(type=VaultSecretType.OTHER, name="Note", payload=OtherPayload(data="x"))

    grant = vault_api.grant_access("Note", "agt_1")  # by secret name
    assert grant.identity_id == "agt_1"
    assert len(vault_api.list_access("note")) == 1  # case-insensitive by name
    vault_api.revoke_access("Note", "agt_1")  # by name
    assert vault_api.list_access("Note") == []
