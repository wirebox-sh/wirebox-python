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
    DeleteDraftResult,
    Draft,
    EmailMessage,
    ForwardEmailResult,
    ListDraftsResult,
    MessageSummary,
    SendDraftResult,
    SendEmailAttachment,
    SendEmailResult,
)


def _format_forward_payload(
    to: str | list[str],
    *,
    subject: str | None = None,
    body_text: str | None = None,
    body_html: str | None = None,
    text: str | None = None,
    html: str | None = None,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    forward_attachments: bool = True,
    attachments: list[SendEmailAttachment] | None = None,
    headers: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    actual_text = text if text is not None else body_text
    actual_html = html if html is not None else body_html
    payload: dict[str, Any] = {
        "to": [to] if isinstance(to, str) else list(to),
        "forward_attachments": forward_attachments,
    }
    if subject is not None:
        payload["subject"] = subject
    if actual_text is not None:
        payload["body_text"] = actual_text
    if actual_html is not None:
        payload["body_html"] = actual_html
    if cc is not None:
        payload["cc"] = [cc] if isinstance(cc, str) else list(cc)
    if bcc is not None:
        payload["bcc"] = [bcc] if isinstance(bcc, str) else list(bcc)
    if attachments:
        payload["attachments"] = [
            {"filename": a.filename, "content_type": a.content_type, "content": a.content}
            for a in attachments
        ]
    if headers:
        payload["headers"] = dict(headers)
    return payload


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


def _format_create_draft_payload(
    *,
    to: str | list[str] | None = None,
    subject: str | None = None,
    text: str | None = None,
    html: str | None = None,
    body_text: str | None = None,
    body_html: str | None = None,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    in_reply_to: str | None = None,
    reply_all: bool | None = None,
    forward_of: str | None = None,
    forward_attachments: bool | None = None,
    attachments: list[SendEmailAttachment] | None = None,
) -> dict[str, Any]:
    actual_text = text if text is not None else body_text
    actual_html = html if html is not None else body_html
    payload: dict[str, Any] = {}
    if to is not None:
        payload["to"] = [to] if isinstance(to, str) else list(to)
    if subject is not None:
        payload["subject"] = subject
    if actual_text is not None:
        payload["text"] = actual_text
    if actual_html is not None:
        payload["html"] = actual_html
    if cc is not None:
        payload["cc"] = [cc] if isinstance(cc, str) else list(cc)
    if bcc is not None:
        payload["bcc"] = [bcc] if isinstance(bcc, str) else list(bcc)
    if in_reply_to is not None:
        payload["in_reply_to"] = in_reply_to
    if reply_all is not None:
        payload["reply_all"] = reply_all
    if forward_of is not None:
        payload["forward_of"] = forward_of
    if forward_attachments is not None:
        payload["forward_attachments"] = forward_attachments
    if attachments:
        payload["attachments"] = [
            {"filename": a.filename, "content_type": a.content_type, "content": a.content}
            for a in attachments
        ]
    return payload


def _format_update_draft_payload(
    *,
    version: int | None = None,
    to: str | list[str] | None = None,
    subject: str | None = None,
    text: str | None = None,
    html: str | None = None,
    body_text: str | None = None,
    body_html: str | None = None,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    add_attachments: list[SendEmailAttachment] | None = None,
    remove_attachments: list[str] | None = None,
) -> dict[str, Any]:
    actual_text = text if text is not None else body_text
    actual_html = html if html is not None else body_html
    payload: dict[str, Any] = {}
    if version is not None:
        payload["version"] = version
    if to is not None:
        payload["to"] = [to] if isinstance(to, str) else list(to)
    if subject is not None:
        payload["subject"] = subject
    if actual_text is not None:
        payload["text"] = actual_text
    if actual_html is not None:
        payload["html"] = actual_html
    if cc is not None:
        payload["cc"] = [cc] if isinstance(cc, str) else list(cc)
    if bcc is not None:
        payload["bcc"] = [bcc] if isinstance(bcc, str) else list(bcc)
    if add_attachments:
        payload["add_attachments"] = [
            {"filename": a.filename, "content_type": a.content_type, "content": a.content}
            for a in add_attachments
        ]
    if remove_attachments:
        payload["remove_attachments"] = list(remove_attachments)
    return payload


def _format_send_draft_payload(
    *,
    version: int | None = None,
    to: str | list[str] | None = None,
    subject: str | None = None,
    text: str | None = None,
    html: str | None = None,
    body_text: str | None = None,
    body_html: str | None = None,
    cc: str | list[str] | None = None,
    bcc: str | list[str] | None = None,
    attachments: list[SendEmailAttachment] | None = None,
) -> dict[str, Any]:
    actual_text = text if text is not None else body_text
    actual_html = html if html is not None else body_html
    payload: dict[str, Any] = {}
    if version is not None:
        payload["version"] = version
    if to is not None:
        payload["to"] = [to] if isinstance(to, str) else list(to)
    if subject is not None:
        payload["subject"] = subject
    if actual_text is not None:
        payload["text"] = actual_text
    if actual_html is not None:
        payload["html"] = actual_html
    if cc is not None:
        payload["cc"] = [cc] if isinstance(cc, str) else list(cc)
    if bcc is not None:
        payload["bcc"] = [bcc] if isinstance(bcc, str) else list(bcc)
    if attachments:
        payload["attachments"] = [
            {"filename": a.filename, "content_type": a.content_type, "content": a.content}
            for a in attachments
        ]
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

    def forward(
        self,
        mailbox_address: str,
        message_id: str,
        *,
        to: str | list[str],
        subject: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        text: str | None = None,
        html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        forward_attachments: bool = True,
        attachments: list[SendEmailAttachment] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ForwardEmailResult:
        """Forwards an email message to new recipients."""
        body = _format_forward_payload(
            to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            text=text,
            html=html,
            cc=cc,
            bcc=bcc,
            forward_attachments=forward_attachments,
            attachments=attachments,
            headers=headers,
        )
        data = self._http.post(
            f"/v1/mailboxes/{quote(mailbox_address)}/messages/{quote(message_id)}/forward",
            json=body,
        )
        return ForwardEmailResult.from_dict(data)

    def delete_message(self, mailbox_address: str, message_id: str) -> bool:
        self._http.delete(f"/v1/mailboxes/{quote(mailbox_address)}/messages/{quote(message_id)}")
        return True

    def create_draft(
        self,
        mailbox_address: str,
        *,
        to: str | list[str] | None = None,
        subject: str | None = None,
        text: str | None = None,
        html: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        in_reply_to: str | None = None,
        reply_all: bool | None = None,
        forward_of: str | None = None,
        forward_attachments: bool | None = None,
        attachments: list[SendEmailAttachment] | None = None,
    ) -> Draft:
        """Creates a new email draft (plain, reply, or forward)."""
        body = _format_create_draft_payload(
            to=to,
            subject=subject,
            text=text,
            html=html,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            in_reply_to=in_reply_to,
            reply_all=reply_all,
            forward_of=forward_of,
            forward_attachments=forward_attachments,
            attachments=attachments,
        )
        data = self._http.post(f"/v1/mailboxes/{quote(mailbox_address)}/drafts", json=body)
        return Draft.from_dict(data)

    def list_drafts(
        self,
        mailbox_address: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ListDraftsResult:
        """Retrieves a paginated list of drafts in the specified mailbox."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = self._http.get(f"/v1/mailboxes/{quote(mailbox_address)}/drafts", params=params)
        return ListDraftsResult.from_dict(data if isinstance(data, dict) else {"drafts": data})

    def get_draft(self, mailbox_address: str, draft_id: str) -> Draft:
        """Retrieves details of an email draft."""
        data = self._http.get(f"/v1/mailboxes/{quote(mailbox_address)}/drafts/{quote(draft_id)}")
        return Draft.from_dict(data)

    def update_draft(
        self,
        mailbox_address: str,
        draft_id: str,
        *,
        version: int | None = None,
        to: str | list[str] | None = None,
        subject: str | None = None,
        text: str | None = None,
        html: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        add_attachments: list[SendEmailAttachment] | None = None,
        remove_attachments: list[str] | None = None,
    ) -> Draft:
        """Updates an existing email draft with delta body, recipients, or attachments."""
        body = _format_update_draft_payload(
            version=version,
            to=to,
            subject=subject,
            text=text,
            html=html,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            add_attachments=add_attachments,
            remove_attachments=remove_attachments,
        )
        data = self._http.patch(
            f"/v1/mailboxes/{quote(mailbox_address)}/drafts/{quote(draft_id)}", json=body
        )
        return Draft.from_dict(data)

    def delete_draft(self, mailbox_address: str, draft_id: str) -> DeleteDraftResult:
        """Permanently deletes an email draft."""
        data = self._http.delete(f"/v1/mailboxes/{quote(mailbox_address)}/drafts/{quote(draft_id)}")
        return DeleteDraftResult.from_dict(
            data if isinstance(data, dict) else {"deleted": True, "id": draft_id}
        )

    def send_draft(
        self,
        mailbox_address: str,
        draft_id: str,
        *,
        version: int | None = None,
        idempotency_key: str | None = None,
        to: str | list[str] | None = None,
        subject: str | None = None,
        text: str | None = None,
        html: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        attachments: list[SendEmailAttachment] | None = None,
    ) -> SendDraftResult:
        """Sends an email draft, converting it into a sent message."""
        body = _format_send_draft_payload(
            version=version,
            to=to,
            subject=subject,
            text=text,
            html=html,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
        )
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        data = self._http.post(
            f"/v1/mailboxes/{quote(mailbox_address)}/drafts/{quote(draft_id)}/send",
            json=body,
            headers=headers if headers else None,
        )
        return SendDraftResult.from_dict(data)


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

    async def forward(
        self,
        mailbox_address: str,
        message_id: str,
        *,
        to: str | list[str],
        subject: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        text: str | None = None,
        html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        forward_attachments: bool = True,
        attachments: list[SendEmailAttachment] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ForwardEmailResult:
        """Asynchronously forwards an email message to new recipients."""
        body = _format_forward_payload(
            to,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            text=text,
            html=html,
            cc=cc,
            bcc=bcc,
            forward_attachments=forward_attachments,
            attachments=attachments,
            headers=headers,
        )
        data = await self._http.post(
            f"/v1/mailboxes/{quote(mailbox_address)}/messages/{quote(message_id)}/forward",
            json=body,
        )
        return ForwardEmailResult.from_dict(data)

    async def delete_message(self, mailbox_address: str, message_id: str) -> bool:
        await self._http.delete(
            f"/v1/mailboxes/{quote(mailbox_address)}/messages/{quote(message_id)}"
        )
        return True

    async def create_draft(
        self,
        mailbox_address: str,
        *,
        to: str | list[str] | None = None,
        subject: str | None = None,
        text: str | None = None,
        html: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        in_reply_to: str | None = None,
        reply_all: bool | None = None,
        forward_of: str | None = None,
        forward_attachments: bool | None = None,
        attachments: list[SendEmailAttachment] | None = None,
    ) -> Draft:
        """Asynchronously creates a new email draft (plain, reply, or forward)."""
        body = _format_create_draft_payload(
            to=to,
            subject=subject,
            text=text,
            html=html,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            in_reply_to=in_reply_to,
            reply_all=reply_all,
            forward_of=forward_of,
            forward_attachments=forward_attachments,
            attachments=attachments,
        )
        data = await self._http.post(f"/v1/mailboxes/{quote(mailbox_address)}/drafts", json=body)
        return Draft.from_dict(data)

    async def list_drafts(
        self,
        mailbox_address: str,
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ListDraftsResult:
        """Asynchronously retrieves a paginated list of drafts in the specified mailbox."""
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        data = await self._http.get(f"/v1/mailboxes/{quote(mailbox_address)}/drafts", params=params)
        return ListDraftsResult.from_dict(data if isinstance(data, dict) else {"drafts": data})

    async def get_draft(self, mailbox_address: str, draft_id: str) -> Draft:
        """Asynchronously retrieves details of an email draft."""
        data = await self._http.get(
            f"/v1/mailboxes/{quote(mailbox_address)}/drafts/{quote(draft_id)}"
        )
        return Draft.from_dict(data)

    async def update_draft(
        self,
        mailbox_address: str,
        draft_id: str,
        *,
        version: int | None = None,
        to: str | list[str] | None = None,
        subject: str | None = None,
        text: str | None = None,
        html: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        add_attachments: list[SendEmailAttachment] | None = None,
        remove_attachments: list[str] | None = None,
    ) -> Draft:
        """Asynchronously updates an existing email draft with delta body, recipients, or attachments."""
        body = _format_update_draft_payload(
            version=version,
            to=to,
            subject=subject,
            text=text,
            html=html,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            add_attachments=add_attachments,
            remove_attachments=remove_attachments,
        )
        data = await self._http.patch(
            f"/v1/mailboxes/{quote(mailbox_address)}/drafts/{quote(draft_id)}", json=body
        )
        return Draft.from_dict(data)

    async def delete_draft(self, mailbox_address: str, draft_id: str) -> DeleteDraftResult:
        """Asynchronously permanently deletes an email draft."""
        data = await self._http.delete(
            f"/v1/mailboxes/{quote(mailbox_address)}/drafts/{quote(draft_id)}"
        )
        return DeleteDraftResult.from_dict(
            data if isinstance(data, dict) else {"deleted": True, "id": draft_id}
        )

    async def send_draft(
        self,
        mailbox_address: str,
        draft_id: str,
        *,
        version: int | None = None,
        idempotency_key: str | None = None,
        to: str | list[str] | None = None,
        subject: str | None = None,
        text: str | None = None,
        html: str | None = None,
        body_text: str | None = None,
        body_html: str | None = None,
        cc: str | list[str] | None = None,
        bcc: str | list[str] | None = None,
        attachments: list[SendEmailAttachment] | None = None,
    ) -> SendDraftResult:
        """Asynchronously sends an email draft, converting it into a sent message."""
        body = _format_send_draft_payload(
            version=version,
            to=to,
            subject=subject,
            text=text,
            html=html,
            body_text=body_text,
            body_html=body_html,
            cc=cc,
            bcc=bcc,
            attachments=attachments,
        )
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        data = await self._http.post(
            f"/v1/mailboxes/{quote(mailbox_address)}/drafts/{quote(draft_id)}/send",
            json=body,
            headers=headers if headers else None,
        )
        return SendDraftResult.from_dict(data)
