"""Tests for grocery list API routes."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def tmp_recipes(tmp_path):
    recipe = tmp_path / "birria-tacos.md"
    recipe.write_text(
        "---\ntitle: Birria Tacos\ntags: [mexican]\nservings: 6\n---\n\n"
        "# Birria Tacos\n\n## Ingredients\n\n- 2 lbs beef\n- 4 dried chiles\n\n"
        "## Instructions\n\n1. Cook beef\n"
    )
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


class TestGroceryGet:
    def test_empty_list(self, client):
        resp = client.get("/api/grocery")
        assert resp.status_code == 200
        data = resp.json()
        assert data["recipes"] == {}
        assert data["checked"] == []


class TestGroceryAddRecipe:
    def test_add_recipe(self, client):
        resp = client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["2 lbs beef", "4 dried chiles"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "birria-tacos" in data["recipes"]
        assert len(data["recipes"]["birria-tacos"]["items"]) == 2
        assert data["recipes"]["birria-tacos"]["items"][0]["name"] == "beef"

    def test_add_recipe_with_fork(self, client):
        resp = client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["2 lbs beef"],
            "fork": "spicy-version",
            "servings": "8",
        })
        data = resp.json()
        assert data["recipes"]["birria-tacos"]["fork"] == "spicy-version"
        assert data["recipes"]["birria-tacos"]["servings"] == "8"

    def test_add_duplicate_replaces(self, client):
        client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["2 lbs beef"],
        })
        resp = client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["3 lbs beef", "1 onion"],
        })
        data = resp.json()
        assert len(data["recipes"]["birria-tacos"]["items"]) == 2


class TestGroceryRemoveRecipe:
    def test_remove_recipe(self, client):
        client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["2 lbs beef"],
        })
        resp = client.delete("/api/grocery/recipes/birria-tacos")
        assert resp.status_code == 200
        assert "birria-tacos" not in resp.json()["recipes"]

    def test_remove_nonexistent(self, client):
        resp = client.delete("/api/grocery/recipes/nonexistent")
        assert resp.status_code == 200


class TestGroceryToggleCheck:
    def test_check_and_uncheck(self, client):
        # Check
        resp = client.post("/api/grocery/check/lb:beef")
        assert resp.status_code == 200
        assert "lb:beef" in resp.json()["checked"]

        # Uncheck
        resp = client.post("/api/grocery/check/lb:beef")
        assert "lb:beef" not in resp.json()["checked"]


class TestGroceryRemoveItem:
    def test_remove_item(self, client):
        client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["2 lbs beef", "4 dried chiles"],
        })
        resp = client.delete("/api/grocery/items/lb:beef")
        assert resp.status_code == 200
        items = resp.json()["recipes"]["birria-tacos"]["items"]
        assert all(i["name"] != "beef" for i in items)

    def test_remove_last_item_removes_recipe(self, client):
        client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["2 lbs beef"],
        })
        resp = client.delete("/api/grocery/items/lb:beef")
        assert "birria-tacos" not in resp.json()["recipes"]


class TestGroceryClear:
    def test_clear_checked(self, client):
        client.post("/api/grocery/check/lb:beef")
        resp = client.delete("/api/grocery/checked")
        assert resp.status_code == 200
        assert resp.json()["checked"] == []

    def test_clear_all(self, client):
        client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["2 lbs beef"],
        })
        resp = client.delete("/api/grocery")
        assert resp.status_code == 200
        assert resp.json()["recipes"] == {}
        assert resp.json()["checked"] == []


class TestGroceryExport:
    def test_export_empty(self, client):
        resp = client.get("/api/grocery/export")
        assert resp.status_code == 200
        assert "empty" in resp.text.lower()

    def test_export_with_items(self, client):
        client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["2 lbs beef", "4 dried chiles"],
        })
        resp = client.get("/api/grocery/export")
        assert resp.status_code == 200
        assert "To buy:" in resp.text
        assert "beef" in resp.text

    def test_export_with_checked(self, client):
        client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["2 lbs beef", "4 dried chiles"],
        })
        client.post("/api/grocery/check/lb:beef")
        resp = client.get("/api/grocery/export")
        assert "Got it:" in resp.text
        assert "[x]" in resp.text

    def test_export_persists_to_file(self, client, tmp_recipes):
        client.post("/api/grocery/recipes", json={
            "slug": "birria-tacos",
            "title": "Birria Tacos",
            "ingredients": ["2 lbs beef"],
        })
        grocery_file = tmp_recipes / "grocery-list.json"
        assert grocery_file.exists()
