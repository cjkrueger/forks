import ipaddress
import socket
from pathlib import Path
from unittest.mock import patch, MagicMock

import httpx
import pytest

from app.scraper import scrape_recipe, download_image, validate_url, SSRFError


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
# validate_url — SSRF protection tests
# ---------------------------------------------------------------------------

class TestValidateUrl:
    """Tests for the SSRF-protection URL validator."""

    # --- scheme checks ---

    def test_http_scheme_allowed(self):
        """http:// URLs with a public hostname are allowed."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 0))]
            validate_url("http://example.com/recipe")  # should not raise

    def test_https_scheme_allowed(self):
        """https:// URLs with a public hostname are allowed."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 0))]
            validate_url("https://example.com/recipe")  # should not raise

    def test_ftp_scheme_rejected(self):
        """ftp:// URLs must be rejected."""
        with pytest.raises(SSRFError, match="scheme"):
            validate_url("ftp://example.com/file.txt")

    def test_file_scheme_rejected(self):
        """file:// URLs must be rejected (local file access)."""
        with pytest.raises(SSRFError, match="scheme"):
            validate_url("file:///etc/passwd")

    def test_gopher_scheme_rejected(self):
        """gopher:// URLs must be rejected."""
        with pytest.raises(SSRFError, match="scheme"):
            validate_url("gopher://example.com")

    def test_empty_scheme_rejected(self):
        """URLs without a scheme must be rejected."""
        with pytest.raises(SSRFError):
            validate_url("//example.com/recipe")

    # --- localhost / loopback ---

    def test_localhost_hostname_rejected(self):
        """'localhost' hostname must be rejected without DNS lookup."""
        with pytest.raises(SSRFError, match="not allowed"):
            validate_url("http://localhost/admin")

    def test_localhost_uppercase_rejected(self):
        """'LOCALHOST' (case-insensitive) must be rejected."""
        with pytest.raises(SSRFError, match="not allowed"):
            validate_url("http://LOCALHOST/admin")

    def test_127_0_0_1_rejected(self):
        """Literal 127.0.0.1 must be rejected (loopback)."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
            with pytest.raises(SSRFError, match="private/internal"):
                validate_url("http://127.0.0.1/secret")

    def test_127_0_0_2_rejected(self):
        """Any 127.x.x.x address must be rejected (loopback range)."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("127.0.0.2", 0))]
            with pytest.raises(SSRFError, match="private/internal"):
                validate_url("http://127.0.0.2/")

    def test_ipv6_loopback_rejected(self):
        """IPv6 loopback ::1 must be rejected."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("::1", 0))]
            with pytest.raises(SSRFError, match="private/internal"):
                validate_url("http://[::1]/secret")

    # --- RFC 1918 private ranges ---

    def test_10_x_rejected(self):
        """10.0.0.0/8 addresses must be rejected."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("10.1.2.3", 0))]
            with pytest.raises(SSRFError, match="private/internal"):
                validate_url("http://internal.example.com/")

    def test_172_16_rejected(self):
        """172.16.0.0/12 addresses must be rejected."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("172.20.0.1", 0))]
            with pytest.raises(SSRFError, match="private/internal"):
                validate_url("http://internal.corp/resource")

    def test_172_31_rejected(self):
        """172.31.255.255 (last address of 172.16/12) must be rejected."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("172.31.255.255", 0))]
            with pytest.raises(SSRFError, match="private/internal"):
                validate_url("http://internal.corp/resource")

    def test_172_15_allowed(self):
        """172.15.x.x is NOT in the 172.16/12 range and should be allowed."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("172.15.0.1", 0))]
            validate_url("https://example.com/recipe")  # should not raise

    def test_192_168_rejected(self):
        """192.168.0.0/16 addresses must be rejected."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("192.168.1.100", 0))]
            with pytest.raises(SSRFError, match="private/internal"):
                validate_url("http://router.local/api")

    # --- link-local ---

    def test_169_254_rejected(self):
        """169.254.x.x (APIPA / link-local) must be rejected."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("169.254.169.254", 0))]
            with pytest.raises(SSRFError, match="private/internal"):
                validate_url("http://metadata.example.com/latest/meta-data/")

    # --- DNS rebinding: hostname resolves to private IP ---

    def test_dns_rebinding_blocked(self):
        """A hostname that resolves to an internal IP must be rejected."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            # e.g. attacker.com → 192.168.1.1
            mock_dns.return_value = [(None, None, None, None, ("192.168.1.1", 0))]
            with pytest.raises(SSRFError, match="private/internal"):
                validate_url("https://totally-legit.attacker.com/recipe")

    def test_dns_resolution_failure_raises(self):
        """If DNS resolution fails, SSRFError is raised (fail-closed)."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.side_effect = socket.gaierror("Name or service not known")
            with pytest.raises(SSRFError, match="Could not resolve"):
                validate_url("https://nonexistent.invalid/recipe")

    # --- public IPs are allowed ---

    def test_public_ipv4_allowed(self):
        """A public IPv4 address must be allowed."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 0))]
            validate_url("https://example.com/recipe")  # should not raise

    def test_public_ipv6_allowed(self):
        """A public IPv6 address must be allowed."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("2606:2800:220:1:248:1893:25c8:1946", 0))]
            validate_url("https://example.com/recipe")  # should not raise

    def test_multiple_resolved_ips_one_private_rejected(self):
        """If any resolved IP is private, the whole URL is rejected."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (None, None, None, None, ("93.184.216.34", 0)),  # public
                (None, None, None, None, ("10.0.0.1", 0)),       # private!
            ]
            with pytest.raises(SSRFError, match="private/internal"):
                validate_url("https://suspicious.example.com/recipe")


# ---------------------------------------------------------------------------
# scrape_recipe — integration with URL validation
# ---------------------------------------------------------------------------

class TestScrapeRecipeSSRF:
    """Tests that scrape_recipe rejects blocked URLs before fetching."""

    def test_scrape_recipe_rejects_localhost(self):
        """scrape_recipe must raise SSRFError for localhost URLs."""
        with pytest.raises(SSRFError):
            scrape_recipe("http://localhost/admin")

    def test_scrape_recipe_rejects_private_ip(self):
        """scrape_recipe must raise SSRFError when DNS resolves to private IP."""
        with patch("app.scraper.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("192.168.1.1", 0))]
            with pytest.raises(SSRFError):
                scrape_recipe("https://internal.corp/recipe")

    def test_scrape_recipe_rejects_file_scheme(self):
        """scrape_recipe must raise SSRFError for file:// URLs."""
        with pytest.raises(SSRFError, match="scheme"):
            scrape_recipe("file:///etc/passwd")

    @patch("app.scraper.socket.getaddrinfo")
    @patch("app.scraper.scrape_html")
    @patch("app.scraper.httpx.get")
    def test_scrape_recipe_allows_public_url(self, mock_get, mock_scrape_html, mock_dns):
        """scrape_recipe proceeds normally for public URLs."""
        mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 0))]

        mock_response = MagicMock()
        mock_response.text = "<html>recipe page</html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        mock_scraper = _make_mock_scraper()
        mock_scrape_html.return_value = mock_scraper

        result = scrape_recipe("https://example.com/recipe")

        assert result["title"] == "Test Recipe"
        assert result["source"] == "https://example.com/recipe"


# ---------------------------------------------------------------------------
# Existing scraper tests (unchanged behaviour)
# ---------------------------------------------------------------------------

@patch("app.scraper.socket.getaddrinfo")
@patch("app.scraper.scrape_html")
@patch("app.scraper.httpx.get")
def test_scrape_recipe_with_mock(mock_get, mock_scrape_html, mock_dns):
    """Full successful scrape returns all fields populated."""
    mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 0))]

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

    mock_get.assert_called_once_with(
        "https://example.com/recipe",
        follow_redirects=True,
        timeout=15.0,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    )
    mock_scrape_html.assert_called_once_with(
        "<html>recipe page</html>", org_url="https://example.com/recipe"
    )


@patch("app.scraper.socket.getaddrinfo")
@patch("app.scraper.scrape_html")
@patch("app.scraper.httpx.get")
def test_scrape_recipe_handles_failure(mock_get, mock_scrape_html, mock_dns):
    """Network failure falls back to online mode; if that also fails, returns empty result."""
    mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 0))]
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


@patch("app.scraper.socket.getaddrinfo")
@patch("app.scraper.scrape_html")
@patch("app.scraper.httpx.get")
def test_scrape_recipe_handles_partial_data(mock_get, mock_scrape_html, mock_dns):
    """Scraper that only has title and ingredients still returns partial data."""
    mock_dns.return_value = [(None, None, None, None, ("93.184.216.34", 0))]

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

    mock_get.assert_called_once_with(
        "https://example.com/photo.png",
        follow_redirects=True,
        timeout=15.0,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"},
    )


@patch("app.scraper.httpx.get")
def test_download_image_failure(mock_get, tmp_path):
    """Failed image download returns False without crashing."""
    mock_get.side_effect = httpx.ConnectError("Connection refused")

    save_path = tmp_path / "images" / "recipe.png"
    result = download_image("https://bad-url.example.com/photo.png", save_path)

    assert result is False
    assert not save_path.exists()
