import json
from typing import Any

import httpx
import pytest

from wirebox import AsyncWirebox, Wirebox
from wirebox.types import (
    DeleteDraftResult,
    Draft,
    ListDraftsResult,
    SendDraftResult,
    SendEmailAttachment,
)


def _mock_identity_dict(handle: str = "alice") -> dict[str, Any]:
    return {
        "id": "agt_01J8ABC123456789",
        "organization_id": "org_01J8XYZ123456789",
        "agent_handle": handle,
        "display_name": "Alice",
        "description": "Sales Rep",
        "status": "active",
        "created_at": "2026-09-18T10:00:00Z",
        "updated_at": "2026-09-18T10:00:00Z",
        "mailboxes": [
            {
                "id": "mbx_01J8DEF123456789",
                "email_address": f"{handle}@wireboxmail.com",
                "created_at": "2026-09-18T10:00:00Z",
            }
        ],
    }


def _mock_draft_dict(
    draft_id: str = "dft_01J8TEST123",
    version: int = 1,
    subject: str = "Meeting Notes",
) -> dict[str, Any]:
    return {
        "id": draft_id,
        "mailbox_id": "mbx_01J8DEF123456789",
        "agent_identity_id": "agt_01J8ABC123456789",
        "version": version,
        "status": "draft",
        "to": ["bob@example.com"],
        "cc": ["carol@example.com"],
        "bcc": [],
        "subject": subject,
        "text": "Hello Bob, please see the proposal.",
        "html": "<p>Hello Bob, please see the proposal.</p>",
        "has_attachments": True,
        "attachments": [
            {
                "id": "att_01J8ATT123",
                "draft_id": draft_id,
                "filename": "proposal.pdf",
                "content_type": "application/pdf",
                "size_bytes": 1024,
                "url": "https://api.wirebox.sh/media/att_01J8ATT123?sig=abc",
                "created_at": "2026-10-06T12:00:00Z",
            }
        ],
        "created_at": "2026-10-06T12:00:00Z",
        "updated_at": "2026-10-06T12:00:00Z",
    }


def test_sync_draft_lifecycle() -> None:
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        path = request.url.path

        if request.method == "GET" and path == "/v1/identities/alice":
            return httpx.Response(200, json=_mock_identity_dict("alice"))

        if request.method == "POST" and path == "/v1/mailboxes/alice@wireboxmail.com/drafts":
            body = json.loads(request.content.decode("utf-8"))
            assert body["to"] == ["bob@example.com"]
            assert body["subject"] == "Draft Proposal"
            assert body["text"] == "Check out the proposal"
            return httpx.Response(201, json=_mock_draft_dict("dft_new_123", 1, "Draft Proposal"))

        if (
            request.method == "GET"
            and path == "/v1/mailboxes/alice@wireboxmail.com/drafts/dft_new_123"
        ):
            return httpx.Response(200, json=_mock_draft_dict("dft_new_123", 1, "Draft Proposal"))

        if (
            request.method == "PATCH"
            and path == "/v1/mailboxes/alice@wireboxmail.com/drafts/dft_new_123"
        ):
            body = json.loads(request.content.decode("utf-8"))
            assert body["version"] == 1
            assert body["subject"] == "Draft Proposal Revised"
            return httpx.Response(
                200, json=_mock_draft_dict("dft_new_123", 2, "Draft Proposal Revised")
            )

        if (
            request.method == "POST"
            and path == "/v1/mailboxes/alice@wireboxmail.com/drafts/dft_new_123/send"
        ):
            body = json.loads(request.content.decode("utf-8"))
            assert body["version"] == 2
            assert request.headers.get("Idempotency-Key") == "idem_abc_123"
            return httpx.Response(
                201,
                json={
                    "id": "msg_sent_456",
                    "thread_id": "thd_789",
                    "status": "sent",
                },
            )

        if (
            request.method == "DELETE"
            and path == "/v1/mailboxes/alice@wireboxmail.com/drafts/dft_new_123"
        ):
            return httpx.Response(200, json={"deleted": True, "id": "dft_new_123"})

        return httpx.Response(404, json={"error": "not found"})

    client = Wirebox(
        api_key="wb_test_123",
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
        ),
    )

    agent = client.get_identity("alice")

    # 1. Create Draft
    draft = agent.create_draft(
        to="bob@example.com",
        subject="Draft Proposal",
        text="Check out the proposal",
        attachments=[
            SendEmailAttachment(
                filename="proposal.pdf",
                content_type="application/pdf",
                content="dGVzdA==",
            )
        ],
    )
    assert isinstance(draft, Draft)
    assert draft.id == "dft_new_123"
    assert draft.version == 1
    assert draft.attachments[0].filename == "proposal.pdf"

    # 2. Get Draft
    fetched = agent.get_draft("dft_new_123")
    assert fetched.id == "dft_new_123"
    assert fetched.subject == "Draft Proposal"

    # 3. Update Draft with optimistic concurrency check
    updated = agent.update_draft(
        "dft_new_123",
        version=1,
        subject="Draft Proposal Revised",
    )
    assert updated.version == 2
    assert updated.subject == "Draft Proposal Revised"

    # 4. Send Draft
    send_res = agent.send_draft(
        "dft_new_123",
        version=2,
        idempotency_key="idem_abc_123",
    )
    assert isinstance(send_res, SendDraftResult)
    assert send_res.id == "msg_sent_456"
    assert send_res.status == "sent"

    # 5. Delete Draft
    del_res = agent.delete_draft("dft_new_123")
    assert isinstance(del_res, DeleteDraftResult)
    assert del_res.deleted is True


def test_sync_draft_pagination_and_iter() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if request.method == "GET" and path == "/v1/identities/alice":
            return httpx.Response(200, json=_mock_identity_dict("alice"))

        if request.method == "GET" and path == "/v1/mailboxes/alice@wireboxmail.com/drafts":
            offset = int(request.url.params.get("offset", 0))
            if offset == 0:
                return httpx.Response(
                    200,
                    json={
                        "drafts": [_mock_draft_dict("dft_1", 1), _mock_draft_dict("dft_2", 1)],
                        "count": 3,
                        "limit": 2,
                        "offset": 0,
                    },
                )
            elif offset == 2:
                return httpx.Response(
                    200,
                    json={
                        "drafts": [_mock_draft_dict("dft_3", 1)],
                        "count": 3,
                        "limit": 2,
                        "offset": 2,
                    },
                )
            return httpx.Response(200, json={"drafts": [], "count": 3, "limit": 2, "offset": 3})

        return httpx.Response(404, json={"error": "not found"})

    client = Wirebox(
        api_key="wb_test_123",
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
        ),
    )

    agent = client.get_identity("alice")

    # Test list_drafts
    page = agent.list_drafts(limit=2, offset=0)
    assert isinstance(page, ListDraftsResult)
    assert len(page.drafts) == 2
    assert page.count == 3

    # Test iter_drafts
    drafts = list(agent.iter_drafts(page_size=2))
    assert len(drafts) == 3
    assert [d.id for d in drafts] == ["dft_1", "dft_2", "dft_3"]


@pytest.mark.asyncio
async def test_async_draft_lifecycle() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path

        if request.method == "GET" and path == "/v1/identities/alice":
            return httpx.Response(200, json=_mock_identity_dict("alice"))

        if request.method == "POST" and path == "/v1/mailboxes/alice@wireboxmail.com/drafts":
            body = json.loads(request.content.decode("utf-8"))
            assert body["in_reply_to"] == "msg_orig_123"
            assert body["reply_all"] is True
            return httpx.Response(201, json=_mock_draft_dict("dft_reply_1", 1, "Re: Discussion"))

        if request.method == "GET" and path == "/v1/mailboxes/alice@wireboxmail.com/drafts":
            return httpx.Response(
                200,
                json={
                    "drafts": [_mock_draft_dict("dft_reply_1", 1)],
                    "count": 1,
                    "limit": 50,
                    "offset": 0,
                },
            )

        if (
            request.method == "POST"
            and path == "/v1/mailboxes/alice@wireboxmail.com/drafts/dft_reply_1/send"
        ):
            return httpx.Response(
                201,
                json={
                    "id": "msg_sent_reply",
                    "thread_id": "thd_orig_123",
                    "status": "sent",
                },
            )

        return httpx.Response(404, json={"error": "not found"})

    client = AsyncWirebox(
        api_key="wb_test_123",
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
        ),
    )

    agent = await client.get_identity("alice")

    draft = await agent.create_draft(
        in_reply_to="msg_orig_123",
        reply_all=True,
        text="Sounds good to me!",
    )
    assert draft.id == "dft_reply_1"

    drafts = [d async for d in agent.iter_drafts()]
    assert len(drafts) == 1
    assert drafts[0].id == "dft_reply_1"

    sent = await agent.send_draft("dft_reply_1")
    assert sent.id == "msg_sent_reply"
    assert sent.thread_id == "thd_orig_123"
