"""Tests for fork history endpoint."""
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


BASE_RECIPE = textwrap.dedent("""\
    ---
    title: Test Recipe
    tags: [test]
    servings: 4
    ---

    # Test Recipe

    ## Ingredients

    - 1 cup flour
    - 2 eggs

    ## Instructions

    1. Mix ingredients
    2. Bake

    ## Notes

    - Serve warm
""")


@pytest.fixture
def tmp_recipes(tmp_path):
    recipe = tmp_path / "test-recipe.md"
    recipe.write_text(BASE_RECIPE)
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


class TestForkHistory:
    def test_404_for_missing_fork(self, client):
        resp = client.get("/api/recipes/test-recipe/forks/nonexistent/history")
        assert resp.status_code == 404

    def test_history_with_mock_git(self, client, tmp_recipes):
        """Test history endpoint with mocked git operations."""
        fork_path = tmp_recipes / "test-recipe.fork.spicy.md"
        fork_path.write_text(
            "---\nfork_name: Spicy\nforked_from: test-recipe\n---\n\n## Ingredients\n\n- chili\n"
        )

        mock_entries = [
            {"hash": "abc123", "date": "2026-02-09T10:00:00", "message": "Create fork: Spicy"},
            {"hash": "def456", "date": "2026-02-08T10:00:00", "message": "Update fork: Spicy"},
        ]
        with patch("app.routes.forks.git_log", return_value=mock_entries):
            resp = client.get("/api/recipes/test-recipe/forks/spicy/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["history"]) == 2
        assert data["history"][0]["hash"] == "abc123"

    def test_history_with_content(self, client, tmp_recipes):
        """Test content flag includes file content at each revision."""
        fork_path = tmp_recipes / "test-recipe.fork.spicy.md"
        fork_path.write_text(
            "---\nfork_name: Spicy\nforked_from: test-recipe\n---\n\n## Ingredients\n\n- chili\n"
        )

        mock_entries = [
            {"hash": "abc123", "date": "2026-02-09T10:00:00", "message": "v2"},
        ]
        with patch("app.routes.forks.git_log", return_value=mock_entries):
            with patch("app.routes.forks.git_show", return_value="old content"):
                resp = client.get("/api/recipes/test-recipe/forks/spicy/history?content=true")
        assert resp.status_code == 200
        assert resp.json()["history"][0]["content"] == "old content"

    def test_history_without_content_flag(self, client, tmp_recipes):
        """Without content flag, entries should not have content field."""
        fork_path = tmp_recipes / "test-recipe.fork.spicy.md"
        fork_path.write_text(
            "---\nfork_name: Spicy\nforked_from: test-recipe\n---\n\n## Ingredients\n\n- chili\n"
        )

        mock_entries = [
            {"hash": "abc123", "date": "2026-02-09T10:00:00", "message": "v1"},
        ]
        with patch("app.routes.forks.git_log", return_value=mock_entries):
            resp = client.get("/api/recipes/test-recipe/forks/spicy/history")
        assert resp.status_code == 200
        assert "content" not in resp.json()["history"][0]
