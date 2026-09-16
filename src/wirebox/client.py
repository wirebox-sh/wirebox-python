"""Wirebox Python SDK — Synchronous Client.

Main synchronous entry point for interacting with the Wirebox Edge Core API.
"""

from __future__ import annotations

import os
from typing import Any, Literal
from urllib.parse import quote

import httpx

from wirebox._http import DEFAULT_BASE_URL, DEFAULT_TIMEOUT_SECONDS, SyncHttpTransport
from wirebox.identity import AgentIdentity
from wirebox.mail import MailClient
from wirebox.tunnels import TunnelsClient
from wirebox.types import IdentityData, WhoamiResult
from wirebox.webhooks import WebhooksClient


class Wirebox:
    """Synchronous client for the Wirebox API.

    Example:
        >>> from wirebox import Wirebox
        >>> client = Wirebox(api_key="wb_live_...")
        >>> agent = client.create_identity("sales-bot", display_name="Sales Bot")
        >>> agent.send_email(to="customer@example.com", subject="Hi", text="Hello!")
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http_client: httpx.Client | None = None,
    ) -> None:
        resolved_key = api_key or os.environ.get("WIREBOX_API_KEY")
        resolved_url = base_url or os.environ.get("WIREBOX_BASE_URL") or DEFAULT_BASE_URL

        self._transport = SyncHttpTransport(
            api_key=resolved_key,
            base_url=resolved_url,
            timeout=timeout,
            client=http_client,
        )

        self.mail = MailClient(self._transport)
        self.tunnels = TunnelsClient(self._transport)
        self.webhooks = WebhooksClient(self._transport)

    def create_identity(
        self,
        agent_handle: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
    ) -> AgentIdentity:
        """Provisions a new agent identity with an atomic dedicated mailbox and network tunnel."""
        payload: dict[str, Any] = {
            "agent_handle": agent_handle.strip().lstrip("@").lower(),
        }
        if display_name is not None:
            payload["display_name"] = display_name
        if description is not None:
            payload["description"] = description

        data = self._transport.post("/v1/identities", json=payload)
        return AgentIdentity(IdentityData.from_dict(data), self._transport)

    def get_identity(self, handle_or_id: str) -> AgentIdentity:
        """Retrieves an existing agent identity by handle or ID."""
        clean_handle = handle_or_id.strip().lstrip("@").lower()
        data = self._transport.get(f"/v1/identities/{quote(clean_handle)}")
        return AgentIdentity(IdentityData.from_dict(data), self._transport)

    def list_identities(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: Literal["active", "archived", "deleted"] | None = None,
    ) -> list[AgentIdentity]:
        """Lists agent identities in the organization."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status

        data = self._transport.get("/v1/identities", params=params)
        raw_items = data.get("identities", []) if isinstance(data, dict) else []
        return [AgentIdentity(IdentityData.from_dict(item), self._transport) for item in raw_items]

    def whoami(self) -> WhoamiResult:
        """Inspects the active API key and organization authentication context."""
        data = self._transport.get("/v1/whoami")
        return WhoamiResult.from_dict(data)

    def close(self) -> None:
        """Closes underlying HTTP connections."""
        self._transport.close()

    def __enter__(self) -> Wirebox:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
