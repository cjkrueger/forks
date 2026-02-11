import textwrap

from app.parser import parse_recipe, parse_frontmatter


SAMPLE_RECIPE = textwrap.dedent("""\
    ---
    title: Chicken Tikka Masala
    tags: [chicken, indian]
    servings: 4 servings
    prep_time: 30min
    cook_time: 50min
    source: https://www.thekitchn.com/chicken-tikka-masala-recipe-23686912
    image: images/chicken-tikka-masala.jpg
    ---

    # Chicken Tikka Masala

    ## Ingredients

    - 1 1/2 pounds boneless, skinless chicken thighs
    - 1/2 cup coconut cream
    - 1 teaspoon garam masala

    ## Instructions

    1. Marinate chicken thighs in yogurt and spices.
    2. Sear chicken in a hot skillet.
    3. Simmer in sauce until cooked through.
""")


def _sample_recipe(tmp_path):
    path = tmp_path / "chicken-tikka-masala.md"
    path.write_text(SAMPLE_RECIPE)
    return path


def test_parse_frontmatter_extracts_metadata(tmp_path):
    path = _sample_recipe(tmp_path)
    result = parse_frontmatter(path)
    assert result.slug == "chicken-tikka-masala"
    assert result.title == "Chicken Tikka Masala"
    assert "chicken" in result.tags
    assert "indian" in result.tags
    assert result.servings == "4 servings"
    assert result.prep_time == "30min"
    assert result.cook_time == "50min"
    assert result.source == "https://www.thekitchn.com/chicken-tikka-masala-recipe-23686912"
    assert result.image == "images/chicken-tikka-masala.jpg"


def test_parse_recipe_includes_content(tmp_path):
    path = _sample_recipe(tmp_path)
    result = parse_recipe(path)
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


def test_parse_frontmatter_coerces_servings_to_string(tmp_path):
    """Servings in YAML may parse as int, we want string."""
    path = _sample_recipe(tmp_path)
    result = parse_frontmatter(path)
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
