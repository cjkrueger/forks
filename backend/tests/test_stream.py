"""Tests for recipe stream/timeline endpoint."""
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

BASE_RECIPE = textwrap.dedent("""\
    ---
    title: Pasta Carbonara
    tags: [italian]
    date_added: 2026-02-01
    ---

    # Pasta Carbonara

    ## Ingredients

    - 400g spaghetti
    - 200g guanciale
    - 4 egg yolks
    - 100g pecorino

    ## Instructions

    1. Cook pasta
    2. Fry guanciale
    3. Mix eggs and cheese
    4. Combine
""")


@pytest.fixture
def tmp_recipes(tmp_path):
    recipe = tmp_path / "pasta-carbonara.md"
    recipe.write_text(BASE_RECIPE)
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


class TestStreamEndpoint:
    def test_returns_stream_for_recipe(self, client):
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert isinstance(data["events"], list)

    def test_404_for_missing_recipe(self, client):
        resp = client.get("/api/recipes/nonexistent/stream")
        assert resp.status_code == 404

    @patch("app.routes.stream.git_log")
    def test_includes_edit_events(self, mock_log, client):
        mock_log.return_value = [
            {"hash": "abc123", "date": "2026-02-03T10:00:00", "message": "Update ingredients"},
            {"hash": "def456", "date": "2026-02-01T10:00:00", "message": "Create recipe: Pasta Carbonara"},
        ]
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        types = [e["type"] for e in events]
        assert "created" in types
        assert "edited" in types

    def test_includes_fork_events(self, tmp_recipes):
        fork = tmp_recipes / "pasta-carbonara.fork.moms-version.md"
        fork.write_text(
            "---\nforked_from: pasta-carbonara\nfork_name: Mom's Version\n"
            "author: mom\ndate_added: 2026-02-05\nforked_at_commit: abc123\n---\n\n"
            "## Ingredients\n\n- 400g rigatoni\n"
        )
        app = create_app(recipes_dir=tmp_recipes)
        c = TestClient(app)
        resp = c.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        fork_events = [e for e in events if e["type"] == "forked"]
        assert len(fork_events) == 1
        assert fork_events[0]["fork_name"] == "Mom's Version"

    def test_includes_merged_events(self, tmp_recipes):
        fork = tmp_recipes / "pasta-carbonara.fork.moms-version.md"
        fork.write_text(
            "---\nforked_from: pasta-carbonara\nfork_name: Mom's Version\n"
            "author: mom\ndate_added: 2026-02-05\nmerged_at: 2026-02-08\n---\n\n"
            "## Ingredients\n\n- 400g rigatoni\n"
        )
        app = create_app(recipes_dir=tmp_recipes)
        c = TestClient(app)
        resp = c.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        merged_events = [e for e in events if e["type"] == "merged"]
        assert len(merged_events) == 1
        assert merged_events[0]["fork_name"] == "Mom's Version"

    @patch("app.routes.stream.git_log")
    def test_filters_noise_commits(self, mock_log, client):
        mock_log.return_value = [
            {"hash": "aaa", "date": "2026-02-03", "message": "Log cook: Pasta Carbonara"},
            {"hash": "bbb", "date": "2026-02-02", "message": "Add favorite: Pasta Carbonara"},
            {"hash": "ccc", "date": "2026-02-01", "message": "Create recipe: Pasta Carbonara"},
        ]
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        assert len(events) == 1
        assert events[0]["type"] == "created"
