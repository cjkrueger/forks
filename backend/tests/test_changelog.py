"""Tests for embedded changelog functionality."""
import subprocess
import textwrap
from pathlib import Path

import frontmatter
import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.sections import detect_changed_sections


# ---------------------------------------------------------------------------
# detect_changed_sections tests
# ---------------------------------------------------------------------------

class TestDetectChangedSections:
    def test_detects_changed_ingredients(self):
        old = "# Title\n\n## Ingredients\n\n- flour\n- 2 eggs\n\n## Instructions\n\n1. Mix"
        new = "# Title\n\n## Ingredients\n\n- flour\n- 2 flax eggs\n\n## Instructions\n\n1. Mix"
        result = detect_changed_sections(old, new)
        assert "Ingredients" in result
        assert "Instructions" not in result

    def test_no_changes_returns_empty(self):
        content = "# Title\n\n## Ingredients\n\n- flour\n\n## Instructions\n\n1. Mix"
        result = detect_changed_sections(content, content)
        assert result == []

    def test_detects_multiple_changes(self):
        old = "# Title\n\n## Ingredients\n\n- flour\n\n## Instructions\n\n1. Mix\n\n## Notes\n\n- old note"
        new = "# Title\n\n## Ingredients\n\n- sugar\n\n## Instructions\n\n1. Bake\n\n## Notes\n\n- old note"
        result = detect_changed_sections(old, new)
        assert "Ingredients" in result
        assert "Instructions" in result
        assert "Notes" not in result

    def test_detects_added_section(self):
        old = "# Title\n\n## Ingredients\n\n- flour"
        new = "# Title\n\n## Ingredients\n\n- flour\n\n## Notes\n\n- new note"
        result = detect_changed_sections(old, new)
        assert "Notes" in result
        assert "Ingredients" not in result

    def test_detects_removed_section(self):
        old = "# Title\n\n## Ingredients\n\n- flour\n\n## Notes\n\n- a note"
        new = "# Title\n\n## Ingredients\n\n- flour"
        result = detect_changed_sections(old, new)
        assert "Notes" in result

    def test_empty_contents(self):
        result = detect_changed_sections("", "")
        assert result == []

    def test_ignores_preamble(self):
        old = "# Old Title\n\n## Ingredients\n\n- flour"
        new = "# New Title\n\n## Ingredients\n\n- flour"
        result = detect_changed_sections(old, new)
        # Preamble changes should be ignored
        assert result == []


# ---------------------------------------------------------------------------
# Integration tests: changelog entries via API
# ---------------------------------------------------------------------------

BASE_RECIPE = textwrap.dedent("""\
    ---
    title: Test Recipe
    tags: [test]
    servings: 4
    date_added: 2026-01-15
    ---

    # Test Recipe

    ## Ingredients

    - 1 cup flour
    - 2 eggs

    ## Instructions

    1. Mix ingredients
    2. Bake at 350F
""")

FORK_BASE = textwrap.dedent("""\
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
    """Create a temp recipes directory with sample recipes and a git repo."""
    images_dir = tmp_path / "images"
    images_dir.mkdir()

    recipe = tmp_path / "test-recipe.md"
    recipe.write_text(BASE_RECIPE)

    cookie_recipe = tmp_path / "chocolate-cookies.md"
    cookie_recipe.write_text(FORK_BASE)

    # Initialize a git repo so git operations work
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit", "--allow-empty"],
        cwd=str(tmp_path), capture_output=True,
    )
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


class TestCreateRecipeChangelog:
    def test_create_recipe_adds_created_changelog(self, client, tmp_recipes):
        resp = client.post("/api/recipes", json={
            "title": "New Recipe",
            "tags": ["test"],
            "servings": "2",
            "ingredients": ["1 apple", "1 banana"],
            "instructions": ["Slice fruit", "Serve"],
            "notes": [],
        })
        assert resp.status_code == 201

        # Read the file and check frontmatter for changelog
        filepath = tmp_recipes / "new-recipe.md"
        assert filepath.exists()
        post = frontmatter.load(filepath)
        changelog = post.metadata.get("changelog", [])
        assert len(changelog) == 1
        assert changelog[0]["action"] == "created"
        assert changelog[0]["summary"] == "Created"
        assert "date" in changelog[0]


class TestUpdateRecipeChangelog:
    def test_update_recipe_adds_edited_changelog(self, client, tmp_recipes):
        resp = client.put("/api/recipes/test-recipe", json={
            "title": "Test Recipe",
            "tags": ["test"],
            "servings": "4",
            "ingredients": ["2 cups flour", "3 eggs"],
            "instructions": ["Mix ingredients", "Bake at 350F"],
            "notes": [],
        })
        assert resp.status_code == 200

        filepath = tmp_recipes / "test-recipe.md"
        post = frontmatter.load(filepath)
        changelog = post.metadata.get("changelog", [])
        assert len(changelog) == 1
        assert changelog[0]["action"] == "edited"
        assert "Ingredients" in changelog[0]["summary"]

    def test_update_recipe_metadata_only(self, client, tmp_recipes):
        """When only metadata changes (no section body changes), summary says 'Edited metadata'."""
        resp = client.put("/api/recipes/test-recipe", json={
            "title": "Test Recipe",
            "tags": ["test", "updated"],
            "servings": "8",
            "ingredients": ["1 cup flour", "2 eggs"],
            "instructions": ["Mix ingredients", "Bake at 350F"],
            "notes": [],
        })
        assert resp.status_code == 200

        filepath = tmp_recipes / "test-recipe.md"
        post = frontmatter.load(filepath)
        changelog = post.metadata.get("changelog", [])
        assert len(changelog) == 1
        assert changelog[0]["action"] == "edited"
        assert changelog[0]["summary"] == "Edited metadata"


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


class TestCreateForkChangelog:
    def test_create_fork_adds_created_changelog(self, client, tmp_recipes):
        resp = client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        assert resp.status_code == 201

        fork_file = tmp_recipes / "chocolate-cookies.fork.vegan-version.md"
        assert fork_file.exists()
        post = frontmatter.load(fork_file)
        changelog = post.metadata.get("changelog", [])
        assert len(changelog) == 1
        assert changelog[0]["action"] == "created"
        assert changelog[0]["summary"] == "Forked from original"


class TestUpdateForkChangelog:
    def test_update_fork_adds_edited_changelog(self, client, tmp_recipes):
        # Create the fork first
        client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )

        # Update the fork with different ingredients
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

        fork_file = tmp_recipes / "chocolate-cookies.fork.vegan-version.md"
        post = frontmatter.load(fork_file)
        changelog = post.metadata.get("changelog", [])
        # Should have 2 entries: created + edited
        assert len(changelog) == 2
        assert changelog[0]["action"] == "created"
        assert changelog[1]["action"] == "edited"
        assert "Ingredients" in changelog[1]["summary"]


class TestMergeForkChangelog:
    def test_merge_adds_changelog_to_both(self, client, tmp_recipes):
        # Create fork
        client.post(
            "/api/recipes/chocolate-cookies/forks",
            json=_fork_input(),
        )
        # Merge fork
        resp = client.post("/api/recipes/chocolate-cookies/forks/vegan-version/merge")
        assert resp.status_code == 200

        # Check base recipe changelog
        base_file = tmp_recipes / "chocolate-cookies.md"
        base_post = frontmatter.load(base_file)
        base_changelog = base_post.metadata.get("changelog", [])
        assert len(base_changelog) == 1
        assert base_changelog[0]["action"] == "merged"
        assert "Vegan Version" in base_changelog[0]["summary"]

        # Check fork changelog
        fork_file = tmp_recipes / "chocolate-cookies.fork.vegan-version.md"
        fork_post = frontmatter.load(fork_file)
        fork_changelog = fork_post.metadata.get("changelog", [])
        # Should have 2 entries: created + merged
        assert len(fork_changelog) == 2
        assert fork_changelog[0]["action"] == "created"
        assert fork_changelog[1]["action"] == "merged"
        assert "chocolate-cookies" in fork_changelog[1]["summary"]
