"""Tests for SSRF protection in url_validator.py"""

import socket
from unittest.mock import patch

import pytest

from app.url_validator import SSRFError, validate_url


# ---------------------------------------------------------------------------
# Scheme validation
# ---------------------------------------------------------------------------


def test_valid_http_url_passes():
    """Plain http URL to a public host is accepted."""
    # Use a mock so we don't make real DNS calls in tests
    with patch("app.url_validator.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(socket.AF_INET, None, None, None, ("93.184.216.34", 0))]
        result = validate_url("http://example.com/recipe")
    assert result == "http://example.com/recipe"


def test_valid_https_url_passes():
    """https URL to a public host is accepted."""
    with patch("app.url_validator.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(socket.AF_INET, None, None, None, ("93.184.216.34", 0))]
        result = validate_url("https://example.com/recipe")
    assert result == "https://example.com/recipe"


def test_ftp_scheme_blocked():
    """ftp:// scheme is rejected."""
    with pytest.raises(SSRFError, match="scheme"):
        validate_url("ftp://example.com/file")


def test_file_scheme_blocked():
    """file:// scheme is rejected."""
    with pytest.raises(SSRFError, match="scheme"):
        validate_url("file:///etc/passwd")


def test_data_scheme_blocked():
    """data: URL is rejected."""
    with pytest.raises(SSRFError, match="scheme"):
        validate_url("data:text/html,<h1>hi</h1>")


def test_javascript_scheme_blocked():
    """javascript: URL is rejected."""
    with pytest.raises(SSRFError, match="scheme"):
        validate_url("javascript:alert(1)")


def test_url_with_no_scheme_blocked():
    """URL with no scheme gets an empty scheme and is rejected."""
    with pytest.raises(SSRFError, match="scheme"):
        validate_url("//example.com/recipe")


# ---------------------------------------------------------------------------
# Missing hostname
# ---------------------------------------------------------------------------


def test_url_with_no_hostname_blocked():
    """URL missing a hostname is rejected."""
    with pytest.raises(SSRFError, match="hostname"):
        validate_url("http:///path")


# ---------------------------------------------------------------------------
# Blocked hostnames
# ---------------------------------------------------------------------------


def test_localhost_blocked():
    """'localhost' hostname is explicitly blocked before DNS."""
    with pytest.raises(SSRFError, match="localhost"):
        validate_url("http://localhost/admin")


def test_localhost_with_port_blocked():
    """localhost with a port is still blocked."""
    with pytest.raises(SSRFError, match="localhost"):
        validate_url("http://localhost:8080/admin")


def test_aws_metadata_hostname_blocked():
    """The AWS IMDS hostname is in the blocked list."""
    with pytest.raises(SSRFError, match="169.254.169.254"):
        validate_url("http://169.254.169.254/latest/meta-data/")


def test_google_metadata_hostname_blocked():
    """GCP internal metadata endpoint is blocked."""
    with pytest.raises(SSRFError, match="metadata.google.internal"):
        validate_url("http://metadata.google.internal/computeMetadata/v1/")


# ---------------------------------------------------------------------------
# IP literal — private ranges blocked without DNS
# ---------------------------------------------------------------------------


def test_loopback_ipv4_literal_blocked():
    """127.0.0.1 IP literal is rejected (loopback)."""
    with pytest.raises(SSRFError, match="127.0.0.1"):
        validate_url("http://127.0.0.1/secret")


def test_loopback_other_ipv4_blocked():
    """127.0.0.2 is also loopback and must be rejected."""
    with pytest.raises(SSRFError, match="127.0.0.2"):
        validate_url("http://127.0.0.2/secret")


def test_rfc1918_10_blocked():
    """10.0.0.1 (RFC 1918) is blocked."""
    with pytest.raises(SSRFError, match="10.0.0.1"):
        validate_url("http://10.0.0.1/internal")


def test_rfc1918_172_blocked():
    """172.16.0.1 (RFC 1918) is blocked."""
    with pytest.raises(SSRFError, match="172.16.0.1"):
        validate_url("http://172.16.0.1/internal")


def test_rfc1918_192_168_blocked():
    """192.168.1.1 (RFC 1918) is blocked."""
    with pytest.raises(SSRFError, match="192.168.1.1"):
        validate_url("http://192.168.1.1/router")


def test_link_local_ipv4_blocked():
    """169.254.x.x link-local is blocked (covers cloud metadata endpoints)."""
    with pytest.raises(SSRFError, match="169.254.0.1"):
        validate_url("http://169.254.0.1/")


def test_loopback_ipv6_literal_blocked():
    """IPv6 loopback ::1 is blocked."""
    with pytest.raises(SSRFError, match="::1"):
        validate_url("http://[::1]/secret")


def test_ula_ipv6_blocked():
    """Unique-local IPv6 (fc00::/7) is blocked."""
    with pytest.raises(SSRFError, match="fc00::1"):
        validate_url("http://[fc00::1]/")


def test_link_local_ipv6_blocked():
    """Link-local IPv6 (fe80::/10) is blocked."""
    with pytest.raises(SSRFError, match="fe80::1"):
        validate_url("http://[fe80::1]/")


def test_public_ipv4_literal_allowed():
    """A public IP literal like 1.1.1.1 (Cloudflare DNS) is allowed."""
    result = validate_url("http://1.1.1.1/")
    assert result == "http://1.1.1.1/"


def test_public_ipv6_literal_allowed():
    """A public IPv6 literal is allowed."""
    # 2606:4700:4700::1111 is Cloudflare's public DNS
    result = validate_url("http://[2606:4700:4700::1111]/")
    assert result == "http://[2606:4700:4700::1111]/"


# ---------------------------------------------------------------------------
# DNS resolution — resolved IP falls in blocked range
# ---------------------------------------------------------------------------


def test_hostname_resolving_to_loopback_blocked():
    """A hostname that resolves to 127.x.x.x is blocked."""
    with patch("app.url_validator.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(socket.AF_INET, None, None, None, ("127.0.0.1", 0))]
        with pytest.raises(SSRFError, match="127.0.0.1"):
            validate_url("http://evil-internal.example.com/")


def test_hostname_resolving_to_private_10_blocked():
    """A hostname that resolves to 10.x.x.x is blocked."""
    with patch("app.url_validator.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(socket.AF_INET, None, None, None, ("10.0.0.5", 0))]
        with pytest.raises(SSRFError, match="10.0.0.5"):
            validate_url("http://internal-service.corp/")


def test_hostname_resolving_to_link_local_blocked():
    """A hostname that resolves to 169.254.x.x is blocked (SSRF via DNS rebinding)."""
    with patch("app.url_validator.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(socket.AF_INET, None, None, None, ("169.254.169.254", 0))]
        with pytest.raises(SSRFError, match="169.254.169.254"):
            validate_url("http://metadata.attacker.com/")


def test_hostname_resolving_to_public_ip_allowed():
    """A hostname resolving to a public IP passes validation."""
    with patch("app.url_validator.socket.getaddrinfo") as mock_dns:
        mock_dns.return_value = [(socket.AF_INET, None, None, None, ("93.184.216.34", 0))]
        result = validate_url("https://www.example.com/recipe")
    assert result == "https://www.example.com/recipe"


def test_hostname_dns_failure_blocked():
    """An unresolvable hostname raises SSRFError (fail closed)."""
    with patch("app.url_validator.socket.getaddrinfo") as mock_dns:
        mock_dns.side_effect = socket.gaierror("Name or service not known")
        with pytest.raises(SSRFError, match="Could not resolve hostname"):
            validate_url("http://nonexistent.invalid/")


def test_all_resolved_addresses_must_be_public():
    """When a hostname resolves to multiple addresses, all must be public."""
    with patch("app.url_validator.socket.getaddrinfo") as mock_dns:
        # First address is public, second is private — should still be blocked
        mock_dns.return_value = [
            (socket.AF_INET, None, None, None, ("93.184.216.34", 0)),
            (socket.AF_INET, None, None, None, ("192.168.0.1", 0)),
        ]
        with pytest.raises(SSRFError, match="192.168.0.1"):
            validate_url("http://dual-homed.example.com/")


# ---------------------------------------------------------------------------
# Integration: scrape_recipe raises SSRFError for bad URLs
# ---------------------------------------------------------------------------


def test_scrape_recipe_raises_on_ssrf():
    """scrape_recipe propagates SSRFError without making any HTTP request."""
    from unittest.mock import patch as upatch

    from app.scraper import scrape_recipe

    with upatch("app.scraper.httpx.get") as mock_get:
        with pytest.raises(SSRFError):
            scrape_recipe("http://192.168.1.100/secret")
        mock_get.assert_not_called()


def test_scrape_recipe_raises_on_localhost():
    """scrape_recipe blocks localhost URLs."""
    from unittest.mock import patch as upatch

    from app.scraper import scrape_recipe

    with upatch("app.scraper.httpx.get") as mock_get:
        with pytest.raises(SSRFError):
            scrape_recipe("http://localhost:5000/api/admin")
        mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# Integration: download_image returns False for bad URLs
# ---------------------------------------------------------------------------


def test_download_image_returns_false_on_ssrf(tmp_path):
    """download_image returns False without fetching when URL is blocked."""
    from unittest.mock import patch as upatch

    from app.scraper import download_image

    save_path = tmp_path / "image.jpg"
    with upatch("app.scraper.httpx.get") as mock_get:
        result = download_image("http://10.0.0.5/image.jpg", save_path)
    assert result is False
    assert not save_path.exists()
    mock_get.assert_not_called()
