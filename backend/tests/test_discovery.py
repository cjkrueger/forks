"""Tests for discovery endpoints: random, sort filters."""
import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


# --- recipe fixtures ----------------------------------------------------------

QUICK_RECIPE = textwrap.dedent("""\
    ---
    title: Quick Salad
    tags: [salad, quick]
    prep_time: 10min
    cook_time: 0min
    date_added: "2026-01-01"
    ---

    # Quick Salad

    ## Ingredients

    - lettuce
    - tomato

    ## Instructions

    1. Toss ingredients together
""")

SLOW_RECIPE = textwrap.dedent("""\
    ---
    title: Slow Braise
    tags: [beef, weekend]
    prep_time: 30min
    cook_time: 3hr
    date_added: "2026-01-05"
    cook_history:
      - date: "2026-01-10"
      - date: "2026-02-01"
    ---

    # Slow Braise

    ## Ingredients

    - beef chuck
    - onions

    ## Instructions

    1. Braise for hours
""")

NEVER_COOKED = textwrap.dedent("""\
    ---
    title: Never Cooked Pasta
    tags: [pasta, quick]
    prep_time: 5min
    cook_time: 15min
    date_added: "2026-01-15"
    ---

    # Never Cooked Pasta

    ## Ingredients

    - pasta
    - butter

    ## Instructions

    1. Boil pasta
""")

COOKED_LONG_AGO = textwrap.dedent("""\
    ---
    title: Old Favorite Soup
    tags: [soup]
    prep_time: 15min
    cook_time: 45min
    date_added: "2025-06-01"
    cook_history:
      - date: "2025-07-01"
    ---

    # Old Favorite Soup

    ## Ingredients

    - water
    - vegetables

    ## Instructions

    1. Make soup
""")


# --- fixtures -----------------------------------------------------------------

@pytest.fixture
def populated(tmp_path):
    """Create a temp directory with several recipes and return a test client."""
    (tmp_path / "quick-salad.md").write_text(QUICK_RECIPE)
    (tmp_path / "slow-braise.md").write_text(SLOW_RECIPE)
    (tmp_path / "never-cooked-pasta.md").write_text(NEVER_COOKED)
    (tmp_path / "old-favorite-soup.md").write_text(COOKED_LONG_AGO)
    app = create_app(recipes_dir=tmp_path)
    return TestClient(app)


@pytest.fixture
def empty_client(tmp_path):
    """Test client backed by an empty recipes directory."""
    app = create_app(recipes_dir=tmp_path)
    return TestClient(app)


# --- random endpoint ----------------------------------------------------------

class TestRandomEndpoint:
    def test_random_returns_recipe(self, populated):
        resp = populated.get("/api/recipes/random")
        assert resp.status_code == 200
        data = resp.json()
        assert "slug" in data
        assert "title" in data

    def test_random_404_on_empty(self, empty_client):
        resp = empty_client.get("/api/recipes/random")
        assert resp.status_code == 404

    def test_random_returns_valid_slug(self, populated):
        resp = populated.get("/api/recipes/random")
        data = resp.json()
        valid_slugs = {"quick-salad", "slow-braise", "never-cooked-pasta", "old-favorite-soup"}
        assert data["slug"] in valid_slugs


# --- sort=never-cooked --------------------------------------------------------

class TestNeverCooked:
    def test_filter_never_cooked(self, populated):
        resp = populated.get("/api/recipes?sort=never-cooked")
        assert resp.status_code == 200
        data = resp.json()
        slugs = [r["slug"] for r in data]
        # quick-salad and never-cooked-pasta have no cook history
        assert "quick-salad" in slugs
        assert "never-cooked-pasta" in slugs
        # These have cook history, should be excluded
        assert "slow-braise" not in slugs
        assert "old-favorite-soup" not in slugs

    def test_filter_never_cooked_with_tags(self, populated):
        resp = populated.get("/api/recipes?sort=never-cooked&tags=pasta")
        assert resp.status_code == 200
        data = resp.json()
        slugs = [r["slug"] for r in data]
        assert "never-cooked-pasta" in slugs
        # quick-salad does not have the pasta tag
        assert "quick-salad" not in slugs


# --- sort=least-recent --------------------------------------------------------

class TestLeastRecent:
    def test_filter_least_recent(self, populated):
        resp = populated.get("/api/recipes?sort=least-recent")
        assert resp.status_code == 200
        data = resp.json()
        slugs = [r["slug"] for r in data]
        # Only recipes WITH cook history should appear
        assert "old-favorite-soup" in slugs
        assert "slow-braise" in slugs
        # Never-cooked recipes should NOT appear
        assert "quick-salad" not in slugs
        assert "never-cooked-pasta" not in slugs

    def test_least_recent_order(self, populated):
        resp = populated.get("/api/recipes?sort=least-recent")
        data = resp.json()
        # old-favorite-soup last cooked 2025-07-01, slow-braise last cooked 2026-02-01
        assert data[0]["slug"] == "old-favorite-soup"
        assert data[1]["slug"] == "slow-braise"


# --- sort=quick ---------------------------------------------------------------

class TestQuick:
    def test_filter_quick(self, populated):
        resp = populated.get("/api/recipes?sort=quick")
        assert resp.status_code == 200
        data = resp.json()
        slugs = [r["slug"] for r in data]
        # quick-salad: 10+0 = 10 min, never-cooked-pasta: 5+15 = 20 min
        assert "quick-salad" in slugs
        assert "never-cooked-pasta" in slugs
        # slow-braise: 30+180 = 210 min, old-favorite-soup: 15+45 = 60 min
        assert "slow-braise" not in slugs
        assert "old-favorite-soup" not in slugs


# --- no sort (default) --------------------------------------------------------

class TestDefaultList:
    def test_no_sort_returns_all(self, populated):
        resp = populated.get("/api/recipes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4

    def test_no_sort_alphabetical(self, populated):
        resp = populated.get("/api/recipes")
        data = resp.json()
        titles = [r["title"] for r in data]
        assert titles == sorted(titles, key=str.lower)
