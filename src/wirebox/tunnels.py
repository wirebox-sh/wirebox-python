"""Wirebox Python SDK — Network Tunnels Client.

Provides control-plane queries and data-plane reverse proxy connections for Wirebox
agent network tunnels using WebSockets.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import inspect
import json
import logging
from typing import Any, Literal
from urllib.parse import quote, urlparse

import httpx
import websockets

try:
    from websockets.asyncio.client import ClientConnection as WebSocketConnection
except ImportError:
    try:
        from websockets.client import WebSocketClientProtocol as WebSocketConnection  # type: ignore
    except ImportError:
        WebSocketConnection = Any  # type: ignore

from wirebox._http import AsyncHttpTransport, SyncHttpTransport
from wirebox._version import __version__
from wirebox.exceptions import WireboxConnectionError, WireboxError
from wirebox.types import Tunnel

logger = logging.getLogger("wirebox.tunnels")


def _normalize_identifier(handle_or_id: str) -> str:
    cleaned = handle_or_id.strip()
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    return cleaned.lower()


def _normalize_forward_to(target: str | int | None) -> str:
    if target is None or target == "":
        return "http://127.0.0.1:3000"
    if isinstance(target, int) or str(target).isdigit():
        return f"http://127.0.0.1:{target}"
    val = str(target).strip()
    if not val.startswith(("http://", "https://")):
        val = f"http://{val}"
    return val.rstrip("/")


def _is_ws_closed(ws: Any) -> bool:
    if hasattr(ws, "closed"):
        return bool(ws.closed)
    if hasattr(ws, "state"):
        try:
            from websockets.protocol import State

            return ws.state in (State.CLOSED, State.CLOSING)
        except Exception:
            return False
    return False


async def _close_ws(ws: Any) -> None:
    if not _is_ws_closed(ws):
        with contextlib.suppress(Exception):
            await ws.close()


class TunnelSession:
    """An active live reverse-proxy tunnel session."""

    def __init__(
        self,
        public_url: str,
        public_host: str,
        agent_handle: str,
        ws: WebSocketConnection,
        listen_task: asyncio.Task[None],
    ) -> None:
        self.public_url = public_url
        self.public_host = public_host
        self.agent_handle = agent_handle
        self._ws = ws
        self._listen_task = listen_task
        self._closed_event = asyncio.Event()

    @property
    def is_connected(self) -> bool:
        return not _is_ws_closed(self._ws)

    async def close(self) -> None:
        """Closes the tunnel WebSocket connection and terminates the proxy session."""
        await _close_ws(self._ws)
        if not self._listen_task.done():
            self._listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._listen_task
        self._closed_event.set()

    async def wait_closed(self) -> None:
        """Awaits until the tunnel session has closed."""
        await self._closed_event.wait()


class TunnelsClient:
    """Synchronous client for querying and managing tunnel control-plane records."""

    def __init__(self, http: SyncHttpTransport) -> None:
        self._http = http

    def list(
        self,
        *,
        status: Literal["active", "disabled"] | None = None,
        is_connected: bool | None = None,
        limit: int | None = None,
    ) -> list[Tunnel]:
        params: dict[str, Any] = {}
        if status is not None:
            params["status"] = status
        if is_connected is not None:
            params["is_connected"] = "true" if is_connected else "false"
        if limit is not None:
            params["limit"] = limit

        data = self._http.get("/v1/tunnels", params=params)
        if isinstance(data, list):
            raw_tunnels = data
        elif isinstance(data, dict):
            raw_tunnels = data.get("tunnels", [])
        else:
            raw_tunnels = []
        return [Tunnel.from_dict(t) for t in raw_tunnels]

    def get(self, handle_or_id: str) -> Tunnel:
        identifier = _normalize_identifier(handle_or_id)
        data = self._http.get(f"/v1/tunnels/{quote(identifier)}")
        return Tunnel.from_dict(data)

    def update(self, handle_or_id: str, *, status: Literal["active", "disabled"]) -> Tunnel:
        identifier = _normalize_identifier(handle_or_id)
        data = self._http.patch(f"/v1/tunnels/{quote(identifier)}", json={"status": status})
        return Tunnel.from_dict(data)


class AsyncTunnelsClient:
    """Asynchronous client for tunnel queries and live WebSocket data-plane connections."""

    def __init__(self, http: AsyncHttpTransport, api_key: str | None, base_url: str) -> None:
        self._http = http
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    async def list(
        self,
        *,
        status: Literal["active", "disabled"] | None = None,
        is_connected: bool | None = None,
        limit: int | None = None,
    ) -> list[Tunnel]:
        params: dict[str, Any] = {}
        if status is not None:
            params["status"] = status
        if is_connected is not None:
            params["is_connected"] = "true" if is_connected else "false"
        if limit is not None:
            params["limit"] = limit

        data = await self._http.get("/v1/tunnels", params=params)
        if isinstance(data, list):
            raw_tunnels = data
        elif isinstance(data, dict):
            raw_tunnels = data.get("tunnels", [])
        else:
            raw_tunnels = []
        return [Tunnel.from_dict(t) for t in raw_tunnels]

    async def get(self, handle_or_id: str) -> Tunnel:
        identifier = _normalize_identifier(handle_or_id)
        data = await self._http.get(f"/v1/tunnels/{quote(identifier)}")
        return Tunnel.from_dict(data)

    async def update(self, handle_or_id: str, *, status: Literal["active", "disabled"]) -> Tunnel:
        identifier = _normalize_identifier(handle_or_id)
        data = await self._http.patch(f"/v1/tunnels/{quote(identifier)}", json={"status": status})
        return Tunnel.from_dict(data)

    async def connect(
        self,
        handle_or_id: str,
        *,
        forward_to: str | int = 3000,
        client_version: str | None = None,
    ) -> TunnelSession:
        """Establishes a live reverse-proxy tunnel connecting a local service to the agent's public URL.

        Args:
            handle_or_id: Agent handle (e.g. 'sales-bot' or '@sales-bot') or tunnel ID.
            forward_to: Local port (e.g. 3456) or origin URL (e.g. 'http://localhost:3456') to proxy traffic to.
            client_version: Optional version tag reported in telemetry.

        Returns:
            An active TunnelSession exposing .public_url and .close().
        """
        if not self._api_key:
            raise WireboxError("Authentication required: API key is missing for tunnel connection.")

        tunnel = await self.get(handle_or_id)
        forward_origin = _normalize_forward_to(forward_to)
        agent_handle = tunnel.agent_handle

        parsed = urlparse(self._base_url)
        ws_proto = "wss" if parsed.scheme == "https" else "ws"
        ws_url = f"{ws_proto}://{parsed.netloc}/v1/tunnels/{quote(agent_handle)}/connect"
        ws_url_with_params = (
            f"{ws_url}?forward_to={quote(forward_origin)}&api_key={quote(self._api_key)}"
        )

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "X-Forward-To": forward_origin,
            "X-Client-Version": client_version or f"wirebox-python/{__version__}",
        }

        ws_kwargs: dict[str, Any] = {
            "ping_interval": 20,
            "ping_timeout": 20,
        }
        if "additional_headers" in inspect.signature(websockets.connect).parameters:
            ws_kwargs["additional_headers"] = headers
        else:
            ws_kwargs["extra_headers"] = headers

        try:
            ws = await websockets.connect(
                ws_url_with_params,
                **ws_kwargs,
            )
        except Exception as exc:
            raise WireboxConnectionError(
                f"Failed to connect tunnel WebSocket to {ws_url}: {exc}", exc
            ) from exc

        # Create persistent HTTP client for local forwarding
        local_http = httpx.AsyncClient(base_url=forward_origin, timeout=30.0)
        local_ws_connections: dict[str, Any] = {}

        async def _bridge_local_ws(c_id: str, local_client: Any) -> None:
            try:
                async for local_msg in local_client:
                    is_binary = isinstance(local_msg, (bytes, bytearray))
                    frame_data = (
                        base64.b64encode(local_msg).decode("ascii") if is_binary else str(local_msg)
                    )
                    await ws.send(
                        json.dumps(
                            {
                                "type": "ws_frame",
                                "connId": c_id,
                                "data": frame_data,
                                "binary": is_binary,
                            }
                        )
                    )
            except Exception:
                pass
            finally:
                local_ws_connections.pop(c_id, None)
                with contextlib.suppress(Exception):
                    await ws.send(
                        json.dumps(
                            {
                                "type": "ws_close",
                                "connId": c_id,
                                "code": 1000,
                                "reason": "Local WebSocket closed",
                            }
                        )
                    )

        async def _proxy_loop() -> None:
            try:
                async for message in ws:
                    try:
                        data = json.loads(message)
                    except Exception:
                        continue

                    msg_type = data.get("type")
                    if msg_type == "ping":
                        await ws.send(json.dumps({"type": "pong"}))
                        continue

                    if msg_type == "ws_open":
                        c_id = data.get("connId")
                        ws_path = data.get("path", "/")
                        inbound_headers = data.get("headers", {})

                        target_ws_origin = (
                            forward_origin.replace("https://", "wss://").replace("http://", "ws://")
                        )
                        target_ws_url = f"{target_ws_origin}{ws_path}"

                        subprotocol = inbound_headers.get("sec-websocket-protocol")
                        subprotocols = (
                            [s.strip() for s in subprotocol.split(",")] if subprotocol else None
                        )

                        try:
                            ws_client_kwargs: dict[str, Any] = {}
                            if subprotocols:
                                ws_client_kwargs["subprotocols"] = subprotocols
                            local_ws = await websockets.connect(target_ws_url, **ws_client_kwargs)
                            local_ws_connections[c_id] = local_ws
                            await ws.send(json.dumps({"type": "ws_opened", "connId": c_id}))
                            asyncio.create_task(_bridge_local_ws(c_id, local_ws))
                        except Exception as err:
                            logger.error(f"Failed to connect local WebSocket at {target_ws_url}: {err}")
                            await ws.send(
                                json.dumps(
                                    {
                                        "type": "ws_error",
                                        "connId": c_id,
                                        "error": str(err),
                                    }
                                )
                            )
                        continue

                    if msg_type == "ws_frame":
                        c_id = data.get("connId")
                        frame_data = data.get("data", "")
                        is_binary = bool(data.get("binary"))
                        local_ws = local_ws_connections.get(c_id)
                        if local_ws and not _is_ws_closed(local_ws):
                            try:
                                if is_binary:
                                    raw_bytes = base64.b64decode(frame_data)
                                    await local_ws.send(raw_bytes)
                                else:
                                    await local_ws.send(frame_data)
                            except Exception as err:
                                logger.error(f"Failed to forward WS frame to local client: {err}")
                        continue

                    if msg_type == "ws_close":
                        c_id = data.get("connId")
                        code = data.get("code", 1000)
                        reason = data.get("reason", "")
                        local_ws = local_ws_connections.pop(c_id, None)
                        if local_ws and not _is_ws_closed(local_ws):
                            with contextlib.suppress(Exception):
                                await local_ws.close(code, reason)
                        continue

                    if msg_type == "http_request":
                        req_id = data.get("id")
                        method = data.get("method", "GET")
                        path = data.get("path", "/")
                        inbound_headers = data.get("headers", {})
                        body_b64 = data.get("body")

                        req_body = base64.b64decode(body_b64) if body_b64 else None

                        # Strip host/connection headers for clean local forwarding
                        forward_headers = {
                            k: v
                            for k, v in inbound_headers.items()
                            if k.lower() not in ("host", "connection", "upgrade", "keep-alive")
                        }

                        try:
                            resp = await local_http.request(
                                method=method,
                                url=path,
                                headers=forward_headers,
                                content=req_body,
                            )
                            resp_body = resp.content
                            resp_b64 = (
                                base64.b64encode(resp_body).decode("ascii") if resp_body else None
                            )

                            resp_headers = {k: v for k, v in resp.headers.items()}
                            await ws.send(
                                json.dumps(
                                    {
                                        "type": "http_response",
                                        "id": req_id,
                                        "status": resp.status_code,
                                        "headers": resp_headers,
                                        "body": resp_b64,
                                    }
                                )
                            )
                        except Exception as forward_err:
                            logger.error(
                                f"Tunnel failed forwarding {method} {path} to local {forward_origin}: {forward_err}"
                            )
                            await ws.send(
                                json.dumps(
                                    {
                                        "type": "http_error",
                                        "id": req_id,
                                        "error": f"Failed to forward request to {forward_origin}: {forward_err}",
                                    }
                                )
                            )
            except asyncio.CancelledError:
                pass
            except websockets.exceptions.ConnectionClosed as exc:
                sent_code = getattr(getattr(exc, "sent", None), "code", None)
                rcvd_code = getattr(getattr(exc, "rcvd", None), "code", None)
                normal_codes = (1000, 1001)
                if exc.code not in normal_codes and sent_code not in normal_codes and rcvd_code not in normal_codes:
                    logger.warning(f"Tunnel connection closed unexpectedly: {exc}")
            except Exception as exc:
                logger.warning(f"Tunnel proxy loop closed: {exc}")
            finally:
                for l_ws in list(local_ws_connections.values()):
                    with contextlib.suppress(Exception):
                        await l_ws.close(1001, "Tunnel disconnecting")
                local_ws_connections.clear()
                await local_http.aclose()
                await _close_ws(ws)

        listen_task = asyncio.create_task(_proxy_loop())

        session = TunnelSession(
            public_url=tunnel.public_url,
            public_host=tunnel.public_host,
            agent_handle=agent_handle,
            ws=ws,
            listen_task=listen_task,
        )

        return session
