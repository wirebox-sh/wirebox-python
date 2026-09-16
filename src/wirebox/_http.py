"""Wirebox Python SDK — HTTP Transport Layer.

Provides unified synchronous and asynchronous HTTP transports built on httpx,
handling authentication, connection pooling, timeouts, and error normalization.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx

from wirebox._version import __version__
from wirebox.exceptions import WireboxConnectionError, parse_api_error

DEFAULT_BASE_URL = "https://api.wirebox.sh"
DEFAULT_TIMEOUT_SECONDS = 30.0


def _build_headers(
    api_key: str | None, custom_headers: Mapping[str, str] | None = None
) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": f"wirebox-python/{__version__}",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if custom_headers:
        headers.update(custom_headers)
    return headers


def _clean_params(params: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not params:
        return None
    return {k: v for k, v in params.items() if v is not None}


def _handle_response(resp: httpx.Response) -> Any:
    request_id = resp.headers.get("x-wirebox-request-id") or resp.headers.get("x-request-id")

    if resp.status_code == 204:
        return None

    content_type = resp.headers.get("content-type", "")
    data: Any
    if "application/json" in content_type:
        try:
            data = resp.json()
        except Exception:
            data = resp.text
    else:
        data = resp.text

    if not resp.is_success:
        raise parse_api_error(resp.status_code, data, request_id)

    return data


class SyncHttpTransport:
    """Synchronous HTTP transport for Wirebox API communication."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._external_client = client is not None
        self._client = client or httpx.Client(
            base_url=self.base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        url = path if path.startswith("/") else f"/{path}"
        try:
            resp = self._client.request(
                method,
                url,
                params=_clean_params(params),
                json=json,
                headers=dict(headers) if headers else None,
                timeout=timeout or self.timeout,
            )
            return _handle_response(resp)
        except httpx.TimeoutException as exc:
            raise WireboxConnectionError(
                f"Request timed out after {timeout or self.timeout}s: {exc}", exc
            ) from exc
        except httpx.NetworkError as exc:
            raise WireboxConnectionError(f"Network connection failed: {exc}", exc) from exc

    def get(self, path: str, *, params: Mapping[str, Any] | None = None, **kwargs: Any) -> Any:
        return self.request("GET", path, params=params, **kwargs)

    def post(self, path: str, *, json: Any = None, **kwargs: Any) -> Any:
        return self.request("POST", path, json=json, **kwargs)

    def patch(self, path: str, *, json: Any = None, **kwargs: Any) -> Any:
        return self.request("PATCH", path, json=json, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Any:
        return self.request("DELETE", path, **kwargs)

    def close(self) -> None:
        if not self._external_client:
            self._client.close()

    def __enter__(self) -> SyncHttpTransport:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncHttpTransport:
    """Asynchronous HTTP transport for Wirebox API communication."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._external_client = client is not None
        self._client = client or httpx.AsyncClient(
            base_url=self.base_url,
            headers=_build_headers(api_key),
            timeout=timeout,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        json: Any = None,
        headers: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> Any:
        url = path if path.startswith("/") else f"/{path}"
        try:
            resp = await self._client.request(
                method,
                url,
                params=_clean_params(params),
                json=json,
                headers=dict(headers) if headers else None,
                timeout=timeout or self.timeout,
            )
            return _handle_response(resp)
        except httpx.TimeoutException as exc:
            raise WireboxConnectionError(
                f"Request timed out after {timeout or self.timeout}s: {exc}", exc
            ) from exc
        except httpx.NetworkError as exc:
            raise WireboxConnectionError(f"Network connection failed: {exc}", exc) from exc

    async def get(
        self, path: str, *, params: Mapping[str, Any] | None = None, **kwargs: Any
    ) -> Any:
        return await self.request("GET", path, params=params, **kwargs)

    async def post(self, path: str, *, json: Any = None, **kwargs: Any) -> Any:
        return await self.request("POST", path, json=json, **kwargs)

    async def patch(self, path: str, *, json: Any = None, **kwargs: Any) -> Any:
        return await self.request("PATCH", path, json=json, **kwargs)

    async def delete(self, path: str, **kwargs: Any) -> Any:
        return await self.request("DELETE", path, **kwargs)

    async def aclose(self) -> None:
        if not self._external_client:
            await self._client.aclose()

    async def __aenter__(self) -> AsyncHttpTransport:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()
