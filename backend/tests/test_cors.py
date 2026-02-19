"""Tests for CORS middleware configuration."""

import subprocess
import textwrap
from unittest import mock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


SIMPLE_RECIPE = textwrap.dedent("""\
    ---
    title: Simple Soup
    tags: [soup]
    ---

    # Simple Soup

    ## Ingredients

    - 1 cup water

    ## Instructions

    1. Boil water.
""")


@pytest.fixture
def tmp_recipes(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "simple-soup.md").write_text(SIMPLE_RECIPE)

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


def test_cors_headers_present_with_wildcard_default(client):
    """Default config (allow *) should include CORS headers on preflight."""
    resp = client.options(
        "/api/recipes",
        headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.headers.get("access-control-allow-origin") in ("*", "http://example.com")


def test_cors_allow_origin_on_regular_request(client):
    """Regular requests from an origin should receive the CORS header."""
    resp = client.get(
        "/api/recipes",
        headers={"Origin": "http://192.168.1.10:3000"},
    )
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


def test_cors_specific_origin(tmp_recipes):
    """When CORS_ORIGINS is set to a specific origin, that origin is reflected."""
    with mock.patch("app.config.settings") as mock_settings:
        mock_settings.cors_origins = ["http://192.168.1.10:3000"]
        mock_settings.recipes_dir = tmp_recipes

        app = create_app(recipes_dir=tmp_recipes)
        restricted_client = TestClient(app)

    resp = restricted_client.get(
        "/api/recipes",
        headers={"Origin": "http://192.168.1.10:3000"},
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://192.168.1.10:3000"


def test_cors_origins_env_var_parsing():
    """FORKS_CORS_ORIGINS env var should be parsed from a comma-separated string."""
    from app.config import Settings

    s = Settings(cors_origins="http://foo.local,http://bar.local:3000")  # type: ignore[call-arg]
    assert s.cors_origins == ["http://foo.local", "http://bar.local:3000"]


def test_cors_origins_default_is_wildcard():
    """Default cors_origins should be ['*'] for self-hosted deployments."""
    from app.config import Settings

    s = Settings()
    assert s.cors_origins == ["*"]
