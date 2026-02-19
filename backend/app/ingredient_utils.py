"""Shared ingredient parsing utilities.

Constants and helpers used by both the normalizer (pre-storage string
normalization) and the structured ingredient parser.
"""

# Canonical word-to-float mapping for English number words that appear in
# recipe ingredient lines.  Both the normalizer and the structured parser
# derive their own lookups from this single source of truth.
WORD_NUMBER_FLOATS: dict[str, float] = {
    "a": 1.0,
    "an": 1.0,
    "half": 0.5,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
    "eleven": 11.0,
    "twelve": 12.0,
}

# String representations used by the normalizer when rewriting scraped text.
# Fractions are kept as strings (e.g. "1/2") so the output reads naturally.
WORD_NUMBER_STRINGS: dict[str, str] = {
    word: ("1/2" if val == 0.5 else str(int(val)))
    for word, val in WORD_NUMBER_FLOATS.items()
}

# Regex alternation of all recognised word-number tokens, longest first so
# that partial matches (e.g. "an" inside "one") are avoided.
_WORD_NUMBERS_SORTED = sorted(WORD_NUMBER_FLOATS.keys(), key=len, reverse=True)
WORD_NUMBER_PATTERN: str = "|".join(_WORD_NUMBERS_SORTED)
