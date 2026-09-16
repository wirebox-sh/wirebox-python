"""Wirebox Python SDK — Agent Identity Domain Model.

Encapsulates an agent's digital identity, assigned mailbox, network tunnel,
and webhook subscriptions into a unified, object-oriented domain model.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator, Mapping
from typing import Any, Literal
from urllib.parse import quote

from wirebox._http import AsyncHttpTransport, SyncHttpTransport
from wirebox.mail import AsyncMailClient, MailClient
from wirebox.tunnels import AsyncTunnelsClient, TunnelsClient, TunnelSession
from wirebox.types import (
    EmailMessage,
    IdentityData,
    IdentityTunnelSummary,
    MailboxSummary,
    MessageSummary,
    SendEmailAttachment,
    SendEmailResult,
    Tunnel,
    Webhook,
    WebhookCreateResult,
    WebhookEventType,
)
from wirebox.webhooks import AsyncWebhooksClient, WebhooksClient


class AgentIdentity:
    """Synchronous domain object representing an active agent identity."""

    def __init__(self, data: IdentityData, http: SyncHttpTransport) -> None:
        self._data = data
        self._http = http
        self._mail = MailClient(http)
        self._tunnels = TunnelsClient(http)
        self._webhooks = WebhooksClient(http)

    @property
    def id(self) -> str:
        return self._data.id

    @property
    def organization_id(self) -> str:
        return self._data.organization_id

    @property
    def agent_handle(self) -> str:
        return self._data.agent_handle

    @property
    def display_name(self) -> str | None:
        return self._data.display_name

    @property
    def description(self) -> str | None:
        return self._data.description

    @property
    def status(self) -> Literal["active", "archived", "deleted"]:
        return self._data.status

    @property
    def created_at(self) -> str:
        return self._data.created_at

    @property
    def updated_at(self) -> str:
        return self._data.updated_at

    @property
    def mailboxes(self) -> list[MailboxSummary]:
        return self._data.mailboxes

    @property
    def mailbox(self) -> MailboxSummary:
        if self._data.mailboxes:
            return self._data.mailboxes[0]
        return MailboxSummary(
            id="",
            email_address=f"{self.agent_handle}@wireboxmail.com",
            created_at=self.created_at,
        )

    @property
    def tunnel(self) -> IdentityTunnelSummary:
        if self._data.tunnel:
            return self._data.tunnel
        return IdentityTunnelSummary(
            id="",
            public_url=f"https://{self.agent_handle}.wirebox.run",
            status="active",
            is_connected=False,
        )

    def update(
        self,
        *,
        display_name: str | None = None,
        description: str | None = None,
    ) -> AgentIdentity:
        payload: dict[str, Any] = {}
        if display_name is not None:
            payload["display_name"] = display_name
        if description is not None:
            payload["description"] = description

        data = self._http.patch(f"/v1/identities/{quote(self.agent_handle)}", json=payload)
        self._data = IdentityData.from_dict(data)
        return self

    def delete(self) -> None:
        self._http.delete(f"/v1/identities/{quote(self.agent_handle)}")

    # ------------------------------------------------------------------------
    # Mail Operations
    # ------------------------------------------------------------------------

    def send_email(
        self,
        to: str | list[str],
        subject: str,
        *,
        text: str | None = None,
        html: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        reply_to: str | None = None,
        attachments: list[SendEmailAttachment] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> SendEmailResult:
        return self._mail.send(
            self.mailbox.email_address,
            to=to,
            subject=subject,
            text=text,
            html=html,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            attachments=attachments,
            headers=headers,
        )

    def list_messages(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: str | None = None,
    ) -> list[MessageSummary]:
        return self._mail.list_messages(
            self.mailbox.email_address,
            limit=limit,
            offset=offset,
            status=status,
        )

    list_emails = list_messages

    def iter_messages(
        self,
        *,
        page_size: int = 50,
        status: str | None = None,
    ) -> Iterator[MessageSummary]:
        offset = 0
        while True:
            batch = self.list_messages(limit=page_size, offset=offset, status=status)
            if not batch:
                break
            yield from batch
            offset += len(batch)
            if len(batch) < page_size:
                break

    iter_emails = iter_messages

    def get_message(self, message_id: str) -> EmailMessage:
        return self._mail.get_message(self.mailbox.email_address, message_id)

    def reply_email(
        self,
        message_id: str,
        text: str,
        *,
        html: str | None = None,
        to: str | list[str] | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        attachments: list[SendEmailAttachment] | None = None,
    ) -> SendEmailResult:
        return self._mail.reply(
            self.mailbox.email_address,
            message_id=message_id,
            text=text,
            html=html,
            to=to,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
        )

    def delete_message(self, message_id: str) -> bool:
        return self._mail.delete_message(self.mailbox.email_address, message_id)

    # ------------------------------------------------------------------------
    # Tunnel & Webhook Operations
    # ------------------------------------------------------------------------

    def get_tunnel(self) -> Tunnel:
        return self._tunnels.get(self.agent_handle)

    def create_webhook(
        self,
        url: str,
        events: list[WebhookEventType],
        *,
        mailbox: str | None = None,
        auth_token: str | None = None,
    ) -> WebhookCreateResult:
        return self._webhooks.create(
            url=url,
            events=events,
            agent=self.agent_handle,
            mailbox=mailbox or self.mailbox.email_address,
            auth_token=auth_token,
        )

    def list_webhooks(
        self,
        *,
        event: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Webhook]:
        return self._webhooks.list(
            agent=self.agent_handle,
            event=event,
            limit=limit,
            offset=offset,
        )


class AsyncAgentIdentity:
    """Asynchronous domain object representing an active agent identity."""

    def __init__(
        self,
        data: IdentityData,
        http: AsyncHttpTransport,
        api_key: str | None,
        base_url: str,
    ) -> None:
        self._data = data
        self._http = http
        self._api_key = api_key
        self._base_url = base_url
        self._mail = AsyncMailClient(http)
        self._tunnels = AsyncTunnelsClient(http, api_key, base_url)
        self._webhooks = AsyncWebhooksClient(http)

    @property
    def id(self) -> str:
        return self._data.id

    @property
    def organization_id(self) -> str:
        return self._data.organization_id

    @property
    def agent_handle(self) -> str:
        return self._data.agent_handle

    @property
    def display_name(self) -> str | None:
        return self._data.display_name

    @property
    def description(self) -> str | None:
        return self._data.description

    @property
    def status(self) -> Literal["active", "archived", "deleted"]:
        return self._data.status

    @property
    def created_at(self) -> str:
        return self._data.created_at

    @property
    def updated_at(self) -> str:
        return self._data.updated_at

    @property
    def mailboxes(self) -> list[MailboxSummary]:
        return self._data.mailboxes

    @property
    def mailbox(self) -> MailboxSummary:
        if self._data.mailboxes:
            return self._data.mailboxes[0]
        return MailboxSummary(
            id="",
            email_address=f"{self.agent_handle}@wireboxmail.com",
            created_at=self.created_at,
        )

    @property
    def tunnel(self) -> IdentityTunnelSummary:
        if self._data.tunnel:
            return self._data.tunnel
        return IdentityTunnelSummary(
            id="",
            public_url=f"https://{self.agent_handle}.wirebox.run",
            status="active",
            is_connected=False,
        )

    async def update(
        self,
        *,
        display_name: str | None = None,
        description: str | None = None,
    ) -> AsyncAgentIdentity:
        payload: dict[str, Any] = {}
        if display_name is not None:
            payload["display_name"] = display_name
        if description is not None:
            payload["description"] = description

        data = await self._http.patch(f"/v1/identities/{quote(self.agent_handle)}", json=payload)
        self._data = IdentityData.from_dict(data)
        return self

    async def delete(self) -> None:
        await self._http.delete(f"/v1/identities/{quote(self.agent_handle)}")

    # ------------------------------------------------------------------------
    # Mail Operations
    # ------------------------------------------------------------------------

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        *,
        text: str | None = None,
        html: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        reply_to: str | None = None,
        attachments: list[SendEmailAttachment] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> SendEmailResult:
        return await self._mail.send(
            self.mailbox.email_address,
            to=to,
            subject=subject,
            text=text,
            html=html,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            reply_to=reply_to,
            attachments=attachments,
            headers=headers,
        )

    async def list_messages(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: str | None = None,
    ) -> list[MessageSummary]:
        return await self._mail.list_messages(
            self.mailbox.email_address,
            limit=limit,
            offset=offset,
            status=status,
        )

    list_emails = list_messages

    async def iter_messages(
        self,
        *,
        page_size: int = 50,
        status: str | None = None,
    ) -> AsyncIterator[MessageSummary]:
        offset = 0
        while True:
            batch = await self.list_messages(limit=page_size, offset=offset, status=status)
            if not batch:
                break
            for msg in batch:
                yield msg
            offset += len(batch)
            if len(batch) < page_size:
                break

    iter_emails = iter_messages

    async def get_message(self, message_id: str) -> EmailMessage:
        return await self._mail.get_message(self.mailbox.email_address, message_id)

    async def reply_email(
        self,
        message_id: str,
        text: str,
        *,
        html: str | None = None,
        to: str | list[str] | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        attachments: list[SendEmailAttachment] | None = None,
    ) -> SendEmailResult:
        return await self._mail.reply(
            self.mailbox.email_address,
            message_id=message_id,
            text=text,
            html=html,
            to=to,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
        )

    async def delete_message(self, message_id: str) -> bool:
        return await self._mail.delete_message(self.mailbox.email_address, message_id)

    # ------------------------------------------------------------------------
    # Tunnel & Webhook Operations
    # ------------------------------------------------------------------------

    async def get_tunnel(self) -> Tunnel:
        return await self._tunnels.get(self.agent_handle)

    async def connect_tunnel(
        self,
        *,
        forward_to: str | int = 3000,
        client_version: str | None = None,
    ) -> TunnelSession:
        return await self._tunnels.connect(
            self.agent_handle,
            forward_to=forward_to,
            client_version=client_version,
        )

    async def create_webhook(
        self,
        url: str,
        events: list[WebhookEventType],
        *,
        mailbox: str | None = None,
        auth_token: str | None = None,
    ) -> WebhookCreateResult:
        return await self._webhooks.create(
            url=url,
            events=events,
            agent=self.agent_handle,
            mailbox=mailbox or self.mailbox.email_address,
            auth_token=auth_token,
        )

    async def list_webhooks(
        self,
        *,
        event: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[Webhook]:
        return await self._webhooks.list(
            agent=self.agent_handle,
            event=event,
            limit=limit,
            offset=offset,
        )
