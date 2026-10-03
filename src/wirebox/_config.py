"""Wirebox Python SDK — Client Configuration and Credentials Resolver.

Resolves API key and base URL from:
1. Explicit constructor arguments
2. Environment variables (WIREBOX_API_KEY, WIREBOX_BASE_URL)
3. ~/.wirebox/credentials or ~/.wirebox/config file
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from wirebox._http import DEFAULT_BASE_URL


def _get_config_search_paths() -> list[Path]:
    custom_cred = os.environ.get("WIREBOX_CREDENTIALS_PATH")
    custom_cfg = os.environ.get("WIREBOX_CONFIG_PATH")
    if custom_cred or custom_cfg:
        paths: list[Path] = []
        if custom_cred:
            paths.append(Path(custom_cred).expanduser())
        if custom_cfg:
            paths.append(Path(custom_cfg).expanduser())
        return paths

    home_dir = os.environ.get("WIREBOX_HOME")
    base_dir = Path(home_dir).expanduser() / ".wirebox" if home_dir else Path.home() / ".wirebox"

    return [base_dir / "credentials", base_dir / "config"]


def _read_config_file(path: Path) -> dict[str, str]:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError:
        return {}

    if not text:
        return {}

    # 1. Try JSON format
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items() if v is not None}
        except Exception:
            pass

    out: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            out[key.strip()] = val.strip().strip("\"'")
        elif ":" in line:
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip().strip("\"'")
        elif line.startswith("wb_live_") or line.startswith("wb_test_"):
            out["api_key"] = line

    return out


def resolve_client_settings(
    *,
    api_key: str | None = None,
    base_url: str | None = None,
) -> tuple[str | None, str]:
    """Resolves (api_key, base_url) with fallback: explicit -> env -> file."""
    # 1. Resolve API key
    resolved_key = api_key.strip() if api_key and api_key.strip() else None
    if not resolved_key:
        env_key = os.environ.get("WIREBOX_API_KEY")
        if env_key and env_key.strip():
            resolved_key = env_key.strip()

    # 2. Resolve Base URL
    resolved_url = base_url.strip().rstrip("/") if base_url and base_url.strip() else None
    if not resolved_url:
        env_url = os.environ.get("WIREBOX_BASE_URL")
        if env_url and env_url.strip():
            resolved_url = env_url.strip().rstrip("/")

    # 3. If either is still missing, search config files
    if not resolved_key or not resolved_url:
        for file_path in _get_config_search_paths():
            cfg = _read_config_file(file_path)
            if not cfg:
                continue

            if not resolved_key:
                file_key = cfg.get("api_key") or cfg.get("apiKey") or cfg.get("token")
                if file_key and file_key.strip():
                    resolved_key = file_key.strip()

            if not resolved_url:
                file_url = cfg.get("base_url") or cfg.get("baseUrl")
                if file_url and file_url.strip():
                    resolved_url = file_url.strip().rstrip("/")

            if resolved_key and resolved_url:
                break

    return (resolved_key, resolved_url or DEFAULT_BASE_URL)
