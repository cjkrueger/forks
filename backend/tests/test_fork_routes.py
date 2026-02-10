"""Tests for fork CRUD API routes."""
import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


BASE_RECIPE = textwrap.dedent("""\
    ---
    title: Chocolate Cookies
    tags: [dessert, baking]
    servings: 24
    date_added: 2026-01-15
    ---

    # Chocolate Cookies

    ## Ingredients

    - 2 cups flour
    - 1 cup sugar
    - 1 cup butter
    - 2 eggs
    - 1 cup chocolate chips

    ## Instructions

    1. Preheat oven to 350F
    2. Mix dry ingredients
    3. Cream butter and sugar
    4. Combine and fold in chocolate chips
    5. Bake for 12 minutes

    ## Notes

    - Let cool on pan for 5 minutes
""")


@pytest.fixture
def tmp_recipes(tmp_path):
    """Create a temp recipes directory with a base recipe."""
    recipe = tmp_path / "chocolate-cookies.md"
    recipe.write_text(BASE_RECIPE)
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


def _fork_input(fork_name="Vegan Version", author="cj", **overrides):
    """Helper to build a ForkInput payload with changed ingredients."""
    data = {
        "fork_name": fork_name,
        "author": author,
        "title": "Chocolate Cookies",
        "tags": ["dessert", "baking"],
        "servings": "24",
        "ingredients": [
            "2 cups flour",
            "1 cup sugar",
            "1/2 cup coconut oil",
            "1 flax egg",
            "1 cup vegan chocolate chips",
        ],
        "instructions": [
            "Preheat oven to 350F",
            "Mix dry ingredients",
            "Cream coconut oil and sugar",
            "Combine and fold in chocolate chips",
            "Bake for 12 minutes",
        ],
        "notes": ["Let cool on pan for 5 minutes"],
    }
    data.update(overrides)
    return data


class TestCreateFork:
    def test_create_fork_success(self, client, tmp_recipes):
        resp = client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "vegan-version"
        assert data["fork_name"] == "Vegan Version"

        # Verify file was created
        fork_file = tmp_recipes / "chocolate-cookies.fork.vegan-version.md"
        assert fork_file.exists()

    def test_create_fork_no_changes_returns_400(self, client):
        """If fork data is identical to base, return 400."""
        resp = client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(
                ingredients=[
                    "2 cups flour",
                    "1 cup sugar",
                    "1 cup butter",
                    "2 eggs",
                    "1 cup chocolate chips",
                ],
                instructions=[
                    "Preheat oven to 350F",
                    "Mix dry ingredients",
                    "Cream butter and sugar",
                    "Combine and fold in chocolate chips",
                    "Bake for 12 minutes",
                ],
                notes=["Let cool on pan for 5 minutes"],
            ),
        )
        assert resp.status_code == 400
        assert "No changes" in resp.json()["detail"]

    def test_create_fork_duplicate_returns_409(self, client):
        resp1 = client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        assert resp2.status_code == 409

    def test_create_fork_base_not_found(self, client):
        resp = client.post(
            "/api/recipes/nonexistent-recipe/forks",
            json=_fork_input(),
        )
        assert resp.status_code == 404

    def test_create_fork_updates_index(self, client):
        """After creating a fork, the base recipe listing should include it."""
        client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        resp = client.get("/api/recipes/chocolate-cookies")
        recipe = resp.json()
        fork_names = [f["name"] for f in recipe["forks"]]
        assert "vegan-version" in fork_names


class TestGetFork:
    def test_get_fork_success(self, client):
        client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        resp = client.get("/api/recipes/chocolate-cookies/forks/vegan-version")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "vegan-version"
        assert data["fork_name"] == "Vegan Version"
        assert data["author"] == "cj"
        assert "content" in data

    def test_get_fork_not_found(self, client):
        resp = client.get("/api/recipes/chocolate-cookies/forks/does-not-exist")
        assert resp.status_code == 404


class TestUpdateFork:
    def test_update_fork_success(self, client, tmp_recipes):
        client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        updated = _fork_input(
            ingredients=[
                "2 cups flour",
                "1 cup coconut sugar",
                "1/2 cup coconut oil",
                "1 flax egg",
                "1 cup dark chocolate chips",
            ],
        )
        resp = client.put(
            "/api/recipes/chocolate-cookies/forks/vegan-version",
            json=updated,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "vegan-version"

        # Verify file was updated
        fork_file = tmp_recipes / "chocolate-cookies.fork.vegan-version.md"
        content = fork_file.read_text()
        assert "dark chocolate chips" in content

    def test_update_fork_not_found(self, client):
        resp = client.put(
            "/api/recipes/chocolate-cookies/forks/nonexistent",
            json=_fork_input(),
        )
        assert resp.status_code == 404

    def test_update_fork_no_changes_returns_400(self, client):
        client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        resp = client.put(
            "/api/recipes/chocolate-cookies/forks/vegan-version",
            json=_fork_input(
                ingredients=[
                    "2 cups flour",
                    "1 cup sugar",
                    "1 cup butter",
                    "2 eggs",
                    "1 cup chocolate chips",
                ],
                instructions=[
                    "Preheat oven to 350F",
                    "Mix dry ingredients",
                    "Cream butter and sugar",
                    "Combine and fold in chocolate chips",
                    "Bake for 12 minutes",
                ],
                notes=["Let cool on pan for 5 minutes"],
            ),
        )
        assert resp.status_code == 400

    def test_update_fork_base_not_found(self, client):
        resp = client.put(
            "/api/recipes/nonexistent-recipe/forks/some-fork",
            json=_fork_input(),
        )
        assert resp.status_code == 404


class TestDeleteFork:
    def test_delete_fork_success(self, client, tmp_recipes):
        client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        fork_file = tmp_recipes / "chocolate-cookies.fork.vegan-version.md"
        assert fork_file.exists()

        resp = client.delete("/api/recipes/chocolate-cookies/forks/vegan-version")
        assert resp.status_code == 204
        assert not fork_file.exists()

    def test_delete_fork_not_found(self, client):
        resp = client.delete("/api/recipes/chocolate-cookies/forks/nonexistent")
        assert resp.status_code == 404

    def test_delete_fork_removes_from_index(self, client):
        client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        # Verify fork is in the index
        resp = client.get("/api/recipes/chocolate-cookies")
        assert len(resp.json()["forks"]) == 1

        client.delete("/api/recipes/chocolate-cookies/forks/vegan-version")

        # Verify fork is removed from the index
        resp = client.get("/api/recipes/chocolate-cookies")
        assert len(resp.json()["forks"]) == 0


class TestExportFork:
    def test_export_fork_success(self, client):
        client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        resp = client.get("/api/recipes/chocolate-cookies/forks/vegan-version/export")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")
        assert "attachment" in resp.headers["content-disposition"]
        assert "chocolate-cookies-vegan-version.md" in resp.headers["content-disposition"]

        body = resp.text
        # Should contain merged frontmatter
        assert "title:" in body
        assert "Vegan Version" in body
        # Should contain merged content from base + fork
        assert "## Ingredients" in body
        assert "## Instructions" in body

    def test_export_fork_not_found(self, client):
        resp = client.get("/api/recipes/chocolate-cookies/forks/nonexistent/export")
        assert resp.status_code == 404

    def test_export_fork_base_not_found(self, client):
        resp = client.get("/api/recipes/nonexistent-recipe/forks/some-fork/export")
        assert resp.status_code == 404

    def test_export_contains_fork_modifications(self, client):
        """The exported markdown should include the fork's changed ingredients."""
        client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        resp = client.get("/api/recipes/chocolate-cookies/forks/vegan-version/export")
        body = resp.text
        # Fork changes coconut oil for butter
        assert "coconut oil" in body
        # Base instruction content should still be present
        assert "Preheat oven" in body
