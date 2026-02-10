from pathlib import Path
from app.index import RecipeIndex


SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "recipes"


def test_index_loads_all_recipes():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    slugs = idx.list_slugs()
    assert "birria-tacos" in slugs
    assert "pasta-carbonara" in slugs
    assert "thai-green-curry" in slugs


def test_index_list_all():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    recipes = idx.list_all()
    assert len(recipes) >= 3
    titles = [r.title for r in recipes]
    assert "Birria Tacos" in titles


def test_index_list_sorted_alphabetically():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    recipes = idx.list_all()
    titles = [r.title for r in recipes]
    assert titles == sorted(titles)


def test_index_filter_by_tags():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    results = idx.filter_by_tags(["mexican"])
    assert len(results) >= 1
    assert all("mexican" in r.tags for r in results)


def test_index_filter_by_multiple_tags():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    results = idx.filter_by_tags(["mexican", "beef"])
    assert all("mexican" in r.tags and "beef" in r.tags for r in results)


def test_index_get_by_slug():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    recipe = idx.get("birria-tacos")
    assert recipe is not None
    assert recipe.title == "Birria Tacos"
    assert "## Ingredients" in recipe.content


def test_index_get_nonexistent_returns_none():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    assert idx.get("nonexistent-recipe") is None


def test_index_search_by_title():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    results = idx.search("carbonara")
    assert len(results) >= 1
    assert any(r.slug == "pasta-carbonara" for r in results)


def test_index_search_by_tag():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    results = idx.search("mexican")
    assert any(r.slug == "birria-tacos" for r in results)


def test_index_search_by_ingredient():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    results = idx.search("coconut milk")
    assert any(r.slug == "thai-green-curry" for r in results)


def test_index_search_case_insensitive():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    results = idx.search("BIRRIA")
    assert any(r.slug == "birria-tacos" for r in results)


def test_index_search_empty_query_returns_all():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    results = idx.search("")
    assert len(results) >= 3


def test_index_update_on_file_change(tmp_path):
    recipe = tmp_path / "new-recipe.md"
    recipe.write_text("---\ntitle: New Recipe\ntags: [test]\n---\n\n# New Recipe\n\nContent here.\n")

    idx = RecipeIndex(tmp_path)
    idx.build()
    assert len(idx.list_all()) == 1

    recipe2 = tmp_path / "another.md"
    recipe2.write_text("---\ntitle: Another\ntags: [test]\n---\n\n# Another\n\nMore content.\n")
    idx.add_or_update(recipe2)
    assert len(idx.list_all()) == 2


def test_index_remove():
    idx = RecipeIndex(SAMPLE_DIR)
    idx.build()
    count_before = len(idx.list_all())
    idx.remove("birria-tacos")
    assert len(idx.list_all()) == count_before - 1
    assert idx.get("birria-tacos") is None
