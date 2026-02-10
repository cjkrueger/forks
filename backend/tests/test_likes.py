"""Tests for the like counter endpoint."""
import textwrap

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


class TestLike:
    def test_like_increments_count(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/test-soup/like")
        assert resp.status_code == 200
        assert resp.json()["likes"] == 1

        # Verify persisted to file
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert post.metadata["likes"] == 1

    def test_like_twice_gives_count_of_two(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/like")
        resp = client.post("/api/recipes/test-soup/like")
        assert resp.status_code == 200
        assert resp.json()["likes"] == 2

        # Verify persisted to file
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert post.metadata["likes"] == 2

    def test_like_not_found(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/nonexistent/like")
        assert resp.status_code == 404
