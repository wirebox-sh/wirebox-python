"""Wirebox Python SDK — Exception Hierarchy.

Provides structured, typed exceptions for network, authentication, validation,
and API error conditions with full request ID tracing.
"""

from __future__ import annotations

from typing import Any


class WireboxError(Exception):
    """Base exception for all Wirebox SDK errors."""


class WireboxConnectionError(WireboxError):
    """Raised when an HTTP or WebSocket connection fails or times out."""

    def __init__(self, message: str, original_error: Exception | None = None) -> None:
        super().__init__(message)
        self.original_error = original_error


class ValidationError(WireboxError):
    """Raised when client-side parameter validation fails before sending a request."""


class WireboxAPIError(WireboxError):
    """Raised when the Wirebox Edge Core API returns a non-2xx response.

    Attributes:
        status: HTTP response status code (e.g. 400, 401, 404, 429, 500).
        code: Machine-readable error code (e.g. 'handle_already_taken', 'unauthorized').
        message: Human-readable error message explaining the failure.
        request_id: Optional Wirebox request ID (x-wirebox-request-id) for tracing.
        details: Optional structured details dictionary from the server.
    """

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        request_id: str | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(
            f"[{status} {code}] {message}"
            if request_id is None
            else f"[{status} {code}] {message} (request_id: {request_id})"
        )
        self.status = status
        self.code = code
        self.message = message
        self.request_id = request_id
        self.details = details


class AuthenticationError(WireboxAPIError):
    """Raised on HTTP 401 or 403 when the provided API key is missing, invalid, or lacks permissions."""


class NotFoundError(WireboxAPIError):
    """Raised on HTTP 404 when the requested identity, mailbox, message, tunnel, or webhook does not exist."""


class RateLimitError(WireboxAPIError):
    """Raised on HTTP 429 when API rate limits are exceeded."""


class HandleAlreadyTakenError(WireboxAPIError):
    """Raised on HTTP 409 when attempting to create an identity with an agent_handle that is already claimed."""


class FreeTierLimitExceededError(WireboxAPIError):
    """Raised when an organization attempts to provision resources beyond their free tier allowance."""


def parse_api_error(status: int, data: Any, request_id: str | None = None) -> WireboxAPIError:
    """Parses a response status and body into the appropriate WireboxAPIError subclass."""
    code = "unknown_error"
    message = f"Request failed with HTTP status {status}"
    details: Any = None

    if isinstance(data, dict):
        if "error" in data:
            err = data["error"]
            if isinstance(err, dict):
                code = str(err.get("code", code))
                message = str(err.get("message", message))
                details = err.get("details", data)
            elif isinstance(err, str):
                message = err
        elif "message" in data:
            message = str(data["message"])
            if "code" in data:
                code = str(data["code"])
        details = data

    clean_code = code.lower()

    if status in (401, 403):
        if "free_tier" in clean_code or "quota" in clean_code:
            return FreeTierLimitExceededError(status, code, message, request_id, details)
        return AuthenticationError(status, code, message, request_id, details)

    if status == 404:
        return NotFoundError(status, code, message, request_id, details)

    if status == 409 or clean_code in ("handle_already_taken", "conflict"):
        return HandleAlreadyTakenError(status, code, message, request_id, details)

    if status == 429:
        if "free_tier" in clean_code:
            return FreeTierLimitExceededError(status, code, message, request_id, details)
        return RateLimitError(status, code, message, request_id, details)

    return WireboxAPIError(status, code, message, request_id, details)
