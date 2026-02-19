"""Normalize scraped ingredient strings into consistent display format."""

import re

from app.ingredient_utils import WORD_NUMBER_STRINGS as WORD_NUMBERS, WORD_NUMBER_PATTERN

# Container words (singular forms — plurals handled by regex)
CONTAINER_WORDS = (
    "can", "bag", "box", "bottle", "jar",
    "package", "packet", "container", "carton",
    "pouch", "tube",
)

# Build a regex alternation for container words (singular + plural)
_container_alt = "|".join(
    rf"{w}s?" for w in CONTAINER_WORDS
)

# --- Pass 1: Compound container ---
# Matches: "One 15-ounce can", "two 8.5-ounce bags", "a 12-oz bottle", "one 12 oz can"
# Groups: (word_number) (digits[.digits]) (-?)(ounce|oz) (container)
_compound_re = re.compile(
    rf"(?i)\b({WORD_NUMBER_PATTERN})\s+"    # word number
    rf"(\d+(?:\.\d+)?)"                     # numeric size
    rf"[- ]?"                               # optional hyphen or space
    rf"(?:ounces?|oz\.?)"                   # unit (ounce/ounces/oz/oz.)
    rf"\s+({_container_alt})\b",            # container word
)


def _compound_repl(m: re.Match) -> str:
    num = WORD_NUMBERS[m.group(1).lower()]
    size = m.group(2)
    container = m.group(3)
    return f"{num} ({size} ounce) {container}"


# --- Pass 2: Hyphenated mixed number ---
# Matches "1-1/2" but NOT "2-3" (range) — only when fraction follows the hyphen
_hyphenated_re = re.compile(
    r"\b(\d+)-(\d+/\d+)\b"
)


def _hyphenated_repl(m: re.Match) -> str:
    return f"{m.group(1)} {m.group(2)}"


# --- Pass 3: Simple word number at start of string ---
# Matches word numbers at the beginning of the ingredient line
_simple_word_re = re.compile(
    rf"(?i)^({WORD_NUMBER_PATTERN})\b(\s+(?:a|an)\b)?",
)


def _simple_word_repl(m: re.Match) -> str:
    num = WORD_NUMBERS[m.group(1).lower()]
    # "half a cup" → "1/2 cup" (strip the "a"/"an" after half)
    if m.group(1).lower() == "half" and m.group(2):
        return num
    return num


def normalize_ingredient(s: str) -> str:
    """Normalize a single ingredient string.

    Three sequential passes:
    1. Compound container: "One 15-ounce can beans" → "1 (15 ounce) can beans"
    2. Hyphenated mixed number: "1-1/2 cups" → "1 1/2 cups"
    3. Simple word number at start: "one cup flour" → "1 cup flour"
    """
    s = s.strip()
    if not s:
        return s

    # Pass 1: compound container amounts
    s = _compound_re.sub(_compound_repl, s)

    # Pass 2: hyphenated mixed numbers
    s = _hyphenated_re.sub(_hyphenated_repl, s)

    # Pass 3: simple word number at start
    s = _simple_word_re.sub(_simple_word_repl, s)

    return s


def normalize_ingredients(items: list[str]) -> list[str]:
    """Normalize a list of ingredient strings."""
    return [normalize_ingredient(item) for item in items]
