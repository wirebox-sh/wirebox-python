import json
from typing import Any

import httpx
import pytest

from wirebox import AsyncWirebox, Wirebox
from wirebox.types import (
    ListMailRulesResult,
    MailPolicy,
    MailRule,
)


def _mock_rule_dict(
    rule_id: str = "mrl_01J8RULE12345678",
    handle: str = "support-bot",
    entry: str = "trusted@partner.com",
    action: str = "allow",
    direction: str = "inbound",
    reason: str | None = "Trusted partner",
) -> dict[str, Any]:
    return {
        "id": rule_id,
        "identity_id": "agt_01J8ABC123456789",
        "agent_handle": handle,
        "type": "email",
        "entry": entry,
        "match_target": entry,
        "action": action,
        "direction": direction,
        "reason": reason,
        "status": "active",
        "created_at": "2026-09-18T10:00:00Z",
        "updated_at": "2026-09-18T10:00:00Z",
    }


def _mock_identity_dict(
    handle: str = "support-bot",
    inbound_mode: str = "whitelist",
    outbound_mode: str = "blacklist",
) -> dict[str, Any]:
    return {
        "id": "agt_01J8ABC123456789",
        "organization_id": "org_01J8XYZ123456789",
        "agent_handle": handle,
        "display_name": "Support Bot",
        "description": "Customer Support Agent",
        "status": "active",
        "mail_inbound_filter_mode": inbound_mode,
        "mail_outbound_filter_mode": outbound_mode,
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


def test_mail_rules_sync_client():
    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        url_path = request.url.path
        method = request.method

        if method == "GET" and url_path == "/v1/identities/support-bot/mail-rules":
            return httpx.Response(
                200,
                json={
                    "rules": [_mock_rule_dict()],
                    "total": 1,
                },
            )

        if (
            method == "GET"
            and url_path == "/v1/identities/support-bot/mail-rules/mrl_01J8RULE12345678"
        ):
            return httpx.Response(200, json=_mock_rule_dict())

        if method == "POST" and url_path == "/v1/identities/support-bot/mail-rules":
            body = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                201,
                json=_mock_rule_dict(
                    entry=body["entry"],
                    action=body.get("action", "allow"),
                    direction=body.get("direction", "both"),
                    reason=body.get("reason"),
                ),
            )

        if (
            method == "PATCH"
            and url_path == "/v1/identities/support-bot/mail-rules/mrl_01J8RULE12345678"
        ):
            body = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json=_mock_rule_dict(action=body.get("action", "block")),
            )

        if (
            method == "DELETE"
            and url_path == "/v1/identities/support-bot/mail-rules/mrl_01J8RULE12345678"
        ):
            return httpx.Response(200, json={"deleted": True, "id": "mrl_01J8RULE12345678"})

        if method == "GET" and url_path == "/v1/identities/support-bot":
            return httpx.Response(200, json=_mock_identity_dict())

        if method == "PATCH" and url_path == "/v1/identities/support-bot":
            body = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json=_mock_identity_dict(
                    inbound_mode=body.get("mail_inbound_filter_mode", "whitelist"),
                    outbound_mode=body.get("mail_outbound_filter_mode", "whitelist"),
                ),
            )

        return httpx.Response(404, json={"error": "not_found"})

    client = Wirebox(
        api_key="test_key",
        http_client=httpx.Client(
            transport=httpx.MockTransport(mock_handler), base_url="https://api.wirebox.sh"
        ),
    )

    # 1. List mail rules
    res = client.mail_rules.list("support-bot", direction="inbound")
    assert isinstance(res, ListMailRulesResult)
    assert len(res.rules) == 1
    assert res.rules[0].entry == "trusted@partner.com"
    assert res.rules[0].action == "allow"

    # 2. Get mail rule
    rule = client.mail_rules.get("support-bot", "mrl_01J8RULE12345678")
    assert isinstance(rule, MailRule)
    assert rule.id == "mrl_01J8RULE12345678"

    # 3. Allow helper
    allowed = client.mail_rules.allow(
        "@support-bot",
        "boss@example.com",
        direction="inbound",
        reason="Leadership",
    )
    assert allowed.entry == "boss@example.com"
    assert allowed.action == "allow"
    assert allowed.direction == "inbound"

    # 4. Block helper
    blocked = client.mail_rules.block(
        "support-bot",
        "spammer.com",
        direction="both",
        reason="Phishing",
    )
    assert blocked.entry == "spammer.com"
    assert blocked.action == "block"

    # 5. Update
    updated = client.mail_rules.update("support-bot", "mrl_01J8RULE12345678", action="block")
    assert updated.action == "block"

    # 6. Delete
    deleted = client.mail_rules.delete("support-bot", "mrl_01J8RULE12345678")
    assert deleted.deleted is True
    assert deleted.id == "mrl_01J8RULE12345678"

    # 7. Get policy
    policy = client.mail_rules.get_policy("support-bot")
    assert isinstance(policy, MailPolicy)
    assert policy.inbound == "protected"
    assert policy.outbound == "open"

    # 8. Set policy
    new_policy = client.mail_rules.set_policy(
        "support-bot",
        inbound="protected",
        outbound="restricted",
    )
    assert new_policy.inbound == "protected"
    assert new_policy.outbound == "restricted"


def test_agent_identity_mail_rules_and_policy():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if method == "GET" and url_path == "/v1/identities/support-bot":
            return httpx.Response(
                200, json=_mock_identity_dict(inbound_mode="whitelist", outbound_mode="blacklist")
            )

        if method == "PATCH" and url_path == "/v1/identities/support-bot":
            body = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200,
                json=_mock_identity_dict(
                    inbound_mode=body.get("mail_inbound_filter_mode", "whitelist"),
                    outbound_mode=body.get("mail_outbound_filter_mode", "whitelist"),
                ),
            )

        if method == "POST" and url_path == "/v1/identities/support-bot/mail-rules":
            body = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                201,
                json=_mock_rule_dict(
                    entry=body["entry"],
                    action=body.get("action", "allow"),
                    direction=body.get("direction", "both"),
                    reason=body.get("reason"),
                ),
            )

        if method == "GET" and url_path == "/v1/identities/support-bot/mail-rules":
            return httpx.Response(
                200,
                json={"rules": [_mock_rule_dict()], "total": 1},
            )

        return httpx.Response(404, json={"error": "not_found"})

    client = Wirebox(
        api_key="test_key",
        http_client=httpx.Client(
            transport=httpx.MockTransport(mock_handler), base_url="https://api.wirebox.sh"
        ),
    )

    agent = client.get_identity("support-bot")

    # Property access
    assert agent.mail_policy.inbound == "protected"
    assert agent.mail_policy.outbound == "open"

    # Set policy via agent
    updated_p = agent.set_mail_policy(outbound="restricted")
    assert updated_p.outbound == "restricted"
    assert agent.mail_policy.outbound == "restricted"

    # Identity mail rules client
    rule = agent.mail_rules.allow("partner@company.com", reason="Partner domain")
    assert rule.entry == "partner@company.com"
    assert rule.action == "allow"

    rules = agent.mail_rules.list()
    assert len(rules.rules) == 1


@pytest.mark.asyncio
async def test_async_mail_rules_client_and_identity():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if method == "GET" and url_path == "/v1/identities/support-bot/mail-rules":
            return httpx.Response(
                200,
                json={"rules": [_mock_rule_dict()], "total": 1},
            )

        if method == "POST" and url_path == "/v1/identities/support-bot/mail-rules":
            body = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                201,
                json=_mock_rule_dict(
                    entry=body["entry"],
                    action=body.get("action", "allow"),
                ),
            )

        if method == "GET" and url_path == "/v1/identities/support-bot":
            return httpx.Response(
                200,
                json=_mock_identity_dict(inbound_mode="blacklist", outbound_mode="blacklist"),
            )

        if method == "PATCH" and url_path == "/v1/identities/support-bot":
            return httpx.Response(
                200,
                json=_mock_identity_dict(inbound_mode="whitelist", outbound_mode="whitelist"),
            )

        if (
            method == "DELETE"
            and url_path == "/v1/identities/support-bot/mail-rules/mrl_01J8RULE12345678"
        ):
            return httpx.Response(200, json={"deleted": True, "id": "mrl_01J8RULE12345678"})

        return httpx.Response(404, json={"error": "not_found"})

    async with AsyncWirebox(
        api_key="test_key",
        http_client=httpx.AsyncClient(
            transport=httpx.MockTransport(mock_handler), base_url="https://api.wirebox.sh"
        ),
    ) as client:
        # Top-level client
        res = await client.mail_rules.list("support-bot")
        assert len(res.rules) == 1

        allowed = await client.mail_rules.allow("support-bot", "client@corp.com")
        assert allowed.entry == "client@corp.com"

        deleted = await client.mail_rules.delete("support-bot", "mrl_01J8RULE12345678")
        assert deleted.deleted is True

        # Async identity
        agent = await client.get_identity("support-bot")
        assert agent.mail_policy.inbound == "open"
        assert agent.mail_policy.outbound == "open"

        new_policy = await agent.set_mail_policy(inbound="protected", outbound="restricted")
        assert new_policy.inbound == "protected"
        assert new_policy.outbound == "restricted"
        assert agent.mail_policy.inbound == "protected"

        agent_rule = await agent.mail_rules.allow("friend@domain.com")
        assert agent_rule.entry == "friend@domain.com"
