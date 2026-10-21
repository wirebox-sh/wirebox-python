"""Wirebox Python SDK — Observable A2A Task Handle.

Provides task lifecycle observation, waiting, cancellation, and live streaming.
Available in both Synchronous (TaskHandle) and Asynchronous (AsyncTaskHandle) variants.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wirebox.a2a.client import A2AClient, AsyncA2AClient
    from wirebox.a2a.types import A2AResolvedTarget, A2ATask, A2AWatchEvent


class TaskHandle:
    """Synchronous lifecycle handle for an in-flight or completed A2A task."""

    def __init__(
        self,
        client: A2AClient,
        target: A2AResolvedTarget,
        initial_task: A2ATask,
    ) -> None:
        self._client = client
        self._target = target
        self._initial_task = initial_task

    @property
    def id(self) -> str:
        """Globally unique task ID."""
        return self._initial_task.task_id

    @property
    def task_id(self) -> str:
        """Alias for id."""
        return self._initial_task.task_id

    @property
    def context_id(self) -> str | None:
        """Context ID to group multi-turn interactions."""
        return self._initial_task.context_id

    @property
    def state(self) -> str:
        """Initial task state."""
        return self._initial_task.state

    @property
    def initial_task(self) -> A2ATask:
        """Initial task snapshot returned when task was created."""
        return self._initial_task

    def get(self, *, timeout: float | None = None) -> A2ATask:
        """Fetch the latest task state and messages from the remote agent."""
        return self._client.get_task(self._target, self.id, timeout=timeout)

    def cancel(self, reason: str | None = None, *, timeout: float | None = None) -> A2ATask:
        """Cancel this task on the remote agent."""
        return self._client.cancel(self._target, self.id, reason=reason, timeout=timeout)

    def watch(
        self,
        *,
        timeout: float = 120.0,
        interval: float = 1.0,
    ) -> Iterator[A2AWatchEvent]:
        """Stream progress updates and milestones until terminal state."""
        return self._client.watch(self._target, self.id, timeout=timeout, interval=interval)

    def wait(
        self,
        *,
        timeout: float = 120.0,
        interval: float = 1.0,
    ) -> A2ATask:
        """Wait until the task reaches a terminal state (completed, failed, or canceled)."""
        return self._client.wait(self._target, self.id, timeout=timeout, interval=interval)

    def __repr__(self) -> str:
        return f"<TaskHandle id={self.id!r} state={self.state!r}>"


class AsyncTaskHandle:
    """Asynchronous lifecycle handle for an in-flight or completed A2A task."""

    def __init__(
        self,
        client: AsyncA2AClient,
        target: A2AResolvedTarget,
        initial_task: A2ATask,
    ) -> None:
        self._client = client
        self._target = target
        self._initial_task = initial_task

    @property
    def id(self) -> str:
        """Globally unique task ID."""
        return self._initial_task.task_id

    @property
    def task_id(self) -> str:
        """Alias for id."""
        return self._initial_task.task_id

    @property
    def context_id(self) -> str | None:
        """Context ID to group multi-turn interactions."""
        return self._initial_task.context_id

    @property
    def state(self) -> str:
        """Initial task state."""
        return self._initial_task.state

    @property
    def initial_task(self) -> A2ATask:
        """Initial task snapshot returned when task was created."""
        return self._initial_task

    async def get(self, *, timeout: float | None = None) -> A2ATask:
        """Fetch the latest task state and messages from the remote agent."""
        return await self._client.get_task(self._target, self.id, timeout=timeout)

    async def cancel(self, reason: str | None = None, *, timeout: float | None = None) -> A2ATask:
        """Cancel this task on the remote agent."""
        return await self._client.cancel(self._target, self.id, reason=reason, timeout=timeout)

    async def watch(
        self,
        *,
        timeout: float = 120.0,
        interval: float = 1.0,
    ) -> AsyncIterator[A2AWatchEvent]:
        """Stream progress updates and milestones until terminal state."""
        async for event in self._client.watch(
            self._target, self.id, timeout=timeout, interval=interval
        ):
            yield event

    async def wait(
        self,
        *,
        timeout: float = 120.0,
        interval: float = 1.0,
    ) -> A2ATask:
        """Wait until the task reaches a terminal state (completed, failed, or canceled)."""
        return await self._client.wait(self._target, self.id, timeout=timeout, interval=interval)

    def __repr__(self) -> str:
        return f"<AsyncTaskHandle id={self.id!r} state={self.state!r}>"
