"""Tests for slug sanitization and path traversal protection."""

import pytest
from fastapi import HTTPException

from app.validation import is_valid_slug, validate_slug


# ---------------------------------------------------------------------------
# is_valid_slug unit tests
# ---------------------------------------------------------------------------

class TestIsValidSlug:
    def test_simple_slug(self):
        assert is_valid_slug("chicken-tikka-masala") is True

    def test_single_word(self):
        assert is_valid_slug("pasta") is True

    def test_single_char(self):
        assert is_valid_slug("a") is True

    def test_numbers_allowed(self):
        assert is_valid_slug("7-layer-casserole") is True
        assert is_valid_slug("recipe123") is True

    def test_empty_string(self):
        assert is_valid_slug("") is False

    def test_path_traversal_dotdot(self):
        assert is_valid_slug("../etc/passwd") is False
        assert is_valid_slug("../../secret") is False
        assert is_valid_slug("recipe/../other") is False

    def test_path_separator_forward_slash(self):
        assert is_valid_slug("recipes/evil") is False
        assert is_valid_slug("/etc/passwd") is False

    def test_path_separator_backslash(self):
        assert is_valid_slug("recipes\\evil") is False
        assert is_valid_slug("..\\windows\\system32") is False

    def test_leading_hyphen(self):
        assert is_valid_slug("-bad-slug") is False

    def test_trailing_hyphen(self):
        assert is_valid_slug("bad-slug-") is False

    def test_uppercase_rejected(self):
        # slugs are lowercase-only by convention
        assert is_valid_slug("Chicken-Tikka") is False

    def test_spaces_rejected(self):
        assert is_valid_slug("chicken tikka") is False

    def test_special_chars_rejected(self):
        assert is_valid_slug("recipe!") is False
        assert is_valid_slug("recipe.md") is False
        assert is_valid_slug("recípe") is False

    def test_null_byte_rejected(self):
        assert is_valid_slug("recipe\x00evil") is False

    def test_consecutive_hyphens(self):
        # Two consecutive hyphens are technically valid characters but unusual;
        # the regex allows them as long as start/end rules are met.
        assert is_valid_slug("a--b") is True

    def test_long_slug(self):
        # 200-char slug (max allowed)
        long = "a" + "-x" * 99  # "a-x-x-x..." = 1 + 199 = 200 chars
        assert len(long) == 200
        assert is_valid_slug(long) is True

    def test_too_long_slug(self):
        # 201 chars
        too_long = "a" * 201
        assert is_valid_slug(too_long) is False


# ---------------------------------------------------------------------------
# validate_slug — should raise HTTPException for invalid slugs
# ---------------------------------------------------------------------------

class TestValidateSlug:
    def test_valid_slug_returns_slug(self):
        result = validate_slug("chicken-tikka-masala")
        assert result == "chicken-tikka-masala"

    def test_path_traversal_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_slug("../etc/passwd")
        assert exc_info.value.status_code == 400

    def test_slash_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_slug("recipes/evil")
        assert exc_info.value.status_code == 400

    def test_backslash_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_slug("recipes\\evil")
        assert exc_info.value.status_code == 400

    def test_empty_raises_400(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_slug("")
        assert exc_info.value.status_code == 400

    def test_error_message_is_helpful(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_slug("../evil")
        assert "slug" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# Integration: route-level rejection of malicious slugs
# ---------------------------------------------------------------------------

import subprocess
import textwrap

from fastapi.testclient import TestClient
from app.main import create_app

BASIC_RECIPE = textwrap.dedent("""\
    ---
    title: Test Recipe
    tags: [test]
    ---

    # Test Recipe

    ## Ingredients

    - 1 cup flour

    ## Instructions

    1. Mix ingredients.
""")


@pytest.fixture
def tmp_recipes(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "test-recipe.md").write_text(BASIC_RECIPE)
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(tmp_path),
        capture_output=True,
    )
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


class TestSlugRouteValidation:
    """Ensure path-traversal slugs are rejected at the HTTP layer."""

    @pytest.mark.parametrize("bad_slug", [
        "../etc/passwd",
        "..%2Fetc%2Fpasswd",
        "valid/../evil",
        "recipes/evil",
    ])
    def test_get_recipe_rejects_traversal(self, client, bad_slug):
        resp = client.get(f"/api/recipes/{bad_slug}")
        # Either 400 (caught by our validator) or 404 (FastAPI routing didn't
        # match at all due to path normalization) — never 200
        assert resp.status_code in (400, 404, 422)

    @pytest.mark.parametrize("bad_slug", [
        "../etc/passwd",
        "recipes/evil",
        "-bad-start",
    ])
    def test_export_recipe_rejects_traversal(self, client, bad_slug):
        resp = client.get(f"/api/recipes/{bad_slug}/export")
        assert resp.status_code in (400, 404, 422)

    def test_valid_slug_still_works(self, client):
        resp = client.get("/api/recipes/test-recipe")
        assert resp.status_code == 200

    def test_export_valid_slug_still_works(self, client):
        resp = client.get("/api/recipes/test-recipe/export")
        assert resp.status_code == 200

    def test_cook_history_rejects_traversal(self, client):
        resp = client.post(
            "/api/recipes/../etc/passwd/cook-history",
            json={},
        )
        assert resp.status_code in (400, 404, 422)

    def test_grocery_remove_rejects_traversal(self, client):
        resp = client.delete("/api/grocery/recipes/../etc/passwd")
        assert resp.status_code in (400, 404, 422)
