"""Tests for cook history and favorite API routes."""
import textwrap
from pathlib import Path

import frontmatter
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


BASE_RECIPE = textwrap.dedent("""\
    ---
    title: Test Soup
    tags: [soup, dinner]
    ---

    # Test Soup

    ## Ingredients

    - water
    - salt

    ## Instructions

    1. Boil water
    2. Add salt
""")


@pytest.fixture
def setup(tmp_path):
    (tmp_path / "test-soup.md").write_text(BASE_RECIPE)
    app = create_app(recipes_dir=tmp_path)
    client = TestClient(app)
    return client, tmp_path


class TestAddCookHistory:
    def test_add_cook_entry(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/test-soup/cook-history", json={})
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["cook_history"]) == 1
        assert "date" in data["cook_history"][0]

    def test_add_cook_entry_with_fork(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/test-soup/cook-history", json={"fork": "vegan"})
        assert resp.status_code == 201
        assert resp.json()["cook_history"][0]["fork"] == "vegan"

    def test_deduplicate_same_day(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/cook-history", json={})
        resp = client.post("/api/recipes/test-soup/cook-history", json={})
        assert len(resp.json()["cook_history"]) == 1

    def test_different_forks_same_day_not_deduplicated(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/cook-history", json={})
        client.post("/api/recipes/test-soup/cook-history", json={"fork": "spicy"})
        resp = client.post("/api/recipes/test-soup/cook-history", json={"fork": "vegan"})
        assert len(resp.json()["cook_history"]) == 3

    def test_cook_history_persisted_to_file(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/cook-history", json={})
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert len(post.metadata["cook_history"]) == 1

    def test_recipe_not_found(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/nonexistent/cook-history", json={})
        assert resp.status_code == 404


class TestDeleteCookHistory:
    def test_delete_entry(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/cook-history", json={})
        resp = client.delete("/api/recipes/test-soup/cook-history/0")
        assert resp.status_code == 200
        assert len(resp.json()["cook_history"]) == 0

    def test_delete_invalid_index(self, setup):
        client, tmp_path = setup
        resp = client.delete("/api/recipes/test-soup/cook-history/5")
        assert resp.status_code == 404

    def test_delete_persisted_to_file(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/cook-history", json={})
        client.delete("/api/recipes/test-soup/cook-history/0")
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert post.metadata.get("cook_history", []) == []


class TestFavorite:
    def test_add_favorite(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/test-soup/favorite")
        assert resp.status_code == 200
        assert resp.json()["favorited"] is True
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert "favorite" in post.metadata["tags"]

    def test_add_favorite_idempotent(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/favorite")
        client.post("/api/recipes/test-soup/favorite")
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert post.metadata["tags"].count("favorite") == 1

    def test_remove_favorite(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/favorite")
        resp = client.delete("/api/recipes/test-soup/favorite")
        assert resp.json()["favorited"] is False
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert "favorite" not in post.metadata["tags"]

    def test_remove_favorite_when_not_set(self, setup):
        client, tmp_path = setup
        resp = client.delete("/api/recipes/test-soup/favorite")
        assert resp.status_code == 200
        assert resp.json()["favorited"] is False

    def test_favorite_not_found(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/nonexistent/favorite")
        assert resp.status_code == 404
