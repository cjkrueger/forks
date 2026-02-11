import json
import os
from pathlib import Path

import pytest

from app.models import RemoteConfig, SyncConfig
from app.remote_config import get_config_path, load_config, save_config


# ---------------------------------------------------------------------------
# Tests: get_config_path
# ---------------------------------------------------------------------------

class TestGetConfigPath:
    def test_returns_path_beside_recipes_dir(self, tmp_path):
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        result = get_config_path(recipes_dir)
        assert result == tmp_path / ".forks-config.json"

    def test_respects_env_override(self, tmp_path, monkeypatch):
        custom_path = str(tmp_path / "custom" / "config.json")
        monkeypatch.setenv("FORKS_CONFIG_PATH", custom_path)
        recipes_dir = tmp_path / "recipes"
        recipes_dir.mkdir()
        result = get_config_path(recipes_dir)
        assert result == Path(custom_path)

    def test_env_override_takes_precedence(self, tmp_path, monkeypatch):
        custom_path = str(tmp_path / "override.json")
        monkeypatch.setenv("FORKS_CONFIG_PATH", custom_path)
        recipes_dir = tmp_path / "some" / "deep" / "recipes"
        result = get_config_path(recipes_dir)
        assert result == Path(custom_path)


# ---------------------------------------------------------------------------
# Tests: load_config
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_returns_defaults_when_no_file(self, tmp_path):
        config_path = tmp_path / ".forks-config.json"
        remote, sync = load_config(config_path)
        assert remote == RemoteConfig()
        assert sync == SyncConfig()

    def test_loads_existing_config(self, tmp_path):
        config_path = tmp_path / ".forks-config.json"
        data = {
            "remote": {
                "provider": "github",
                "url": "https://github.com/user/repo.git",
                "token": "ghp_secret123",
            },
            "sync": {
                "enabled": True,
                "interval_seconds": 120,
            },
        }
        config_path.write_text(json.dumps(data))

        remote, sync = load_config(config_path)
        assert remote.provider == "github"
        assert remote.url == "https://github.com/user/repo.git"
        assert remote.token == "ghp_secret123"
        assert sync.enabled is True
        assert sync.interval_seconds == 120

    def test_handles_partial_config(self, tmp_path):
        config_path = tmp_path / ".forks-config.json"
        data = {
            "remote": {"provider": "gitea"},
        }
        config_path.write_text(json.dumps(data))

        remote, sync = load_config(config_path)
        assert remote.provider == "gitea"
        assert remote.url is None
        assert remote.token is None
        # sync should be defaults since it's missing
        assert sync.enabled is False
        assert sync.interval_seconds == 5400

    def test_returns_defaults_on_corrupt_file(self, tmp_path):
        config_path = tmp_path / ".forks-config.json"
        config_path.write_text("not valid json {{{")

        remote, sync = load_config(config_path)
        assert remote == RemoteConfig()
        assert sync == SyncConfig()


# ---------------------------------------------------------------------------
# Tests: save_config
# ---------------------------------------------------------------------------

class TestSaveConfig:
    def test_writes_config_file(self, tmp_path):
        config_path = tmp_path / ".forks-config.json"
        remote = RemoteConfig(provider="github", url="https://example.com/repo.git", token="tok123")
        sync = SyncConfig(enabled=True, interval_seconds=60)

        save_config(config_path, remote, sync)

        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["remote"]["provider"] == "github"
        assert data["remote"]["url"] == "https://example.com/repo.git"
        assert data["remote"]["token"] == "tok123"
        assert data["sync"]["enabled"] is True
        assert data["sync"]["interval_seconds"] == 60

    def test_creates_parent_dirs(self, tmp_path):
        config_path = tmp_path / "deep" / "nested" / "dir" / "config.json"
        remote = RemoteConfig()
        sync = SyncConfig()

        save_config(config_path, remote, sync)

        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert "remote" in data
        assert "sync" in data

    def test_roundtrip(self, tmp_path):
        config_path = tmp_path / ".forks-config.json"
        remote = RemoteConfig(provider="gitea", url="https://git.example.com/repo", token="secret")
        sync = SyncConfig(enabled=True, interval_seconds=300)

        save_config(config_path, remote, sync)
        loaded_remote, loaded_sync = load_config(config_path)

        assert loaded_remote.provider == remote.provider
        assert loaded_remote.url == remote.url
        assert loaded_remote.token == remote.token
        assert loaded_sync.enabled == sync.enabled
        assert loaded_sync.interval_seconds == sync.interval_seconds

    def test_preserves_none_values(self, tmp_path):
        config_path = tmp_path / ".forks-config.json"
        remote = RemoteConfig(provider="github")
        sync = SyncConfig()

        save_config(config_path, remote, sync)

        data = json.loads(config_path.read_text())
        # url and token should be present as None
        assert data["remote"]["url"] is None
        assert data["remote"]["token"] is None
