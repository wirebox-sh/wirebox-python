"""Wirebox Python SDK — Mail Rules & Security Guardrails Client.

Provides synchronous and asynchronous clients for managing inbound and outbound
email security rules (allowlist/blocklist) and high-level policy postures (protected/open/restricted)
scoped to agent identities.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from wirebox._http import AsyncHttpTransport, SyncHttpTransport
from wirebox.types import (
    DeleteMailRuleResult,
    InboundMailPolicy,
    ListMailRulesResult,
    MailPolicy,
    MailRule,
    MailRuleAction,
    MailRuleDirection,
    MailRuleStatus,
    OutboundMailPolicy,
)


def _clean_handle(agent_handle: str) -> str:
    return agent_handle.strip().lstrip("@").lower()


def _resolve_modes(
    inbound: InboundMailPolicy | None,
    outbound: OutboundMailPolicy | None,
) -> tuple[str | None, str | None]:
    target_inbound = None
    if inbound is not None:
        target_inbound = "whitelist" if inbound in ("protected", "allowlist") else "blacklist"

    target_outbound = None
    if outbound is not None:
        target_outbound = "whitelist" if outbound in ("restricted", "allowlist") else "blacklist"

    return target_inbound, target_outbound


def _parse_policy(data: dict[str, Any]) -> MailPolicy:
    in_mode = data.get("mail_inbound_filter_mode") or data.get("mail_filter_mode")
    out_mode = data.get("mail_outbound_filter_mode") or data.get("mail_filter_mode")
    return MailPolicy(
        inbound="protected" if in_mode == "whitelist" else "open",
        outbound="restricted" if out_mode == "whitelist" else "open",
    )


class MailRulesClient:
    """Synchronous client for managing agent mail rules and security guardrails."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self._http = http

    def list(
        self,
        agent_handle: str,
        *,
        direction: MailRuleDirection | None = None,
        action: MailRuleAction | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ListMailRulesResult:
        """Lists mail rules for an agent identity."""
        handle = _clean_handle(agent_handle)
        params: dict[str, Any] = {}
        if direction is not None:
            params["direction"] = direction
        if action is not None:
            params["action"] = action
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        data = self._http.get(f"/v1/identities/{quote(handle)}/mail-rules", params=params)
        return ListMailRulesResult.from_dict(data)

    def get(self, agent_handle: str, rule_id: str) -> MailRule:
        """Retrieves a single mail rule by its ID."""
        handle = _clean_handle(agent_handle)
        data = self._http.get(f"/v1/identities/{quote(handle)}/mail-rules/{quote(rule_id)}")
        return MailRule.from_dict(data)

    def create(
        self,
        agent_handle: str,
        entry: str,
        *,
        action: MailRuleAction = "allow",
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        """Creates a new mail rule for an agent identity."""
        handle = _clean_handle(agent_handle)
        payload: dict[str, Any] = {
            "entry": entry.strip(),
            "action": action,
            "direction": direction,
        }
        if reason is not None:
            payload["reason"] = reason

        data = self._http.post(f"/v1/identities/{quote(handle)}/mail-rules", json=payload)
        return MailRule.from_dict(data)

    def allow(
        self,
        agent_handle: str,
        entry: str,
        *,
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        """Ergonomic helper: allows an email address or domain pattern."""
        return self.create(
            agent_handle,
            entry,
            action="allow",
            direction=direction,
            reason=reason,
        )

    def block(
        self,
        agent_handle: str,
        entry: str,
        *,
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        """Ergonomic helper: blocks an email address or domain pattern."""
        return self.create(
            agent_handle,
            entry,
            action="block",
            direction=direction,
            reason=reason,
        )

    def update(
        self,
        agent_handle: str,
        rule_id: str,
        *,
        action: MailRuleAction | None = None,
        direction: MailRuleDirection | None = None,
        reason: str | None = None,
        status: MailRuleStatus | None = None,
    ) -> MailRule:
        """Updates an existing mail rule."""
        handle = _clean_handle(agent_handle)
        payload: dict[str, Any] = {}
        if action is not None:
            payload["action"] = action
        if direction is not None:
            payload["direction"] = direction
        if reason is not None:
            payload["reason"] = reason
        if status is not None:
            payload["status"] = status

        data = self._http.patch(
            f"/v1/identities/{quote(handle)}/mail-rules/{quote(rule_id)}",
            json=payload,
        )
        return MailRule.from_dict(data)

    def delete(self, agent_handle: str, rule_id: str) -> DeleteMailRuleResult:
        """Deletes a mail rule by ID."""
        handle = _clean_handle(agent_handle)
        data = self._http.delete(f"/v1/identities/{quote(handle)}/mail-rules/{quote(rule_id)}")
        return DeleteMailRuleResult.from_dict(data or {"deleted": True, "id": rule_id})

    def get_policy(self, agent_handle: str) -> MailPolicy:
        """Retrieves the current inbound and outbound mail security policy."""
        handle = _clean_handle(agent_handle)
        data = self._http.get(f"/v1/identities/{quote(handle)}")
        return _parse_policy(data)

    def set_policy(
        self,
        agent_handle: str,
        *,
        inbound: InboundMailPolicy | None = None,
        outbound: OutboundMailPolicy | None = None,
    ) -> MailPolicy:
        """Configures the inbound and outbound mail security policy."""
        handle = _clean_handle(agent_handle)
        target_in, target_out = _resolve_modes(inbound, outbound)
        payload: dict[str, Any] = {}
        if target_in is not None:
            payload["mail_inbound_filter_mode"] = target_in
        if target_out is not None:
            payload["mail_outbound_filter_mode"] = target_out

        data = self._http.patch(f"/v1/identities/{quote(handle)}", json=payload)
        return _parse_policy(data)


class AsyncMailRulesClient:
    """Asynchronous client for managing agent mail rules and security guardrails."""

    def __init__(self, http: AsyncHttpTransport) -> None:
        self._http = http

    async def list(
        self,
        agent_handle: str,
        *,
        direction: MailRuleDirection | None = None,
        action: MailRuleAction | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ListMailRulesResult:
        """Lists mail rules for an agent identity asynchronously."""
        handle = _clean_handle(agent_handle)
        params: dict[str, Any] = {}
        if direction is not None:
            params["direction"] = direction
        if action is not None:
            params["action"] = action
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        data = await self._http.get(f"/v1/identities/{quote(handle)}/mail-rules", params=params)
        return ListMailRulesResult.from_dict(data)

    async def get(self, agent_handle: str, rule_id: str) -> MailRule:
        """Retrieves a single mail rule by its ID asynchronously."""
        handle = _clean_handle(agent_handle)
        data = await self._http.get(f"/v1/identities/{quote(handle)}/mail-rules/{quote(rule_id)}")
        return MailRule.from_dict(data)

    async def create(
        self,
        agent_handle: str,
        entry: str,
        *,
        action: MailRuleAction = "allow",
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        """Creates a new mail rule for an agent identity asynchronously."""
        handle = _clean_handle(agent_handle)
        payload: dict[str, Any] = {
            "entry": entry.strip(),
            "action": action,
            "direction": direction,
        }
        if reason is not None:
            payload["reason"] = reason

        data = await self._http.post(f"/v1/identities/{quote(handle)}/mail-rules", json=payload)
        return MailRule.from_dict(data)

    async def allow(
        self,
        agent_handle: str,
        entry: str,
        *,
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        """Ergonomic helper: allows an email address or domain pattern asynchronously."""
        return await self.create(
            agent_handle,
            entry,
            action="allow",
            direction=direction,
            reason=reason,
        )

    async def block(
        self,
        agent_handle: str,
        entry: str,
        *,
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        """Ergonomic helper: blocks an email address or domain pattern asynchronously."""
        return await self.create(
            agent_handle,
            entry,
            action="block",
            direction=direction,
            reason=reason,
        )

    async def update(
        self,
        agent_handle: str,
        rule_id: str,
        *,
        action: MailRuleAction | None = None,
        direction: MailRuleDirection | None = None,
        reason: str | None = None,
        status: MailRuleStatus | None = None,
    ) -> MailRule:
        """Updates an existing mail rule asynchronously."""
        handle = _clean_handle(agent_handle)
        payload: dict[str, Any] = {}
        if action is not None:
            payload["action"] = action
        if direction is not None:
            payload["direction"] = direction
        if reason is not None:
            payload["reason"] = reason
        if status is not None:
            payload["status"] = status

        data = await self._http.patch(
            f"/v1/identities/{quote(handle)}/mail-rules/{quote(rule_id)}",
            json=payload,
        )
        return MailRule.from_dict(data)

    async def delete(self, agent_handle: str, rule_id: str) -> DeleteMailRuleResult:
        """Deletes a mail rule by ID asynchronously."""
        handle = _clean_handle(agent_handle)
        data = await self._http.delete(
            f"/v1/identities/{quote(handle)}/mail-rules/{quote(rule_id)}"
        )
        return DeleteMailRuleResult.from_dict(data or {"deleted": True, "id": rule_id})

    async def get_policy(self, agent_handle: str) -> MailPolicy:
        """Retrieves the current inbound and outbound mail security policy asynchronously."""
        handle = _clean_handle(agent_handle)
        data = await self._http.get(f"/v1/identities/{quote(handle)}")
        return _parse_policy(data)

    async def set_policy(
        self,
        agent_handle: str,
        *,
        inbound: InboundMailPolicy | None = None,
        outbound: OutboundMailPolicy | None = None,
    ) -> MailPolicy:
        """Configures the inbound and outbound mail security policy asynchronously."""
        handle = _clean_handle(agent_handle)
        target_in, target_out = _resolve_modes(inbound, outbound)
        payload: dict[str, Any] = {}
        if target_in is not None:
            payload["mail_inbound_filter_mode"] = target_in
        if target_out is not None:
            payload["mail_outbound_filter_mode"] = target_out

        data = await self._http.patch(f"/v1/identities/{quote(handle)}", json=payload)
        return _parse_policy(data)


class IdentityMailRulesClient:
    """Identity-bound synchronous mail rules client."""

    def __init__(self, http: SyncHttpTransport, agent_handle: str) -> None:
        self._client = MailRulesClient(http)
        self._handle = agent_handle

    def list(
        self,
        *,
        direction: MailRuleDirection | None = None,
        action: MailRuleAction | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ListMailRulesResult:
        return self._client.list(
            self._handle, direction=direction, action=action, limit=limit, offset=offset
        )

    def get(self, rule_id: str) -> MailRule:
        return self._client.get(self._handle, rule_id)

    def create(
        self,
        entry: str,
        *,
        action: MailRuleAction = "allow",
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        return self._client.create(
            self._handle, entry, action=action, direction=direction, reason=reason
        )

    def allow(
        self,
        entry: str,
        *,
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        return self._client.allow(self._handle, entry, direction=direction, reason=reason)

    def block(
        self,
        entry: str,
        *,
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        return self._client.block(self._handle, entry, direction=direction, reason=reason)

    def update(
        self,
        rule_id: str,
        *,
        action: MailRuleAction | None = None,
        direction: MailRuleDirection | None = None,
        reason: str | None = None,
        status: MailRuleStatus | None = None,
    ) -> MailRule:
        return self._client.update(
            self._handle, rule_id, action=action, direction=direction, reason=reason, status=status
        )

    def delete(self, rule_id: str) -> DeleteMailRuleResult:
        return self._client.delete(self._handle, rule_id)

    def get_policy(self) -> MailPolicy:
        return self._client.get_policy(self._handle)

    def set_policy(
        self,
        *,
        inbound: InboundMailPolicy | None = None,
        outbound: OutboundMailPolicy | None = None,
    ) -> MailPolicy:
        return self._client.set_policy(self._handle, inbound=inbound, outbound=outbound)


class AsyncIdentityMailRulesClient:
    """Identity-bound asynchronous mail rules client."""

    def __init__(self, http: AsyncHttpTransport, agent_handle: str) -> None:
        self._client = AsyncMailRulesClient(http)
        self._handle = agent_handle

    async def list(
        self,
        *,
        direction: MailRuleDirection | None = None,
        action: MailRuleAction | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> ListMailRulesResult:
        return await self._client.list(
            self._handle, direction=direction, action=action, limit=limit, offset=offset
        )

    async def get(self, rule_id: str) -> MailRule:
        return await self._client.get(self._handle, rule_id)

    async def create(
        self,
        entry: str,
        *,
        action: MailRuleAction = "allow",
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        return await self._client.create(
            self._handle, entry, action=action, direction=direction, reason=reason
        )

    async def allow(
        self,
        entry: str,
        *,
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        return await self._client.allow(self._handle, entry, direction=direction, reason=reason)

    async def block(
        self,
        entry: str,
        *,
        direction: MailRuleDirection = "both",
        reason: str | None = None,
    ) -> MailRule:
        return await self._client.block(self._handle, entry, direction=direction, reason=reason)

    async def update(
        self,
        rule_id: str,
        *,
        action: MailRuleAction | None = None,
        direction: MailRuleDirection | None = None,
        reason: str | None = None,
        status: MailRuleStatus | None = None,
    ) -> MailRule:
        return await self._client.update(
            self._handle, rule_id, action=action, direction=direction, reason=reason, status=status
        )

    async def delete(self, rule_id: str) -> DeleteMailRuleResult:
        return await self._client.delete(self._handle, rule_id)

    async def get_policy(self) -> MailPolicy:
        return await self._client.get_policy(self._handle)

    async def set_policy(
        self,
        *,
        inbound: InboundMailPolicy | None = None,
        outbound: OutboundMailPolicy | None = None,
    ) -> MailPolicy:
        return await self._client.set_policy(self._handle, inbound=inbound, outbound=outbound)
