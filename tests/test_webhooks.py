import json

import httpx
import pytest

from wirebox import AsyncWirebox, Wirebox


def test_sync_webhooks_crud():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if method == "POST" and url_path == "/v1/webhooks":
            body = json.loads(request.content.decode())
            return httpx.Response(
                201,
                json={
                    "id": "whk_test_1",
                    "agent_handle": body.get("agent"),
                    "mailbox_address": body.get("mailbox"),
                    "url": body["url"],
                    "events": body["events"],
                    "auth_token": None,
                    "has_auth_token": False,
                    "status": "active",
                    "secret": "whsec_live_key_999",
                    "created_at": "2026-09-14T10:00:00Z",
                    "updated_at": "2026-09-14T10:00:00Z",
                },
            )

        if method == "GET" and url_path == "/v1/webhooks":
            return httpx.Response(
                200,
                json={
                    "webhooks": [
                        {
                            "id": "whk_test_1",
                            "agent_handle": "sales-bot",
                            "mailbox_address": "sales-bot@wireboxmail.com",
                            "url": "https://agent.example.com/hook",
                            "events": ["message.received"],
                            "auth_token": None,
                            "has_auth_token": False,
                            "status": "active",
                            "created_at": "2026-09-14T10:00:00Z",
                            "updated_at": "2026-09-14T10:00:00Z",
                        }
                    ],
                    "total": 1,
                },
            )

        if method == "GET" and url_path == "/v1/webhooks/whk_test_1":
            return httpx.Response(
                200,
                json={
                    "id": "whk_test_1",
                    "agent_handle": "sales-bot",
                    "mailbox_address": "sales-bot@wireboxmail.com",
                    "url": "https://agent.example.com/hook",
                    "events": ["message.received"],
                    "auth_token": None,
                    "has_auth_token": False,
                    "status": "active",
                    "created_at": "2026-09-14T10:00:00Z",
                    "updated_at": "2026-09-14T10:00:00Z",
                },
            )

        if method == "PATCH" and url_path == "/v1/webhooks/whk_test_1":
            body = json.loads(request.content.decode())
            return httpx.Response(
                200,
                json={
                    "id": "whk_test_1",
                    "agent_handle": "sales-bot",
                    "mailbox_address": "sales-bot@wireboxmail.com",
                    "url": "https://agent.example.com/hook",
                    "events": ["message.received"],
                    "auth_token": None,
                    "has_auth_token": False,
                    "status": body.get("status", "paused"),
                    "created_at": "2026-09-14T10:00:00Z",
                    "updated_at": "2026-09-14T11:00:00Z",
                },
            )

        if method == "DELETE" and url_path == "/v1/webhooks/whk_test_1":
            return httpx.Response(204)

        if method == "POST" and url_path == "/v1/webhooks/whk_test_1/test":
            return httpx.Response(
                200,
                json={
                    "webhook_id": "whk_test_1",
                    "url": "https://agent.example.com/hook",
                    "event_type": "test.ping",
                    "status_code": 200,
                    "latency_ms": 135,
                    "success": True,
                    "error": None,
                },
            )

        if method == "POST" and url_path == "/v1/webhooks/whk_test_1/rotate-secret":
            return httpx.Response(
                200,
                json={
                    "id": "whk_test_1",
                    "secret": "whsec_rotated_new_key_888",
                    "updated_at": "2026-09-14T12:00:00Z",
                },
            )

        return httpx.Response(404, json={"error": {"code": "not_found", "message": "Not found"}})

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.Client(transport=transport, base_url="https://api.wirebox.sh")

    client = Wirebox(api_key="wb_live_test", http_client=http_client)

    # 1. Create
    created = client.webhooks.create(
        url="https://agent.example.com/hook",
        events=["message.received"],
        agent="sales-bot",
    )
    assert created.id == "whk_test_1"
    assert created.secret == "whsec_live_key_999"

    # 2. List
    webhooks = client.webhooks.list(agent="sales-bot")
    assert len(webhooks) == 1
    assert webhooks[0].id == "whk_test_1"

    # 3. Get
    wh = client.webhooks.get("whk_test_1")
    assert wh.id == "whk_test_1"
    assert wh.status == "active"

    # 4. Update
    updated = client.webhooks.update("whk_test_1", status="paused")
    assert updated.status == "paused"

    # 5. Test ping
    test_res = client.webhooks.test("whk_test_1")
    assert test_res.success is True
    assert test_res.status_code == 200
    assert test_res.latency_ms == 135

    # 6. Rotate secret
    rot_res = client.webhooks.rotate_secret("whk_test_1")
    assert rot_res.secret == "whsec_rotated_new_key_888"

    # 7. Delete
    deleted = client.webhooks.delete("whk_test_1")
    assert deleted is True


@pytest.mark.asyncio
async def test_async_webhooks_methods():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST" and request.url.path == "/v1/webhooks/whk_async_1/test":
            return httpx.Response(
                200,
                json={
                    "webhook_id": "whk_async_1",
                    "url": "https://agent.example.com/hook",
                    "event_type": "test.ping",
                    "status_code": 204,
                    "latency_ms": 42,
                    "success": True,
                    "error": None,
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="https://api.wirebox.sh")

    async with AsyncWirebox(api_key="wb_live_test", http_client=http_client) as client:
        res = await client.webhooks.ping("whk_async_1")
        assert res.success is True
        assert res.latency_ms == 42
