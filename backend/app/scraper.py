import ipaddress
import logging
import re
import socket
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse

import httpx
from recipe_scrapers import scrape_html

logger = logging.getLogger(__name__)

_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Private/reserved IP networks that must never be fetched
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),       # RFC 1918 private
    ipaddress.ip_network("172.16.0.0/12"),     # RFC 1918 private
    ipaddress.ip_network("192.168.0.0/16"),    # RFC 1918 private
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback (IPv4)
    ipaddress.ip_network("::1/128"),           # Loopback (IPv6)
    ipaddress.ip_network("fc00::/7"),          # IPv6 unique local
    ipaddress.ip_network("fe80::/10"),         # IPv6 link-local
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local (APIPA)
    ipaddress.ip_network("0.0.0.0/8"),         # "This" network
    ipaddress.ip_network("100.64.0.0/10"),     # Shared address space (RFC 6598)
    ipaddress.ip_network("192.0.0.0/24"),      # IANA special-purpose
    ipaddress.ip_network("198.18.0.0/15"),     # Benchmarking (RFC 2544)
    ipaddress.ip_network("198.51.100.0/24"),   # TEST-NET-2 (RFC 5737)
    ipaddress.ip_network("203.0.113.0/24"),    # TEST-NET-3 (RFC 5737)
    ipaddress.ip_network("240.0.0.0/4"),       # Reserved
    ipaddress.ip_network("255.255.255.255/32"),# Broadcast
]

_ALLOWED_SCHEMES = {"http", "https"}


class SSRFError(ValueError):
    """Raised when a URL is blocked for SSRF-protection reasons."""
    pass


def _is_private_ip(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True if the IP address falls within any blocked network."""
    for network in _BLOCKED_NETWORKS:
        try:
            if addr in network:
                return True
        except TypeError:
            # IPv4/IPv6 type mismatch — not in this network
            continue
    return False


def validate_url(url: str) -> None:
    """Validate a URL for SSRF safety.

    Checks:
    1. Scheme must be http or https.
    2. Hostname must not resolve to a private/internal IP (IPv4 or IPv6).
    3. Literal IP addresses in the URL are also checked.

    Raises SSRFError on any violation.
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise SSRFError(f"Invalid URL: {e}") from e

    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise SSRFError(
            f"URL scheme '{scheme}' is not allowed. Only http and https are permitted."
        )

    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("URL has no hostname.")

    # Reject bare 'localhost' (and variants) without DNS lookup
    if hostname.lower() in ("localhost", "ip6-localhost", "ip6-loopback"):
        raise SSRFError(f"Hostname '{hostname}' is not allowed.")

    # Resolve hostname to IP(s) and check each one
    try:
        # getaddrinfo returns all addresses (both IPv4 and IPv6)
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFError(f"Could not resolve hostname '{hostname}': {e}") from e

    if not addr_infos:
        raise SSRFError(f"Hostname '{hostname}' resolved to no addresses.")

    for addr_info in addr_infos:
        ip_str = addr_info[4][0]
        # Strip IPv6 zone IDs (e.g. "fe80::1%eth0" → "fe80::1")
        ip_str = ip_str.split("%")[0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            raise SSRFError(f"Could not parse resolved IP address: {ip_str}")

        if _is_private_ip(ip_obj):
            raise SSRFError(
                f"URL resolves to a private/internal IP address ({ip_obj}) and is not allowed."
            )


def scrape_recipe(url: str) -> Dict[str, Any]:
    """Scrape a recipe from a URL and return structured data."""
    result: Dict[str, Any] = {
        "title": None,
        "author": None,
        "ingredients": [],
        "instructions": [],
        "prep_time": None,
        "cook_time": None,
        "total_time": None,
        "servings": None,
        "image_url": None,
        "source": url,
        "notes": None,
    }

    # SSRF protection: validate before any network request
    validate_url(url)

    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": _BROWSER_UA},
        )
        response.raise_for_status()
        try:
            scraper = scrape_html(response.text, org_url=url)
        except Exception:
            # Site not explicitly supported — fall back to wild mode (JSON-LD/schema.org)
            scraper = scrape_html(response.text, org_url=url, wild_mode=True)
    except SSRFError:
        raise
    except Exception as e:
        # Direct fetch failed (e.g. 403) — let recipe_scrapers fetch the page itself
        logger.info(f"Direct fetch failed for {url}, trying online mode: {e}")
        try:
            scraper = scrape_html(None, org_url=url, online=True)
        except Exception as e2:
            logger.error(f"Failed to scrape {url}: {e2}")
            return result

    try:
        result["title"] = scraper.title()
    except Exception:
        pass

    try:
        result["ingredients"] = scraper.ingredients()
    except Exception:
        pass

    try:
        raw_instructions = scraper.instructions()
        if raw_instructions:
            result["instructions"] = [
                s.strip() for s in raw_instructions.split("\n") if s.strip()
            ]
    except Exception:
        pass

    try:
        prep = scraper.prep_time()
        if prep:
            result["prep_time"] = f"{prep}min"
    except Exception:
        pass

    try:
        cook = scraper.cook_time()
        if cook:
            result["cook_time"] = f"{cook}min"
    except Exception:
        pass

    try:
        total = scraper.total_time()
        if total:
            result["total_time"] = f"{total}min"
    except Exception:
        pass

    try:
        result["servings"] = str(scraper.yields())
    except Exception:
        pass

    try:
        image = scraper.image()
        if image:
            result["image_url"] = _upgrade_image_url(image)
    except Exception:
        pass

    try:
        author = scraper.author()
        if author:
            result["author"] = author
    except Exception:
        pass

    return result


def _upgrade_image_url(url: str) -> str:
    """Try to get the full-size image URL instead of a thumbnail.

    WordPress sites often serve thumbnails with dimension suffixes like
    '-225x225.jpg'. Stripping the suffix gives the full-size original.
    """
    upgraded = re.sub(r"-\d+x\d+(\.\w+)$", r"\1", url)
    if upgraded != url:
        try:
            resp = httpx.head(
                upgraded,
                follow_redirects=True,
                timeout=5.0,
                headers={"User-Agent": _BROWSER_UA},
            )
            if resp.status_code == 200:
                return upgraded
        except Exception:
            pass
    return url


def download_image(image_url: str, save_path: Path) -> bool:
    """Download an image from a URL and save it to disk."""
    try:
        response = httpx.get(
            image_url,
            follow_redirects=True,
            timeout=15.0,
            headers={"User-Agent": _BROWSER_UA},
        )
        response.raise_for_status()

        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_path.write_bytes(response.content)
        logger.info(f"Downloaded image to {save_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to download image from {image_url}: {e}")
        return False
