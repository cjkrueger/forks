from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "recipes"


@pytest.fixture
def client():
    app = create_app(recipes_dir=SAMPLE_DIR)
    return TestClient(app)


def test_list_recipes(client):
    resp = client.get("/api/recipes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    slugs = [r["slug"] for r in data]
    assert "chicken-tikka-masala" in slugs


def test_list_recipes_sorted_alphabetically(client):
    resp = client.get("/api/recipes")
    data = resp.json()
    titles = [r["title"] for r in data]
    assert titles == sorted(titles, key=str.lower)


def test_list_recipes_no_content_field(client):
    """List endpoint should return summaries, not full content."""
    resp = client.get("/api/recipes")
    data = resp.json()
    for recipe in data:
        assert "content" not in recipe


def test_filter_by_tag(client):
    resp = client.get("/api/recipes?tags=mexican")
    data = resp.json()
    assert len(data) >= 1
    assert all("mexican" in r["tags"] for r in data)


def test_filter_by_multiple_tags(client):
    resp = client.get("/api/recipes?tags=mexican,beef")
    data = resp.json()
    assert all("mexican" in r["tags"] and "beef" in r["tags"] for r in data)


def test_get_recipe(client):
    resp = client.get("/api/recipes/chicken-tikka-masala")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "chicken-tikka-masala"
    assert data["title"] == "Chicken Tikka Masala"
    assert "content" in data
    assert "## Ingredients" in data["content"]


def test_get_recipe_not_found(client):
    resp = client.get("/api/recipes/does-not-exist")
    assert resp.status_code == 404


def test_search_by_title(client):
    resp = client.get("/api/search?q=tikka")
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["slug"] == "chicken-tikka-masala" for r in data)


def test_search_by_ingredient(client):
    resp = client.get("/api/search?q=coconut cream")
    data = resp.json()
    assert any(r["slug"] == "chicken-tikka-masala" for r in data)


def test_search_empty_returns_all(client):
    resp = client.get("/api/search?q=")
    data = resp.json()
    assert len(data) >= 3


def test_search_no_results(client):
    resp = client.get("/api/search?q=xyznonexistent")
    data = resp.json()
    assert len(data) == 0


def test_get_recipe_includes_structured_fields(client):
    """Recipe detail should include parsed ingredients, instructions, notes."""
    resp = client.get("/api/recipes/7-layer-casserole")
    assert resp.status_code == 200
    data = resp.json()
    assert "ingredients" in data
    assert "instructions" in data
    assert "notes" in data
    assert isinstance(data["ingredients"], list)
    assert len(data["ingredients"]) > 0


def test_list_tags(client):
    resp = client.get("/api/tags")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Each entry should have tag and count
    assert all("tag" in t and "count" in t for t in data)


def test_export_recipe(client):
    resp = client.get("/api/recipes/7-layer-casserole/export")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "7-Layer Casserole" in resp.text
    assert "attachment" in resp.headers.get("content-disposition", "")


def test_export_recipe_not_found(client):
    resp = client.get("/api/recipes/does-not-exist/export")
    assert resp.status_code == 404
