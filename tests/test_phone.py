import json

import httpx
import pytest

from wirebox import AsyncWirebox, Wirebox
from wirebox.types import IdentityData


def test_phone_sync_client_and_agent_identity():
    mock_number_data = {
        "id": "pn_01J8DEF123456789",
        "phone_number": "+14155552671",
        "country_code": "US",
        "type": "local",
        "region": "CA",
        "agent_handle": "support-bot",
        "agent_identity_id": "agt_01J8ABC123456789",
        "status": "active",
        "sms_status": "ready",
        "sms_error_code": None,
        "sms_error_detail": None,
        "sms_ready_at": "2026-09-18T10:00:00Z",
        "capabilities": {
            "sms": True,
            "mms": True,
            "voice": True,
        },
        "created_at": "2026-09-18T10:00:00Z",
        "updated_at": "2026-09-18T10:00:00Z",
    }

    mock_msg_data = {
        "id": "msg_01J8SMS123456789",
        "phone_number": "+14155552671",
        "agent_handle": "support-bot",
        "direction": "inbound",
        "type": "sms",
        "from_number": "+15559876543",
        "to_numbers": ["+14155552671"],
        "text": "Hello, need support",
        "media": None,
        "is_read": False,
        "segments": 1,
        "created_at": "2026-09-18T10:05:00Z",
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if method == "POST" and url_path == "/v1/phone/numbers":
            body = json.loads(request.content.decode("utf-8"))
            assert body["agent_handle"] == "support-bot"
            assert body["region"] == "CA"
            return httpx.Response(201, json=mock_number_data)

        if method == "GET" and url_path == "/v1/phone/numbers":
            assert request.url.params.get("status") == "active"
            return httpx.Response(
                200,
                json={
                    "numbers": [mock_number_data],
                    "next_cursor": "cur_123",
                    "has_more": True,
                },
            )

        if method == "GET" and url_path == "/v1/phone/numbers/support-bot":
            return httpx.Response(200, json=mock_number_data)

        if method == "DELETE" and url_path == "/v1/phone/numbers/support-bot":
            return httpx.Response(204)

        if method == "GET" and url_path == "/v1/phone/numbers/support-bot/messages":
            return httpx.Response(
                200,
                json={
                    "messages": [mock_msg_data],
                    "next_cursor": None,
                    "has_more": False,
                },
            )

        if (
            method == "GET"
            and url_path == "/v1/phone/numbers/support-bot/messages/msg_01J8SMS123456789"
        ):
            return httpx.Response(200, json=mock_msg_data)

        if (
            method == "PATCH"
            and url_path == "/v1/phone/numbers/support-bot/messages/msg_01J8SMS123456789"
        ):
            body = json.loads(request.content.decode("utf-8"))
            assert body["is_read"] is True
            updated = dict(mock_msg_data)
            updated["is_read"] = True
            return httpx.Response(200, json=updated)

        return httpx.Response(404, json={"error": "Not Found"})

    client = Wirebox(
        api_key="wb_live_test_key",
        http_client=httpx.Client(
            transport=httpx.MockTransport(mock_handler),
            base_url="https://api.wirebox.sh",
        ),
    )

    # 1. Phone numbers provision
    number = client.phone.numbers.provision("@support-bot", region="CA")
    assert number.phone_number == "+14155552671"
    assert number.capabilities.sms is True

    # 2. Phone numbers list
    nums_list = client.phone.numbers.list(status="active")
    assert len(nums_list.numbers) == 1
    assert nums_list.has_more is True

    # 3. Phone numbers get
    fetched_num = client.phone.numbers.get("@support-bot")
    assert fetched_num.id == "pn_01J8DEF123456789"

    # 4. Phone numbers release
    client.phone.numbers.release("@support-bot")

    # 5. Messages list
    msgs = client.phone.messages.list("@support-bot")
    assert len(msgs.messages) == 1
    assert msgs.messages[0].is_read is False

    # 6. Messages mark_read
    updated_msg = client.phone.messages.mark_read("@support-bot", "msg_01J8SMS123456789")
    assert updated_msg.is_read is True

    # 7. AgentIdentity helpers
    client.create_identity(
        "support-bot",
        display_name="Support Bot",
    ) if False else None  # Create agent manually with mock data
    agent_data = IdentityData(
        id="agt_01J8ABC123456789",
        organization_id="org_123",
        agent_handle="support-bot",
        display_name="Support Bot",
        description="Customer support",
        status="active",
        created_at="2026-09-18T10:00:00Z",
        updated_at="2026-09-18T10:00:00Z",
    )
    from wirebox.identity import AgentIdentity

    agent_identity = AgentIdentity(agent_data, client._transport)
    agent_num = agent_identity.provision_phone_number(region="CA")
    assert agent_num.phone_number == "+14155552671"
    assert agent_identity.get_phone_number().id == "pn_01J8DEF123456789"
    agent_identity.release_phone_number()

    agent_msgs = agent_identity.phone.list_messages()
    assert len(agent_msgs.messages) == 1
    marked = agent_identity.phone.mark_message_read("msg_01J8SMS123456789")
    assert marked.is_read is True


@pytest.mark.asyncio
async def test_phone_async_client():
    mock_number_data = {
        "id": "pn_01J8DEF123456789",
        "phone_number": "+14155552671",
        "country_code": "US",
        "type": "local",
        "region": "CA",
        "agent_handle": "support-bot",
        "agent_identity_id": "agt_01J8ABC123456789",
        "status": "active",
        "sms_status": "ready",
        "sms_error_code": None,
        "sms_error_detail": None,
        "sms_ready_at": "2026-09-18T10:00:00Z",
        "capabilities": {
            "sms": True,
            "mms": True,
            "voice": True,
        },
        "created_at": "2026-09-18T10:00:00Z",
        "updated_at": "2026-09-18T10:00:00Z",
    }

    mock_msg_data = {
        "id": "msg_01J8SMS123456789",
        "phone_number": "+14155552671",
        "agent_handle": "support-bot",
        "direction": "inbound",
        "type": "sms",
        "from_number": "+15559876543",
        "to_numbers": ["+14155552671"],
        "text": "Hello, async test",
        "media": None,
        "is_read": False,
        "segments": 1,
        "created_at": "2026-09-18T10:05:00Z",
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if method == "POST" and url_path == "/v1/phone/numbers":
            return httpx.Response(201, json=mock_number_data)
        if method == "GET" and url_path == "/v1/phone/numbers/support-bot":
            return httpx.Response(200, json=mock_number_data)
        if method == "DELETE" and url_path == "/v1/phone/numbers/support-bot":
            return httpx.Response(204)
        if method == "GET" and url_path == "/v1/phone/numbers/support-bot/messages":
            return httpx.Response(
                200,
                json={
                    "messages": [mock_msg_data],
                    "next_cursor": None,
                    "has_more": False,
                },
            )
        if (
            method == "PATCH"
            and url_path == "/v1/phone/numbers/support-bot/messages/msg_01J8SMS123456789"
        ):
            updated = dict(mock_msg_data)
            updated["is_read"] = True
            return httpx.Response(200, json=updated)

        return httpx.Response(404)

    client = AsyncWirebox(
        api_key="wb_live_test_key",
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(mock_handler),
            base_url="https://api.wirebox.sh",
        ),
    )

    num = await client.phone.numbers.provision("support-bot", region="CA")
    assert num.phone_number == "+14155552671"

    fetched = await client.phone.numbers.get("support-bot")
    assert fetched.id == "pn_01J8DEF123456789"

    await client.phone.numbers.release("support-bot")

    msgs = await client.phone.messages.list("support-bot")
    assert len(msgs.messages) == 1

    updated = await client.phone.messages.mark_read("support-bot", "msg_01J8SMS123456789")
    assert updated.is_read is True
