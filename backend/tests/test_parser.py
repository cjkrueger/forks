from pathlib import Path
from app.parser import parse_recipe, parse_frontmatter


SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "recipes"


def test_parse_frontmatter_extracts_metadata():
    result = parse_frontmatter(SAMPLE_DIR / "chicken-tikka-masala.md")
    assert result.slug == "chicken-tikka-masala"
    assert result.title == "Chicken Tikka Masala"
    assert "chicken" in result.tags
    assert "indian" in result.tags
    assert result.servings == "4 servings"
    assert result.prep_time == "30min"
    assert result.cook_time == "50min"
    assert result.source == "https://www.thekitchn.com/chicken-tikka-masala-recipe-23686912"
    assert result.image == "images/chicken-tikka-masala.jpg"


def test_parse_recipe_includes_content():
    result = parse_recipe(SAMPLE_DIR / "chicken-tikka-masala.md")
    assert result.slug == "chicken-tikka-masala"
    assert result.title == "Chicken Tikka Masala"
    assert "## Ingredients" in result.content
    assert "chicken thighs" in result.content
    assert "## Instructions" in result.content


def test_parse_recipe_without_image(tmp_path):
    no_image = tmp_path / "no-image-recipe.md"
    no_image.write_text(
        "---\ntitle: No Image Recipe\ntags: [test]\nservings: 4\n---\n\n"
        "# No Image Recipe\n\n## Ingredients\n\n- 1 cup water\n"
    )
    result = parse_recipe(no_image)
    assert result.slug == "no-image-recipe"
    assert result.image is None


def test_parse_frontmatter_coerces_servings_to_string():
    """Servings in YAML may parse as int, we want string."""
    result = parse_frontmatter(SAMPLE_DIR / "chicken-tikka-masala.md")
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
