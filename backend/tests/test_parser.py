from pathlib import Path
from app.parser import parse_recipe, parse_frontmatter


SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "recipes"


def test_parse_frontmatter_extracts_metadata():
    result = parse_frontmatter(SAMPLE_DIR / "birria-tacos.md")
    assert result.slug == "birria-tacos"
    assert result.title == "Birria Tacos"
    assert "mexican" in result.tags
    assert "beef" in result.tags
    assert result.servings == "6"
    assert result.prep_time == "30min"
    assert result.cook_time == "3hr"
    assert result.source == "https://example.com/birria-tacos"
    assert result.image == "images/birria-tacos.jpg"


def test_parse_recipe_includes_content():
    result = parse_recipe(SAMPLE_DIR / "birria-tacos.md")
    assert result.slug == "birria-tacos"
    assert result.title == "Birria Tacos"
    assert "## Ingredients" in result.content
    assert "chuck roast" in result.content
    assert "## Instructions" in result.content


def test_parse_recipe_without_image():
    result = parse_recipe(SAMPLE_DIR / "pasta-carbonara.md")
    assert result.slug == "pasta-carbonara"
    assert result.image is None


def test_parse_frontmatter_coerces_servings_to_string():
    """Servings in YAML may parse as int, we want string."""
    result = parse_frontmatter(SAMPLE_DIR / "birria-tacos.md")
    assert isinstance(result.servings, str)


def test_parse_recipe_malformed_file(tmp_path):
    """A file with no frontmatter should still parse without crashing."""
    bad_file = tmp_path / "bad-recipe.md"
    bad_file.write_text("# Just a title\n\nSome content without frontmatter.\n")
    result = parse_recipe(bad_file)
    assert result.slug == "bad-recipe"
    assert result.title == "bad-recipe"
    assert result.tags == []
    assert "Just a title" in result.content
