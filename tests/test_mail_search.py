from typing import Any

import httpx

from wirebox import AsyncWirebox, Wirebox


def _mock_identity_dict(handle: str = "support-bot") -> dict[str, Any]:
    return {
        "id": "agt_01J8SEARCH123456",
        "organization_id": "org_01J8SEARCH12345",
        "agent_handle": handle,
        "display_name": "Support Bot",
        "description": "Customer Support Agent",
        "status": "active",
        "created_at": "2026-09-18T10:00:00Z",
        "updated_at": "2026-09-18T10:00:00Z",
        "mailboxes": [
            {
                "id": "mbx_01J8SEARCH123456",
                "email_address": f"{handle}@wireboxmail.com",
                "created_at": "2026-09-18T10:00:00Z",
            }
        ],
    }


_SEARCH_MESSAGE: dict[str, Any] = {
    "id": "msg_01J8SEARCH001",
    "thread_id": "thd_01J8SEARCH",
    "direction": "inbound",
    "from": "billing@vendor.com",
    "from_address": "billing@vendor.com",
    "to": ["support-bot@wireboxmail.com"],
    "to_addresses": ["support-bot@wireboxmail.com"],
    "subject": "Invoice follow-up",
    "snippet": "invoice #1042 is now overdue",
    "highlight": "invoice #1042 is now <b>overdue</b>",
    "highlights": {"text": ["invoice #1042 is now <b>overdue</b>"]},
    "is_read": False,
    "is_starred": False,
    "has_attachments": False,
    "created_at": "2026-09-18T12:00:00Z",
}


_SEARCH_RESPONSE: dict[str, Any] = {
    "items": [_SEARCH_MESSAGE],
    "messages": [_SEARCH_MESSAGE],
    "count": 1,
}


def test_sync_mail_search() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.method == "GET" and request.url.path == "/v1/identities/support-bot":
            return httpx.Response(200, json=_mock_identity_dict("support-bot"))
        if (
            request.method == "GET"
            and request.url.path == "/v1/mailboxes/support-bot@wireboxmail.com/search"
        ):
            assert request.url.params["q"] == "invoice overdue"
            assert request.url.params["limit"] == "5"
            return httpx.Response(200, json=_SEARCH_RESPONSE)
        return httpx.Response(404, json={"error": "not found"})

    client = Wirebox(
        api_key="wb_test_123",
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
        ),
    )

    agent = client.get_identity("support-bot")
    results = agent.search_messages(q="invoice overdue", limit=5)

    assert len(results) == 1
    assert results[0].id == "msg_01J8SEARCH001"
    assert results[0].subject == "Invoice follow-up"
    assert results[0].highlight == "invoice #1042 is now <b>overdue</b>"
    assert results[0].highlights == {"text": ["invoice #1042 is now <b>overdue</b>"]}


def test_sync_mail_search_omits_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/v1/identities/support-bot":
            return httpx.Response(200, json=_mock_identity_dict("support-bot"))
        if (
            request.method == "GET"
            and request.url.path == "/v1/mailboxes/support-bot@wireboxmail.com/search"
        ):
            assert request.url.params["q"] == "no-match"
            assert "limit" not in request.url.params
            return httpx.Response(200, json={"items": [], "messages": [], "count": 0})
        return httpx.Response(404, json={"error": "not found"})

    client = Wirebox(
        api_key="wb_test_123",
        http_client=httpx.Client(
            transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
        ),
    )

    agent = client.get_identity("support-bot")
    assert agent.search_messages(q="no-match") == []


async def test_async_mail_search() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/v1/identities/support-bot":
            return httpx.Response(200, json=_mock_identity_dict("support-bot"))
        if (
            request.method == "GET"
            and request.url.path == "/v1/mailboxes/support-bot@wireboxmail.com/search"
        ):
            assert request.url.params["q"] == "invoice"
            assert request.url.params["limit"] == "10"
            return httpx.Response(200, json=_SEARCH_RESPONSE)
        return httpx.Response(404, json={"error": "not found"})

    async_client = AsyncWirebox(
        api_key="wb_test_123",
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
        ),
    )

    agent = await async_client.get_identity("support-bot")
    results = await agent.search_messages(q="invoice", limit=10)

    assert len(results) == 1
    assert results[0].highlight == "invoice #1042 is now <b>overdue</b>"
