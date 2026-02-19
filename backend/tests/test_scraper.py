import socket
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import httpx
import pytest

from app.scraper import scrape_recipe, download_image, _check_redirect
from app.url_validator import SSRFError

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def _make_mock_scraper(
    title="Test Recipe",
    ingredients=None,
    instructions="Step one\nStep two\nStep three",
    prep_time=10,
    cook_time=25,
    total_time=35,
    yields="4 servings",
    image="https://example.com/image.jpg",
    author="Test Author",
):
    """Create a mock scraper object with configurable return values."""
    scraper = MagicMock()
    scraper.title.return_value = title
    scraper.ingredients.return_value = ingredients or ["1 cup flour", "2 eggs", "1 tsp salt"]
    scraper.instructions.return_value = instructions
    scraper.prep_time.return_value = prep_time
    scraper.cook_time.return_value = cook_time
    scraper.total_time.return_value = total_time
    scraper.yields.return_value = yields
    scraper.image.return_value = image
    scraper.author.return_value = author
    return scraper


# ---------------------------------------------------------------------------
# Normal scraping behaviour
# ---------------------------------------------------------------------------


@patch("app.scraper.scrape_html")
@patch("app.scraper.httpx.get")
def test_scrape_recipe_with_mock(mock_get, mock_scrape_html):
    """Full successful scrape returns all fields populated."""
    mock_response = MagicMock()
    mock_response.text = "<html>recipe page</html>"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    mock_scraper = _make_mock_scraper()
    mock_scrape_html.return_value = mock_scraper

    result = scrape_recipe("https://example.com/recipe")

    assert result["title"] == "Test Recipe"
    assert result["author"] == "Test Author"
    assert result["ingredients"] == ["1 cup flour", "2 eggs", "1 tsp salt"]
    assert result["instructions"] == ["Step one", "Step two", "Step three"]
    assert result["prep_time"] == "10min"
    assert result["cook_time"] == "25min"
    assert result["total_time"] == "35min"
    assert result["servings"] == "4 servings"
    assert result["image_url"] == "https://example.com/image.jpg"
    assert result["source"] == "https://example.com/recipe"

    # Verify event_hooks are passed for redirect protection
    args, kwargs = mock_get.call_args
    assert kwargs.get("follow_redirects") is True
    assert "event_hooks" in kwargs
    assert "response" in kwargs["event_hooks"]

    mock_scrape_html.assert_called_once_with(
        "<html>recipe page</html>", org_url="https://example.com/recipe"
    )


@patch("app.scraper.scrape_html")
@patch("app.scraper.httpx.get")
def test_scrape_recipe_handles_failure(mock_get, mock_scrape_html):
    """Network failure falls back to online mode; if that also fails, returns empty result."""
    mock_get.side_effect = httpx.ConnectError("Connection refused")
    mock_scrape_html.side_effect = Exception("Online mode also failed")

    result = scrape_recipe("https://bad-url.example.com/recipe")

    assert result["title"] is None
    assert result["author"] is None
    assert result["ingredients"] == []
    assert result["instructions"] == []
    assert result["prep_time"] is None
    assert result["cook_time"] is None
    assert result["total_time"] is None
    assert result["servings"] is None
    assert result["image_url"] is None
    assert result["source"] == "https://bad-url.example.com/recipe"
    assert result["notes"] is None


@patch("app.scraper.scrape_html")
@patch("app.scraper.httpx.get")
def test_scrape_recipe_handles_partial_data(mock_get, mock_scrape_html):
    """Scraper that only has title and ingredients still returns partial data."""
    mock_response = MagicMock()
    mock_response.text = "<html>partial recipe</html>"
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    scraper = MagicMock()
    scraper.title.return_value = "Partial Recipe"
    scraper.ingredients.return_value = ["some ingredient"]
    scraper.instructions.side_effect = Exception("not available")
    scraper.prep_time.side_effect = Exception("not available")
    scraper.cook_time.side_effect = Exception("not available")
    scraper.total_time.side_effect = Exception("not available")
    scraper.yields.side_effect = Exception("not available")
    scraper.image.side_effect = Exception("not available")
    scraper.author.side_effect = Exception("not available")
    mock_scrape_html.return_value = scraper

    result = scrape_recipe("https://example.com/partial")

    assert result["title"] == "Partial Recipe"
    assert result["author"] is None
    assert result["ingredients"] == ["some ingredient"]
    assert result["instructions"] == []
    assert result["prep_time"] is None
    assert result["cook_time"] is None
    assert result["total_time"] is None
    assert result["servings"] is None
    assert result["image_url"] is None
    assert result["source"] == "https://example.com/partial"


# ---------------------------------------------------------------------------
# SSRF protection: pre-request URL validation
# ---------------------------------------------------------------------------


@patch("app.scraper.httpx.get")
def test_scrape_recipe_blocks_private_ip(mock_get):
    """scrape_recipe raises SSRFError for a private IP without making any HTTP request."""
    with pytest.raises(SSRFError):
        scrape_recipe("http://192.168.1.100/secret")
    mock_get.assert_not_called()


@patch("app.scraper.httpx.get")
def test_scrape_recipe_blocks_localhost(mock_get):
    """scrape_recipe blocks localhost URLs and makes no HTTP request."""
    with pytest.raises(SSRFError):
        scrape_recipe("http://localhost:5000/api/admin")
    mock_get.assert_not_called()


@patch("app.scraper.httpx.get")
def test_scrape_recipe_blocks_loopback_ip(mock_get):
    """scrape_recipe blocks 127.x.x.x loopback addresses."""
    with pytest.raises(SSRFError):
        scrape_recipe("http://127.0.0.1/internal")
    mock_get.assert_not_called()


@patch("app.scraper.httpx.get")
def test_scrape_recipe_blocks_link_local(mock_get):
    """scrape_recipe blocks link-local / cloud metadata addresses."""
    with pytest.raises(SSRFError):
        scrape_recipe("http://169.254.169.254/latest/meta-data/")
    mock_get.assert_not_called()


@patch("app.scraper.httpx.get")
def test_scrape_recipe_blocks_file_scheme(mock_get):
    """scrape_recipe rejects file:// URLs."""
    with pytest.raises(SSRFError):
        scrape_recipe("file:///etc/passwd")
    mock_get.assert_not_called()


def test_scrape_recipe_blocks_hostname_resolving_to_private():
    """scrape_recipe blocks hostnames that resolve to private IPs."""
    with patch("app.url_validator.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(socket.AF_INET, None, None, None, ("10.0.0.1", 0))]
        with patch("app.scraper.httpx.get") as mock_get:
            with pytest.raises(SSRFError):
                scrape_recipe("http://internal.corp/secret")
            mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# SSRF protection: redirect validation hook
# ---------------------------------------------------------------------------


def test_check_redirect_passes_public_redirect():
    """_check_redirect allows redirects to public addresses."""
    response = MagicMock()
    response.is_redirect = True
    response.headers = {"location": "https://www.example.com/recipe"}
    response.url = httpx.URL("https://example.com/")

    with patch("app.url_validator.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(socket.AF_INET, None, None, None, ("93.184.216.34", 0))]
        # Should not raise
        _check_redirect(response)


def test_check_redirect_blocks_internal_redirect():
    """_check_redirect raises SSRFError when redirect targets a private address."""
    response = MagicMock()
    response.is_redirect = True
    response.headers = {"location": "http://192.168.1.1/data"}
    response.url = httpx.URL("https://example.com/recipe")

    with pytest.raises(SSRFError, match="Redirect"):
        _check_redirect(response)


def test_check_redirect_blocks_loopback_redirect():
    """_check_redirect raises SSRFError when redirect targets loopback."""
    response = MagicMock()
    response.is_redirect = True
    response.headers = {"location": "http://127.0.0.1/admin"}
    response.url = httpx.URL("https://example.com/recipe")

    with pytest.raises(SSRFError, match="Redirect"):
        _check_redirect(response)


def test_check_redirect_blocks_metadata_redirect():
    """_check_redirect raises SSRFError when redirect targets the cloud metadata IP."""
    response = MagicMock()
    response.is_redirect = True
    response.headers = {"location": "http://169.254.169.254/latest/meta-data/"}
    response.url = httpx.URL("https://example.com/recipe")

    with pytest.raises(SSRFError, match="Redirect"):
        _check_redirect(response)


def test_check_redirect_ignored_for_non_redirect():
    """_check_redirect is a no-op when response is not a redirect."""
    response = MagicMock()
    response.is_redirect = False
    # No exception should be raised even with a bad location header
    response.headers = {"location": "http://192.168.1.1/evil"}
    _check_redirect(response)  # Should be silent


# ---------------------------------------------------------------------------
# download_image
# ---------------------------------------------------------------------------


@patch("app.scraper.httpx.get")
def test_download_image_success(mock_get, tmp_path):
    """Successful image download saves file and returns True."""
    fake_image_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    mock_response = MagicMock()
    mock_response.content = fake_image_bytes
    mock_response.raise_for_status = MagicMock()
    mock_get.return_value = mock_response

    save_path = tmp_path / "images" / "recipe.png"
    result = download_image("https://example.com/photo.png", save_path)

    assert result is True
    assert save_path.exists()
    assert save_path.read_bytes() == fake_image_bytes

    # Verify event_hooks are passed for redirect protection
    args, kwargs = mock_get.call_args
    assert kwargs.get("follow_redirects") is True
    assert "event_hooks" in kwargs


@patch("app.scraper.httpx.get")
def test_download_image_failure(mock_get, tmp_path):
    """Failed image download returns False without crashing."""
    mock_get.side_effect = httpx.ConnectError("Connection refused")

    save_path = tmp_path / "images" / "recipe.png"
    result = download_image("https://bad-url.example.com/photo.png", save_path)

    assert result is False
    assert not save_path.exists()


@patch("app.scraper.httpx.get")
def test_download_image_blocks_private_ip(mock_get, tmp_path):
    """download_image returns False without fetching when URL is a private IP."""
    save_path = tmp_path / "image.jpg"
    result = download_image("http://10.0.0.5/image.jpg", save_path)
    assert result is False
    assert not save_path.exists()
    mock_get.assert_not_called()


@patch("app.scraper.httpx.get")
def test_download_image_blocks_localhost(mock_get, tmp_path):
    """download_image returns False without fetching for localhost URLs."""
    save_path = tmp_path / "image.jpg"
    result = download_image("http://localhost/image.jpg", save_path)
    assert result is False
    mock_get.assert_not_called()


@patch("app.scraper.httpx.get")
def test_download_image_blocks_redirect_to_internal(mock_get, tmp_path):
    """download_image returns False when a redirect hook fires for an internal address."""
    # Simulate the SSRFError being raised by the redirect hook during the GET
    mock_get.side_effect = SSRFError("Redirect to 'http://10.0.0.1/' was blocked")

    save_path = tmp_path / "image.jpg"
    result = download_image("https://example.com/image.jpg", save_path)
    assert result is False
    assert not save_path.exists()
