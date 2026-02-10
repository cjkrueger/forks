"""Tests for settings and sync API routes."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def tmp_recipes(tmp_path):
    recipe = tmp_path / "recipes"
    recipe.mkdir()
    md = recipe / "test-recipe.md"
    md.write_text("---\ntitle: Test Recipe\ntags: []\n---\n\n# Test Recipe\n\n## Ingredients\n\n- flour\n")
    return recipe


@pytest.fixture
def config_path(tmp_path):
    return tmp_path / ".forks-config.json"


@pytest.fixture
def client(tmp_recipes, config_path, monkeypatch):
    monkeypatch.setenv("FORKS_CONFIG_PATH", str(config_path))
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


class TestGetSyncStatus:
    def test_returns_status(self, client):
        resp = client.get("/api/sync/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "connected" in data
        assert data["connected"] is False


class TestGetSettings:
    def test_returns_defaults_when_no_config(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["remote"]["provider"] is None
        assert data["sync"]["enabled"] is False


class TestSaveSettings:
    def test_saves_remote_config(self, client, config_path):
        resp = client.put("/api/settings", json={
            "remote": {"provider": "generic", "url": "https://example.com/repo.git", "token": "tok"},
            "sync": {"enabled": True, "interval_seconds": 60},
        })
        assert resp.status_code == 200
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["remote"]["url"] == "https://example.com/repo.git"

    def test_returns_saved_config(self, client):
        client.put("/api/settings", json={
            "remote": {"provider": "github", "url": "https://github.com/u/r.git"},
            "sync": {"enabled": True},
        })
        resp = client.get("/api/settings")
        data = resp.json()
        assert data["remote"]["provider"] == "github"
        assert data["sync"]["enabled"] is True


class TestDisconnect:
    def test_clears_config(self, client, config_path):
        client.put("/api/settings", json={
            "remote": {"provider": "github", "url": "https://github.com/u/r.git", "token": "tok"},
            "sync": {"enabled": True},
        })
        assert config_path.exists()
        resp = client.delete("/api/settings/remote")
        assert resp.status_code == 200
        resp = client.get("/api/settings")
        data = resp.json()
        assert data["remote"]["provider"] is None
        assert data["sync"]["enabled"] is False
