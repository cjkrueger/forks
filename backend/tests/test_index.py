import textwrap

import pytest

from app.index import RecipeIndex


CHICKEN_TIKKA = textwrap.dedent("""\
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

CASSEROLE = textwrap.dedent("""\
    ---
    title: 7-Layer Casserole
    tags: [mexican, beef]
    servings: 6 servings
    cook_time: 20min
    source: https://www.foodnetwork.com/recipes/7-layer-casserole
    image: images/7-layer-casserole.webp
    ---

    # 7-Layer Casserole

    ## Ingredients

    - 1 pound ground beef
    - 2 tablespoons taco seasoning
    - 1 cup frozen corn

    ## Instructions

    1. Preheat oven to 375 degrees F.
    2. Brown beef with taco seasoning.
    3. Layer ingredients in baking dish and bake.

    ## Notes

    - Serve with sour cream and salsa.
""")

CAULIFLOWER_RICE = textwrap.dedent("""\
    ---
    title: How to Make Cauliflower Rice
    tags: [vegetable, quick]
    servings: 4 servings
    prep_time: 15min
    ---

    # How to Make Cauliflower Rice

    ## Ingredients

    - 1 large head cauliflower, cut into florets
    - 2 tbsp extra-virgin olive oil
    - Kosher salt and freshly ground black pepper

    ## Instructions

    1. Pulse cauliflower florets in a food processor until finely chopped.
    2. Heat oil in a large skillet over medium heat.
    3. Add riced cauliflower and cook until tender, 5 minutes.
""")


@pytest.fixture
def tmp_recipes(tmp_path):
    (tmp_path / "images").mkdir()
    (tmp_path / "chicken-tikka-masala.md").write_text(CHICKEN_TIKKA)
    (tmp_path / "7-layer-casserole.md").write_text(CASSEROLE)
    (tmp_path / "how-to-make-cauliflower-rice.md").write_text(CAULIFLOWER_RICE)
    return tmp_path


def test_index_loads_all_recipes(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    slugs = idx.list_slugs()
    assert "chicken-tikka-masala" in slugs
    assert "7-layer-casserole" in slugs
    assert "how-to-make-cauliflower-rice" in slugs


def test_index_list_all(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    recipes = idx.list_all()
    assert len(recipes) == 3
    titles = [r.title for r in recipes]
    assert "Chicken Tikka Masala" in titles


def test_index_list_sorted_alphabetically(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    recipes = idx.list_all()
    titles = [r.title for r in recipes]
    assert titles == sorted(titles)


def test_index_filter_by_tags(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    results = idx.filter_by_tags(["mexican"])
    assert len(results) >= 1
    assert all(any(t.lower() == "mexican" for t in r.tags) for r in results)


def test_index_filter_by_multiple_tags(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    results = idx.filter_by_tags(["mexican", "beef"])
    assert all(
        any(t.lower() == "mexican" for t in r.tags)
        and any(t.lower() == "beef" for t in r.tags)
        for r in results
    )


def test_index_filter_by_tags_case_insensitive(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    # Tags stored as "mexican" should match query "Mexican" (capital M)
    results_lower = idx.filter_by_tags(["mexican"])
    results_upper = idx.filter_by_tags(["Mexican"])
    assert len(results_lower) == len(results_upper)
    assert {r.slug for r in results_lower} == {r.slug for r in results_upper}


def test_index_get_by_slug(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    recipe = idx.get("chicken-tikka-masala")
    assert recipe is not None
    assert recipe.title == "Chicken Tikka Masala"
    assert "## Ingredients" in recipe.content


def test_index_get_nonexistent_returns_none(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    assert idx.get("nonexistent-recipe") is None


def test_index_search_by_title(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    results = idx.search("tikka")
    assert len(results) >= 1
    assert any(r.slug == "chicken-tikka-masala" for r in results)


def test_index_search_by_tag(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    results = idx.search("mexican")
    assert any(r.slug == "7-layer-casserole" for r in results)


def test_index_search_by_ingredient(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    results = idx.search("coconut cream")
    assert any(r.slug == "chicken-tikka-masala" for r in results)


def test_index_search_case_insensitive(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    results = idx.search("CASSEROLE")
    assert any(r.slug == "7-layer-casserole" for r in results)


def test_index_search_empty_query_returns_all(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    results = idx.search("")
    assert len(results) == 3


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


def test_index_remove(tmp_recipes):
    idx = RecipeIndex(tmp_recipes)
    idx.build()
    count_before = len(idx.list_all())
    idx.remove("chicken-tikka-masala")
    assert len(idx.list_all()) == count_before - 1
    assert idx.get("chicken-tikka-masala") is None
