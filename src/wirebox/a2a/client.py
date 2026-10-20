"""Wirebox Python SDK — Standalone A2A 1.0 JSON-RPC Client.

Implements standard A2A 1.0 client communication with strict Origin Pinning
to prevent API key leakage to external third-party agent endpoints.
Supports both Synchronous (A2AClient) and Asynchronous (AsyncA2AClient) interfaces.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import httpx

from wirebox.a2a.types import (
    A2ACard,
    A2APart,
    A2AResolvedTarget,
    A2ATask,
    A2ATaskState,
    A2AWatchEvent,
)
from wirebox.exceptions import A2AProtocolError, WireboxConnectionError, WireboxError

DEFAULT_TIMEOUT = 30.0
TERMINAL_STATES: set[str] = {"completed", "failed", "canceled"}


def _canonical_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("A2A URLs cannot contain credentials or fragments.")
    local = parsed.hostname in {"localhost", "127.0.0.1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and local):
        raise ValueError("A2A URLs must use HTTPS (HTTP is only permitted for localhost).")
    if not parsed.hostname:
        raise ValueError("A2A URL must include a host.")
    host = parsed.hostname.lower()
    port = parsed.port
    default_port = 443 if parsed.scheme == "https" else 80
    netloc = host if port in {None, default_port} else f"{host}:{port}"
    path = parsed.path or "/"
    return urlunsplit((parsed.scheme.lower(), netloc, path, parsed.query, ""))


def _origin(value: str) -> str:
    parsed = urlsplit(_canonical_url(value))
    return f"{parsed.scheme}://{parsed.netloc}"


class A2AClient:
    """Synchronous A2A 1.0 JSON-RPC client with strict Origin Pinning."""

    def __init__(
        self,
        api_key: str | None = None,
        platform_base_url: str = "https://api.wirebox.sh",
        *,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._platform_origin = _origin(platform_base_url)
        self._timeout = timeout
        self._external_client = http_client is not None
        self._client = http_client or httpx.Client(
            timeout=timeout,
            follow_redirects=False,
        )
        self._next_id = 0

    def close(self) -> None:
        if not self._external_client:
            self._client.close()

    def __enter__(self) -> A2AClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def fetch_card(
        self,
        card_url: str,
        *,
        credential: str | None = None,
        timeout: float | None = None,
    ) -> A2AResolvedTarget:
        canonical_card_url = _canonical_url(card_url)
        card_origin = _origin(canonical_card_url)

        headers: dict[str, str] = {"Accept": "application/json"}
        # Auto-pin platform API key ONLY if the target card resides on the Wirebox platform
        if self._api_key and card_origin == self._platform_origin:
            headers["Authorization"] = f"Bearer {self._api_key}"
        elif credential and card_origin != self._platform_origin:
            headers["Authorization"] = f"Bearer {credential}"

        try:
            resp = self._client.get(
                canonical_card_url, headers=headers, timeout=timeout or self._timeout
            )
            if 300 <= resp.status_code < 400:
                raise WireboxError("A2A Agent Card redirects are refused for security.")
            resp.raise_for_status()
            card_data = resp.json()
        except httpx.TimeoutException as exc:
            raise WireboxConnectionError(
                f"Agent Card request timed out after {timeout or self._timeout}s", exc
            ) from exc
        except httpx.HTTPError as exc:
            raise WireboxError(f"Failed to fetch Agent Card from '{card_url}': {exc}") from exc

        card = A2ACard.from_dict(card_data)
        selected = next(
            (
                item
                for item in card.supported_interfaces
                if item.protocol_version == "1.0" and item.protocol_binding.upper() == "JSONRPC"
            ),
            None,
        )
        if selected is None:
            raise WireboxError(
                f"Agent Card at '{card_url}' does not advertise supported interface '1.0' with 'JSONRPC' binding."
            )

        rpc_url = _canonical_url(selected.url)
        rpc_origin = _origin(rpc_url)

        pinned_credential = credential
        if credential is not None and rpc_origin != card_origin:
            raise ValueError("External A2A credentials require matching Card and RPC origins.")

        if card_origin == self._platform_origin:
            if rpc_origin != self._platform_origin:
                raise ValueError("Wirebox Agent Card points to a non-Wirebox RPC origin.")
            pinned_credential = self._api_key

        return A2AResolvedTarget(
            card_url=canonical_card_url,
            rpc_url=rpc_url,
            protocol_version="1.0",
            card=card,
            credential=pinned_credential,
        )

    def send(
        self,
        target: A2AResolvedTarget,
        *,
        text: str | None = None,
        parts: list[A2APart | dict[str, Any]] | None = None,
        context_id: str | None = None,
        task_id: str | None = None,
        message_id: str | None = None,
        timeout: float | None = None,
    ) -> A2ATask:
        if text is None and (not parts):
            raise ValueError("A2A call requires either 'text' or non-empty 'parts'.")

        formatted_parts: list[dict[str, Any]] = []
        if parts:
            for p in parts:
                formatted_parts.append(p.to_dict() if isinstance(p, A2APart) else p)
        elif text is not None:
            formatted_parts.append({"type": "text", "text": text})

        message: dict[str, Any] = {
            "messageId": message_id or f"msg_{uuid.uuid4().hex[:12]}",
            "role": "user",
            "parts": formatted_parts,
        }

        params: dict[str, Any] = {"message": message}
        if context_id is not None:
            params["contextId"] = context_id
        if task_id is not None:
            params["taskId"] = task_id

        result = self._rpc(target, "SendMessage", params, timeout=timeout)
        if isinstance(result, dict):
            return A2ATask.from_dict(result)

        raise WireboxError("Invalid SendMessage response payload from remote agent.")

    def get_task(
        self,
        target: A2AResolvedTarget,
        task_id: str,
        *,
        timeout: float | None = None,
    ) -> A2ATask:
        result = self._rpc(target, "GetTask", {"taskId": task_id, "id": task_id}, timeout=timeout)
        if isinstance(result, dict):
            return A2ATask.from_dict(result)

        raise WireboxError(f"Invalid GetTask response payload for taskId '{task_id}'.")

    def list_tasks(
        self,
        target: A2AResolvedTarget,
        *,
        context_id: str | None = None,
        state: A2ATaskState | str | None = None,
        limit: int = 50,
        timeout: float | None = None,
    ) -> list[A2ATask]:
        params: dict[str, Any] = {"limit": limit}
        if context_id is not None:
            params["contextId"] = context_id
        if state is not None:
            params["state"] = state

        result = self._rpc(target, "ListTasks", params, timeout=timeout)
        raw_tasks = result.get("tasks", []) if isinstance(result, dict) else []
        return [A2ATask.from_dict(t) for t in raw_tasks if isinstance(t, dict)]

    def cancel(
        self,
        target: A2AResolvedTarget,
        task_id: str,
        *,
        reason: str | None = None,
        timeout: float | None = None,
    ) -> A2ATask:
        params: dict[str, Any] = {"taskId": task_id, "id": task_id}
        if reason is not None:
            params["reason"] = reason

        result = self._rpc(target, "CancelTask", params, timeout=timeout)
        if isinstance(result, dict):
            return A2ATask.from_dict(result)

        raise WireboxError(f"Invalid CancelTask response payload for taskId '{task_id}'.")

    def watch(
        self,
        target: A2AResolvedTarget,
        task_id: str,
        *,
        timeout: float = 120.0,
        interval: float = 1.0,
    ) -> Iterator[A2AWatchEvent]:
        start = time.monotonic()
        last_state: str | None = None
        last_message: str | None = None
        last_msg_count = -1

        while True:
            remaining = timeout - (time.monotonic() - start)
            if remaining <= 0:
                raise TimeoutError(
                    f"A2A task '{task_id}' did not reach terminal state within {int(timeout * 1000)}ms."
                )

            req_timeout = min(remaining, self._timeout)
            task = self.get_task(target, task_id, timeout=req_timeout)

            cur_state = task.state
            cur_message = task.message
            cur_msg_count = len(task.messages)

            has_changed = (
                cur_state != last_state
                or cur_message != last_message
                or cur_msg_count != last_msg_count
            )

            if has_changed:
                last_state = cur_state
                last_message = cur_message
                last_msg_count = cur_msg_count

                yield A2AWatchEvent(
                    task=task,
                    state=cur_state,
                    message=cur_message,
                )

            if cur_state in TERMINAL_STATES:
                return

            time.sleep(interval)

    def wait(
        self,
        target: A2AResolvedTarget,
        task_id: str,
        *,
        timeout: float = 120.0,
        interval: float = 1.0,
    ) -> A2ATask:
        last_task: A2ATask | None = None
        for event in self.watch(target, task_id, timeout=timeout, interval=interval):
            last_task = event.task
            if event.is_terminal:
                return last_task

        if last_task is not None:
            return last_task
        return self.get_task(target, task_id)

    def _rpc(
        self,
        target: A2AResolvedTarget,
        method: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        self._next_id += 1
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "A2A-Version": "1.0",
        }
        if target.credential:
            headers["Authorization"] = f"Bearer {target.credential}"

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params,
        }

        try:
            resp = self._client.post(
                target.rpc_url,
                json=payload,
                headers=headers,
                timeout=timeout or self._timeout,
            )
            if 300 <= resp.status_code < 400:
                raise WireboxError("A2A RPC redirects are refused for security.")
            resp.raise_for_status()
            res_json = resp.json()
        except httpx.TimeoutException as exc:
            raise WireboxConnectionError(f"A2A RPC {method} request timed out: {exc}", exc) from exc
        except httpx.HTTPError as exc:
            raise WireboxError(f"A2A RPC {method} failed: {exc}") from exc

        if not isinstance(res_json, dict):
            raise WireboxError(f"Invalid JSON response from A2A RPC endpoint '{target.rpc_url}'.")

        if "error" in res_json:
            err = res_json["error"]
            code = int(err.get("code", -32603)) if isinstance(err, dict) else -32603
            msg = str(err.get("message", "Unknown error")) if isinstance(err, dict) else str(err)
            data = err.get("data") if isinstance(err, dict) else None
            raise A2AProtocolError(code, msg, data)

        return res_json.get("result", {})


class AsyncA2AClient:
    """Asynchronous A2A 1.0 JSON-RPC client with strict Origin Pinning."""

    def __init__(
        self,
        api_key: str | None = None,
        platform_base_url: str = "https://api.wirebox.sh",
        *,
        timeout: float = DEFAULT_TIMEOUT,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._platform_origin = _origin(platform_base_url)
        self._timeout = timeout
        self._external_client = http_client is not None
        self._client = http_client or httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
        )
        self._next_id = 0

    async def close(self) -> None:
        if not self._external_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncA2AClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def fetch_card(
        self,
        card_url: str,
        *,
        credential: str | None = None,
        timeout: float | None = None,
    ) -> A2AResolvedTarget:
        canonical_card_url = _canonical_url(card_url)
        card_origin = _origin(canonical_card_url)

        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key and card_origin == self._platform_origin:
            headers["Authorization"] = f"Bearer {self._api_key}"
        elif credential and card_origin != self._platform_origin:
            headers["Authorization"] = f"Bearer {credential}"

        try:
            resp = await self._client.get(
                canonical_card_url, headers=headers, timeout=timeout or self._timeout
            )
            if 300 <= resp.status_code < 400:
                raise WireboxError("A2A Agent Card redirects are refused for security.")
            resp.raise_for_status()
            card_data = resp.json()
        except httpx.TimeoutException as exc:
            raise WireboxConnectionError(
                f"Agent Card request timed out after {timeout or self._timeout}s", exc
            ) from exc
        except httpx.HTTPError as exc:
            raise WireboxError(f"Failed to fetch Agent Card from '{card_url}': {exc}") from exc

        card = A2ACard.from_dict(card_data)
        selected = next(
            (
                item
                for item in card.supported_interfaces
                if item.protocol_version == "1.0" and item.protocol_binding.upper() == "JSONRPC"
            ),
            None,
        )
        if selected is None:
            raise WireboxError(
                f"Agent Card at '{card_url}' does not advertise supported interface '1.0' with 'JSONRPC' binding."
            )

        rpc_url = _canonical_url(selected.url)
        rpc_origin = _origin(rpc_url)

        pinned_credential = credential
        if credential is not None and rpc_origin != card_origin:
            raise ValueError("External A2A credentials require matching Card and RPC origins.")

        if card_origin == self._platform_origin:
            if rpc_origin != self._platform_origin:
                raise ValueError("Wirebox Agent Card points to a non-Wirebox RPC origin.")
            pinned_credential = self._api_key

        return A2AResolvedTarget(
            card_url=canonical_card_url,
            rpc_url=rpc_url,
            protocol_version="1.0",
            card=card,
            credential=pinned_credential,
        )

    async def send(
        self,
        target: A2AResolvedTarget,
        *,
        text: str | None = None,
        parts: list[A2APart | dict[str, Any]] | None = None,
        context_id: str | None = None,
        task_id: str | None = None,
        message_id: str | None = None,
        timeout: float | None = None,
    ) -> A2ATask:
        if text is None and (not parts):
            raise ValueError("A2A call requires either 'text' or non-empty 'parts'.")

        formatted_parts: list[dict[str, Any]] = []
        if parts:
            for p in parts:
                formatted_parts.append(p.to_dict() if isinstance(p, A2APart) else p)
        elif text is not None:
            formatted_parts.append({"type": "text", "text": text})

        message: dict[str, Any] = {
            "messageId": message_id or f"msg_{uuid.uuid4().hex[:12]}",
            "role": "user",
            "parts": formatted_parts,
        }

        params: dict[str, Any] = {"message": message}
        if context_id is not None:
            params["contextId"] = context_id
        if task_id is not None:
            params["taskId"] = task_id

        result = await self._rpc(target, "SendMessage", params, timeout=timeout)
        if isinstance(result, dict):
            return A2ATask.from_dict(result)

        raise WireboxError("Invalid SendMessage response payload from remote agent.")

    async def get_task(
        self,
        target: A2AResolvedTarget,
        task_id: str,
        *,
        timeout: float | None = None,
    ) -> A2ATask:
        result = await self._rpc(
            target, "GetTask", {"taskId": task_id, "id": task_id}, timeout=timeout
        )
        if isinstance(result, dict):
            return A2ATask.from_dict(result)

        raise WireboxError(f"Invalid GetTask response payload for taskId '{task_id}'.")

    async def list_tasks(
        self,
        target: A2AResolvedTarget,
        *,
        context_id: str | None = None,
        state: A2ATaskState | str | None = None,
        limit: int = 50,
        timeout: float | None = None,
    ) -> list[A2ATask]:
        params: dict[str, Any] = {"limit": limit}
        if context_id is not None:
            params["contextId"] = context_id
        if state is not None:
            params["state"] = state

        result = await self._rpc(target, "ListTasks", params, timeout=timeout)
        raw_tasks = result.get("tasks", []) if isinstance(result, dict) else []
        return [A2ATask.from_dict(t) for t in raw_tasks if isinstance(t, dict)]

    async def cancel(
        self,
        target: A2AResolvedTarget,
        task_id: str,
        *,
        reason: str | None = None,
        timeout: float | None = None,
    ) -> A2ATask:
        params: dict[str, Any] = {"taskId": task_id, "id": task_id}
        if reason is not None:
            params["reason"] = reason

        result = await self._rpc(target, "CancelTask", params, timeout=timeout)
        if isinstance(result, dict):
            return A2ATask.from_dict(result)

        raise WireboxError(f"Invalid CancelTask response payload for taskId '{task_id}'.")

    async def watch(
        self,
        target: A2AResolvedTarget,
        task_id: str,
        *,
        timeout: float = 120.0,
        interval: float = 1.0,
    ) -> AsyncIterator[A2AWatchEvent]:
        loop = asyncio.get_running_loop()
        start = loop.time()
        last_state: str | None = None
        last_message: str | None = None
        last_msg_count = -1

        while True:
            remaining = timeout - (loop.time() - start)
            if remaining <= 0:
                raise TimeoutError(
                    f"A2A task '{task_id}' did not reach terminal state within {int(timeout * 1000)}ms."
                )

            req_timeout = min(remaining, self._timeout)
            task = await self.get_task(target, task_id, timeout=req_timeout)

            cur_state = task.state
            cur_message = task.message
            cur_msg_count = len(task.messages)

            has_changed = (
                cur_state != last_state
                or cur_message != last_message
                or cur_msg_count != last_msg_count
            )

            if has_changed:
                last_state = cur_state
                last_message = cur_message
                last_msg_count = cur_msg_count

                yield A2AWatchEvent(
                    task=task,
                    state=cur_state,
                    message=cur_message,
                )

            if cur_state in TERMINAL_STATES:
                return

            await asyncio.sleep(interval)

    async def wait(
        self,
        target: A2AResolvedTarget,
        task_id: str,
        *,
        timeout: float = 120.0,
        interval: float = 1.0,
    ) -> A2ATask:
        last_task: A2ATask | None = None
        async for event in self.watch(target, task_id, timeout=timeout, interval=interval):
            last_task = event.task
            if event.is_terminal:
                return last_task

        if last_task is not None:
            return last_task
        return await self.get_task(target, task_id)

    async def _rpc(
        self,
        target: A2AResolvedTarget,
        method: str,
        params: dict[str, Any],
        *,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        self._next_id += 1
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "A2A-Version": "1.0",
        }
        if target.credential:
            headers["Authorization"] = f"Bearer {target.credential}"

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id,
            "method": method,
            "params": params,
        }

        try:
            resp = await self._client.post(
                target.rpc_url,
                json=payload,
                headers=headers,
                timeout=timeout or self._timeout,
            )
            if 300 <= resp.status_code < 400:
                raise WireboxError("A2A RPC redirects are refused for security.")
            resp.raise_for_status()
            res_json = resp.json()
        except httpx.TimeoutException as exc:
            raise WireboxConnectionError(f"A2A RPC {method} request timed out: {exc}", exc) from exc
        except httpx.HTTPError as exc:
            raise WireboxError(f"A2A RPC {method} failed: {exc}") from exc

        if not isinstance(res_json, dict):
            raise WireboxError(f"Invalid JSON response from A2A RPC endpoint '{target.rpc_url}'.")

        if "error" in res_json:
            err = res_json["error"]
            code = int(err.get("code", -32603)) if isinstance(err, dict) else -32603
            msg = str(err.get("message", "Unknown error")) if isinstance(err, dict) else str(err)
            data = err.get("data") if isinstance(err, dict) else None
            raise A2AProtocolError(code, msg, data)

        return res_json.get("result", {})
