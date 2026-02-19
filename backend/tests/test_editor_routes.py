import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def tmp_recipes(tmp_path):
    """Create a temp recipes directory with one sample recipe."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()
    recipe = tmp_path / "test-recipe.md"
    recipe.write_text(
        "---\ntitle: Test Recipe\ntags: [test]\nservings: 4\n---\n\n"
        "# Test Recipe\n\n## Ingredients\n\n- 1 cup flour\n\n"
        "## Instructions\n\n1. Mix ingredients\n"
    )
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


def test_scrape_endpoint(client):
    mock_data = {
        "title": "Scraped Recipe",
        "ingredients": ["1 cup flour", "2 eggs"],
        "instructions": ["Mix flour", "Add eggs"],
        "prep_time": "10min",
        "cook_time": "20min",
        "total_time": "30min",
        "servings": "4",
        "image_url": "https://example.com/image.jpg",
        "source": "https://example.com/recipe",
        "notes": None,
    }
    with patch("app.routes.editor.scrape_recipe", return_value=mock_data):
        resp = client.post("/api/scrape", json={"url": "https://example.com/recipe"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Scraped Recipe"
        assert len(data["ingredients"]) == 2


def test_scrape_endpoint_failure(client):
    mock_data = {"title": None, "ingredients": [], "instructions": [],
                 "prep_time": None, "cook_time": None, "total_time": None,
                 "servings": None, "image_url": None, "source": "https://bad.com", "notes": None}
    with patch("app.routes.editor.scrape_recipe", return_value=mock_data):
        resp = client.post("/api/scrape", json={"url": "https://bad.com"})
        assert resp.status_code == 422


def test_create_recipe(client, tmp_recipes):
    resp = client.post("/api/recipes", json={
        "title": "New Recipe",
        "tags": ["test", "new"],
        "servings": "2",
        "ingredients": ["1 apple", "1 banana"],
        "instructions": ["Slice fruit", "Serve"],
        "notes": [],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "New Recipe"
    assert data["slug"] == "new-recipe"

    # Verify file was created
    assert (tmp_recipes / "new-recipe.md").exists()


def test_create_recipe_duplicate(client, tmp_recipes):
    # test-recipe.md already exists
    resp = client.post("/api/recipes", json={
        "title": "Test Recipe",
        "ingredients": ["something"],
        "instructions": ["do something"],
    })
    assert resp.status_code == 409


def test_update_recipe(client, tmp_recipes):
    resp = client.put("/api/recipes/test-recipe", json={
        "title": "Test Recipe Updated",
        "tags": ["updated"],
        "servings": "8",
        "ingredients": ["2 cups flour"],
        "instructions": ["Mix well"],
        "notes": ["Updated note"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Test Recipe Updated"

    # Verify file was modified
    content = (tmp_recipes / "test-recipe.md").read_text()
    assert "Test Recipe Updated" in content


def test_update_nonexistent(client):
    resp = client.put("/api/recipes/nonexistent", json={
        "title": "Nope",
        "ingredients": [],
        "instructions": [],
    })
    assert resp.status_code == 404


def test_delete_recipe(client, tmp_recipes):
    assert (tmp_recipes / "test-recipe.md").exists()
    resp = client.delete("/api/recipes/test-recipe")
    assert resp.status_code == 204
    assert not (tmp_recipes / "test-recipe.md").exists()


def test_delete_nonexistent(client):
    resp = client.delete("/api/recipes/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# SSRF protection: scrape endpoint returns 400 for blocked URLs
# ---------------------------------------------------------------------------


def test_scrape_endpoint_blocks_localhost(client):
    """POST /api/scrape with a localhost URL returns 400 (SSRF blocked)."""
    resp = client.post("/api/scrape", json={"url": "http://localhost/admin"})
    assert resp.status_code == 400
    assert "localhost" in resp.json()["detail"].lower() or "not allowed" in resp.json()["detail"].lower()


def test_scrape_endpoint_blocks_private_ip(client):
    """POST /api/scrape with a private IP returns 400 (SSRF blocked)."""
    resp = client.post("/api/scrape", json={"url": "http://192.168.1.1/secret"})
    assert resp.status_code == 400


def test_scrape_endpoint_blocks_loopback(client):
    """POST /api/scrape with 127.x.x.x returns 400 (SSRF blocked)."""
    resp = client.post("/api/scrape", json={"url": "http://127.0.0.1/internal"})
    assert resp.status_code == 400


def test_scrape_endpoint_blocks_metadata_ip(client):
    """POST /api/scrape with the AWS/GCP metadata IP returns 400 (SSRF blocked)."""
    resp = client.post("/api/scrape", json={"url": "http://169.254.169.254/latest/meta-data/"})
    assert resp.status_code == 400


def test_scrape_endpoint_blocks_file_scheme(client):
    """POST /api/scrape with file:// scheme returns 400 (SSRF blocked)."""
    resp = client.post("/api/scrape", json={"url": "file:///etc/passwd"})
    assert resp.status_code == 400


def test_scrape_endpoint_blocks_10_net(client):
    """POST /api/scrape with RFC 1918 10.x.x.x address returns 400 (SSRF blocked)."""
    resp = client.post("/api/scrape", json={"url": "http://10.0.0.1/internal"})
    assert resp.status_code == 400
