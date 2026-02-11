"""Ingredient parsing — Python port of frontend/src/lib/ingredients.ts."""

import re
from typing import Optional


UNIT_MAP = {
    "cup": "cup", "cups": "cup", "c": "cup",
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp": "tbsp", "tbs": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp", "tsp": "tsp",
    "ounce": "oz", "ounces": "oz", "oz": "oz",
    "pound": "lb", "pounds": "lb", "lb": "lb", "lbs": "lb",
    "gram": "g", "grams": "g", "g": "g",
    "kilogram": "kg", "kilograms": "kg", "kg": "kg",
    "liter": "l", "liters": "l", "l": "l",
    "milliliter": "ml", "milliliters": "ml", "ml": "ml",
    "pint": "pint", "pints": "pint",
    "quart": "quart", "quarts": "quart",
    "gallon": "gallon", "gallons": "gallon",
    "can": "can", "cans": "can",
    "clove": "clove", "cloves": "clove",
    "slice": "slice", "slices": "slice",
    "piece": "piece", "pieces": "piece",
    "bunch": "bunch", "bunches": "bunch",
    "head": "head", "heads": "head",
    "sprig": "sprig", "sprigs": "sprig",
    "pinch": "pinch",
    "dash": "dash",
    "stick": "stick", "sticks": "stick",
}

WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "half": 0.5, "a": 1, "an": 1,
}

UNICODE_FRACTIONS = {
    "\u00BC": 0.25, "\u00BD": 0.5, "\u00BE": 0.75,
    "\u2153": 1 / 3, "\u2154": 2 / 3, "\u2155": 1 / 5,
    "\u2156": 2 / 5, "\u2157": 3 / 5, "\u2158": 4 / 5,
    "\u2159": 1 / 6, "\u215A": 5 / 6, "\u215B": 1 / 8,
    "\u215C": 3 / 8, "\u215D": 5 / 8, "\u215E": 7 / 8,
}

PREP_WORDS_RE = re.compile(
    r",?\s*\b(diced|minced|chopped|sliced|thinly sliced|grated|shredded|crushed|"
    r"ground|melted|softened|warmed|cooled|room temperature|to taste|for garnish|"
    r"for serving|optional|divided|packed|sifted|peeled|seeded|trimmed|halved|"
    r"quartered|cubed|julienned|roughly chopped|finely chopped|finely diced|"
    r"finely minced)\b.*$",
    re.IGNORECASE,
)

PARENTHETICAL_RE = re.compile(r"\s*\([^)]*\)\s*")


def _parse_fraction(s: str) -> Optional[float]:
    """Parse a string that may contain fractions, mixed numbers, ranges, or unicode."""
    # Unicode fractions
    for char, val in UNICODE_FRACTIONS.items():
        if char in s:
            prefix = s.replace(char, "").strip()
            whole = float(prefix) if prefix else 0
            return whole + val

    # Mixed number: "2 1/2"
    m = re.match(r"^(\d+)\s+(\d+)/(\d+)$", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / int(m.group(3))

    # Simple fraction: "1/2"
    m = re.match(r"^(\d+)/(\d+)$", s)
    if m:
        return int(m.group(1)) / int(m.group(2))

    # Range: "2-3"
    m = re.match(r"^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$", s)
    if m:
        return float(m.group(2))

    # Plain number
    try:
        return float(s)
    except ValueError:
        return None


def parse_ingredient(line: str) -> dict:
    """Parse an ingredient line into structured data."""
    original = line.strip()
    text = original

    # Strip leading "- "
    text = re.sub(r"^-\s*", "", text)

    # Strip parentheticals for parsing
    parse_text = PARENTHETICAL_RE.sub(" ", text).strip()

    quantity: Optional[float] = None
    rest = parse_text

    # Check for word numbers first
    word_match = re.match(
        r"^(one|two|three|four|five|six|seven|eight|nine|ten|half|a|an)\b\s*",
        parse_text,
        re.IGNORECASE,
    )
    if word_match:
        word = word_match.group(1).lower()
        if word in WORD_NUMBERS:
            quantity = WORD_NUMBERS[word]
            rest = parse_text[word_match.end():]

    if quantity is None:
        # Try numeric patterns
        num_match = re.match(
            r"^(\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?|[^\x00-\x7f])",
            parse_text,
        )
        if num_match:
            parsed = _parse_fraction(num_match.group(1).strip())
            if parsed is not None:
                quantity = parsed
                rest = parse_text[num_match.end():].strip()

    # Try to extract unit
    unit: Optional[str] = None
    unit_match = re.match(r"^(\S+)\s+", rest)
    if unit_match:
        candidate = unit_match.group(1).lower().rstrip(".")
        if candidate in UNIT_MAP:
            unit = UNIT_MAP[candidate]
            rest = rest[unit_match.end():]

    # Strip "of " after unit
    rest = re.sub(r"^of\s+", "", rest, flags=re.IGNORECASE)

    display_text = rest.strip()

    # Name: stripped of prep words for aggregation
    stripped_rest = PREP_WORDS_RE.sub("", rest)
    stripped_rest = re.sub(r"[\s,\-\u2013\u2014]+$", "", stripped_rest).strip()
    name = stripped_rest.lower() if stripped_rest else display_text.lower()

    return {
        "quantity": quantity,
        "unit": unit,
        "name": name,
        "displayText": display_text,
        "original": original,
    }


def ingredient_key(parsed: dict) -> str:
    """Create a deduplication key for a parsed ingredient."""
    return f"{parsed.get('unit') or '_'}:{parsed['name']}"


def format_quantity(qty: float) -> str:
    """Format a quantity as a string, using fractions where possible."""
    if qty == int(qty):
        return str(int(qty))

    fractions = [
        (0.125, "1/8"), (0.25, "1/4"), (0.333, "1/3"), (0.375, "3/8"),
        (0.5, "1/2"), (0.625, "5/8"), (0.667, "2/3"), (0.75, "3/4"), (0.875, "7/8"),
    ]

    whole = int(qty)
    frac = qty - whole

    for val, s in fractions:
        if abs(frac - val) < 0.05:
            return f"{whole} {s}" if whole > 0 else s

    formatted = f"{qty:.1f}"
    return formatted.rstrip("0").rstrip(".")
