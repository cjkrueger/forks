import subprocess
import textwrap

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


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

    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(tmp_path), capture_output=True,
    )
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


def test_list_recipes(client):
    resp = client.get("/api/recipes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 3
    slugs = [r["slug"] for r in data]
    assert "chicken-tikka-masala" in slugs


def test_list_recipes_sorted_alphabetically(client):
    resp = client.get("/api/recipes")
    data = resp.json()
    titles = [r["title"] for r in data]
    assert titles == sorted(titles, key=str.lower)


def test_list_recipes_no_content_field(client):
    """List endpoint should return summaries, not full content."""
    resp = client.get("/api/recipes")
    data = resp.json()
    for recipe in data:
        assert "content" not in recipe


def test_filter_by_tag(client):
    resp = client.get("/api/recipes?tags=mexican")
    data = resp.json()
    assert len(data) >= 1
    assert all("mexican" in r["tags"] for r in data)


def test_filter_by_multiple_tags(client):
    resp = client.get("/api/recipes?tags=mexican,beef")
    data = resp.json()
    assert all("mexican" in r["tags"] and "beef" in r["tags"] for r in data)


def test_get_recipe(client):
    resp = client.get("/api/recipes/chicken-tikka-masala")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "chicken-tikka-masala"
    assert data["title"] == "Chicken Tikka Masala"
    assert "content" in data
    assert "## Ingredients" in data["content"]


def test_get_recipe_not_found(client):
    resp = client.get("/api/recipes/does-not-exist")
    assert resp.status_code == 404


def test_search_by_title(client):
    resp = client.get("/api/search?q=tikka")
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["slug"] == "chicken-tikka-masala" for r in data)


def test_search_by_ingredient(client):
    resp = client.get("/api/search?q=coconut cream")
    data = resp.json()
    assert any(r["slug"] == "chicken-tikka-masala" for r in data)


def test_search_empty_returns_all(client):
    resp = client.get("/api/search?q=")
    data = resp.json()
    assert len(data) == 3


def test_search_no_results(client):
    resp = client.get("/api/search?q=xyznonexistent")
    data = resp.json()
    assert len(data) == 0


def test_get_recipe_includes_structured_fields(client):
    """Recipe detail should include parsed ingredients, instructions, notes."""
    resp = client.get("/api/recipes/7-layer-casserole")
    assert resp.status_code == 200
    data = resp.json()
    assert "ingredients" in data
    assert "instructions" in data
    assert "notes" in data
    assert isinstance(data["ingredients"], list)
    assert len(data["ingredients"]) > 0


def test_list_tags(client):
    resp = client.get("/api/tags")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) > 0
    # Each entry should have tag and count
    assert all("tag" in t and "count" in t for t in data)


def test_export_recipe(client):
    resp = client.get("/api/recipes/7-layer-casserole/export")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "7-Layer Casserole" in resp.text
    assert "attachment" in resp.headers.get("content-disposition", "")


def test_export_recipe_not_found(client):
    resp = client.get("/api/recipes/does-not-exist/export")
    assert resp.status_code == 404
