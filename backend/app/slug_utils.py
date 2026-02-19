"""Slug validation utilities.

Slugs are used to construct filesystem paths (e.g. ``recipes_dir / f"{slug}.md"``).
Without validation an attacker can supply a value such as ``../../etc/passwd`` and
read or overwrite arbitrary files on the server (path traversal / directory
traversal, CWE-22).

The safe allowlist ``^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$`` permits only
lowercase letters, digits, and hyphens — exactly the character set produced by the
``slugify()`` helper in ``generator.py`` — so all legitimately-created recipes
continue to work while every malicious value is rejected with HTTP 400.
"""

import re

from fastapi import HTTPException

# Allowlist: one or more lowercase alphanumeric characters or hyphens.
# Hyphens must not appear at the start or the end (a single character is fine).
_SLUG_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")

# Maximum length guard — slugs derived from recipe titles are never this long.
_SLUG_MAX_LEN = 200


def validate_slug(slug: str, field_name: str = "slug") -> str:
    """Validate *slug* against the safe allowlist and return it unchanged.

    Raises ``HTTPException(400)`` if the value contains any character that is
    not in ``[a-z0-9-]``, starts or ends with a hyphen, is empty, or exceeds
    the maximum allowed length.  This prevents path traversal attacks such as
    ``../../etc/passwd``, null-byte injection, and Windows-style traversals
    such as ``..\\secret``.

    Parameters
    ----------
    slug:
        The raw value received from the HTTP path parameter.
    field_name:
        Human-readable label used in the error message (e.g. ``"fork"``,
        ``"slug"``).

    Returns
    -------
    str
        The validated slug, identical to the input.
    """
    if not slug or len(slug) > _SLUG_MAX_LEN:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {field_name}: must be 1–{_SLUG_MAX_LEN} characters",
        )
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid {field_name}: only lowercase letters, digits, and "
                "hyphens are allowed (no leading/trailing hyphens)"
            ),
        )
    return slug
