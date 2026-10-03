"""Wirebox Python SDK — Asynchronous Client.

Main asynchronous entry point for interacting with the Wirebox Edge Core API.
"""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

import httpx

from wirebox._config import resolve_client_settings
from wirebox._http import DEFAULT_TIMEOUT_SECONDS, AsyncHttpTransport
from wirebox.exceptions import NotFoundError
from wirebox.identity import AsyncAgentIdentity
from wirebox.imessage import AsyncIMessageClient
from wirebox.mail import AsyncMailClient
from wirebox.phone import AsyncPhoneClient
from wirebox.tunnels import AsyncTunnelsClient
from wirebox.types import IdentityData, WhoamiResult
from wirebox.webhooks import AsyncWebhooksClient


class AsyncWirebox:
    """Asynchronous client for the Wirebox API.

    Example:
        >>> from wirebox import AsyncWirebox
        >>> async with AsyncWirebox() as client:  # Automatically reads from ~/.wirebox/credentials or ~/.wirebox/config
        ...     agent = await client.create_identity("sales-bot", display_name="Sales Bot")
        ...     await agent.send_email(to="customer@example.com", subject="Hi", text="Hello!")
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        resolved_key, resolved_url = resolve_client_settings(
            api_key=api_key,
            base_url=base_url,
        )

        self._api_key = resolved_key
        self._base_url = resolved_url

        self._transport = AsyncHttpTransport(
            api_key=resolved_key,
            base_url=resolved_url,
            timeout=timeout,
            client=http_client,
        )

        self.mail = AsyncMailClient(self._transport)
        self.tunnels = AsyncTunnelsClient(self._transport, resolved_key, resolved_url)
        self.webhooks = AsyncWebhooksClient(self._transport)
        self.imessage = AsyncIMessageClient(self._transport)
        self.phone = AsyncPhoneClient(self._transport)

    async def create_identity(
        self,
        agent_handle: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
    ) -> AsyncAgentIdentity:
        """Provisions a new agent identity with an atomic dedicated mailbox and network tunnel."""
        payload: dict[str, Any] = {
            "agent_handle": agent_handle.strip().lstrip("@").lower(),
        }
        if display_name is not None:
            payload["display_name"] = display_name
        if description is not None:
            payload["description"] = description

        data = await self._transport.post("/v1/identities", json=payload)
        return AsyncAgentIdentity(
            IdentityData.from_dict(data),
            self._transport,
            self._api_key,
            self._base_url,
        )

    async def get_identity(self, handle_or_id: str | None = None) -> AsyncAgentIdentity:
        """Retrieves an existing agent identity by handle.

        If handle_or_id is omitted, returns the caller's scoped identity or the primary identity.
        """
        if handle_or_id:
            clean = handle_or_id.strip().lstrip("@").lower()
            if not clean.startswith("agt_"):
                data = await self._transport.get(f"/v1/identities/{quote(clean)}")
                return AsyncAgentIdentity(
                    IdentityData.from_dict(data),
                    self._transport,
                    self._api_key,
                    self._base_url,
                )

        # Handle omitted or starts with agt_: query /v1/identities
        all_agents = await self.list_identities()
        if not all_agents:
            raise NotFoundError(
                404,
                "identity_not_found",
                "No agent identities found in this organization.",
            )

        if handle_or_id:
            clean = handle_or_id.strip().lstrip("@").lower()
            for ag in all_agents:
                if ag.id.lower() == clean or ag.agent_handle.lower() == clean:
                    return ag
            raise NotFoundError(
                404,
                "identity_not_found",
                f"Identity '{handle_or_id}' not found.",
            )

        return all_agents[0]

    async def list_identities(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: Literal["active", "archived", "deleted"] | None = None,
    ) -> list[AsyncAgentIdentity]:
        """Lists agent identities in the organization."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status

        data = await self._transport.get("/v1/identities", params=params)
        if isinstance(data, list):
            raw_items = data
        elif isinstance(data, dict):
            raw_items = data.get("identities", [])
        else:
            raw_items = []
        return [
            AsyncAgentIdentity(
                IdentityData.from_dict(item),
                self._transport,
                self._api_key,
                self._base_url,
            )
            for item in raw_items
        ]

    async def whoami(self) -> WhoamiResult:
        """Inspects the active API key and organization authentication context. Maps to GET /v1/me."""
        data = await self._transport.get("/v1/me")
        return WhoamiResult.from_dict(data)

    async def me(self) -> WhoamiResult:
        """Alias for whoami()."""
        return await self.whoami()

    async def aclose(self) -> None:
        """Closes underlying HTTP connections."""
        await self._transport.aclose()

    async def __aenter__(self) -> AsyncWirebox:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
