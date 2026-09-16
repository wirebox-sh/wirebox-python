import httpx

from wirebox import Wirebox
from wirebox.tunnels import _normalize_forward_to, _normalize_identifier


def test_tunnels_normalization_helpers():
    assert _normalize_identifier("@sales-bot") == "sales-bot"
    assert _normalize_identifier("Sales-Bot") == "sales-bot"
    assert _normalize_identifier("  tun_123  ") == "tun_123"

    assert _normalize_forward_to(3456) == "http://127.0.0.1:3456"
    assert _normalize_forward_to("8080") == "http://127.0.0.1:8080"
    assert _normalize_forward_to("localhost:5000") == "http://localhost:5000"
    assert _normalize_forward_to("https://api.local/") == "https://api.local"
    assert _normalize_forward_to(None) == "http://127.0.0.1:3000"


def test_sync_tunnels_crud():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if method == "GET" and url_path == "/v1/tunnels":
            return httpx.Response(
                200,
                json={
                    "tunnels": [
                        {
                            "id": "tun_1",
                            "agent_handle": "sales-bot",
                            "public_url": "https://sales-bot.tunnel.wirebox.sh",
                            "public_host": "sales-bot.tunnel.wirebox.sh",
                            "status": "active",
                            "is_connected": False,
                            "connected_clients": 0,
                            "created_at": "2026-09-14T10:00:00Z",
                            "updated_at": "2026-09-14T10:00:00Z",
                        }
                    ],
                    "total": 1,
                },
            )

        if method == "GET" and url_path == "/v1/tunnels/sales-bot":
            return httpx.Response(
                200,
                json={
                    "id": "tun_1",
                    "agent_handle": "sales-bot",
                    "public_url": "https://sales-bot.tunnel.wirebox.sh",
                    "public_host": "sales-bot.tunnel.wirebox.sh",
                    "status": "active",
                    "is_connected": True,
                    "connected_clients": 1,
                    "created_at": "2026-09-14T10:00:00Z",
                    "updated_at": "2026-09-14T10:00:00Z",
                },
            )

        if method == "PATCH" and url_path == "/v1/tunnels/sales-bot":
            return httpx.Response(
                200,
                json={
                    "id": "tun_1",
                    "agent_handle": "sales-bot",
                    "public_url": "https://sales-bot.tunnel.wirebox.sh",
                    "public_host": "sales-bot.tunnel.wirebox.sh",
                    "status": "disabled",
                    "is_connected": False,
                    "connected_clients": 0,
                    "created_at": "2026-09-14T10:00:00Z",
                    "updated_at": "2026-09-14T11:00:00Z",
                },
            )

        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.Client(transport=transport, base_url="https://api.wirebox.sh")

    client = Wirebox(api_key="wb_live_test", http_client=http_client)

    # 1. List
    tunnels = client.tunnels.list()
    assert len(tunnels) == 1
    assert tunnels[0].agent_handle == "sales-bot"

    # 2. Get with @ prefix
    t = client.tunnels.get("@sales-bot")
    assert t.id == "tun_1"
    assert t.is_connected is True

    # 3. Update
    updated = client.tunnels.update("sales-bot", status="disabled")
    assert updated.status == "disabled"
