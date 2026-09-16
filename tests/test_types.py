from wirebox.types import (
    IdentityData,
    Tunnel,
    WebhookCreateResult,
)


def test_identity_data_from_dict():
    raw = {
        "id": "agt_1",
        "organization_id": "org_1",
        "agent_handle": "sales-bot",
        "display_name": "Sales Bot",
        "description": "Handles inquiries",
        "status": "active",
        "created_at": "2026-09-14T10:00:00Z",
        "updated_at": "2026-09-14T10:00:00Z",
        "mailboxes": [
            {
                "id": "mbx_1",
                "email_address": "sales-bot@wireboxmail.com",
                "created_at": "2026-09-14T10:00:00Z",
            }
        ],
    }
    identity = IdentityData.from_dict(raw)
    assert identity.id == "agt_1"
    assert identity.agent_handle == "sales-bot"
    assert len(identity.mailboxes) == 1
    assert identity.mailboxes[0].email_address == "sales-bot@wireboxmail.com"


def test_identity_data_from_dict_singular_mailbox_and_tunnel():
    # Matches actual Wirebox Core API POST /v1/identities and GET /v1/identities/:handle responses
    raw = {
        "id": "agt_2",
        "organization_id": "org_1",
        "agent_handle": "webhook-bot",
        "display_name": "Webhook Bot",
        "description": "Handles webhooks",
        "status": "active",
        "email_address": "webhook-bot@wireboxmail.com",
        "created_at": "2026-09-14T10:00:00Z",
        "updated_at": "2026-09-14T10:00:00Z",
        "mailbox": {
            "id": "mbx_2",
            "email_address": "webhook-bot@wireboxmail.com",
            "created_at": "2026-09-14T10:00:00Z",
        },
        "tunnel": {
            "id": "tun_2",
            "public_url": "https://webhook-bot.wirebox.run",
            "status": "active",
            "is_connected": False,
        },
    }
    identity = IdentityData.from_dict(raw)
    assert identity.id == "agt_2"
    assert len(identity.mailboxes) == 1
    assert identity.mailboxes[0].id == "mbx_2"
    assert identity.mailboxes[0].email_address == "webhook-bot@wireboxmail.com"
    assert identity.tunnel is not None
    assert identity.tunnel.public_url == "https://webhook-bot.wirebox.run"


def test_identity_data_fallback_mailbox_and_tunnel():
    raw = {
        "id": "agt_3",
        "organization_id": "org_1",
        "agent_handle": "fallback-bot",
        "status": "active",
        "created_at": "2026-09-14T10:00:00Z",
        "updated_at": "2026-09-14T10:00:00Z",
    }
    identity = IdentityData.from_dict(raw)
    assert len(identity.mailboxes) == 1
    assert identity.mailboxes[0].email_address == "fallback-bot@wireboxmail.com"
    assert identity.tunnel is not None
    assert identity.tunnel.public_url == "https://fallback-bot.wirebox.run"


def test_tunnel_from_dict():
    raw = {
        "id": "tun_1",
        "agent_handle": "sales-bot",
        "public_url": "https://sales-bot.tunnel.wirebox.sh",
        "public_host": "sales-bot.tunnel.wirebox.sh",
        "status": "active",
        "is_connected": True,
        "connected_clients": 1,
        "created_at": "2026-09-14T10:00:00Z",
        "updated_at": "2026-09-14T10:00:00Z",
        "client": {
            "ip": "1.2.3.4",
            "version": "wirebox-sdk/0.1.0",
            "forward_to": "http://127.0.0.1:3000",
        },
    }
    tunnel = Tunnel.from_dict(raw)
    assert tunnel.id == "tun_1"
    assert tunnel.is_connected is True
    assert tunnel.client.forward_to == "http://127.0.0.1:3000"


def test_webhook_create_result_from_dict():
    raw = {
        "id": "whk_1",
        "agent_handle": "sales-bot",
        "mailbox_address": "sales-bot@wireboxmail.com",
        "url": "https://agent.example.com/hook",
        "events": ["message.received"],
        "auth_token": "token123",
        "has_auth_token": True,
        "status": "active",
        "secret": "whsec_super_secret",
        "created_at": "2026-09-14T10:00:00Z",
        "updated_at": "2026-09-14T10:00:00Z",
    }
    wh = WebhookCreateResult.from_dict(raw)
    assert wh.id == "whk_1"
    assert wh.secret == "whsec_super_secret"
    assert wh.events == ["message.received"]
