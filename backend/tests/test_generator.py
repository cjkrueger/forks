import datetime
from unittest.mock import patch

from app.generator import RecipeInput, generate_markdown, slugify


# ---------------------------------------------------------------------------
# slugify tests
# ---------------------------------------------------------------------------

def test_slugify_basic():
    assert slugify("Birria Tacos") == "birria-tacos"


def test_slugify_special_characters():
    assert slugify("Birria Tacos (Mom's Recipe!)") == "birria-tacos-moms-recipe"


def test_slugify_multiple_hyphens():
    assert slugify("One -- Two --- Three") == "one-two-three"


def test_slugify_leading_trailing_special():
    assert slugify("!Hello World!") == "hello-world"


def test_slugify_already_clean():
    assert slugify("simple-slug") == "simple-slug"


def test_slugify_numbers():
    assert slugify("Top 10 Recipes") == "top-10-recipes"


def test_slugify_empty_string():
    assert slugify("") == ""


# ---------------------------------------------------------------------------
# generate_markdown tests — full recipe
# ---------------------------------------------------------------------------

FAKE_TODAY = datetime.date(2026, 2, 9)


def _full_input() -> RecipeInput:
    return RecipeInput(
        title="Birria Tacos",
        tags=["mexican", "beef", "tacos"],
        servings="6",
        prep_time="30min",
        cook_time="3hr",
        source="https://example.com/birria-tacos",
        image="images/birria-tacos.jpg",
        ingredients=[
            "3 lbs chuck roast",
            "4 dried guajillo chiles",
        ],
        instructions=[
            "Toast the chiles in a dry skillet until fragrant.",
            "Blend soaked chiles with tomatoes and spices.",
        ],
        notes=[
            "The consomé is the star",
            "Works great in a slow cooker: 8 hours on low",
        ],
    )


@patch("app.generator.datetime")
def test_full_recipe(mock_dt):
    mock_dt.date.today.return_value = FAKE_TODAY
    mock_dt.side_effect = lambda *a, **kw: datetime.datetime(*a, **kw)

    md = generate_markdown(_full_input())

    # Frontmatter assertions
    assert md.startswith("---\n")
    assert "title: Birria Tacos" in md
    assert "source: https://example.com/birria-tacos" in md
    assert "tags: [mexican, beef, tacos]" in md
    assert "servings: 6" in md
    assert "prep_time: 30min" in md
    assert "cook_time: 3hr" in md
    assert "date_added: 2026-02-09" in md
    assert "image: images/birria-tacos.jpg" in md

    # Body assertions
    assert "# Birria Tacos" in md
    assert "## Ingredients" in md
    assert "- 3 lbs chuck roast" in md
    assert "- 4 dried guajillo chiles" in md
    assert "## Instructions" in md
    assert "1. Toast the chiles" in md
    assert "2. Blend soaked chiles" in md
    assert "## Notes" in md
    assert "- The consomé is the star" in md


# ---------------------------------------------------------------------------
# generate_markdown tests — no notes
# ---------------------------------------------------------------------------

@patch("app.generator.datetime")
def test_no_notes_section_omitted(mock_dt):
    mock_dt.date.today.return_value = FAKE_TODAY

    data = _full_input()
    data.notes = []
    md = generate_markdown(data)

    assert "## Notes" not in md


# ---------------------------------------------------------------------------
# generate_markdown tests — no image
# ---------------------------------------------------------------------------

@patch("app.generator.datetime")
def test_no_image_field_omitted(mock_dt):
    mock_dt.date.today.return_value = FAKE_TODAY

    data = _full_input()
    data.image = None
    md = generate_markdown(data)

    assert "image:" not in md


# ---------------------------------------------------------------------------
# generate_markdown tests — empty ingredients and instructions
# ---------------------------------------------------------------------------

@patch("app.generator.datetime")
def test_empty_ingredients_and_instructions(mock_dt):
    mock_dt.date.today.return_value = FAKE_TODAY

    data = RecipeInput(title="Empty Recipe")
    md = generate_markdown(data)

    # Should still contain the section headers
    assert "## Ingredients" in md
    assert "## Instructions" in md
    # No list items under either section
    assert "- " not in md.split("## Instructions")[0].split("## Ingredients")[1]
    # No notes section
    assert "## Notes" not in md


# ---------------------------------------------------------------------------
# generate_markdown tests — date_added is automatic
# ---------------------------------------------------------------------------

@patch("app.generator.datetime")
def test_date_added_is_automatic(mock_dt):
    mock_dt.date.today.return_value = datetime.date(2030, 12, 25)

    data = RecipeInput(title="Holiday Special")
    md = generate_markdown(data)

    assert "date_added: 2030-12-25" in md


# ---------------------------------------------------------------------------
# generate_markdown tests — optional frontmatter fields skipped when empty
# ---------------------------------------------------------------------------

@patch("app.generator.datetime")
def test_optional_frontmatter_fields_skipped(mock_dt):
    mock_dt.date.today.return_value = FAKE_TODAY

    data = RecipeInput(title="Minimal Recipe")
    md = generate_markdown(data)

    assert "title: Minimal Recipe" in md
    assert "date_added:" in md
    # None of the optional fields should appear
    assert "source:" not in md
    assert "tags:" not in md
    assert "servings:" not in md
    assert "prep_time:" not in md
    assert "cook_time:" not in md
    assert "image:" not in md


# ---------------------------------------------------------------------------
# generate_markdown tests — trailing newline
# ---------------------------------------------------------------------------

@patch("app.generator.datetime")
def test_output_ends_with_newline(mock_dt):
    mock_dt.date.today.return_value = FAKE_TODAY

    md = generate_markdown(_full_input())
    assert md.endswith("\n")
