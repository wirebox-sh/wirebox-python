"""Wirebox Python SDK — iMessage Client.

Provides synchronous and asynchronous clients to manage real-world iMessage
communication channels for autonomous AI agents.
"""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

from wirebox._http import AsyncHttpTransport, SyncHttpTransport
from wirebox.types import (
    ImessageConversation,
    ImessageMessage,
    ImessageRouterInfo,
    ImessageUser,
    SendImessageResult,
)


def _normalize_handle(agent: str | None) -> str | None:
    if not agent:
        return None
    cleaned = agent.strip()
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    return cleaned.lower()


# ============================================================================
# Synchronous Sub-resources
# ============================================================================


class IMessageConversationsClient:
    """Synchronous operations on iMessage conversations."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self._http = http

    def list(
        self,
        *,
        identity_id: str | None = None,
        status: Literal["connected", "disconnected"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> list[ImessageConversation]:
        """Lists iMessage conversations matching the specified filter criteria."""
        params: dict[str, Any] = {}
        if identity_id is not None:
            params["identity_id"] = identity_id
        if status is not None:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor

        data = self._http.get("/v1/imessage/conversations", params=params)
        raw_items = (
            data.get("data", [])
            if isinstance(data, dict)
            else (data if isinstance(data, list) else [])
        )
        return [ImessageConversation.from_dict(c) for c in raw_items]

    def get(self, conversation_id: str) -> ImessageConversation:
        """Retrieves details of a specific conversation by ID."""
        data = self._http.get(f"/v1/imessage/conversations/{quote(conversation_id)}")
        return ImessageConversation.from_dict(data)

    def disconnect(self, conversation_id: str) -> dict[str, Any]:
        """Disconnects an active conversation session."""
        data = self._http.post(
            f"/v1/imessage/conversations/{quote(conversation_id)}/disconnect", json={}
        )
        return data if isinstance(data, dict) else {"status": "disconnected"}


class IMessageMessagesClient:
    """Synchronous operations on iMessage messages."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self._http = http

    def list(
        self,
        conversation_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> list[ImessageMessage]:
        """Lists message history within a conversation, ordered chronologically."""
        params: dict[str, Any] = {"conversation_id": conversation_id}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor

        data = self._http.get("/v1/imessage/messages", params=params)
        raw_items = (
            data.get("data", [])
            if isinstance(data, dict)
            else (data if isinstance(data, list) else [])
        )
        return [ImessageMessage.from_dict(m) for m in raw_items]

    def send(
        self,
        *,
        conversation_id: str | None = None,
        to: str | None = None,
        text: str | None = None,
        media_url: str | None = None,
        identity_id: str | None = None,
    ) -> SendImessageResult:
        """Sends an outbound iMessage to an active conversation or phone number."""
        body: dict[str, Any] = {}
        if conversation_id is not None:
            body["conversation_id"] = conversation_id
        if to is not None:
            body["to"] = to
        if text is not None:
            body["text"] = text
        if media_url is not None:
            body["media_url"] = media_url
        if identity_id is not None:
            body["identity_id"] = identity_id

        data = self._http.post("/v1/imessage/messages", json=body)
        return SendImessageResult.from_dict(data)


class IMessageUsersClient:
    """Synchronous operations on iMessage gateway user allowlist."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self._http = http

    def list(self) -> list[ImessageUser]:
        """Lists registered phone numbers on the gateway."""
        data = self._http.get("/v1/imessage/users")
        raw_items = (
            data.get("data", [])
            if isinstance(data, dict)
            else (data if isinstance(data, list) else [])
        )
        return [ImessageUser.from_dict(u) for u in raw_items]

    def add(self, phone_number: str) -> ImessageUser:
        """Pre-provisions a user phone number on the gateway."""
        data = self._http.post("/v1/imessage/users", json={"phone_number": phone_number})
        return ImessageUser.from_dict(data)

    def remove(self, phone_number: str) -> dict[str, Any]:
        """Removes a user phone number from the gateway."""
        data = self._http.delete(f"/v1/imessage/users/{quote(phone_number)}")
        return (
            data if isinstance(data, dict) else {"status": "deleted", "phone_number": phone_number}
        )


class IMessageClient:
    """Synchronous top-level client for Wirebox iMessage operations."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self._http = http
        self.conversations = IMessageConversationsClient(http)
        self.messages = IMessageMessagesClient(http)
        self.users = IMessageUsersClient(http)

    def get_router(
        self,
        *,
        agent: str | None = None,
        user_phone: str | None = None,
    ) -> ImessageRouterInfo:
        """Retrieves active router number, connect command, and QR code URI."""
        params: dict[str, Any] = {}
        clean_agent = _normalize_handle(agent)
        if clean_agent:
            params["agent"] = clean_agent
        if user_phone:
            params["user_phone"] = user_phone.strip()

        data = self._http.get("/v1/imessage/router", params=params)
        return ImessageRouterInfo.from_dict(data)


# ============================================================================
# Asynchronous Sub-resources
# ============================================================================


class AsyncIMessageConversationsClient:
    """Asynchronous operations on iMessage conversations."""

    def __init__(self, http: AsyncHttpTransport) -> None:
        self._http = http

    async def list(
        self,
        *,
        identity_id: str | None = None,
        status: Literal["connected", "disconnected"] | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> list[ImessageConversation]:
        """Lists iMessage conversations matching the specified filter criteria."""
        params: dict[str, Any] = {}
        if identity_id is not None:
            params["identity_id"] = identity_id
        if status is not None:
            params["status"] = status
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor

        data = await self._http.get("/v1/imessage/conversations", params=params)
        raw_items = (
            data.get("data", [])
            if isinstance(data, dict)
            else (data if isinstance(data, list) else [])
        )
        return [ImessageConversation.from_dict(c) for c in raw_items]

    async def get(self, conversation_id: str) -> ImessageConversation:
        """Retrieves details of a specific conversation by ID."""
        data = await self._http.get(f"/v1/imessage/conversations/{quote(conversation_id)}")
        return ImessageConversation.from_dict(data)

    async def disconnect(self, conversation_id: str) -> dict[str, Any]:
        """Disconnects an active conversation session."""
        data = await self._http.post(
            f"/v1/imessage/conversations/{quote(conversation_id)}/disconnect", json={}
        )
        return data if isinstance(data, dict) else {"status": "disconnected"}


class AsyncIMessageMessagesClient:
    """Asynchronous operations on iMessage messages."""

    def __init__(self, http: AsyncHttpTransport) -> None:
        self._http = http

    async def list(
        self,
        conversation_id: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> list[ImessageMessage]:
        """Lists message history within a conversation, ordered chronologically."""
        params: dict[str, Any] = {"conversation_id": conversation_id}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor

        data = await self._http.get("/v1/imessage/messages", params=params)
        raw_items = (
            data.get("data", [])
            if isinstance(data, dict)
            else (data if isinstance(data, list) else [])
        )
        return [ImessageMessage.from_dict(m) for m in raw_items]

    async def send(
        self,
        *,
        conversation_id: str | None = None,
        to: str | None = None,
        text: str | None = None,
        media_url: str | None = None,
        identity_id: str | None = None,
    ) -> SendImessageResult:
        """Sends an outbound iMessage to an active conversation or phone number."""
        body: dict[str, Any] = {}
        if conversation_id is not None:
            body["conversation_id"] = conversation_id
        if to is not None:
            body["to"] = to
        if text is not None:
            body["text"] = text
        if media_url is not None:
            body["media_url"] = media_url
        if identity_id is not None:
            body["identity_id"] = identity_id

        data = await self._http.post("/v1/imessage/messages", json=body)
        return SendImessageResult.from_dict(data)


class AsyncIMessageUsersClient:
    """Asynchronous operations on iMessage gateway user allowlist."""

    def __init__(self, http: AsyncHttpTransport) -> None:
        self._http = http

    async def list(self) -> list[ImessageUser]:
        """Lists registered phone numbers on the gateway."""
        data = await self._http.get("/v1/imessage/users")
        raw_items = (
            data.get("data", [])
            if isinstance(data, dict)
            else (data if isinstance(data, list) else [])
        )
        return [ImessageUser.from_dict(u) for u in raw_items]

    async def add(self, phone_number: str) -> ImessageUser:
        """Pre-provisions a user phone number on the gateway."""
        data = await self._http.post("/v1/imessage/users", json={"phone_number": phone_number})
        return ImessageUser.from_dict(data)

    async def remove(self, phone_number: str) -> dict[str, Any]:
        """Removes a user phone number from the gateway."""
        data = await self._http.delete(f"/v1/imessage/users/{quote(phone_number)}")
        return (
            data if isinstance(data, dict) else {"status": "deleted", "phone_number": phone_number}
        )


class AsyncIMessageClient:
    """Asynchronous top-level client for Wirebox iMessage operations."""

    def __init__(self, http: AsyncHttpTransport) -> None:
        self._http = http
        self.conversations = AsyncIMessageConversationsClient(http)
        self.messages = AsyncIMessageMessagesClient(http)
        self.users = AsyncIMessageUsersClient(http)

    async def get_router(
        self,
        *,
        agent: str | None = None,
        user_phone: str | None = None,
    ) -> ImessageRouterInfo:
        """Retrieves active router number, connect command, and QR code URI."""
        params: dict[str, Any] = {}
        clean_agent = _normalize_handle(agent)
        if clean_agent:
            params["agent"] = clean_agent
        if user_phone:
            params["user_phone"] = user_phone.strip()

        data = await self._http.get("/v1/imessage/router", params=params)
        return ImessageRouterInfo.from_dict(data)
