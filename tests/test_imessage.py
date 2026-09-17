import json

import httpx
import pytest

from wirebox import AsyncWirebox, Wirebox
from wirebox.types import IdentityData


def test_imessage_sync_client_and_agent_identity():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if method == "GET" and url_path == "/v1/imessage/router":
            assert request.url.params["agent"] == "sale-mark"
            assert request.url.params["user_phone"] == "+16465550123"
            return httpx.Response(
                200,
                json={
                    "router_number": "+16282649335",
                    "agent_handle": "sale-mark",
                    "connect_command": "connect @sale-mark",
                    "qr_uri": "sms:+16282649335&body=connect%20%40sale-mark",
                    "status": "online",
                },
            )

        if method == "GET" and url_path == "/v1/imessage/conversations":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "conv_001",
                            "identity_id": "agt_123",
                            "user_phone": "+16465550123",
                            "status": "connected",
                            "unread_count": 0,
                            "last_message": {
                                "id": "msg_001",
                                "direction": "inbound",
                                "text": "Hi",
                                "has_media": False,
                                "created_at": "2026-09-17T02:00:00Z",
                            },
                            "created_at": "2026-09-17T01:00:00Z",
                            "updated_at": "2026-09-17T02:00:00Z",
                        }
                    ],
                    "next_cursor": None,
                    "has_more": False,
                },
            )

        if method == "GET" and url_path == "/v1/imessage/conversations/conv_001":
            return httpx.Response(
                200,
                json={
                    "id": "conv_001",
                    "identity_id": "agt_123",
                    "user_phone": "+16465550123",
                    "status": "connected",
                    "unread_count": 0,
                    "created_at": "2026-09-17T01:00:00Z",
                    "updated_at": "2026-09-17T02:00:00Z",
                },
            )

        if method == "POST" and url_path == "/v1/imessage/conversations/conv_001/disconnect":
            return httpx.Response(
                200,
                json={
                    "id": "conv_001",
                    "status": "disconnected",
                    "disconnected_at": "2026-09-17T02:30:00Z",
                },
            )

        if method == "POST" and url_path == "/v1/imessage/messages":
            body = json.loads(request.content.decode())
            assert body["text"] == "Hello from Python SDK"
            return httpx.Response(
                201,
                json={
                    "id": "msg_sent001",
                    "conversation_id": body.get("conversation_id", "conv_001"),
                    "identity_id": "agt_123",
                    "direction": "outbound",
                    "to": "+16465550123",
                    "text": body["text"],
                    "media_url": None,
                    "status": "sent",
                    "created_at": "2026-09-17T02:35:00Z",
                },
            )

        if method == "GET" and url_path == "/v1/imessage/messages":
            assert request.url.params["conversation_id"] == "conv_001"
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "msg_001",
                            "conversation_id": "conv_001",
                            "identity_id": "agt_123",
                            "direction": "inbound",
                            "sender": "+16465550123",
                            "text": "First message",
                            "media_url": None,
                            "is_read": True,
                            "created_at": "2026-09-17T02:00:00Z",
                        }
                    ],
                    "next_cursor": None,
                    "has_more": False,
                },
            )

        if method == "GET" and url_path == "/v1/imessage/users":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"phone_number": "+16465550123", "assigned_router_number": "+16282649335"}
                    ],
                    "total": 1,
                },
            )

        if method == "POST" and url_path == "/v1/imessage/users":
            body = json.loads(request.content.decode())
            return httpx.Response(
                201,
                json={
                    "phone_number": body["phone_number"],
                    "assigned_router_number": "+16282649335",
                },
            )

        if method == "DELETE" and url_path.startswith("/v1/imessage/users/"):
            return httpx.Response(200, json={"status": "deleted", "phone_number": "+16465550123"})

        return httpx.Response(404, json={"error": "Not Found"})

    client = Wirebox(
        api_key="wb_live_test_key",
        http_client=httpx.Client(
            transport=httpx.MockTransport(mock_handler), base_url="https://api.wirebox.sh"
        ),
    )

    # 1. Router
    router = client.imessage.get_router(agent="@sale-mark", user_phone="+16465550123")
    assert router.router_number == "+16282649335"
    assert router.agent_handle == "sale-mark"
    assert router.connect_command == "connect @sale-mark"
    assert router.qr_uri.startswith("sms:+16282649335")

    # 2. Conversations
    convs = client.imessage.conversations.list(status="connected", limit=10)
    assert len(convs) == 1
    assert convs[0].id == "conv_001"
    assert convs[0].last_message is not None
    assert convs[0].last_message.text == "Hi"

    conv = client.imessage.conversations.get("conv_001")
    assert conv.id == "conv_001"
    assert conv.user_phone == "+16465550123"

    disc = client.imessage.conversations.disconnect("conv_001")
    assert disc["status"] == "disconnected"

    # 3. Messages
    msgs = client.imessage.messages.list("conv_001", limit=10)
    assert len(msgs) == 1
    assert msgs[0].text == "First message"

    sent = client.imessage.messages.send(conversation_id="conv_001", text="Hello from Python SDK")
    assert sent.id == "msg_sent001"
    assert sent.status == "sent"

    # 4. Users
    users = client.imessage.users.list()
    assert len(users) == 1
    assert users[0].phone_number == "+16465550123"

    user_added = client.imessage.users.add("+16465559999")
    assert user_added.phone_number == "+16465559999"

    user_del = client.imessage.users.remove("+16465550123")
    assert user_del["status"] == "deleted"

    # 5. AgentIdentity scoped methods
    agent_data = IdentityData(
        id="agt_123",
        organization_id="org_abc",
        agent_handle="sale-mark",
        display_name="Sale Mark",
        description=None,
        status="active",
        created_at="2026-09-17T00:00:00Z",
        updated_at="2026-09-17T00:00:00Z",
    )
    from wirebox.identity import AgentIdentity

    agent_instance = AgentIdentity(agent_data, client._transport)

    agent_router = agent_instance.get_imessage_router(user_phone="+16465550123")
    assert agent_router.agent_handle == "sale-mark"

    agent_sent = agent_instance.send_imessage(
        conversation_id="conv_001", text="Hello from Python SDK"
    )
    assert agent_sent.status == "sent"

    agent_convs = agent_instance.list_imessage_conversations(status="connected")
    assert len(agent_convs) == 1

    agent_msgs = agent_instance.list_imessage_messages("conv_001")
    assert len(agent_msgs) == 1

    iter_received = list(agent_instance.iter_imessage_messages("conv_001", limit=10))
    assert len(iter_received) == 1
    assert iter_received[0].text == "First message"

    agent_disc = agent_instance.disconnect_imessage_conversation("conv_001")
    assert agent_disc["status"] == "disconnected"


@pytest.mark.asyncio
async def test_imessage_async_client_and_async_agent():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if method == "GET" and url_path == "/v1/imessage/router":
            return httpx.Response(
                200,
                json={
                    "router_number": "+16282649335",
                    "agent_handle": "async-agent",
                    "connect_command": "connect @async-agent",
                    "qr_uri": "sms:+16282649335&body=connect%20%40async-agent",
                    "status": "online",
                },
            )

        if method == "GET" and url_path == "/v1/imessage/conversations":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "conv_async_1",
                            "identity_id": "agt_async",
                            "user_phone": "+16465550123",
                            "status": "connected",
                            "unread_count": 0,
                            "created_at": "2026-09-17T00:00:00Z",
                            "updated_at": "2026-09-17T00:00:00Z",
                        }
                    ]
                },
            )

        if method == "POST" and url_path == "/v1/imessage/messages":
            body = json.loads(request.content.decode())
            return httpx.Response(
                201,
                json={
                    "id": "msg_async_sent",
                    "conversation_id": body.get("conversation_id", "conv_async_1"),
                    "identity_id": "agt_async",
                    "direction": "outbound",
                    "to": "+16465550123",
                    "text": body["text"],
                    "media_url": None,
                    "status": "sent",
                    "created_at": "2026-09-17T02:00:00Z",
                },
            )

        if method == "GET" and url_path == "/v1/imessage/messages":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "msg_1",
                            "conversation_id": "conv_async_1",
                            "identity_id": "agt_async",
                            "direction": "inbound",
                            "sender": "+16465550123",
                            "text": "Async Inbound",
                            "media_url": None,
                            "is_read": True,
                            "created_at": "2026-09-17T00:00:00Z",
                        }
                    ]
                },
            )

        return httpx.Response(200, json={})

    async_client = AsyncWirebox(
        api_key="wb_live_test_key",
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(mock_handler), base_url="https://api.wirebox.sh"
        ),
    )

    router = await async_client.imessage.get_router(agent="async-agent")
    assert router.router_number == "+16282649335"

    convs = await async_client.imessage.conversations.list()
    assert len(convs) == 1

    sent = await async_client.imessage.messages.send(
        conversation_id="conv_async_1", text="Hello Async"
    )
    assert sent.id == "msg_async_sent"

    # AsyncAgentIdentity
    from wirebox.identity import AsyncAgentIdentity

    agent_data = IdentityData(
        id="agt_async",
        organization_id="org_async",
        agent_handle="async-agent",
        display_name="Async Agent",
        description=None,
        status="active",
        created_at="2026-09-17T00:00:00Z",
        updated_at="2026-09-17T00:00:00Z",
    )
    async_agent = AsyncAgentIdentity(
        agent_data, async_client._transport, "wb_live_test_key", "https://api.wirebox.sh"
    )

    agent_router = await async_agent.get_imessage_router()
    assert agent_router.agent_handle == "async-agent"

    agent_sent = await async_agent.send_imessage(
        conversation_id="conv_async_1", text="Hello from AsyncAgent"
    )
    assert agent_sent.status == "sent"

    iter_msgs = []
    async for m in async_agent.iter_imessage_messages("conv_async_1"):
        iter_msgs.append(m.text)
    assert iter_msgs == ["Async Inbound"]
