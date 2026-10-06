import json
from typing import Any

import httpx
import pytest

from wirebox import AsyncWirebox, Wirebox
from wirebox.types import ForwardEmailResult, SendEmailAttachment


def _mock_identity_dict(handle: str = "support-bot") -> dict[str, Any]:
    return {
        "id": "agt_01J8ABC123456789",
        "organization_id": "org_01J8XYZ123456789",
        "agent_handle": handle,
        "display_name": "Support Bot",
        "description": "Customer Support Agent",
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


def test_sync_mail_forward() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "GET" and request.url.path == "/v1/identities/support-bot":
            return httpx.Response(200, json=_mock_identity_dict("support-bot"))
        if (
            request.method == "POST"
            and request.url.path
            == "/v1/mailboxes/support-bot@wireboxmail.com/messages/msg_123/forward"
        ):
            body = json.loads(request.content.decode("utf-8"))
            assert body["to"] == ["boss@company.com"]
            assert body["body_text"] == "FYI, review this invoice."
            assert body["forward_attachments"] is True
            return httpx.Response(
                201,
                json={
                    "id": "msg_fwd_789",
                    "thread_id": "thd_new_999",
                    "status": "sent",
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    client = Wirebox(
        api_key="wb_test_123",
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
        ),
    )

    agent = client.get_identity("support-bot")
    result = agent.forward_email(
        "msg_123",
        to="boss@company.com",
        body_text="FYI, review this invoice.",
        forward_attachments=True,
    )

    assert isinstance(result, ForwardEmailResult)
    assert result.id == "msg_fwd_789"
    assert result.thread_id == "thd_new_999"
    assert result.status == "sent"


def test_sync_mail_forward_without_attachments() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if (
            request.method == "POST"
            and request.url.path
            == "/v1/mailboxes/support-bot@wireboxmail.com/messages/msg_456/forward"
        ):
            body = json.loads(request.content.decode("utf-8"))
            assert body["to"] == ["external@partner.com", "cc@partner.com"]
            assert body["forward_attachments"] is False
            assert body["subject"] == "Fwd: Urgent"
            return httpx.Response(
                201,
                json={
                    "id": "msg_fwd_888",
                    "thread_id": "thd_new_777",
                    "status": "sent",
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    client = Wirebox(
        api_key="wb_test_123",
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
        ),
    )

    result = client.mail.forward(
        "support-bot@wireboxmail.com",
        "msg_456",
        to=["external@partner.com", "cc@partner.com"],
        subject="Fwd: Urgent",
        forward_attachments=False,
    )

    assert result.id == "msg_fwd_888"
    assert result.thread_id == "thd_new_777"
    assert result.status == "sent"


@pytest.mark.asyncio
async def test_async_mail_forward() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "GET" and request.url.path == "/v1/identities/support-bot":
            return httpx.Response(200, json=_mock_identity_dict("support-bot"))
        if (
            request.method == "POST"
            and request.url.path
            == "/v1/mailboxes/support-bot@wireboxmail.com/messages/msg_async_123/forward"
        ):
            body = json.loads(request.content.decode("utf-8"))
            assert body["to"] == ["auditor@company.com"]
            assert body["forward_attachments"] is True
            assert len(body["attachments"]) == 1
            assert body["attachments"][0]["filename"] == "extra.pdf"
            return httpx.Response(
                201,
                json={
                    "id": "msg_fwd_async_999",
                    "thread_id": "thd_new_async_888",
                    "status": "sent",
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    async_client = AsyncWirebox(
        api_key="wb_test_123",
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
        ),
    )

    agent = await async_client.get_identity("support-bot")
    result = await agent.forward_email(
        "msg_async_123",
        to=["auditor@company.com"],
        forward_attachments=True,
        attachments=[
            SendEmailAttachment(
                filename="extra.pdf",
                content_type="application/pdf",
                content="base64content",
            )
        ],
    )

    assert isinstance(result, ForwardEmailResult)
    assert result.id == "msg_fwd_async_999"
    assert result.thread_id == "thd_new_async_888"
    assert result.status == "sent"
