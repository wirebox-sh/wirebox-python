"""Wirebox Python SDK — Webhooks Client.

Provides synchronous and asynchronous clients to manage webhook subscriptions,
rotate HMAC secrets, and dispatch connectivity test pings.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from wirebox._http import AsyncHttpTransport, SyncHttpTransport
from wirebox.types import (
    Webhook,
    WebhookCreateResult,
    WebhookEventType,
    WebhookRotateSecretResult,
    WebhookStatus,
    WebhookTestResult,
)


def _normalize_handle(agent: str | None) -> str | None:
    if not agent:
        return None
    cleaned = agent.strip()
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    return cleaned.lower()


class WebhooksClient:
    """Synchronous client for managing webhook endpoints."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self._http = http

    def create(
        self,
        url: str,
        events: list[WebhookEventType],
        *,
        agent: str | None = None,
        mailbox: str | None = None,
        auth_token: str | None = None,
    ) -> WebhookCreateResult:
        body: dict[str, Any] = {
            "url": url,
            "events": list(events),
        }
        clean_agent = _normalize_handle(agent)
        if clean_agent:
            body["agent"] = clean_agent
        if mailbox:
            body["mailbox"] = mailbox.strip()
        if auth_token is not None:
            body["auth_token"] = auth_token

        data = self._http.post("/v1/webhooks", json=body)
        return WebhookCreateResult.from_dict(data)

    def list(
        self,
        *,
        agent: str | None = None,
        mailbox: str | None = None,
        event: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Webhook]:
        params: dict[str, Any] = {}
        clean_agent = _normalize_handle(agent)
        if clean_agent:
            params["agent"] = clean_agent
        if mailbox:
            params["mailbox"] = mailbox.strip()
        if event:
            params["event"] = event
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        data = self._http.get("/v1/webhooks", params=params)
        raw_webhooks = data.get("webhooks", []) if isinstance(data, dict) else []
        return [Webhook.from_dict(w) for w in raw_webhooks]

    def get(self, webhook_id: str) -> Webhook:
        data = self._http.get(f"/v1/webhooks/{quote(webhook_id)}")
        return Webhook.from_dict(data)

    def update(
        self,
        webhook_id: str,
        *,
        url: str | None = None,
        events: list[WebhookEventType] | None = None,
        auth_token: str | None = None,
        status: WebhookStatus | None = None,
    ) -> Webhook:
        body: dict[str, Any] = {}
        if url is not None:
            body["url"] = url
        if events is not None:
            body["events"] = list(events)
        if auth_token is not None:
            body["auth_token"] = auth_token
        if status is not None:
            body["status"] = status

        data = self._http.patch(f"/v1/webhooks/{quote(webhook_id)}", json=body)
        return Webhook.from_dict(data)

    def delete(self, webhook_id: str) -> bool:
        self._http.delete(f"/v1/webhooks/{quote(webhook_id)}")
        return True

    def test(self, webhook_id: str) -> WebhookTestResult:
        data = self._http.post(f"/v1/webhooks/{quote(webhook_id)}/test", json={})
        return WebhookTestResult.from_dict(data)

    def ping(self, webhook_id: str) -> WebhookTestResult:
        return self.test(webhook_id)

    def rotate_secret(self, webhook_id: str) -> WebhookRotateSecretResult:
        data = self._http.post(f"/v1/webhooks/{quote(webhook_id)}/rotate-secret", json={})
        return WebhookRotateSecretResult.from_dict(data)


class AsyncWebhooksClient:
    """Asynchronous client for managing webhook endpoints."""

    def __init__(self, http: AsyncHttpTransport) -> None:
        self._http = http

    async def create(
        self,
        url: str,
        events: list[WebhookEventType],
        *,
        agent: str | None = None,
        mailbox: str | None = None,
        auth_token: str | None = None,
    ) -> WebhookCreateResult:
        body: dict[str, Any] = {
            "url": url,
            "events": list(events),
        }
        clean_agent = _normalize_handle(agent)
        if clean_agent:
            body["agent"] = clean_agent
        if mailbox:
            body["mailbox"] = mailbox.strip()
        if auth_token is not None:
            body["auth_token"] = auth_token

        data = await self._http.post("/v1/webhooks", json=body)
        return WebhookCreateResult.from_dict(data)

    async def list(
        self,
        *,
        agent: str | None = None,
        mailbox: str | None = None,
        event: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Webhook]:
        params: dict[str, Any] = {}
        clean_agent = _normalize_handle(agent)
        if clean_agent:
            params["agent"] = clean_agent
        if mailbox:
            params["mailbox"] = mailbox.strip()
        if event:
            params["event"] = event
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        data = await self._http.get("/v1/webhooks", params=params)
        raw_webhooks = data.get("webhooks", []) if isinstance(data, dict) else []
        return [Webhook.from_dict(w) for w in raw_webhooks]

    async def get(self, webhook_id: str) -> Webhook:
        data = await self._http.get(f"/v1/webhooks/{quote(webhook_id)}")
        return Webhook.from_dict(data)

    async def update(
        self,
        webhook_id: str,
        *,
        url: str | None = None,
        events: list[WebhookEventType] | None = None,
        auth_token: str | None = None,
        status: WebhookStatus | None = None,
    ) -> Webhook:
        body: dict[str, Any] = {}
        if url is not None:
            body["url"] = url
        if events is not None:
            body["events"] = list(events)
        if auth_token is not None:
            body["auth_token"] = auth_token
        if status is not None:
            body["status"] = status

        data = await self._http.patch(f"/v1/webhooks/{quote(webhook_id)}", json=body)
        return Webhook.from_dict(data)

    async def delete(self, webhook_id: str) -> bool:
        await self._http.delete(f"/v1/webhooks/{quote(webhook_id)}")
        return True

    async def test(self, webhook_id: str) -> WebhookTestResult:
        data = await self._http.post(f"/v1/webhooks/{quote(webhook_id)}/test", json={})
        return WebhookTestResult.from_dict(data)

    async def ping(self, webhook_id: str) -> WebhookTestResult:
        return await self.test(webhook_id)

    async def rotate_secret(self, webhook_id: str) -> WebhookRotateSecretResult:
        data = await self._http.post(f"/v1/webhooks/{quote(webhook_id)}/rotate-secret", json={})
        return WebhookRotateSecretResult.from_dict(data)
