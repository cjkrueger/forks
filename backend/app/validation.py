"""Shared validation utilities for route parameters."""

import re

from fastapi import HTTPException, Path

# Valid slug: alphanumeric and hyphens only, 1–200 characters
_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,198}[a-z0-9]$|^[a-z0-9]$")


def is_valid_slug(slug: str) -> bool:
    """Return True if *slug* is a safe, well-formed recipe slug.

    Accepts only lowercase alphanumeric characters and hyphens.  Explicitly
    rejects any value that contains ``/``, ``\\``, or ``..`` (path traversal
    sequences), or that starts/ends with a hyphen.
    """
    if not slug:
        return False
    # Fast-reject path separators and traversal sequences before the regex
    if "/" in slug or "\\" in slug or ".." in slug:
        return False
    return bool(_SLUG_RE.match(slug))


def validate_slug(slug: str) -> str:
    """Raise HTTP 400 if *slug* is not a valid recipe slug, else return it."""
    if not is_valid_slug(slug):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid slug. Slugs may only contain lowercase letters, digits, "
                "and hyphens, and must not start or end with a hyphen."
            ),
        )
    return slug


# ---------------------------------------------------------------------------
# FastAPI path-parameter dependency
# ---------------------------------------------------------------------------

def SlugPath(description: str = "Recipe slug") -> str:  # noqa: N802  (matches FastAPI convention)
    """FastAPI ``Path`` dependency that validates a ``{slug}`` path parameter."""
    return Path(..., description=description, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$")
