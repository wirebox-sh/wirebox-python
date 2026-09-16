import json

import httpx
import pytest

from wirebox import AsyncWirebox


@pytest.mark.asyncio
async def test_async_client_lifecycle():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if method == "POST" and url_path == "/v1/identities":
            body = json.loads(request.content.decode())
            return httpx.Response(
                201,
                json={
                    "id": "agt_async_1",
                    "organization_id": "org_async",
                    "agent_handle": body["agent_handle"],
                    "display_name": "Async Bot",
                    "description": None,
                    "status": "active",
                    "created_at": "2026-09-14T10:00:00Z",
                    "updated_at": "2026-09-14T10:00:00Z",
                    "mailboxes": [
                        {
                            "id": "mbx_async",
                            "email_address": f"{body['agent_handle']}@wireboxmail.com",
                            "created_at": "2026-09-14T10:00:00Z",
                        }
                    ],
                },
            )

        if method == "GET" and url_path == "/v1/whoami":
            return httpx.Response(
                200,
                json={
                    "authenticated": True,
                    "type": "api_key",
                    "organization": {
                        "id": "org_async",
                        "name": "Async Org",
                        "slug": "async-org",
                        "billing_plan": "pro",
                        "is_claimed": True,
                        "claimed_by_email": "admin@example.com",
                        "created_at": "2026-09-14T10:00:00Z",
                    },
                    "api_key": {
                        "id": "key_1",
                        "name": "Production Key",
                        "key_prefix": "wb_live",
                        "key_preview": "wb_live_***abcd",
                        "role": "admin",
                        "created_at": "2026-09-14T10:00:00Z",
                    },
                    "agent_identity_id": None,
                },
            )

        if method == "GET" and url_path == "/v1/tunnels/support-bot":
            return httpx.Response(
                200,
                json={
                    "id": "tun_async",
                    "agent_handle": "support-bot",
                    "public_url": "https://support-bot.tunnel.wirebox.sh",
                    "public_host": "support-bot.tunnel.wirebox.sh",
                    "status": "active",
                    "is_connected": False,
                    "connected_clients": 0,
                    "created_at": "2026-09-14T10:00:00Z",
                    "updated_at": "2026-09-14T10:00:00Z",
                },
            )

        return httpx.Response(404, json={"error": {"code": "not_found", "message": "Not found"}})

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.AsyncClient(transport=transport, base_url="https://api.wirebox.sh")

    async with AsyncWirebox(api_key="wb_live_test", http_client=http_client) as client:
        # Test whoami
        me = await client.whoami()
        assert me.authenticated is True
        assert me.organization is not None
        assert me.organization.slug == "async-org"
        assert me.api_key is not None
        assert me.api_key.role == "admin"

        # Test create identity
        agent = await client.create_identity("support-bot")
        assert agent.agent_handle == "support-bot"
        assert agent.mailbox.email_address == "support-bot@wireboxmail.com"

        # Test tunnel get
        tunnel = await agent.get_tunnel()
        assert tunnel.agent_handle == "support-bot"
        assert tunnel.public_url == "https://support-bot.tunnel.wirebox.sh"
