"""Wirebox Python SDK — Identity-Scoped A2A Client.

Exposes ergonomic, high-level A2A capabilities bound to a specific agent identity (e.g. `agent.a2a.*`).
Provides both Synchronous (A2AIdentityClient) and Asynchronous (AsyncA2AIdentityClient) variants.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any
from urllib.parse import quote

from wirebox._http import AsyncHttpTransport, SyncHttpTransport
from wirebox.a2a.client import A2AClient, AsyncA2AClient
from wirebox.a2a.task_handle import AsyncTaskHandle, TaskHandle
from wirebox.a2a.types import (
    A2ACard,
    A2APart,
    A2AReplyIntent,
    A2ASettings,
    A2ASkill,
    A2ATask,
    A2ATaskState,
)


class _IdentityTasksScope:
    def __init__(self, handle: str, http: SyncHttpTransport) -> None:
        self._handle = handle
        self._http = http

    def list(
        self,
        *,
        role: str = "worker",
        state: A2ATaskState | str | None = None,
        context_id: str | None = None,
        limit: int = 25,
    ) -> list[A2ATask]:
        """List tasks assigned to this identity (worker) or created by this identity (requester)."""
        query: dict[str, Any] = {"limit": limit}
        if role == "requester":
            query["requester_handle"] = self._handle
        else:
            query["agent_handle"] = self._handle

        if state is not None:
            query["state"] = state
        if context_id is not None:
            query["context_id"] = context_id

        res = self._http.get("/api/v1/a2a/tasks", params=query)
        raw_tasks = res.get("tasks", []) if isinstance(res, dict) else []
        return [A2ATask.from_dict(t) for t in raw_tasks if isinstance(t, dict)]

    def iter(
        self,
        *,
        role: str = "worker",
        state: A2ATaskState | str | None = None,
        context_id: str | None = None,
        limit: int = 25,
    ) -> Iterator[A2ATask]:
        """Iterate over tasks."""
        tasks = self.list(role=role, state=state, context_id=context_id, limit=limit)
        yield from tasks

    def get(self, task_id: str) -> A2ATask:
        """Retrieve a specific task by ID."""
        res = self._http.get(f"/api/v1/a2a/tasks/{quote(task_id)}")
        return A2ATask.from_dict(res.get("task", res))

    def reply(
        self,
        task_id: str,
        *,
        intent: A2AReplyIntent | str,
        text: str | None = None,
        parts: list[A2APart | dict[str, Any]] | None = None,
        artifacts: list[dict[str, Any]] | None = None,
        status_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> A2ATask:
        """Reply to a task using a semantic intent (progress, complete, ask_caller, or fail)."""
        payload: dict[str, Any] = {"intent": intent}
        if text is not None:
            payload["text"] = text
        if parts is not None:
            payload["parts"] = [p.to_dict() if isinstance(p, A2APart) else p for p in parts]
        if artifacts is not None:
            payload["artifacts"] = artifacts
        if status_message is not None:
            payload["status_message"] = status_message
        if metadata is not None:
            payload["metadata"] = metadata

        res = self._http.post(f"/api/v1/a2a/tasks/{quote(task_id)}/reply", json=payload)
        return A2ATask.from_dict(res.get("task", res))

    def progress(self, task_id: str, message: str) -> A2ATask:
        """Report in-progress milestone and keep task in 'working' state."""
        return self.reply(task_id, intent="progress", text=message)

    def complete(
        self,
        task_id: str,
        result: str,
        *,
        artifacts: list[dict[str, Any]] | None = None,
    ) -> A2ATask:
        """Complete task successfully with final message and optional deliverables."""
        return self.reply(task_id, intent="complete", text=result, artifacts=artifacts)

    def ask(self, task_id: str, question: str) -> A2ATask:
        """Request caller input and place task into 'input-required' state."""
        return self.reply(task_id, intent="ask_caller", text=question)

    def fail(self, task_id: str, reason: str) -> A2ATask:
        """Fail task with error explanation and place task into 'failed' state."""
        return self.reply(task_id, intent="fail", text=reason)

    def cancel(self, task_id: str, reason: str | None = None) -> A2ATask:
        """Cancel an active task."""
        payload: dict[str, Any] = {
            "state": "canceled",
            "status_message": reason or "Task canceled by requester.",
        }
        res = self._http.patch(f"/api/v1/a2a/tasks/{quote(task_id)}", json=payload)
        return A2ATask.from_dict(res.get("task", res))


class _IdentityCardScope:
    def __init__(self, handle: str, http: SyncHttpTransport) -> None:
        self._handle = handle
        self._http = http

    def get(self) -> A2ACard:
        """Retrieve this identity's public Agent Card."""
        res = self._http.get(f"/api/v1/identities/{quote(self._handle)}/a2a/card")
        return A2ACard.from_dict(res.get("card", res))


class _IdentitySettingsScope:
    def __init__(self, handle: str, http: SyncHttpTransport) -> None:
        self._handle = handle
        self._http = http

    def get(self) -> A2ASettings:
        """Get identity A2A configuration."""
        res = self._http.get(f"/api/v1/identities/{quote(self._handle)}/a2a/settings")
        return A2ASettings.from_dict(res.get("a2a", res))

    def update(self, **changes: Any) -> A2ASettings:
        """Update identity A2A configuration."""
        res = self._http.patch(
            f"/api/v1/identities/{quote(self._handle)}/a2a/settings", json=changes
        )
        return A2ASettings.from_dict(res.get("a2a", res))

    def enable(self) -> A2ASettings:
        """Enable A2A receiver."""
        return self.update(a2a_enabled=True)

    def disable(self) -> A2ASettings:
        """Disable A2A receiver."""
        return self.update(a2a_enabled=False)

    def set_skills(self, skills: list[A2ASkill] | list[dict[str, Any]]) -> A2ASettings:
        """Set advertised skills on the Agent Card."""
        raw_skills = [s.to_dict() if isinstance(s, A2ASkill) else s for s in skills]
        return self.update(a2a_skills=raw_skills)


class A2AIdentityClient:
    """Synchronous identity-scoped A2A operations client (mounted at `agent.a2a`)."""

    def __init__(
        self,
        handle: str,
        identity_id: str,
        http: SyncHttpTransport,
        client: A2AClient | None = None,
    ) -> None:
        self.handle = handle
        self.identity_id = identity_id
        self._http = http
        self.client = client or A2AClient(
            api_key=http.api_key,
            platform_base_url=http.base_url,
            timeout=http.timeout,
            http_client=getattr(http, "_client", None),
        )
        self.tasks = _IdentityTasksScope(handle, http)
        self.card = _IdentityCardScope(handle, http)
        self.settings = _IdentitySettingsScope(handle, http)

    def call(
        self,
        target_url_or_handle: str,
        *,
        text: str | None = None,
        parts: list[A2APart | dict[str, Any]] | None = None,
        context_id: str | None = None,
        credential: str | None = None,
        timeout: float | None = None,
    ) -> TaskHandle:
        """Send a task to a remote A2A agent and return an observable TaskHandle."""
        if target_url_or_handle.startswith("http://") or target_url_or_handle.startswith(
            "https://"
        ):
            card_url = (
                target_url_or_handle
                if target_url_or_handle.endswith("/card") or target_url_or_handle.endswith(".json")
                else f"{target_url_or_handle.rstrip('/')}/card"
            )
        else:
            clean_handle = target_url_or_handle.strip().lstrip("@").lower()
            card_url = f"{self._http.base_url}/a2a/{clean_handle}/card"

        target = self.client.fetch_card(card_url, credential=credential, timeout=timeout)
        initial_task = self.client.send(
            target,
            text=text,
            parts=parts,
            context_id=context_id,
            timeout=timeout,
        )
        return TaskHandle(self.client, target, initial_task)


# =============================================================================
# Asynchronous Identity Scopes
# =============================================================================


class _AsyncIdentityTasksScope:
    def __init__(self, handle: str, http: AsyncHttpTransport) -> None:
        self._handle = handle
        self._http = http

    async def list(
        self,
        *,
        role: str = "worker",
        state: A2ATaskState | str | None = None,
        context_id: str | None = None,
        limit: int = 25,
    ) -> list[A2ATask]:
        """List tasks assigned to this identity (worker) or created by this identity (requester)."""
        query: dict[str, Any] = {"limit": limit}
        if role == "requester":
            query["requester_handle"] = self._handle
        else:
            query["agent_handle"] = self._handle

        if state is not None:
            query["state"] = state
        if context_id is not None:
            query["context_id"] = context_id

        res = await self._http.get("/api/v1/a2a/tasks", params=query)
        raw_tasks = res.get("tasks", []) if isinstance(res, dict) else []
        return [A2ATask.from_dict(t) for t in raw_tasks if isinstance(t, dict)]

    async def iter(
        self,
        *,
        role: str = "worker",
        state: A2ATaskState | str | None = None,
        context_id: str | None = None,
        limit: int = 25,
    ) -> AsyncIterator[A2ATask]:
        """Iterate over tasks asynchronously."""
        tasks = await self.list(role=role, state=state, context_id=context_id, limit=limit)
        for t in tasks:
            yield t

    async def get(self, task_id: str) -> A2ATask:
        """Retrieve a specific task by ID."""
        res = await self._http.get(f"/api/v1/a2a/tasks/{quote(task_id)}")
        return A2ATask.from_dict(res.get("task", res))

    async def reply(
        self,
        task_id: str,
        *,
        intent: A2AReplyIntent | str,
        text: str | None = None,
        parts: list[A2APart | dict[str, Any]] | None = None,
        artifacts: list[dict[str, Any]] | None = None,
        status_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> A2ATask:
        """Reply to a task using a semantic intent (progress, complete, ask_caller, or fail)."""
        payload: dict[str, Any] = {"intent": intent}
        if text is not None:
            payload["text"] = text
        if parts is not None:
            payload["parts"] = [p.to_dict() if isinstance(p, A2APart) else p for p in parts]
        if artifacts is not None:
            payload["artifacts"] = artifacts
        if status_message is not None:
            payload["status_message"] = status_message
        if metadata is not None:
            payload["metadata"] = metadata

        res = await self._http.post(f"/api/v1/a2a/tasks/{quote(task_id)}/reply", json=payload)
        return A2ATask.from_dict(res.get("task", res))

    async def progress(self, task_id: str, message: str) -> A2ATask:
        """Report in-progress milestone and keep task in 'working' state."""
        return await self.reply(task_id, intent="progress", text=message)

    async def complete(
        self,
        task_id: str,
        result: str,
        *,
        artifacts: list[dict[str, Any]] | None = None,
    ) -> A2ATask:
        """Complete task successfully with final message and optional deliverables."""
        return await self.reply(task_id, intent="complete", text=result, artifacts=artifacts)

    async def ask(self, task_id: str, question: str) -> A2ATask:
        """Request caller input and place task into 'input-required' state."""
        return await self.reply(task_id, intent="ask_caller", text=question)

    async def fail(self, task_id: str, reason: str) -> A2ATask:
        """Fail task with error explanation and place task into 'failed' state."""
        return await self.reply(task_id, intent="fail", text=reason)

    async def cancel(self, task_id: str, reason: str | None = None) -> A2ATask:
        """Cancel an active task."""
        payload: dict[str, Any] = {
            "state": "canceled",
            "status_message": reason or "Task canceled by requester.",
        }
        res = await self._http.patch(f"/api/v1/a2a/tasks/{quote(task_id)}", json=payload)
        return A2ATask.from_dict(res.get("task", res))


class _AsyncIdentityCardScope:
    def __init__(self, handle: str, http: AsyncHttpTransport) -> None:
        self._handle = handle
        self._http = http

    async def get(self) -> A2ACard:
        """Retrieve this identity's public Agent Card."""
        res = await self._http.get(f"/api/v1/identities/{quote(self._handle)}/a2a/card")
        return A2ACard.from_dict(res.get("card", res))


class _AsyncIdentitySettingsScope:
    def __init__(self, handle: str, http: AsyncHttpTransport) -> None:
        self._handle = handle
        self._http = http

    async def get(self) -> A2ASettings:
        """Get identity A2A configuration."""
        res = await self._http.get(f"/api/v1/identities/{quote(self._handle)}/a2a/settings")
        return A2ASettings.from_dict(res.get("a2a", res))

    async def update(self, **changes: Any) -> A2ASettings:
        """Update identity A2A configuration."""
        res = await self._http.patch(
            f"/api/v1/identities/{quote(self._handle)}/a2a/settings", json=changes
        )
        return A2ASettings.from_dict(res.get("a2a", res))

    async def enable(self) -> A2ASettings:
        """Enable A2A receiver."""
        return await self.update(a2a_enabled=True)

    async def disable(self) -> A2ASettings:
        """Disable A2A receiver."""
        return await self.update(a2a_enabled=False)

    async def set_skills(self, skills: list[A2ASkill] | list[dict[str, Any]]) -> A2ASettings:
        """Set advertised skills on the Agent Card."""
        raw_skills = [s.to_dict() if isinstance(s, A2ASkill) else s for s in skills]
        return await self.update(a2a_skills=raw_skills)


class AsyncA2AIdentityClient:
    """Asynchronous identity-scoped A2A operations client (mounted at `async_agent.a2a`)."""

    def __init__(
        self,
        handle: str,
        identity_id: str,
        http: AsyncHttpTransport,
        client: AsyncA2AClient | None = None,
    ) -> None:
        self.handle = handle
        self.identity_id = identity_id
        self._http = http
        self.client = client or AsyncA2AClient(
            api_key=http.api_key,
            platform_base_url=http.base_url,
            timeout=http.timeout,
            http_client=getattr(http, "_client", None),
        )
        self.tasks = _AsyncIdentityTasksScope(handle, http)
        self.card = _AsyncIdentityCardScope(handle, http)
        self.settings = _AsyncIdentitySettingsScope(handle, http)

    async def call(
        self,
        target_url_or_handle: str,
        *,
        text: str | None = None,
        parts: list[A2APart | dict[str, Any]] | None = None,
        context_id: str | None = None,
        credential: str | None = None,
        timeout: float | None = None,
    ) -> AsyncTaskHandle:
        """Send a task to a remote A2A agent and return an observable AsyncTaskHandle."""
        if target_url_or_handle.startswith("http://") or target_url_or_handle.startswith(
            "https://"
        ):
            card_url = (
                target_url_or_handle
                if target_url_or_handle.endswith("/card") or target_url_or_handle.endswith(".json")
                else f"{target_url_or_handle.rstrip('/')}/card"
            )
        else:
            clean_handle = target_url_or_handle.strip().lstrip("@").lower()
            card_url = f"{self._http.base_url}/a2a/{clean_handle}/card"

        target = await self.client.fetch_card(card_url, credential=credential, timeout=timeout)
        initial_task = await self.client.send(
            target,
            text=text,
            parts=parts,
            context_id=context_id,
            timeout=timeout,
        )
        return AsyncTaskHandle(self.client, target, initial_task)
