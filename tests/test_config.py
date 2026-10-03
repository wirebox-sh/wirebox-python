import json

from wirebox import AsyncWirebox, Wirebox
from wirebox._config import resolve_client_settings
from wirebox._http import DEFAULT_BASE_URL


def test_resolve_explicit_arguments(monkeypatch, tmp_path):
    monkeypatch.setenv("WIREBOX_API_KEY", "wb_live_env_key")
    monkeypatch.setenv("WIREBOX_BASE_URL", "https://env.wirebox.sh")

    key, url = resolve_client_settings(
        api_key="wb_live_explicit_key",
        base_url="https://custom.wirebox.sh",
    )
    assert key == "wb_live_explicit_key"
    assert url == "https://custom.wirebox.sh"


def test_resolve_from_environment(monkeypatch):
    monkeypatch.setenv("WIREBOX_API_KEY", "wb_live_env_key")
    monkeypatch.setenv("WIREBOX_BASE_URL", "https://env.wirebox.sh")

    key, url = resolve_client_settings()
    assert key == "wb_live_env_key"
    assert url == "https://env.wirebox.sh"


def test_resolve_from_credentials_file_key_value(monkeypatch, tmp_path):
    monkeypatch.delenv("WIREBOX_API_KEY", raising=False)
    monkeypatch.delenv("WIREBOX_BASE_URL", raising=False)

    cred_dir = tmp_path / ".wirebox"
    cred_dir.mkdir(parents=True)
    cred_file = cred_dir / "credentials"
    cred_file.write_text("api_key=wb_live_from_credentials\nbase_url=https://cred.wirebox.sh\n")

    monkeypatch.setenv("WIREBOX_HOME", str(tmp_path))

    key, url = resolve_client_settings()
    assert key == "wb_live_from_credentials"
    assert url == "https://cred.wirebox.sh"


def test_resolve_from_config_file_json(monkeypatch, tmp_path):
    monkeypatch.delenv("WIREBOX_API_KEY", raising=False)
    monkeypatch.delenv("WIREBOX_BASE_URL", raising=False)

    cfg_dir = tmp_path / ".wirebox"
    cfg_dir.mkdir(parents=True)
    cfg_file = cfg_dir / "config"
    cfg_file.write_text(
        json.dumps(
            {
                "api_key": "wb_live_from_json_config",
                "base_url": "https://json.wirebox.sh",
            }
        )
    )

    monkeypatch.setenv("WIREBOX_HOME", str(tmp_path))

    key, url = resolve_client_settings()
    assert key == "wb_live_from_json_config"
    assert url == "https://json.wirebox.sh"


def test_resolve_from_raw_token_file(monkeypatch, tmp_path):
    monkeypatch.delenv("WIREBOX_API_KEY", raising=False)
    monkeypatch.delenv("WIREBOX_BASE_URL", raising=False)

    cfg_dir = tmp_path / ".wirebox"
    cfg_dir.mkdir(parents=True)
    cfg_file = cfg_dir / "credentials"
    cfg_file.write_text("wb_live_raw_bearer_token\n")

    monkeypatch.setenv("WIREBOX_HOME", str(tmp_path))

    key, url = resolve_client_settings()
    assert key == "wb_live_raw_bearer_token"
    assert url == DEFAULT_BASE_URL


def test_client_zero_config_initialization(monkeypatch, tmp_path):
    monkeypatch.delenv("WIREBOX_API_KEY", raising=False)
    monkeypatch.delenv("WIREBOX_BASE_URL", raising=False)

    cfg_dir = tmp_path / ".wirebox"
    cfg_dir.mkdir(parents=True)
    cfg_file = cfg_dir / "config"
    cfg_file.write_text("api_key=wb_live_zero_config_client\n")

    monkeypatch.setenv("WIREBOX_HOME", str(tmp_path))

    sync_client = Wirebox()
    assert sync_client._api_key == "wb_live_zero_config_client"
    assert sync_client._base_url == DEFAULT_BASE_URL
    sync_client.close()

    async_client = AsyncWirebox()
    assert async_client._api_key == "wb_live_zero_config_client"
    assert async_client._base_url == DEFAULT_BASE_URL
