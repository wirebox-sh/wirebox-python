"""Wirebox Python SDK — Core Data Types and Models.

Defines immutable, strongly-typed dataclasses for all Wirebox domain objects:
identities, mailboxes, messages, tunnels, webhooks, and whoami introspection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# ============================================================================
# Identity & Mailbox Types
# ============================================================================


@dataclass(frozen=True)
class MailboxSummary:
    """Summary representation of an agent's assigned mailbox."""

    id: str
    email_address: str
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MailboxSummary:
        return cls(
            id=str(data.get("id", "")),
            email_address=str(data.get("email_address", "")),
            created_at=str(data.get("created_at", "")),
        )


@dataclass(frozen=True)
class IdentityTunnelSummary:
    """Summary representation of an agent's network tunnel attached to its identity."""

    id: str
    public_url: str
    status: Literal["active", "disabled"] = "active"
    is_connected: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IdentityTunnelSummary:
        return cls(
            id=str(data.get("id", "")),
            public_url=str(data.get("public_url", "")),
            status=data.get("status", "active"),
            is_connected=bool(data.get("is_connected", False)),
        )


@dataclass(frozen=True)
class IdentityData:
    """Raw snapshot of an agent identity returned by the API."""

    id: str
    organization_id: str
    agent_handle: str
    display_name: str | None
    description: str | None
    status: Literal["active", "archived", "deleted"]
    created_at: str
    updated_at: str
    mailboxes: list[MailboxSummary] = field(default_factory=list)
    tunnel: IdentityTunnelSummary | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IdentityData:
        mailboxes: list[MailboxSummary] = []
        if "mailboxes" in data and isinstance(data["mailboxes"], list):
            for m in data["mailboxes"]:
                if isinstance(m, dict):
                    mailboxes.append(MailboxSummary.from_dict(m))
                elif isinstance(m, MailboxSummary):
                    mailboxes.append(m)
        elif "mailbox" in data and isinstance(data["mailbox"], dict):
            mailboxes.append(MailboxSummary.from_dict(data["mailbox"]))
        elif "email_address" in data and data["email_address"]:
            mailboxes.append(
                MailboxSummary(
                    id=str(data.get("mailbox_id") or ""),
                    email_address=str(data["email_address"]),
                    created_at=str(data.get("created_at") or ""),
                )
            )
        else:
            handle = str(data.get("agent_handle", ""))
            if handle:
                mailboxes.append(
                    MailboxSummary(
                        id="",
                        email_address=f"{handle}@wireboxmail.com",
                        created_at=str(data.get("created_at") or ""),
                    )
                )

        tunnel_summary: IdentityTunnelSummary | None = None
        if "tunnel" in data and isinstance(data["tunnel"], dict):
            tunnel_summary = IdentityTunnelSummary.from_dict(data["tunnel"])
        elif "tunnels" in data and isinstance(data["tunnels"], list) and data["tunnels"]:
            first_t = data["tunnels"][0]
            if isinstance(first_t, dict):
                tunnel_summary = IdentityTunnelSummary.from_dict(first_t)
            elif isinstance(first_t, IdentityTunnelSummary):
                tunnel_summary = first_t
        elif "agent_handle" in data:
            handle = str(data["agent_handle"])
            tunnel_summary = IdentityTunnelSummary(
                id="",
                public_url=f"https://{handle}.wirebox.run",
                status="active",
                is_connected=False,
            )

        return cls(
            id=str(data.get("id", "")),
            organization_id=str(data.get("organization_id", "")),
            agent_handle=str(data.get("agent_handle", "")),
            display_name=data.get("display_name"),
            description=data.get("description"),
            status=data.get("status", "active"),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            mailboxes=mailboxes,
            tunnel=tunnel_summary,
        )


# ============================================================================
# Mail & Message Types
# ============================================================================


@dataclass(frozen=True)
class SendEmailAttachment:
    """Attachment specification for sending an email."""

    filename: str
    content_type: str
    content: str  # Base64-encoded string


@dataclass(frozen=True)
class SendEmailResult:
    """Result of an outbound email dispatch."""

    message_id: str
    id: str
    status: Literal["queued", "sent", "failed"] | str = "queued"
    thread_id: str | None = None
    mailbox_address: str | None = None
    created_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendEmailResult:
        resolved_id = str(data.get("id") or data.get("message_id") or "")
        resolved_msg_id = str(data.get("message_id") or data.get("id") or "")
        return cls(
            message_id=resolved_msg_id,
            id=resolved_id,
            status=data.get("status", "queued"),
            thread_id=data.get("thread_id"),
            mailbox_address=data.get("mailbox_address"),
            created_at=data.get("created_at"),
        )


@dataclass(frozen=True)
class MessageAttachmentSummary:
    """Metadata summary of an email attachment."""

    id: str
    filename: str
    content_type: str
    size_bytes: int
    download_url: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MessageAttachmentSummary:
        return cls(
            id=str(data.get("id", "")),
            filename=str(data.get("filename", "")),
            content_type=str(data.get("content_type", "")),
            size_bytes=int(data.get("size_bytes", 0)),
            download_url=data.get("download_url"),
        )


@dataclass(frozen=True)
class MessageSummary:
    """Compact summary of an email message in an inbox list."""

    id: str
    mailbox_id: str
    direction: Literal["inbound", "outbound"]
    from_address: str
    to_addresses: list[str]
    subject: str
    preview: str
    status: Literal["queued", "sent", "delivered", "bounced", "failed"] | str
    created_at: str
    thread_id: str | None = None
    is_read: bool = False
    is_starred: bool = False
    has_attachments: bool = False
    cc_addresses: list[str] = field(default_factory=list)

    @property
    def snippet(self) -> str:
        """Alias for preview matching Core API and CLI format."""
        return self.preview

    @property
    def from_(self) -> str:
        """Alias for from_address."""
        return self.from_address

    @property
    def to(self) -> list[str]:
        """Alias for to_addresses."""
        return self.to_addresses

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MessageSummary:
        from_val = str(data.get("from_address") or data.get("from") or "")

        to_raw = data.get("to_addresses") if "to_addresses" in data else data.get("to")
        if isinstance(to_raw, list):
            to_list = [str(x) for x in to_raw]
        elif isinstance(to_raw, str):
            to_list = [to_raw]
        else:
            to_list = []

        cc_raw = data.get("cc_addresses") if "cc_addresses" in data else data.get("cc")
        if isinstance(cc_raw, list):
            cc_list = [str(x) for x in cc_raw]
        elif isinstance(cc_raw, str):
            cc_list = [cc_raw]
        else:
            cc_list = []

        preview_val = str(data.get("preview") or data.get("snippet") or "")

        return cls(
            id=str(data.get("id", "")),
            mailbox_id=str(data.get("mailbox_id", "")),
            direction=data.get("direction", "inbound"),
            from_address=from_val,
            to_addresses=to_list,
            subject=str(data.get("subject", "")),
            preview=preview_val,
            status=data.get("status", "delivered"),
            created_at=str(data.get("created_at", "")),
            thread_id=data.get("thread_id"),
            is_read=bool(data.get("is_read", False)),
            is_starred=bool(data.get("is_starred", False)),
            has_attachments=bool(data.get("has_attachments", False)),
            cc_addresses=cc_list,
        )


@dataclass(frozen=True)
class EmailMessage:
    """Full detail of an email message including body content and headers."""

    id: str
    mailbox_id: str
    direction: Literal["inbound", "outbound"]
    from_address: str
    to_addresses: list[str]
    cc_addresses: list[str]
    bcc_addresses: list[str]
    reply_to: str | None
    subject: str
    text: str | None
    html: str | None
    attachments: list[MessageAttachmentSummary]
    status: Literal["queued", "sent", "delivered", "bounced", "failed"] | str
    created_at: str
    headers: dict[str, str] = field(default_factory=dict)
    thread_id: str | None = None
    in_reply_to_message_id: str | None = None
    is_read: bool = False
    is_starred: bool = False

    @property
    def from_(self) -> str:
        """Alias for from_address."""
        return self.from_address

    @property
    def to(self) -> list[str]:
        """Alias for to_addresses."""
        return self.to_addresses

    @property
    def cc(self) -> list[str]:
        """Alias for cc_addresses."""
        return self.cc_addresses

    @property
    def bcc(self) -> list[str]:
        """Alias for bcc_addresses."""
        return self.bcc_addresses

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmailMessage:
        attachments_raw = data.get("attachments", [])
        attachments = [
            MessageAttachmentSummary.from_dict(a) if isinstance(a, dict) else a
            for a in attachments_raw
        ]

        from_val = str(data.get("from_address") or data.get("from") or "")

        to_raw = data.get("to_addresses") if "to_addresses" in data else data.get("to")
        if isinstance(to_raw, list):
            to_list = [str(x) for x in to_raw]
        elif isinstance(to_raw, str):
            to_list = [to_raw]
        else:
            to_list = []

        cc_raw = data.get("cc_addresses") if "cc_addresses" in data else data.get("cc")
        if isinstance(cc_raw, list):
            cc_list = [str(x) for x in cc_raw]
        elif isinstance(cc_raw, str):
            cc_list = [cc_raw]
        else:
            cc_list = []

        bcc_raw = data.get("bcc_addresses") if "bcc_addresses" in data else data.get("bcc")
        if isinstance(bcc_raw, list):
            bcc_list = [str(x) for x in bcc_raw]
        elif isinstance(bcc_raw, str):
            bcc_list = [bcc_raw]
        else:
            bcc_list = []

        return cls(
            id=str(data.get("id", "")),
            mailbox_id=str(data.get("mailbox_id", "")),
            direction=data.get("direction", "inbound"),
            from_address=from_val,
            to_addresses=to_list,
            cc_addresses=cc_list,
            bcc_addresses=bcc_list,
            reply_to=data.get("reply_to"),
            subject=str(data.get("subject", "")),
            text=data.get("text"),
            html=data.get("html"),
            attachments=attachments,
            status=data.get("status", "delivered"),
            created_at=str(data.get("created_at", "")),
            headers=dict(data.get("headers", {})),
            thread_id=data.get("thread_id"),
            in_reply_to_message_id=data.get("in_reply_to_message_id"),
            is_read=bool(data.get("is_read", False)),
            is_starred=bool(data.get("is_starred", False)),
        )


# ============================================================================
# Tunnel Types
# ============================================================================


@dataclass(frozen=True)
class TunnelClientTelemetry:
    """Diagnostic telemetry reported by a connected tunnel client."""

    ip: str | None = None
    version: str | None = None
    forward_to: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> TunnelClientTelemetry:
        if not data:
            return cls()
        return cls(
            ip=data.get("ip"),
            version=data.get("version"),
            forward_to=data.get("forward_to"),
        )


@dataclass(frozen=True)
class Tunnel:
    """Represents an agent's secure network tunnel."""

    id: str
    agent_handle: str
    public_url: str
    public_host: str
    status: Literal["active", "disabled"]
    is_connected: bool
    connected_clients: int
    connected_at: str | None
    disconnected_at: str | None
    last_request_at: str | None
    client: TunnelClientTelemetry
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tunnel:
        client_data = data.get("client")
        client = TunnelClientTelemetry.from_dict(
            client_data if isinstance(client_data, dict) else None
        )
        return cls(
            id=str(data.get("id", "")),
            agent_handle=str(data.get("agent_handle", "")),
            public_url=str(data.get("public_url", "")),
            public_host=str(data.get("public_host", "")),
            status=data.get("status", "active"),
            is_connected=bool(data.get("is_connected", False)),
            connected_clients=int(data.get("connected_clients", 0)),
            connected_at=data.get("connected_at"),
            disconnected_at=data.get("disconnected_at"),
            last_request_at=data.get("last_request_at"),
            client=client,
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


# ============================================================================
# Webhook Types
# ============================================================================

WebhookEventType = Literal[
    # Email Events
    "email.received",
    "email.sent",
    "email.delivered",
    "email.bounced",
    "email.failed",
    # SMS Events
    "sms.received",
    "sms.sent",
    "sms.delivered",
    "sms.failed",
    # iMessage Events
    "imessage.connected",
    "imessage.disconnected",
    "imessage.received",
    "imessage.sent",
    "imessage.delivered",
    "imessage.failed",
    # System Events
    "test.ping",
    "*",
    str,
]

WebhookStatus = Literal["active", "paused"]


@dataclass(frozen=True)
class Webhook:
    """Webhook subscription configuration."""

    id: str
    agent_handle: str | None
    mailbox_address: str | None
    url: str
    events: list[str]
    auth_token: str | None
    has_auth_token: bool
    status: WebhookStatus
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Webhook:
        return cls(
            id=str(data.get("id", "")),
            agent_handle=data.get("agent_handle"),
            mailbox_address=data.get("mailbox_address"),
            url=str(data.get("url", "")),
            events=list(data.get("events", [])),
            auth_token=data.get("auth_token"),
            has_auth_token=bool(data.get("has_auth_token", False)),
            status=data.get("status", "active"),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


@dataclass(frozen=True)
class WebhookCreateResult(Webhook):
    """Result of creating a webhook, including the one-time HMAC signing secret."""

    secret: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebhookCreateResult:
        base = Webhook.from_dict(data)
        return cls(
            id=base.id,
            agent_handle=base.agent_handle,
            mailbox_address=base.mailbox_address,
            url=base.url,
            events=base.events,
            auth_token=base.auth_token,
            has_auth_token=base.has_auth_token,
            status=base.status,
            created_at=base.created_at,
            updated_at=base.updated_at,
            secret=str(data.get("secret", "")),
        )


@dataclass(frozen=True)
class WebhookTestResult:
    """Outcome of sending an immediate test.ping event to a webhook endpoint."""

    webhook_id: str
    url: str
    event_type: str
    status_code: int | None
    latency_ms: int
    success: bool
    error: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebhookTestResult:
        return cls(
            webhook_id=str(data.get("webhook_id", "")),
            url=str(data.get("url", "")),
            event_type=str(data.get("event_type", "test.ping")),
            status_code=data.get("status_code"),
            latency_ms=int(data.get("latency_ms", 0)),
            success=bool(data.get("success", False)),
            error=data.get("error"),
        )


@dataclass(frozen=True)
class WebhookRotateSecretResult:
    """Result of rotating a webhook's HMAC signing secret."""

    id: str
    secret: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WebhookRotateSecretResult:
        return cls(
            id=str(data.get("id", "")),
            secret=str(data.get("secret", "")),
            updated_at=str(data.get("updated_at", "")),
        )


# ============================================================================
# Whoami Types
# ============================================================================


@dataclass(frozen=True)
class WhoamiOrganization:
    """Organization metadata associated with the current authentication context."""

    id: str
    name: str
    slug: str
    billing_plan: str
    is_claimed: bool
    claimed_by_email: str | None
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WhoamiOrganization:
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            slug=str(data.get("slug", "")),
            billing_plan=str(data.get("billing_plan", "free")),
            is_claimed=bool(data.get("is_claimed", False)),
            claimed_by_email=data.get("claimed_by_email"),
            created_at=str(data.get("created_at", "")),
        )


@dataclass(frozen=True)
class WhoamiApiKey:
    """Metadata for the authenticated API key."""

    id: str
    name: str
    key_prefix: str
    key_preview: str
    role: str
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WhoamiApiKey:
        return cls(
            id=str(data.get("id", "")),
            name=str(data.get("name", "")),
            key_prefix=str(data.get("key_prefix", "")),
            key_preview=str(data.get("key_preview", "")),
            role=str(data.get("role", "")),
            created_at=str(data.get("created_at", "")),
        )


@dataclass(frozen=True)
class WhoamiAuth:
    """Authentication and actor context returned by /v1/me."""

    type: Literal["api_key", "jwt"] | str
    actor_id: str
    scoped_identity_id: str | None = None
    scopes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WhoamiAuth:
        return cls(
            type=str(data.get("type", "api_key")),
            actor_id=str(data.get("actor_id", "")),
            scoped_identity_id=data.get("scoped_identity_id"),
            scopes=list(data.get("scopes", [])),
        )


@dataclass(frozen=True)
class WhoamiUsage:
    """Usage limits and current counts returned by /v1/me."""

    agents_count: int = 0
    agents_limit: int = 0
    webhooks_count: int = 0
    webhooks_limit: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WhoamiUsage:
        return cls(
            agents_count=int(data.get("agents_count", 0)),
            agents_limit=int(data.get("agents_limit", 0)),
            webhooks_count=int(data.get("webhooks_count", 0)),
            webhooks_limit=int(data.get("webhooks_limit", 0)),
        )


@dataclass(frozen=True)
class WhoamiResult:
    """Introspection payload describing the active credentials and organization context."""

    organization: WhoamiOrganization
    auth: WhoamiAuth
    usage: WhoamiUsage = field(default_factory=lambda: WhoamiUsage())
    api_key: WhoamiApiKey | None = None

    @property
    def authenticated(self) -> bool:
        return bool(self.organization and self.organization.id)

    @property
    def type(self) -> str:
        return str(self.auth.type)

    @property
    def org_id(self) -> str:
        return self.organization.id

    @property
    def actor_id(self) -> str:
        return self.auth.actor_id

    @property
    def scoped_identity_id(self) -> str | None:
        return self.auth.scoped_identity_id

    @property
    def agent_identity_id(self) -> str | None:
        return self.auth.scoped_identity_id

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WhoamiResult:
        org_raw = data.get("organization") or {}
        org = WhoamiOrganization.from_dict(org_raw) if isinstance(org_raw, dict) else org_raw

        auth_raw = data.get("auth") or {}
        if not auth_raw and "api_key" in data and isinstance(data["api_key"], dict):
            k = data["api_key"]
            auth = WhoamiAuth(
                type=str(data.get("type", "api_key")),
                actor_id=str(k.get("id", "")),
                scoped_identity_id=data.get("agent_identity_id"),
                scopes=[],
            )
        else:
            auth = WhoamiAuth.from_dict(auth_raw) if isinstance(auth_raw, dict) else auth_raw

        usage_raw = data.get("usage") or {}
        usage = WhoamiUsage.from_dict(usage_raw) if isinstance(usage_raw, dict) else usage_raw

        api_key_raw = data.get("api_key")
        api_key = WhoamiApiKey.from_dict(api_key_raw) if isinstance(api_key_raw, dict) else None

        return cls(
            organization=org,
            auth=auth,
            usage=usage,
            api_key=api_key,
        )


# ============================================================================
# iMessage Types
# ============================================================================


@dataclass(frozen=True)
class ImessageRouterInfo:
    """Active iMessage router number, connect command, and QR code URI."""

    router_number: str
    agent_handle: str
    connect_command: str
    qr_uri: str
    status: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImessageRouterInfo:
        return cls(
            router_number=str(data.get("router_number", "")),
            agent_handle=str(data.get("agent_handle", "")),
            connect_command=str(data.get("connect_command", "")),
            qr_uri=str(data.get("qr_uri", "")),
            status=str(data.get("status", "online")),
        )


@dataclass(frozen=True)
class ImessageConversationLastMessage:
    """Summary of the latest message in an iMessage conversation."""

    id: str
    direction: Literal["inbound", "outbound"]
    text: str | None
    has_media: bool
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImessageConversationLastMessage:
        return cls(
            id=str(data.get("id", "")),
            direction=data.get("direction", "inbound"),
            text=data.get("text"),
            has_media=bool(data.get("has_media", False)),
            created_at=str(data.get("created_at", "")),
        )


@dataclass(frozen=True)
class ImessageConversation:
    """An iMessage conversation between an agent identity and a human recipient."""

    id: str
    identity_id: str
    user_phone: str
    status: Literal["connected", "disconnected"]
    unread_count: int
    created_at: str
    updated_at: str
    last_message: ImessageConversationLastMessage | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImessageConversation:
        last_msg_raw = data.get("last_message")
        return cls(
            id=str(data.get("id", "")),
            identity_id=str(data.get("identity_id", "")),
            user_phone=str(data.get("user_phone", "")),
            status=data.get("status", "connected"),
            unread_count=int(data.get("unread_count", 0)),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            last_message=ImessageConversationLastMessage.from_dict(last_msg_raw)
            if isinstance(last_msg_raw, dict)
            else None,
        )


@dataclass(frozen=True)
class ImessageMessage:
    """A message in an iMessage conversation."""

    id: str
    conversation_id: str
    identity_id: str
    direction: Literal["inbound", "outbound"]
    sender: str
    text: str | None
    media_url: str | None
    is_read: bool
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ImessageMessage:
        return cls(
            id=str(data.get("id", "")),
            conversation_id=str(data.get("conversation_id", "")),
            identity_id=str(data.get("identity_id", "")),
            direction=data.get("direction", "inbound"),
            sender=str(data.get("sender", "")),
            text=data.get("text"),
            media_url=data.get("media_url"),
            is_read=bool(data.get("is_read", False)),
            created_at=str(data.get("created_at", "")),
        )


@dataclass(frozen=True)
class SendImessageResult:
    """Delivery confirmation for an outbound iMessage."""

    id: str
    conversation_id: str
    identity_id: str
    direction: str
    to: str
    text: str | None
    media_url: str | None
    status: str
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SendImessageResult:
        return cls(
            id=str(data.get("id", "")),
            conversation_id=str(data.get("conversation_id", "")),
            identity_id=str(data.get("identity_id", "")),
            direction=str(data.get("direction", "outbound")),
            to=str(data.get("to", "")),
            text=data.get("text"),
            media_url=data.get("media_url"),
            status=str(data.get("status", "sent")),
            created_at=str(data.get("created_at", "")),
        )


# ============================================================================
# Phone & SMS Types
# ============================================================================


@dataclass(frozen=True)
class PhoneNumberCapabilities:
    """Supported carrier capabilities for a phone number."""

    sms: bool = True
    mms: bool = False
    voice: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> PhoneNumberCapabilities:
        if not data:
            return cls()
        return cls(
            sms=bool(data.get("sms", True)),
            mms=bool(data.get("mms", False)),
            voice=bool(data.get("voice", False)),
        )


@dataclass(frozen=True)
class PhoneNumber:
    """A carrier phone number bound to an agent identity."""

    id: str
    phone_number: str
    country_code: str
    type: str
    region: str | None
    agent_handle: str
    agent_identity_id: str
    status: str
    sms_status: str
    sms_error_code: str | None
    sms_error_detail: str | None
    sms_ready_at: str | None
    capabilities: PhoneNumberCapabilities
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PhoneNumber:
        return cls(
            id=str(data.get("id", "")),
            phone_number=str(data.get("phone_number", "")),
            country_code=str(data.get("country_code", "US")),
            type=str(data.get("type", "local")),
            region=data.get("region"),
            agent_handle=str(data.get("agent_handle", "")),
            agent_identity_id=str(data.get("agent_identity_id", "")),
            status=str(data.get("status", "active")),
            sms_status=str(data.get("sms_status", "ready")),
            sms_error_code=data.get("sms_error_code"),
            sms_error_detail=data.get("sms_error_detail"),
            sms_ready_at=data.get("sms_ready_at"),
            capabilities=PhoneNumberCapabilities.from_dict(data.get("capabilities")),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
        )


@dataclass(frozen=True)
class PhoneMediaItem:
    """MMS media attachment item with signed download URL."""

    content_type: str
    size_bytes: int
    url: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PhoneMediaItem:
        return cls(
            content_type=str(data.get("content_type", "")),
            size_bytes=int(data.get("size_bytes", 0)),
            url=data.get("url"),
        )


@dataclass(frozen=True)
class PhoneMessage:
    """An SMS or MMS message received on a carrier phone number."""

    id: str
    phone_number: str
    agent_handle: str
    direction: str
    type: str
    from_number: str
    to_numbers: list[str]
    text: str
    media: list[PhoneMediaItem] | None
    is_read: bool
    segments: int
    created_at: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PhoneMessage:
        media_raw = data.get("media")
        media = (
            [PhoneMediaItem.from_dict(m) for m in media_raw]
            if isinstance(media_raw, list)
            else None
        )
        return cls(
            id=str(data.get("id", "")),
            phone_number=str(data.get("phone_number", "")),
            agent_handle=str(data.get("agent_handle", "")),
            direction=str(data.get("direction", "inbound")),
            type=str(data.get("type", "sms")),
            from_number=str(data.get("from_number", "")),
            to_numbers=list(data.get("to_numbers", [])),
            text=str(data.get("text", "")),
            media=media,
            is_read=bool(data.get("is_read", False)),
            segments=int(data.get("segments", 1)),
            created_at=str(data.get("created_at", "")),
        )


@dataclass(frozen=True)
class ListPhoneNumbersResult:
    """Paginated list of carrier phone numbers."""

    numbers: list[PhoneNumber]
    next_cursor: str | None
    has_more: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ListPhoneNumbersResult:
        items = [PhoneNumber.from_dict(n) for n in data.get("numbers", [])]
        return cls(
            numbers=items,
            next_cursor=data.get("next_cursor"),
            has_more=bool(data.get("has_more", False)),
        )


@dataclass(frozen=True)
class ListPhoneMessagesResult:
    """Paginated list of SMS/MMS messages."""

    messages: list[PhoneMessage]
    next_cursor: str | None
    has_more: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ListPhoneMessagesResult:
        items = [PhoneMessage.from_dict(m) for m in data.get("messages", [])]
        return cls(
            messages=items,
            next_cursor=data.get("next_cursor"),
            has_more=bool(data.get("has_more", False)),
        )
