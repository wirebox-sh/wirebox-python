"""Unit tests for Wirebox Python SDK — Agent-to-Agent (A2A 1.0) Protocol."""

import json
from typing import Any

import httpx
import pytest

from wirebox import (
    A2AClient,
    A2AProtocolError,
    AgentIdentity,
    AsyncA2AClient,
    AsyncAgentIdentity,
    AsyncWirebox,
    Wirebox,
)
from wirebox._http import AsyncHttpTransport, SyncHttpTransport
from wirebox.a2a.client import _canonical_url, _origin
from wirebox.types import IdentityData


def _mock_card_json(
    handle: str = "auditor", base: str = "https://api.wirebox.sh"
) -> dict[str, Any]:
    return {
        "name": f"Agent {handle}",
        "description": "Test Agent",
        "version": "1.0.0",
        "supportedInterfaces": [
            {
                "url": f"{base}/a2a/{handle}",
                "protocolBinding": "JSONRPC",
                "protocolVersion": "1.0",
            }
        ],
        "capabilities": {
            "streaming": False,
            "pushNotifications": True,
            "extendedAgentCard": False,
        },
        "skills": [],
    }


def _mock_task_json(
    task_id: str = "task_01TESTA2A12345678",
    state: str = "submitted",
    message: str | None = "Task received and queued in task ledger.",
    context_id: str | None = None,
) -> dict[str, Any]:
    return {
        "kind": "task",
        "taskId": task_id,
        "contextId": context_id,
        "status": {
            "state": state,
            "message": message,
            "timestamp": "2026-10-20T10:00:00Z",
        },
        "messages": [
            {
                "role": "user",
                "parts": [{"type": "text", "text": "Please review this pull request"}],
                "messageId": "msg_01TESTA2AMSG1234",
                "timestamp": "2026-10-20T10:00:00Z",
            }
        ],
        "artifacts": [],
        "metadata": {},
        "createdAt": "2026-10-20T10:00:00Z",
        "updatedAt": "2026-10-20T10:00:00Z",
    }


class TestA2AUrlAndOriginSecurity:
    def test_canonical_url_valid_https(self) -> None:
        url = "https://API.Wirebox.SH:443/a2a/agent/card?foo=bar"
        canonical = _canonical_url(url)
        assert canonical == "https://api.wirebox.sh/a2a/agent/card?foo=bar"
        assert _origin(canonical) == "https://api.wirebox.sh"

    def test_canonical_url_localhost_http(self) -> None:
        url = "http://127.0.0.1:8787/a2a/test/card"
        assert _canonical_url(url) == "http://127.0.0.1:8787/a2a/test/card"
        assert _origin(url) == "http://127.0.0.1:8787"

        url_local = "http://localhost:3000/card"
        assert _canonical_url(url_local) == "http://localhost:3000/card"

    def test_canonical_url_rejects_non_local_http(self) -> None:
        with pytest.raises(ValueError, match="HTTPS"):
            _canonical_url("http://external-agent.com/card")

    def test_canonical_url_rejects_credentials(self) -> None:
        with pytest.raises(ValueError, match="credentials or fragments"):
            _canonical_url("https://user:pass@api.wirebox.sh/card")

    def test_canonical_url_rejects_fragments(self) -> None:
        with pytest.raises(ValueError, match="credentials or fragments"):
            _canonical_url("https://api.wirebox.sh/card#section")


class TestA2AClientOriginPinning:
    def test_pins_platform_api_key_to_wirebox_origin(self) -> None:
        captured_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(request.headers)
            if request.url.path == "/a2a/eva/card":
                return httpx.Response(200, json=_mock_card_json("eva", "https://api.wirebox.sh"))
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        mock_client = httpx.Client(transport=transport)

        client = A2AClient(
            api_key="wb_live_secretkey123",
            platform_base_url="https://api.wirebox.sh",
            http_client=mock_client,
        )

        target = client.fetch_card("https://api.wirebox.sh/a2a/eva/card")
        assert target.rpc_url == "https://api.wirebox.sh/a2a/eva"
        assert target.credential == "wb_live_secretkey123"
        assert captured_headers.get("authorization") == "Bearer wb_live_secretkey123"

    def test_strips_platform_api_key_from_third_party_origin(self) -> None:
        captured_headers: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_headers.update(request.headers)
            if request.url.path == "/card":
                return httpx.Response(200, json=_mock_card_json("bot", "https://external.agent.ai"))
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        mock_client = httpx.Client(transport=transport)

        client = A2AClient(
            api_key="wb_live_secretkey123",
            platform_base_url="https://api.wirebox.sh",
            http_client=mock_client,
        )

        target = client.fetch_card("https://external.agent.ai/card")
        assert target.rpc_url == "https://external.agent.ai/a2a/bot"
        assert target.credential is None
        assert "authorization" not in captured_headers

    def test_refuses_card_redirects(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(302, headers={"location": "https://malicious.site/card"})

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        client = A2AClient(api_key="key", http_client=mock_client)

        with pytest.raises(Exception, match="redirects are refused"):
            client.fetch_card("https://api.wirebox.sh/a2a/bot/card")

    def test_rejects_mismatched_external_card_and_rpc_origin(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            # Card is on external.org, but RPC points to attacker.org
            return httpx.Response(200, json=_mock_card_json("bot", "https://attacker.org"))

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        client = A2AClient(http_client=mock_client)

        with pytest.raises(ValueError, match="require matching Card and RPC origins"):
            client.fetch_card("https://external.org/card", credential="third-party-token")


class TestA2AClientJsonRpcOperations:
    def test_sync_send_get_list_cancel_task(self) -> None:
        sent_rpc: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.read())
            sent_rpc.append(body)
            method = body.get("method")
            if method == "SendMessage":
                return httpx.Response(
                    200, json={"jsonrpc": "2.0", "id": body["id"], "result": _mock_task_json()}
                )
            if method == "GetTask":
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": _mock_task_json(state="working", message="Analyzing AST"),
                    },
                )
            if method == "ListTasks":
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": {"tasks": [_mock_task_json()]},
                    },
                )
            if method == "CancelTask":
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": body["id"],
                        "result": _mock_task_json(state="canceled", message="Canceled by user"),
                    },
                )
            return httpx.Response(400)

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        client = A2AClient(http_client=mock_client)

        from wirebox.a2a.types import A2ACard, A2AInterface, A2AResolvedTarget

        target = A2AResolvedTarget(
            card_url="https://api.wirebox.sh/a2a/auditor/card",
            rpc_url="https://api.wirebox.sh/a2a/auditor",
            protocol_version="1.0",
            card=A2ACard(
                name="Auditor",
                supported_interfaces=[A2AInterface("https://api.wirebox.sh/a2a/auditor")],
            ),
            credential="key",
        )

        # 1. Send
        task = client.send(target, text="Please review PR", context_id="ctx_123")
        assert task.id == "task_01TESTA2A12345678"
        assert task.state == "submitted"
        assert sent_rpc[0]["method"] == "SendMessage"
        assert sent_rpc[0]["params"]["contextId"] == "ctx_123"

        # 2. Get
        got = client.get_task(target, task.id)
        assert got.state == "working"
        assert got.message == "Analyzing AST"

        # 3. List
        listed = client.list_tasks(target, state="submitted")
        assert len(listed) == 1
        assert listed[0].id == task.id

        # 4. Cancel
        canceled = client.cancel(target, task.id, reason="No longer needed")
        assert canceled.state == "canceled"
        assert canceled.is_canceled is True

    def test_rpc_error_raises_a2a_protocol_error(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: contextId required",
                    },
                },
            )

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        client = A2AClient(http_client=mock_client)

        from wirebox.a2a.types import A2ACard, A2AInterface, A2AResolvedTarget

        target = A2AResolvedTarget(
            card_url="https://api.wirebox.sh/a2a/auditor/card",
            rpc_url="https://api.wirebox.sh/a2a/auditor",
            protocol_version="1.0",
            card=A2ACard(
                name="Auditor",
                supported_interfaces=[A2AInterface("https://api.wirebox.sh/a2a/auditor")],
            ),
        )

        with pytest.raises(A2AProtocolError) as exc_info:
            client.get_task(target, "task_123")

        assert exc_info.value.code == -32602
        assert "Invalid params" in exc_info.value.message


class TestA2AStreamingAndWatch:
    def test_sync_watch_and_wait(self) -> None:
        poll_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal poll_count
            poll_count += 1
            body = json.loads(request.read())
            req_id = body["id"]

            if poll_count == 1:
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": _mock_task_json(state="working", message="Step 1: Reading diff"),
                    },
                )
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": _mock_task_json(
                        state="completed", message="Audit passed without issues"
                    ),
                },
            )

        mock_client = httpx.Client(transport=httpx.MockTransport(handler))
        client = A2AClient(http_client=mock_client)

        from wirebox.a2a.types import A2ACard, A2AInterface, A2AResolvedTarget

        target = A2AResolvedTarget(
            card_url="https://api.wirebox.sh/a2a/auditor/card",
            rpc_url="https://api.wirebox.sh/a2a/auditor",
            protocol_version="1.0",
            card=A2ACard(
                name="Auditor",
                supported_interfaces=[A2AInterface("https://api.wirebox.sh/a2a/auditor")],
            ),
        )

        events = list(client.watch(target, "task_01", timeout=5.0, interval=0.01))
        assert len(events) == 2
        assert events[0].is_progress is True
        assert events[0].message == "Step 1: Reading diff"

        assert events[1].is_completed is True
        assert events[1].message == "Audit passed without issues"

    @pytest.mark.asyncio
    async def test_async_watch_and_wait(self) -> None:
        poll_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal poll_count
            poll_count += 1
            body = json.loads(request.read())
            req_id = body["id"]

            if poll_count == 1:
                return httpx.Response(
                    200,
                    json={
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": _mock_task_json(state="working", message="Async Step 1"),
                    },
                )
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": _mock_task_json(state="completed", message="Async Complete"),
                },
            )

        mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AsyncA2AClient(http_client=mock_client)

        from wirebox.a2a.types import A2ACard, A2AInterface, A2AResolvedTarget

        target = A2AResolvedTarget(
            card_url="https://api.wirebox.sh/a2a/auditor/card",
            rpc_url="https://api.wirebox.sh/a2a/auditor",
            protocol_version="1.0",
            card=A2ACard(
                name="Auditor",
                supported_interfaces=[A2AInterface("https://api.wirebox.sh/a2a/auditor")],
            ),
        )

        events = []
        async for ev in client.watch(target, "task_01", timeout=5.0, interval=0.01):
            events.append(ev)

        assert len(events) == 2
        assert events[0].state == "working"
        assert events[1].state == "completed"

        # Test wait
        poll_count = 1  # Next will return completed
        final_task = await client.wait(target, "task_01", timeout=5.0, interval=0.01)
        assert final_task.state == "completed"


class TestAgentIdentityA2AInterface:
    def test_sync_identity_a2a_call_and_tasks(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path

            if path == "/a2a/auditor/card":
                return httpx.Response(200, json=_mock_card_json("auditor"))

            if path == "/a2a/auditor":
                # JSON-RPC SendMessage
                return httpx.Response(
                    200, json={"jsonrpc": "2.0", "id": 1, "result": _mock_task_json()}
                )

            if path == "/api/v1/a2a/tasks":
                return httpx.Response(200, json={"tasks": [_mock_task_json()], "count": 1})

            if path == "/api/v1/a2a/tasks/task_01TESTA2A12345678":
                if request.method == "GET":
                    return httpx.Response(200, json={"task": _mock_task_json()})
                if request.method == "PATCH":
                    return httpx.Response(200, json={"task": _mock_task_json(state="canceled")})

            if path == "/api/v1/a2a/tasks/task_01TESTA2A12345678/reply":
                req_json = json.loads(request.read())
                intent = req_json.get("intent")
                text = req_json.get("text")
                state = (
                    "working"
                    if intent == "progress"
                    else "completed"
                    if intent == "complete"
                    else "failed"
                )
                return httpx.Response(
                    200, json={"task": _mock_task_json(state=state, message=text)}
                )

            if path == "/api/v1/identities/eva/a2a/card":
                return httpx.Response(200, json={"card": _mock_card_json("eva")})

            if path == "/api/v1/identities/eva/a2a/settings":
                return httpx.Response(
                    200,
                    json={
                        "a2a": {
                            "a2a_enabled": True,
                            "card_url": "https://api.wirebox.sh/a2a/eva/card",
                            "rpc_endpoint": "https://api.wirebox.sh/a2a/eva",
                            "a2a_skills": [],
                        }
                    },
                )

            return httpx.Response(404, json={"error": "Not Found"})

        transport = SyncHttpTransport(
            api_key="wb_live_test",
            base_url="https://api.wirebox.sh",
            client=httpx.Client(
                transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
            ),
        )

        identity_data = IdentityData(
            id="agt_01TESTEVA1234",
            organization_id="org_01TEST",
            agent_handle="eva",
            display_name="Eva",
            description=None,
            status="active",
            created_at="2026-10-20T10:00:00Z",
            updated_at="2026-10-20T10:00:00Z",
        )
        agent = AgentIdentity(identity_data, transport)

        # 1. Call -> returns TaskHandle
        handle = agent.a2a.call("auditor", text="Review this PR")
        assert handle.id == "task_01TESTA2A12345678"
        assert handle.state == "submitted"

        # 2. Tasks list
        tasks = agent.a2a.tasks.list(role="worker")
        assert len(tasks) == 1
        assert tasks[0].id == "task_01TESTA2A12345678"

        # 3. Tasks get
        task = agent.a2a.tasks.get(handle.id)
        assert task.id == handle.id

        # 4. Tasks progress
        progress_task = agent.a2a.tasks.progress(handle.id, "Step 1: Reading AST")
        assert progress_task.state == "working"
        assert progress_task.message == "Step 1: Reading AST"

        # 5. Tasks complete
        completed_task = agent.a2a.tasks.complete(handle.id, "All checks passed")
        assert completed_task.state == "completed"
        assert completed_task.is_completed is True

        # 6. Tasks cancel
        canceled_task = agent.a2a.tasks.cancel(handle.id, "Aborted")
        assert canceled_task.state == "canceled"

        # 7. Card & Settings
        card = agent.a2a.card.get()
        assert card.name == "Agent eva"

        settings = agent.a2a.settings.get()
        assert settings.a2a_enabled is True

    @pytest.mark.asyncio
    async def test_async_identity_a2a_call_and_tasks(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path

            if path == "/a2a/auditor/card":
                return httpx.Response(200, json=_mock_card_json("auditor"))

            if path == "/a2a/auditor":
                return httpx.Response(
                    200, json={"jsonrpc": "2.0", "id": 1, "result": _mock_task_json()}
                )

            if path == "/api/v1/a2a/tasks":
                return httpx.Response(200, json={"tasks": [_mock_task_json()], "count": 1})

            if path == "/api/v1/a2a/tasks/task_01TESTA2A12345678":
                return httpx.Response(200, json={"task": _mock_task_json()})

            return httpx.Response(404, json={"error": "Not Found"})

        transport = AsyncHttpTransport(
            api_key="wb_live_test",
            base_url="https://api.wirebox.sh",
            client=httpx.AsyncClient(
                transport=httpx.MockTransport(handler), base_url="https://api.wirebox.sh"
            ),
        )

        identity_data = IdentityData(
            id="agt_01TESTEVA1234",
            organization_id="org_01TEST",
            agent_handle="eva",
            display_name="Eva",
            description=None,
            status="active",
            created_at="2026-10-20T10:00:00Z",
            updated_at="2026-10-20T10:00:00Z",
        )
        agent = AsyncAgentIdentity(
            identity_data, transport, "wb_live_test", "https://api.wirebox.sh"
        )

        # 1. Async Call -> returns AsyncTaskHandle
        handle = await agent.a2a.call("auditor", text="Review this PR")
        assert handle.id == "task_01TESTA2A12345678"

        # 2. Async Tasks list
        tasks = await agent.a2a.tasks.list()
        assert len(tasks) == 1

        # 3. Async Task get
        task = await agent.a2a.tasks.get(handle.id)
        assert task.id == handle.id


class TestTopLevelWireboxMounts:
    def test_sync_and_async_client_mount_a2a(self) -> None:
        client = Wirebox(api_key="wb_live_test", base_url="https://api.wirebox.sh")
        assert isinstance(client.a2a, A2AClient)

        async_client = AsyncWirebox(api_key="wb_live_test", base_url="https://api.wirebox.sh")
        assert isinstance(async_client.a2a, AsyncA2AClient)
