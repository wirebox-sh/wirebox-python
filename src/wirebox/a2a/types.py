"""Wirebox Python SDK — Agent-to-Agent (A2A 1.0) Type Definitions.

Strict dataclasses and type definitions matching A2A 1.0 JSON-RPC protocol
specifications with zero external schema validator dependencies.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Literal

A2ATaskState = Literal[
    "submitted",
    "working",
    "input-required",
    "completed",
    "failed",
    "canceled",
]

A2AReplyIntent = Literal["progress", "complete", "ask_caller", "fail"]


@dataclasses.dataclass
class A2APart:
    """A granular content part within an A2A message or artifact."""

    type: str = "text"
    text: str | None = None
    data: Any = None
    mime_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"type": self.type}
        if self.text is not None:
            out["text"] = self.text
        if self.data is not None:
            out["data"] = self.data
        if self.mime_type is not None:
            out["mimeType"] = self.mime_type
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2APart:
        return cls(
            type=str(data.get("type", "text")),
            text=data.get("text"),
            data=data.get("data"),
            mime_type=data.get("mimeType") or data.get("mime_type"),
        )


@dataclasses.dataclass
class A2AMessage:
    """An interaction turn in the A2A task conversation history."""

    role: Literal["user", "agent"] | str
    parts: list[A2APart]
    message_id: str | None = None
    timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "role": self.role,
            "parts": [p.to_dict() for p in self.parts],
        }
        if self.message_id is not None:
            out["messageId"] = self.message_id
        if self.timestamp is not None:
            out["timestamp"] = self.timestamp
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2AMessage:
        raw_parts = data.get("parts") or []
        parts = [
            A2APart.from_dict(p) if isinstance(p, dict) else A2APart(text=str(p)) for p in raw_parts
        ]
        return cls(
            role=str(data.get("role", "user")),
            parts=parts,
            message_id=data.get("messageId") or data.get("message_id"),
            timestamp=data.get("timestamp"),
        )


@dataclasses.dataclass
class A2AArtifact:
    """A deliverable generated as a result of task execution."""

    name: str
    mime_type: str
    parts: list[A2APart]
    artifact_id: str | None = None
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "name": self.name,
            "mimeType": self.mime_type,
            "parts": [p.to_dict() for p in self.parts],
            "metadata": self.metadata,
        }
        if self.artifact_id is not None:
            out["artifactId"] = self.artifact_id
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2AArtifact:
        raw_parts = data.get("parts") or []
        parts = [
            A2APart.from_dict(p) if isinstance(p, dict) else A2APart(text=str(p)) for p in raw_parts
        ]
        return cls(
            name=str(data.get("name", "artifact")),
            mime_type=str(data.get("mimeType") or data.get("mime_type") or "application/json"),
            parts=parts,
            artifact_id=data.get("artifactId") or data.get("artifact_id"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclasses.dataclass
class A2ASkill:
    """A specialized capability advertised on an Agent Card."""

    id: str
    name: str
    description: str
    tags: list[str] = dataclasses.field(default_factory=list)
    examples: list[str] | None = None
    input_modes: list[str] | None = None
    output_modes: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
        }
        if self.examples is not None:
            out["examples"] = self.examples
        if self.input_modes is not None:
            out["inputModes"] = self.input_modes
        if self.output_modes is not None:
            out["outputModes"] = self.output_modes
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2ASkill:
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            tags=list(data.get("tags") or []),
            examples=data.get("examples"),
            input_modes=data.get("inputModes") or data.get("input_modes"),
            output_modes=data.get("outputModes") or data.get("output_modes"),
        )


@dataclasses.dataclass
class A2ACapabilities:
    """Optional protocol capabilities supported by the agent."""

    streaming: bool = False
    push_notifications: bool = True
    extended_agent_card: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "streaming": self.streaming,
            "pushNotifications": self.push_notifications,
            "extendedAgentCard": self.extended_agent_card,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2ACapabilities:
        return cls(
            streaming=bool(data.get("streaming", False)),
            push_notifications=bool(
                data.get("pushNotifications")
                if "pushNotifications" in data
                else data.get("push_notifications", True)
            ),
            extended_agent_card=bool(
                data.get("extendedAgentCard")
                if "extendedAgentCard" in data
                else data.get("extended_agent_card", False)
            ),
        )


@dataclasses.dataclass
class A2AInterface:
    """An interface binding advertised by the Agent Card."""

    url: str
    protocol_binding: str = "JSONRPC"
    protocol_version: str = "1.0"

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "protocolBinding": self.protocol_binding,
            "protocolVersion": self.protocol_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2AInterface:
        return cls(
            url=str(data.get("url", "")),
            protocol_binding=str(
                data.get("protocolBinding") or data.get("protocol_binding", "JSONRPC")
            ),
            protocol_version=str(
                data.get("protocolVersion") or data.get("protocol_version", "1.0")
            ),
        )


@dataclasses.dataclass
class A2ACard:
    """Standard public Agent Card defining identity, endpoint, and capabilities."""

    name: str
    supported_interfaces: list[A2AInterface]
    description: str | None = None
    version: str = "1.0.0"
    capabilities: A2ACapabilities = dataclasses.field(default_factory=A2ACapabilities)
    skills: list[A2ASkill] = dataclasses.field(default_factory=list)
    raw: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = dict(self.raw)
        out.update(
            {
                "name": self.name,
                "version": self.version,
                "supportedInterfaces": [i.to_dict() for i in self.supported_interfaces],
                "capabilities": self.capabilities.to_dict(),
                "skills": [s.to_dict() for s in self.skills],
            }
        )
        if self.description is not None:
            out["description"] = self.description
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2ACard:
        raw_interfaces = data.get("supportedInterfaces") or data.get("supported_interfaces") or []
        interfaces = [A2AInterface.from_dict(i) for i in raw_interfaces if isinstance(i, dict)]

        raw_skills = data.get("skills") or []
        skills = [A2ASkill.from_dict(s) for s in raw_skills if isinstance(s, dict)]

        raw_caps = data.get("capabilities") or {}
        capabilities = (
            A2ACapabilities.from_dict(raw_caps) if isinstance(raw_caps, dict) else A2ACapabilities()
        )

        return cls(
            name=str(data.get("name", "Unknown Agent")),
            description=data.get("description"),
            version=str(data.get("version", "1.0.0")),
            supported_interfaces=interfaces,
            capabilities=capabilities,
            skills=skills,
            raw=data,
        )


@dataclasses.dataclass(frozen=True)
class A2AResolvedTarget:
    """Validated target endpoint with pinned security credentials."""

    card_url: str
    rpc_url: str
    card: A2ACard
    protocol_version: str = "1.0"
    credential: str | None = None


@dataclasses.dataclass
class A2ATaskStatus:
    """Current execution status of an A2A task."""

    state: A2ATaskState | str
    message: str | None = None
    timestamp: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"state": self.state}
        if self.message is not None:
            out["message"] = self.message
        if self.timestamp is not None:
            out["timestamp"] = self.timestamp
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2ATaskStatus:
        return cls(
            state=str(data.get("state", "submitted")),
            message=data.get("message"),
            timestamp=data.get("timestamp"),
        )


@dataclasses.dataclass
class A2ATask:
    """An autonomous task executed or tracked over the A2A protocol."""

    task_id: str
    status: A2ATaskStatus
    messages: list[A2AMessage] = dataclasses.field(default_factory=list)
    artifacts: list[A2AArtifact] = dataclasses.field(default_factory=list)
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    context_id: str | None = None
    completed_at: str | None = None
    requester: dict[str, Any] | None = None
    kind: str = "task"

    @property
    def id(self) -> str:
        """Ergonomic alias for task_id."""
        return self.task_id

    @property
    def state(self) -> str:
        """Ergonomic alias for status.state."""
        return self.status.state

    @property
    def message(self) -> str | None:
        """Ergonomic alias for status.message."""
        return self.status.message

    @property
    def is_completed(self) -> bool:
        return self.status.state == "completed"

    @property
    def is_failed(self) -> bool:
        return self.status.state == "failed"

    @property
    def is_canceled(self) -> bool:
        return self.status.state == "canceled"

    @property
    def is_input_required(self) -> bool:
        return self.status.state == "input-required"

    @property
    def is_working(self) -> bool:
        return self.status.state == "working"

    @property
    def is_terminal(self) -> bool:
        return self.status.state in {"completed", "failed", "canceled"}

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "kind": self.kind,
            "taskId": self.task_id,
            "status": self.status.to_dict(),
            "messages": [m.to_dict() for m in self.messages],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "metadata": self.metadata,
            "createdAt": self.created_at,
            "updatedAt": self.updated_at,
        }
        if self.context_id is not None:
            out["contextId"] = self.context_id
        if self.completed_at is not None:
            out["completedAt"] = self.completed_at
        if self.requester is not None:
            out["requester"] = self.requester
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2ATask:
        # Handle wrapped tasks { task: { ... } } or raw { taskId: ... }
        task_data = data.get("task") if isinstance(data.get("task"), dict) else data

        task_id = str(
            task_data.get("taskId") or task_data.get("task_id") or task_data.get("id") or ""
        )

        status_raw = task_data.get("status")
        if isinstance(status_raw, dict):
            status = A2ATaskStatus.from_dict(status_raw)
        else:
            status = A2ATaskStatus(state=str(status_raw or "submitted"))

        raw_messages = task_data.get("messages") or []
        messages = [A2AMessage.from_dict(m) for m in raw_messages if isinstance(m, dict)]

        raw_artifacts = task_data.get("artifacts") or []
        artifacts = [A2AArtifact.from_dict(a) for a in raw_artifacts if isinstance(a, dict)]

        return cls(
            task_id=task_id,
            status=status,
            messages=messages,
            artifacts=artifacts,
            metadata=dict(task_data.get("metadata") or {}),
            created_at=str(task_data.get("createdAt") or task_data.get("created_at") or ""),
            updated_at=str(task_data.get("updatedAt") or task_data.get("updated_at") or ""),
            context_id=task_data.get("contextId") or task_data.get("context_id"),
            completed_at=task_data.get("completedAt") or task_data.get("completed_at"),
            requester=task_data.get("requester"),
            kind=str(task_data.get("kind", "task")),
        )


@dataclasses.dataclass
class A2ASettings:
    """Agent identity A2A receiver configuration."""

    a2a_enabled: bool
    card_url: str
    rpc_endpoint: str
    a2a_publicly_discoverable: bool = False
    a2a_capabilities: dict[str, Any] = dataclasses.field(default_factory=dict)
    a2a_skills: list[A2ASkill] = dataclasses.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "a2a_enabled": self.a2a_enabled,
            "card_url": self.card_url,
            "rpc_endpoint": self.rpc_endpoint,
            "a2a_publicly_discoverable": self.a2a_publicly_discoverable,
            "a2a_capabilities": self.a2a_capabilities,
            "a2a_skills": [s.to_dict() for s in self.a2a_skills],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> A2ASettings:
        raw_skills = data.get("a2a_skills") or data.get("skills") or []
        skills = [A2ASkill.from_dict(s) for s in raw_skills if isinstance(s, dict)]
        return cls(
            a2a_enabled=bool(data.get("a2a_enabled", data.get("enabled", False))),
            card_url=str(data.get("card_url", "")),
            rpc_endpoint=str(data.get("rpc_endpoint", "")),
            a2a_publicly_discoverable=bool(data.get("a2a_publicly_discoverable", False)),
            a2a_capabilities=dict(data.get("a2a_capabilities") or {}),
            a2a_skills=skills,
        )


@dataclasses.dataclass
class A2AWatchEvent:
    """Streaming milestone emitted by task observation."""

    task: A2ATask
    state: str
    message: str | None = None

    @property
    def is_progress(self) -> bool:
        return self.state in {"working", "submitted"}

    @property
    def is_completed(self) -> bool:
        return self.state == "completed"

    @property
    def is_failed(self) -> bool:
        return self.state == "failed"

    @property
    def is_canceled(self) -> bool:
        return self.state == "canceled"

    @property
    def is_input_required(self) -> bool:
        return self.state == "input-required"

    @property
    def is_terminal(self) -> bool:
        return self.state in {"completed", "failed", "canceled"}
