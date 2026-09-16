"""Wirebox Python SDK — Mail & Messaging Client.

Provides synchronous and asynchronous operations for sending, listing, reading,
replying to, and deleting agent mailbox messages.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from wirebox._http import AsyncHttpTransport, SyncHttpTransport
from wirebox.types import (
    EmailMessage,
    MessageSummary,
    SendEmailAttachment,
    SendEmailResult,
)


def _format_send_payload(
    to: str | list[str],
    subject: str,
    text: str | None = None,
    html: str | None = None,
    body_text: str | None = None,
    body_html: str | None = None,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    reply_to: str | None = None,
    attachments: list[SendEmailAttachment] | None = None,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    actual_text = text if text is not None else body_text
    actual_html = html if html is not None else body_html
    payload: dict[str, Any] = {
        "to": [to] if isinstance(to, str) else list(to),
        "subject": subject,
    }
    if actual_text is not None:
        payload["text"] = actual_text
    if actual_html is not None:
        payload["html"] = actual_html
    if cc is not None:
        payload["cc"] = [cc] if isinstance(cc, str) else list(cc)
    if bcc is not None:
        payload["bcc"] = [bcc] if isinstance(bcc, str) else list(bcc)
    if reply_to is not None:
        payload["reply_to"] = reply_to
    if attachments:
        payload["attachments"] = [
            {"filename": a.filename, "content_type": a.content_type, "content": a.content}
            for a in attachments
        ]
    if headers:
        payload["headers"] = dict(headers)
    return payload


class MailClient:
    """Synchronous client for mail operations."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self._http = http

    def send(
        self,
        mailbox_address: str,
        *,
        to: str | list[str],
        subject: str,
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
        body = _format_send_payload(
            to,
            subject,
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
        data = self._http.post(f"/v1/mailboxes/{quote(mailbox_address)}/messages", json=body)
        return SendEmailResult.from_dict(data)

    def list_messages(
        self,
        mailbox_address: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: str | None = None,
    ) -> list[MessageSummary]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status

        data = self._http.get(f"/v1/mailboxes/{quote(mailbox_address)}/messages", params=params)
        if isinstance(data, list):
            messages_raw = data
        elif isinstance(data, dict):
            messages_raw = data.get("messages", [])
        else:
            messages_raw = []
        return [MessageSummary.from_dict(m) for m in messages_raw]

    def get_message(self, mailbox_address: str, message_id: str) -> EmailMessage:
        data = self._http.get(
            f"/v1/mailboxes/{quote(mailbox_address)}/messages/{quote(message_id)}"
        )
        return EmailMessage.from_dict(data)

    def reply(
        self,
        mailbox_address: str,
        message_id: str,
        text: str,
        *,
        html: str | None = None,
        to: str | list[str] | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        attachments: list[SendEmailAttachment] | None = None,
    ) -> SendEmailResult:
        body: dict[str, Any] = {"text": text}
        if html is not None:
            body["html"] = html
        if to is not None:
            body["to"] = [to] if isinstance(to, str) else list(to)
        if cc is not None:
            body["cc"] = [cc] if isinstance(cc, str) else list(cc)
        if bcc is not None:
            body["bcc"] = [bcc] if isinstance(bcc, str) else list(bcc)
        if attachments:
            body["attachments"] = [
                {"filename": a.filename, "content_type": a.content_type, "content": a.content}
                for a in attachments
            ]
        data = self._http.post(
            f"/v1/mailboxes/{quote(mailbox_address)}/messages/{quote(message_id)}/reply",
            json=body,
        )
        return SendEmailResult.from_dict(data)

    def delete_message(self, mailbox_address: str, message_id: str) -> bool:
        self._http.delete(f"/v1/mailboxes/{quote(mailbox_address)}/messages/{quote(message_id)}")
        return True


class AsyncMailClient:
    """Asynchronous mail management client."""

    def __init__(self, http: AsyncHttpTransport) -> None:
        self._http = http

    async def send(
        self,
        mailbox_address: str,
        *,
        to: str | list[str],
        subject: str,
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
        body = _format_send_payload(
            to,
            subject,
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
        data = await self._http.post(f"/v1/mailboxes/{quote(mailbox_address)}/messages", json=body)
        return SendEmailResult.from_dict(data)

    async def list_messages(
        self,
        mailbox_address: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
        status: str | None = None,
    ) -> list[MessageSummary]:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if status is not None:
            params["status"] = status

        data = await self._http.get(
            f"/v1/mailboxes/{quote(mailbox_address)}/messages", params=params
        )
        if isinstance(data, list):
            messages_raw = data
        elif isinstance(data, dict):
            messages_raw = data.get("messages", [])
        else:
            messages_raw = []
        return [MessageSummary.from_dict(m) for m in messages_raw]

    list_emails = list_messages

    async def get_message(self, mailbox_address: str, message_id: str) -> EmailMessage:
        data = await self._http.get(
            f"/v1/mailboxes/{quote(mailbox_address)}/messages/{quote(message_id)}"
        )
        return EmailMessage.from_dict(data)

    async def reply(
        self,
        mailbox_address: str,
        message_id: str,
        text: str,
        *,
        html: str | None = None,
        to: str | list[str] | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        attachments: list[SendEmailAttachment] | None = None,
    ) -> SendEmailResult:
        body: dict[str, Any] = {"text": text}
        if html is not None:
            body["html"] = html
        if to is not None:
            body["to"] = [to] if isinstance(to, str) else list(to)
        if cc is not None:
            body["cc"] = [cc] if isinstance(cc, str) else list(cc)
        if bcc is not None:
            body["bcc"] = [bcc] if isinstance(bcc, str) else list(bcc)
        if attachments:
            body["attachments"] = [
                {"filename": a.filename, "content_type": a.content_type, "content": a.content}
                for a in attachments
            ]
        data = await self._http.post(
            f"/v1/mailboxes/{quote(mailbox_address)}/messages/{quote(message_id)}/reply",
            json=body,
        )
        return SendEmailResult.from_dict(data)

    async def delete_message(self, mailbox_address: str, message_id: str) -> bool:
        await self._http.delete(
            f"/v1/mailboxes/{quote(mailbox_address)}/messages/{quote(message_id)}"
        )
        return True
