"""Wirebox Python SDK — Phone & SMS Client.

Provides synchronous and asynchronous clients to manage cellular phone numbers,
provisioning, release, and inbound SMS/MMS message retrieval.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from wirebox._http import AsyncHttpTransport, SyncHttpTransport
from wirebox.types import (
    ListPhoneMessagesResult,
    ListPhoneNumbersResult,
    PhoneMessage,
    PhoneNumber,
)


def _normalize_target(target: str) -> str:
    cleaned = target.strip()
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    return cleaned


# ============================================================================
# Synchronous Sub-resources
# ============================================================================


class PhoneNumbersClient:
    """Synchronous operations on carrier phone numbers."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self._http = http

    def provision(
        self,
        agent_handle: str,
        *,
        country_code: str = "US",
        type: str = "local",
        region: str | None = None,
        area_code: str | None = None,
    ) -> PhoneNumber:
        """Provisions a new carrier phone number and binds it to an agent identity."""
        handle = _normalize_target(agent_handle)
        body: dict[str, Any] = {
            "agent_handle": handle,
            "country_code": country_code,
            "type": type,
        }
        if region is not None:
            body["region"] = region
        if area_code is not None:
            body["area_code"] = area_code

        data = self._http.post("/v1/phone/numbers", json=body)
        return PhoneNumber.from_dict(data)

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        status: str | None = None,
        sms_status: str | None = None,
    ) -> ListPhoneNumbersResult:
        """Lists active phone numbers in the organization."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        if status is not None:
            params["status"] = status
        if sms_status is not None:
            params["sms_status"] = sms_status

        data = self._http.get("/v1/phone/numbers", params=params)
        return ListPhoneNumbersResult.from_dict(data)

    def get(self, number: str) -> PhoneNumber:
        """Retrieves details of a specific phone number by ID, E.164, or agent handle."""
        target = _normalize_target(number)
        data = self._http.get(f"/v1/phone/numbers/{quote(target)}")
        return PhoneNumber.from_dict(data)

    def release(self, number: str) -> None:
        """Releases a phone number back to the carrier."""
        target = _normalize_target(number)
        self._http.delete(f"/v1/phone/numbers/{quote(target)}")


class PhoneMessagesClient:
    """Synchronous operations on received SMS/MMS messages."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self._http = http

    def list(
        self,
        number: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        is_read: bool | None = None,
        from_number: str | None = None,
    ) -> ListPhoneMessagesResult:
        """Lists SMS/MMS messages received on a phone number, newest first."""
        target = _normalize_target(number)
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        if is_read is not None:
            params["is_read"] = "true" if is_read else "false"
        if from_number is not None:
            params["from_number"] = from_number

        data = self._http.get(f"/v1/phone/numbers/{quote(target)}/messages", params=params)
        return ListPhoneMessagesResult.from_dict(data)

    def get(self, number: str, message_id: str) -> PhoneMessage:
        """Retrieves a single SMS/MMS message by ID."""
        target = _normalize_target(number)
        data = self._http.get(f"/v1/phone/numbers/{quote(target)}/messages/{quote(message_id)}")
        return PhoneMessage.from_dict(data)

    def update(
        self,
        number: str,
        message_id: str,
        *,
        is_read: bool,
    ) -> PhoneMessage:
        """Updates message attributes (e.g. marking as read/unread)."""
        target = _normalize_target(number)
        data = self._http.patch(
            f"/v1/phone/numbers/{quote(target)}/messages/{quote(message_id)}",
            json={"is_read": is_read},
        )
        return PhoneMessage.from_dict(data)

    def mark_read(self, number: str, message_id: str) -> PhoneMessage:
        """Convenience helper to mark an SMS/MMS message as read."""
        return self.update(number, message_id, is_read=True)


class PhoneClient:
    """Top-level synchronous client for phone numbers and SMS/MMS messaging."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self.numbers = PhoneNumbersClient(http)
        self.messages = PhoneMessagesClient(http)


# ============================================================================
# Asynchronous Sub-resources
# ============================================================================


class AsyncPhoneNumbersClient:
    """Asynchronous operations on carrier phone numbers."""

    def __init__(self, http: AsyncHttpTransport) -> None:
        self._http = http

    async def provision(
        self,
        agent_handle: str,
        *,
        country_code: str = "US",
        type: str = "local",
        region: str | None = None,
        area_code: str | None = None,
    ) -> PhoneNumber:
        """Provisions a new carrier phone number and binds it to an agent identity."""
        handle = _normalize_target(agent_handle)
        body: dict[str, Any] = {
            "agent_handle": handle,
            "country_code": country_code,
            "type": type,
        }
        if region is not None:
            body["region"] = region
        if area_code is not None:
            body["area_code"] = area_code

        data = await self._http.post("/v1/phone/numbers", json=body)
        return PhoneNumber.from_dict(data)

    async def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        status: str | None = None,
        sms_status: str | None = None,
    ) -> ListPhoneNumbersResult:
        """Lists active phone numbers in the organization."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        if status is not None:
            params["status"] = status
        if sms_status is not None:
            params["sms_status"] = sms_status

        data = await self._http.get("/v1/phone/numbers", params=params)
        return ListPhoneNumbersResult.from_dict(data)

    async def get(self, number: str) -> PhoneNumber:
        """Retrieves details of a specific phone number by ID, E.164, or agent handle."""
        target = _normalize_target(number)
        data = await self._http.get(f"/v1/phone/numbers/{quote(target)}")
        return PhoneNumber.from_dict(data)

    async def release(self, number: str) -> None:
        """Releases a phone number back to the carrier."""
        target = _normalize_target(number)
        await self._http.delete(f"/v1/phone/numbers/{quote(target)}")


class AsyncPhoneMessagesClient:
    """Asynchronous operations on received SMS/MMS messages."""

    def __init__(self, http: AsyncHttpTransport) -> None:
        self._http = http

    async def list(
        self,
        number: str,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        is_read: bool | None = None,
        from_number: str | None = None,
    ) -> ListPhoneMessagesResult:
        """Lists SMS/MMS messages received on a phone number, newest first."""
        target = _normalize_target(number)
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if cursor is not None:
            params["cursor"] = cursor
        if is_read is not None:
            params["is_read"] = "true" if is_read else "false"
        if from_number is not None:
            params["from_number"] = from_number

        data = await self._http.get(f"/v1/phone/numbers/{quote(target)}/messages", params=params)
        return ListPhoneMessagesResult.from_dict(data)

    async def get(self, number: str, message_id: str) -> PhoneMessage:
        """Retrieves a single SMS/MMS message by ID."""
        target = _normalize_target(number)
        data = await self._http.get(
            f"/v1/phone/numbers/{quote(target)}/messages/{quote(message_id)}"
        )
        return PhoneMessage.from_dict(data)

    async def update(
        self,
        number: str,
        message_id: str,
        *,
        is_read: bool,
    ) -> PhoneMessage:
        """Updates message attributes (e.g. marking as read/unread)."""
        target = _normalize_target(number)
        data = await self._http.patch(
            f"/v1/phone/numbers/{quote(target)}/messages/{quote(message_id)}",
            json={"is_read": is_read},
        )
        return PhoneMessage.from_dict(data)

    async def mark_read(self, number: str, message_id: str) -> PhoneMessage:
        """Convenience helper to mark an SMS/MMS message as read."""
        return await self.update(number, message_id, is_read=True)


class AsyncPhoneClient:
    """Top-level asynchronous client for phone numbers and SMS/MMS messaging."""

    def __init__(self, http: AsyncHttpTransport) -> None:
        self.numbers = AsyncPhoneNumbersClient(http)
        self.messages = AsyncPhoneMessagesClient(http)
