import json

import httpx

from wirebox import Wirebox


def test_client_create_identity_and_email_operations():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if method == "POST" and url_path == "/v1/identities":
            body = json.loads(request.content.decode())
            assert body["agent_handle"] == "sales-bot"
            return httpx.Response(
                201,
                json={
                    "id": "agt_123",
                    "organization_id": "org_abc",
                    "agent_handle": "sales-bot",
                    "display_name": "Sales Assistant",
                    "description": "Auto sales",
                    "status": "active",
                    "created_at": "2026-09-14T10:00:00Z",
                    "updated_at": "2026-09-14T10:00:00Z",
                    "mailboxes": [
                        {
                            "id": "mbx_123",
                            "email_address": "sales-bot@wireboxmail.com",
                            "created_at": "2026-09-14T10:00:00Z",
                        }
                    ],
                },
            )

        if method == "POST" and "/messages" in url_path and not url_path.endswith("/reply"):
            body = json.loads(request.content.decode())
            assert body["to"] == ["customer@example.com"]
            return httpx.Response(
                202,
                json={
                    "message_id": "<msg_1@wireboxmail.com>",
                    "id": "msg_001",
                    "status": "queued",
                },
            )

        if method == "POST" and url_path.endswith("/reply"):
            body = json.loads(request.content.decode())
            assert body["text"] == "Thanks for contacting sales!"
            return httpx.Response(
                202,
                json={
                    "message_id": "<msg_reply@wireboxmail.com>",
                    "id": "msg_002",
                    "status": "queued",
                },
            )

        if method == "GET" and "/messages" in url_path:
            return httpx.Response(
                200,
                json={
                    "messages": [
                        {
                            "id": "msg_001",
                            "mailbox_id": "mbx_123",
                            "direction": "inbound",
                            "from_address": "customer@example.com",
                            "to_addresses": ["sales-bot@wireboxmail.com"],
                            "subject": "Inquiry",
                            "preview": "Interested in pricing",
                            "status": "delivered",
                            "created_at": "2026-09-14T11:00:00Z",
                        }
                    ],
                    "total": 1,
                },
            )

        if method == "POST" and url_path == "/v1/webhooks":
            body = json.loads(request.content.decode())
            return httpx.Response(
                201,
                json={
                    "id": "whk_001",
                    "agent_handle": body.get("agent"),
                    "mailbox_address": body.get("mailbox"),
                    "url": body["url"],
                    "events": body["events"],
                    "auth_token": None,
                    "has_auth_token": False,
                    "status": "active",
                    "secret": "whsec_test_secret_777",
                    "created_at": "2026-09-14T10:00:00Z",
                    "updated_at": "2026-09-14T10:00:00Z",
                },
            )

        return httpx.Response(404, json={"error": {"code": "not_found", "message": "Not found"}})

    transport = httpx.MockTransport(mock_handler)
    http_client = httpx.Client(transport=transport, base_url="https://api.wirebox.sh")

    with Wirebox(api_key="wb_live_test", http_client=http_client) as client:
        # Create identity
        agent = client.create_identity("sales-bot", display_name="Sales Assistant")
        assert agent.id == "agt_123"
        assert agent.agent_handle == "sales-bot"
        assert agent.mailbox.email_address == "sales-bot@wireboxmail.com"

        # Send email with body_text (inkbox compatibility)
        result = agent.send_email(
            to=["customer@example.com"], subject="Pricing", body_text="Here is pricing."
        )
        assert result.id == "msg_001"
        assert result.status == "queued"

        # Reply email
        reply_res = agent.reply_email("msg_001", text="Thanks for contacting sales!")
        assert reply_res.id == "msg_002"

        # List messages and iter_emails (inkbox compatibility)
        msgs = agent.list_messages(limit=10)
        assert len(msgs) == 1
        assert msgs[0].from_address == "customer@example.com"
        emails = list(agent.iter_emails())
        assert len(emails) == 1
        assert emails[0].subject == "Inquiry"

        # Create webhook
        webhook = agent.create_webhook(
            url="https://agent.example.com/hook", events=["message.received"]
        )
        assert webhook.id == "whk_001"
        assert webhook.secret == "whsec_test_secret_777"
