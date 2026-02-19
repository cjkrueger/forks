"""
SSRF protection utilities for validating URLs before server-side fetching.

Blocks requests to private/internal IP ranges, loopback addresses, link-local
addresses, and other non-routable destinations that could be used to probe
internal services.
"""

import ipaddress
import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Only these schemes are safe to fetch
_ALLOWED_SCHEMES = {"http", "https"}

# Private, loopback, link-local, and other non-routable IPv4 ranges
_BLOCKED_IPV4_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),        # "This" network
    ipaddress.ip_network("10.0.0.0/8"),        # RFC 1918 private
    ipaddress.ip_network("100.64.0.0/10"),     # Shared address space (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),       # Loopback
    ipaddress.ip_network("169.254.0.0/16"),    # Link-local / AWS metadata
    ipaddress.ip_network("172.16.0.0/12"),     # RFC 1918 private
    ipaddress.ip_network("192.0.0.0/24"),      # IETF protocol assignments
    ipaddress.ip_network("192.168.0.0/16"),    # RFC 1918 private
    ipaddress.ip_network("198.18.0.0/15"),     # Benchmarking (RFC 2544)
    ipaddress.ip_network("198.51.100.0/24"),   # TEST-NET-2 (RFC 5737)
    ipaddress.ip_network("203.0.113.0/24"),    # TEST-NET-3 (RFC 5737)
    ipaddress.ip_network("240.0.0.0/4"),       # Reserved
    ipaddress.ip_network("255.255.255.255/32"),# Broadcast
]

# Private and loopback IPv6 ranges
_BLOCKED_IPV6_NETWORKS = [
    ipaddress.ip_network("::1/128"),           # Loopback
    ipaddress.ip_network("::/128"),            # Unspecified
    ipaddress.ip_network("fc00::/7"),          # Unique local (ULA)
    ipaddress.ip_network("fe80::/10"),         # Link-local
    ipaddress.ip_network("::ffff:0:0/96"),     # IPv4-mapped
]

# Hostnames that should never be fetched
_BLOCKED_HOSTNAMES = {
    "localhost",
    "ip6-localhost",
    "ip6-loopback",
    "broadcasthost",
    # Common internal metadata endpoints
    "metadata.google.internal",
    "169.254.169.254",  # AWS/GCP/Azure IMDS
}


class SSRFError(ValueError):
    """Raised when a URL is blocked due to SSRF risk."""
    pass


def _is_ip_blocked(addr: str) -> bool:
    """Return True if the IP address falls in a blocked network range."""
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        # Not a valid IP address string; let the caller handle it
        return False

    if isinstance(ip, ipaddress.IPv4Address):
        return any(ip in net for net in _BLOCKED_IPV4_NETWORKS)
    else:
        return any(ip in net for net in _BLOCKED_IPV6_NETWORKS)


def validate_url(url: str) -> str:
    """
    Validate a URL for safe server-side fetching.

    Checks:
    - Scheme is http or https
    - Hostname is present and not a blocked name
    - Resolved IP address is not in a private/internal range

    Returns the original URL if valid, raises SSRFError if blocked.
    """
    try:
        parsed = urlparse(url)
    except Exception as exc:
        raise SSRFError(f"Malformed URL: {exc}") from exc

    # 1. Scheme check
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise SSRFError(
            f"URL scheme '{scheme}' is not allowed. Only http and https are permitted."
        )

    # 2. Hostname must be present
    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("URL has no hostname.")

    # Normalize: strip brackets from IPv6 literals (urlparse includes them)
    hostname = hostname.strip("[]").lower()

    # 3. Blocked hostname check (before DNS resolution)
    if hostname in _BLOCKED_HOSTNAMES:
        raise SSRFError(f"Requests to '{hostname}' are not allowed.")

    # 4. If hostname is already an IP literal, check it directly
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if _is_ip_blocked(str(ip_obj)):
            raise SSRFError(
                f"Requests to IP address '{ip_obj}' are not allowed (private/internal range)."
            )
        # It's a valid public IP literal — no DNS needed
        return url
    except ValueError:
        pass  # Not an IP literal — fall through to DNS resolution

    # 5. DNS resolution: check every address the hostname resolves to
    try:
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise SSRFError(f"Could not resolve hostname '{hostname}': {exc}") from exc

    if not results:
        raise SSRFError(f"Hostname '{hostname}' did not resolve to any address.")

    for family, _type, _proto, _canonname, sockaddr in results:
        addr = sockaddr[0]  # (ip, port) or (ip, port, flow, scope)
        if _is_ip_blocked(addr):
            raise SSRFError(
                f"Hostname '{hostname}' resolves to '{addr}', which is in a "
                "private/internal IP range. Request blocked."
            )

    return url
