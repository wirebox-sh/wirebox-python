"""Wirebox — Real-world identity, communication, and context execution layer for AI agents.

Official Python SDK providing synchronous and asynchronous interfaces to equip autonomous
agents with dedicated phone numbers, email inboxes, network tunnels, and webhooks.
"""

from wirebox._version import __version__
from wirebox.async_client import AsyncWirebox
from wirebox.client import Wirebox
from wirebox.exceptions import (
    AuthenticationError,
    FreeTierLimitExceededError,
    HandleAlreadyTakenError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    WireboxAPIError,
    WireboxConnectionError,
    WireboxError,
)
from wirebox.identity import AgentIdentity, AsyncAgentIdentity
from wirebox.imessage import AsyncIMessageClient, IMessageClient
from wirebox.tunnels import TunnelSession
from wirebox.types import (
    EmailMessage,
    IdentityData,
    IdentityTunnelSummary,
    ImessageConversation,
    ImessageConversationLastMessage,
    ImessageMessage,
    ImessageRouterInfo,
    ImessageUser,
    MailboxSummary,
    MessageAttachmentSummary,
    MessageSummary,
    SendEmailAttachment,
    SendEmailResult,
    SendImessageResult,
    Tunnel,
    TunnelClientTelemetry,
    Webhook,
    WebhookCreateResult,
    WebhookEventType,
    WebhookRotateSecretResult,
    WebhookStatus,
    WebhookTestResult,
    WhoamiApiKey,
    WhoamiOrganization,
    WhoamiResult,
)
from wirebox.verify_webhook import verify_webhook

# Canonical aliases for cross-SDK naming consistency
WireboxClient = Wirebox
AsyncWireboxClient = AsyncWirebox

__all__ = [
    "__version__",
    "Wirebox",
    "WireboxClient",
    "AsyncWirebox",
    "AsyncWireboxClient",
    "AgentIdentity",
    "AsyncAgentIdentity",
    "IMessageClient",
    "AsyncIMessageClient",
    "TunnelSession",
    "verify_webhook",
    # Exceptions
    "WireboxError",
    "WireboxAPIError",
    "AuthenticationError",
    "NotFoundError",
    "RateLimitError",
    "HandleAlreadyTakenError",
    "FreeTierLimitExceededError",
    "WireboxConnectionError",
    "ValidationError",
    # Types
    "IdentityData",
    "IdentityTunnelSummary",
    "MailboxSummary",
    "SendEmailAttachment",
    "SendEmailResult",
    "SendImessageResult",
    "MessageAttachmentSummary",
    "MessageSummary",
    "EmailMessage",
    "ImessageRouterInfo",
    "ImessageConversation",
    "ImessageConversationLastMessage",
    "ImessageMessage",
    "ImessageUser",
    "Tunnel",
    "TunnelClientTelemetry",
    "Webhook",
    "WebhookCreateResult",
    "WebhookTestResult",
    "WebhookRotateSecretResult",
    "WebhookEventType",
    "WebhookStatus",
    "WhoamiOrganization",
    "WhoamiApiKey",
    "WhoamiResult",
]
