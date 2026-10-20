"""Wirebox Python SDK — Agent-to-Agent (A2A 1.0) Protocol.

Enables autonomous agents to discover capabilities, exchange tasks,
stream progress events, and negotiate deliverables using the open A2A 1.0 standard.
"""

from wirebox.a2a.client import A2AClient, AsyncA2AClient
from wirebox.a2a.identity_client import (
    A2AIdentityClient,
    AsyncA2AIdentityClient,
)
from wirebox.a2a.task_handle import AsyncTaskHandle, TaskHandle
from wirebox.a2a.types import (
    A2AArtifact,
    A2ACapabilities,
    A2ACard,
    A2AInterface,
    A2AMessage,
    A2APart,
    A2AReplyIntent,
    A2AResolvedTarget,
    A2ASettings,
    A2ASkill,
    A2ATask,
    A2ATaskState,
    A2ATaskStatus,
    A2AWatchEvent,
)
from wirebox.exceptions import A2AProtocolError

__all__ = [
    "A2AArtifact",
    "A2ACapabilities",
    "A2ACard",
    "A2AClient",
    "A2AIdentityClient",
    "A2AInterface",
    "A2AMessage",
    "A2APart",
    "A2AProtocolError",
    "A2AReplyIntent",
    "A2AResolvedTarget",
    "A2ASettings",
    "A2ASkill",
    "A2ATask",
    "A2ATaskState",
    "A2ATaskStatus",
    "A2AWatchEvent",
    "AsyncA2AClient",
    "AsyncA2AIdentityClient",
    "AsyncTaskHandle",
    "TaskHandle",
]
