"""Tests for slug parameter sanitization (path traversal prevention).

All routes that accept a ``slug`` or ``fork_name_slug`` path parameter must
call ``validate_slug`` before using the value to construct a filesystem path.
An attacker-supplied value such as ``../../etc/passwd`` must be rejected with
HTTP 400 rather than allowing arbitrary file reads or writes.
"""
import subprocess
import textwrap

import pytest
from fastapi.testclient import TestClient

from app.slug_utils import validate_slug
from fastapi import HTTPException
from app.main import create_app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE_RECIPE = textwrap.dedent("""\
    ---
    title: Test Soup
    tags: [soup]
    servings: 2
    ---

    # Test Soup

    ## Ingredients

    - 1 cup water
    - 1 tsp salt

    ## Instructions

    1. Boil water
    2. Add salt
""")


@pytest.fixture
def tmp_recipes(tmp_path):
    """Temp recipes dir with one recipe and a git repo."""
    recipe = tmp_path / "test-soup.md"
    recipe.write_text(BASE_RECIPE)
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init", "--allow-empty"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


# ---------------------------------------------------------------------------
# validate_slug unit tests
# ---------------------------------------------------------------------------

VALID_SLUGS = [
    "a",
    "abc",
    "chicken-tikka-masala",
    "7-layer-casserole",
    "how-to-make-cauliflower-rice",
    "a1",
    "1a",
    "abc123",
    "a" * 200,  # exactly at max length
]

INVALID_SLUGS = [
    # path traversal
    "../etc/passwd",
    "../../etc/shadow",
    "foo/../bar",
    # path separators
    "foo/bar",
    "foo\\bar",
    # leading/trailing hyphens
    "-foo",
    "foo-",
    # empty string
    "",
    # too long
    "a" * 201,
    # uppercase (not produced by slugify)
    "Foo",
    "FOO",
    # spaces
    "foo bar",
    # null byte
    "foo\x00bar",
    # dots
    "foo.bar",
    "..bar",
    # special characters
    "foo@bar",
    "foo;bar",
    "foo&bar",
]


class TestValidateSlugUnit:
    @pytest.mark.parametrize("slug", VALID_SLUGS)
    def test_valid_slug_passes(self, slug):
        assert validate_slug(slug) == slug

    @pytest.mark.parametrize("slug", INVALID_SLUGS)
    def test_invalid_slug_raises_400(self, slug):
        with pytest.raises(HTTPException) as exc_info:
            validate_slug(slug)
        assert exc_info.value.status_code == 400

    def test_field_name_in_error_message(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_slug("../evil", field_name="fork")
        assert "fork" in exc_info.value.detail

    def test_returns_slug_unchanged(self):
        result = validate_slug("chicken-tikka-masala")
        assert result == "chicken-tikka-masala"


# ---------------------------------------------------------------------------
# Path traversal tests — recipe routes
# ---------------------------------------------------------------------------

TRAVERSAL_SLUGS = [
    "../etc/passwd",
    "../../secret",
    "..%2fetc%2fpasswd",
    "foo/../bar",
]


class TestRecipeRouteSlugValidation:
    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_get_recipe_rejects_traversal(self, client, slug):
        resp = client.get(f"/api/recipes/{slug}")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_export_recipe_rejects_traversal(self, client, slug):
        resp = client.get(f"/api/recipes/{slug}/export")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_recipe_history_rejects_traversal(self, client, slug):
        resp = client.get(f"/api/recipes/{slug}/history")
        assert resp.status_code in (400, 404, 422)

    def test_get_recipe_plain_invalid_returns_400(self, client):
        resp = client.get("/api/recipes/UPPERCASE")
        assert resp.status_code == 400

    def test_get_recipe_with_dots_returns_400(self, client):
        resp = client.get("/api/recipes/foo.bar")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Path traversal tests — editor routes (PUT, DELETE)
# ---------------------------------------------------------------------------

class TestEditorRouteSlugValidation:
    RECIPE_PAYLOAD = {
        "title": "Evil Recipe",
        "tags": [],
        "ingredients": ["1 cup water"],
        "instructions": ["Boil it"],
        "notes": [],
    }

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_update_recipe_rejects_traversal(self, client, slug):
        resp = client.put(f"/api/recipes/{slug}", json=self.RECIPE_PAYLOAD)
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_delete_recipe_rejects_traversal(self, client, slug):
        resp = client.delete(f"/api/recipes/{slug}")
        assert resp.status_code in (400, 404, 422)

    def test_update_recipe_plain_invalid_returns_400(self, client):
        resp = client.put("/api/recipes/UPPER_CASE", json=self.RECIPE_PAYLOAD)
        assert resp.status_code == 400

    def test_delete_recipe_plain_invalid_returns_400(self, client):
        resp = client.delete("/api/recipes/foo.bar")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Path traversal tests — cook routes
# ---------------------------------------------------------------------------

class TestCookRouteSlugValidation:
    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_add_cook_history_rejects_traversal(self, client, slug):
        resp = client.post(f"/api/recipes/{slug}/cook-history", json={})
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_delete_cook_history_rejects_traversal(self, client, slug):
        resp = client.delete(f"/api/recipes/{slug}/cook-history/0")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_add_favorite_rejects_traversal(self, client, slug):
        resp = client.post(f"/api/recipes/{slug}/favorite")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_remove_favorite_rejects_traversal(self, client, slug):
        resp = client.delete(f"/api/recipes/{slug}/favorite")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_like_recipe_rejects_traversal(self, client, slug):
        resp = client.post(f"/api/recipes/{slug}/like")
        assert resp.status_code in (400, 404, 422)

    def test_cook_history_plain_invalid_returns_400(self, client):
        resp = client.post("/api/recipes/INVALID_SLUG/cook-history", json={})
        assert resp.status_code == 400

    def test_favorite_plain_invalid_returns_400(self, client):
        resp = client.post("/api/recipes/has.dot/favorite")
        assert resp.status_code == 400

    def test_like_plain_invalid_returns_400(self, client):
        resp = client.post("/api/recipes/-leading-hyphen/like")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Path traversal tests — fork routes
# ---------------------------------------------------------------------------

FORK_PAYLOAD = {
    "fork_name": "Vegan Version",
    "author": "tester",
    "title": "Test Soup",
    "tags": ["soup"],
    "servings": "2",
    "ingredients": ["2 cups water", "2 tsp salt"],
    "instructions": ["Boil 2 cups water", "Add 2 tsp salt"],
    "notes": [],
}


class TestForkRouteSlugValidation:
    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_get_fork_rejects_traversal_in_slug(self, client, slug):
        resp = client.get(f"/api/recipes/{slug}/forks/some-fork")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_get_fork_rejects_traversal_in_fork_slug(self, client, slug):
        resp = client.get(f"/api/recipes/test-soup/forks/{slug}")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_create_fork_rejects_traversal_in_slug(self, client, slug):
        resp = client.post(f"/api/recipes/{slug}/forks", json=FORK_PAYLOAD)
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_update_fork_rejects_traversal_in_slug(self, client, slug):
        resp = client.put(f"/api/recipes/{slug}/forks/some-fork", json=FORK_PAYLOAD)
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_update_fork_rejects_traversal_in_fork_slug(self, client, slug):
        resp = client.put(f"/api/recipes/test-soup/forks/{slug}", json=FORK_PAYLOAD)
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_delete_fork_rejects_traversal_in_slug(self, client, slug):
        resp = client.delete(f"/api/recipes/{slug}/forks/some-fork")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_delete_fork_rejects_traversal_in_fork_slug(self, client, slug):
        resp = client.delete(f"/api/recipes/test-soup/forks/{slug}")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_merge_fork_rejects_traversal_in_slug(self, client, slug):
        resp = client.post(f"/api/recipes/{slug}/forks/some-fork/merge", json={"note": "x"})
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_merge_fork_rejects_traversal_in_fork_slug(self, client, slug):
        resp = client.post(f"/api/recipes/test-soup/forks/{slug}/merge", json={"note": "x"})
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_unmerge_fork_rejects_traversal_in_slug(self, client, slug):
        resp = client.post(f"/api/recipes/{slug}/forks/some-fork/unmerge")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_unmerge_fork_rejects_traversal_in_fork_slug(self, client, slug):
        resp = client.post(f"/api/recipes/test-soup/forks/{slug}/unmerge")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_fail_fork_rejects_traversal_in_slug(self, client, slug):
        resp = client.post(
            f"/api/recipes/{slug}/forks/some-fork/fail",
            json={"reason": "test"},
        )
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_fail_fork_rejects_traversal_in_fork_slug(self, client, slug):
        resp = client.post(
            f"/api/recipes/test-soup/forks/{slug}/fail",
            json={"reason": "test"},
        )
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_unfail_fork_rejects_traversal_in_slug(self, client, slug):
        resp = client.post(f"/api/recipes/{slug}/forks/some-fork/unfail")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_unfail_fork_rejects_traversal_in_fork_slug(self, client, slug):
        resp = client.post(f"/api/recipes/test-soup/forks/{slug}/unfail")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_export_fork_rejects_traversal_in_slug(self, client, slug):
        resp = client.get(f"/api/recipes/{slug}/forks/some-fork/export")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_export_fork_rejects_traversal_in_fork_slug(self, client, slug):
        resp = client.get(f"/api/recipes/test-soup/forks/{slug}/export")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_fork_history_rejects_traversal_in_slug(self, client, slug):
        resp = client.get(f"/api/recipes/{slug}/forks/some-fork/history")
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_fork_history_rejects_traversal_in_fork_slug(self, client, slug):
        resp = client.get(f"/api/recipes/test-soup/forks/{slug}/history")
        assert resp.status_code in (400, 404, 422)

    def test_fork_plain_invalid_slug_returns_400(self, client):
        resp = client.get("/api/recipes/UPPER/forks/some-fork")
        assert resp.status_code == 400

    def test_fork_plain_invalid_fork_slug_returns_400(self, client):
        resp = client.get("/api/recipes/test-soup/forks/foo.bar")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Path traversal tests — stream route
# ---------------------------------------------------------------------------

class TestStreamRouteSlugValidation:
    @pytest.mark.parametrize("slug", TRAVERSAL_SLUGS)
    def test_get_stream_rejects_traversal(self, client, slug):
        resp = client.get(f"/api/recipes/{slug}/stream")
        assert resp.status_code in (400, 404, 422)

    def test_get_stream_plain_invalid_returns_400(self, client):
        resp = client.get("/api/recipes/foo.bar/stream")
        assert resp.status_code == 400

    def test_get_stream_valid_slug_proceeds(self, client):
        # Valid slug, recipe exists — should not get 400
        resp = client.get("/api/recipes/test-soup/stream")
        assert resp.status_code != 400
