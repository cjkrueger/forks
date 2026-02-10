# Phase 1 Implementation Plan: "I can read recipes"

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a self-hosted web app that reads `.md` recipe files from a folder and renders them in a clean, mobile-friendly UI with tag filtering and search.

**Architecture:** FastAPI backend serves a SvelteKit static frontend from a single container. Recipes are `.md` files with YAML frontmatter in a mounted volume. An in-memory index stores metadata; full recipe content is read from disk on demand. Watchdog monitors the folder for changes.

**Tech Stack:** Python (FastAPI, python-frontmatter, watchdog, pydantic), SvelteKit (adapter-static, marked), Docker multi-stage build.

---

### Task 1: Backend Scaffolding

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/models.py`
- Create: `backend/app/parser.py`
- Create: `backend/app/index.py`
- Create: `backend/app/routes/__init__.py`
- Create: `backend/app/routes/recipes.py`
- Create: `backend/requirements.txt`
- Create: `backend/tests/__init__.py`

**Step 1: Create backend directory structure**

```bash
mkdir -p backend/app/routes backend/tests
```

**Step 2: Create requirements.txt**

Create `backend/requirements.txt`:
```
fastapi==0.115.8
uvicorn[standard]==0.34.0
python-frontmatter==1.1.0
watchdog==6.0.0
pydantic==2.10.6
pytest==8.3.4
httpx==0.28.1
```

**Step 3: Create empty init files**

Create empty `backend/app/__init__.py`, `backend/app/routes/__init__.py`, `backend/tests/__init__.py`.

**Step 4: Install dependencies**

```bash
cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

**Step 5: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend directory structure and dependencies"
```

---

### Task 2: Sample Recipes

Create sample recipes so we have data to test against throughout development.

**Files:**
- Create: `recipes/birria-tacos.md`
- Create: `recipes/pasta-carbonara.md`
- Create: `recipes/thai-green-curry.md`
- Create: `recipes/images/.gitkeep`

**Step 1: Create recipes directory**

```bash
mkdir -p recipes/images
```

**Step 2: Create birria-tacos.md**

Create `recipes/birria-tacos.md`:
```markdown
---
title: Birria Tacos
source: https://example.com/birria-tacos
tags: [mexican, beef, tacos, weekend]
servings: 6
prep_time: 30min
cook_time: 3hr
date_added: 2026-02-09
image: images/birria-tacos.jpg
---

# Birria Tacos

## Ingredients

- 3 lbs chuck roast, cut into chunks
- 4 dried guajillo chiles, stemmed and seeded
- 2 dried ancho chiles, stemmed and seeded
- 1 can (14 oz) crushed tomatoes
- 1 medium white onion, quartered
- 4 cloves garlic
- 1 tbsp cumin
- 1 tsp oregano
- 1 tsp black pepper
- 2 cups beef broth
- Salt to taste
- Corn tortillas
- Shredded Oaxaca cheese
- Fresh cilantro, diced onion, lime wedges for serving

## Instructions

1. Toast the chiles in a dry skillet over medium heat for 1-2 minutes per side until fragrant. Transfer to a bowl and cover with hot water. Soak for 15 minutes.
2. Blend soaked chiles with crushed tomatoes, onion, garlic, cumin, oregano, and black pepper until smooth.
3. Season the chuck roast generously with salt. Sear in a Dutch oven over high heat until browned on all sides, about 3-4 minutes per side.
4. Pour the chile sauce over the meat. Add beef broth. Bring to a simmer.
5. Cover and cook on low heat for 3 hours, or until meat is fall-apart tender.
6. Shred the meat and return to the consomé.
7. Dip corn tortillas in the consomé, then pan-fry with shredded cheese until crispy.
8. Fill with birria meat, top with cilantro, diced onion, and a squeeze of lime. Serve with a side of consomé for dipping.

## Notes

- The consomé is the star — don't skip the dipping step
- Works great in a slow cooker: 8 hours on low
- Leftovers make incredible quesadillas the next day
```

**Step 3: Create pasta-carbonara.md**

Create `recipes/pasta-carbonara.md`:
```markdown
---
title: Pasta Carbonara
source: https://example.com/carbonara
tags: [italian, pasta, quick, pork]
servings: 4
prep_time: 10min
cook_time: 20min
date_added: 2026-02-08
---

# Pasta Carbonara

## Ingredients

- 1 lb spaghetti
- 6 oz guanciale or pancetta, diced
- 4 large egg yolks
- 2 large whole eggs
- 1 cup freshly grated Pecorino Romano
- 1/2 cup freshly grated Parmigiano-Reggiano
- Freshly cracked black pepper
- Salt for pasta water

## Instructions

1. Bring a large pot of well-salted water to a boil. Cook spaghetti until al dente. Reserve 1 cup pasta water before draining.
2. While pasta cooks, cook guanciale in a cold skillet over medium heat until fat renders and meat is crispy, about 8 minutes.
3. In a bowl, whisk together egg yolks, whole eggs, Pecorino, and Parmigiano. Add generous black pepper.
4. Drain pasta and add to the skillet with guanciale. Remove from heat.
5. Pour egg mixture over pasta, tossing quickly and constantly. The residual heat cooks the eggs into a creamy sauce. Add pasta water a splash at a time if needed.
6. Serve immediately with extra Pecorino and black pepper.

## Notes

- Never add cream — the egg and cheese IS the sauce
- Remove pan from heat before adding eggs to avoid scrambling
- Guanciale is traditional but pancetta works in a pinch
```

**Step 4: Create thai-green-curry.md**

Create `recipes/thai-green-curry.md`:
```markdown
---
title: Thai Green Curry
source: https://example.com/green-curry
tags: [thai, chicken, curry, weeknight]
servings: 4
prep_time: 15min
cook_time: 25min
date_added: 2026-02-07
image: images/thai-green-curry.jpg
---

# Thai Green Curry

## Ingredients

- 1.5 lbs chicken thighs, sliced
- 1 can (14 oz) coconut milk
- 3 tbsp green curry paste
- 1 Japanese eggplant, sliced
- 1 red bell pepper, sliced
- 1 cup Thai basil leaves
- 2 tbsp fish sauce
- 1 tbsp palm sugar or brown sugar
- 4 kaffir lime leaves
- Jasmine rice for serving

## Instructions

1. Heat a large skillet or wok over medium-high heat. Scoop the thick cream from the top of the coconut milk into the pan.
2. When the cream begins to sizzle, add the curry paste and fry for 2 minutes until fragrant.
3. Add chicken and stir to coat in the curry paste. Cook for 3-4 minutes.
4. Pour in the remaining coconut milk. Add kaffir lime leaves, fish sauce, and sugar.
5. Add eggplant and bell pepper. Simmer for 15-20 minutes until chicken is cooked through and vegetables are tender.
6. Stir in Thai basil just before serving.
7. Serve over jasmine rice.

## Notes

- Mae Ploy is a solid store-bought curry paste
- Swap chicken for shrimp or tofu for variation
- Add bamboo shoots or baby corn if you have them
```

**Step 5: Commit**

```bash
git add recipes/
git commit -m "feat: add sample recipes for development and testing"
```

---

### Task 3: Config Module

**Files:**
- Create: `backend/app/config.py`

**Step 1: Write config.py**

Create `backend/app/config.py`:
```python
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    recipes_dir: Path = Path(__file__).resolve().parent.parent.parent / "recipes"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "FORKS_"}


settings = Settings()
```

Note: This requires `pydantic-settings`. Add it to requirements.txt:
```
pydantic-settings==2.7.1
```

**Step 2: Commit**

```bash
git add backend/app/config.py backend/requirements.txt
git commit -m "feat: add config module with settings"
```

---

### Task 4: Pydantic Models

**Files:**
- Create: `backend/app/models.py`

**Step 1: Write models.py**

Create `backend/app/models.py`:
```python
from pydantic import BaseModel


class RecipeSummary(BaseModel):
    slug: str
    title: str
    tags: list[str] = []
    servings: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    date_added: str | None = None
    source: str | None = None
    image: str | None = None


class Recipe(RecipeSummary):
    content: str
```

**Step 2: Commit**

```bash
git add backend/app/models.py
git commit -m "feat: add Pydantic models for Recipe and RecipeSummary"
```

---

### Task 5: Recipe Parser (TDD)

**Files:**
- Create: `backend/app/parser.py`
- Create: `backend/tests/test_parser.py`

**Step 1: Write the failing tests**

Create `backend/tests/test_parser.py`:
```python
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
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && source venv/bin/activate && python -m pytest tests/test_parser.py -v
```

Expected: FAIL — `cannot import name 'parse_recipe' from 'app.parser'`

**Step 3: Write parser.py**

Create `backend/app/parser.py`:
```python
import logging
from pathlib import Path

import frontmatter

from app.models import Recipe, RecipeSummary

logger = logging.getLogger(__name__)


def parse_frontmatter(path: Path) -> RecipeSummary:
    """Parse only the frontmatter metadata from a recipe file."""
    slug = path.stem
    try:
        post = frontmatter.load(path)
        meta = post.metadata
    except Exception:
        logger.warning(f"Failed to parse frontmatter: {path}")
        return RecipeSummary(slug=slug, title=slug)

    servings = meta.get("servings")

    return RecipeSummary(
        slug=slug,
        title=meta.get("title", slug),
        tags=meta.get("tags", []),
        servings=str(servings) if servings is not None else None,
        prep_time=meta.get("prep_time"),
        cook_time=meta.get("cook_time"),
        date_added=str(meta.get("date_added")) if meta.get("date_added") else None,
        source=meta.get("source"),
        image=meta.get("image"),
    )


def parse_recipe(path: Path) -> Recipe:
    """Parse full recipe including frontmatter and markdown body."""
    slug = path.stem
    try:
        post = frontmatter.load(path)
        meta = post.metadata
        content = post.content
    except Exception:
        logger.warning(f"Failed to parse recipe: {path}")
        content = path.read_text()
        return Recipe(slug=slug, title=slug, content=content)

    servings = meta.get("servings")

    return Recipe(
        slug=slug,
        title=meta.get("title", slug),
        tags=meta.get("tags", []),
        servings=str(servings) if servings is not None else None,
        prep_time=meta.get("prep_time"),
        cook_time=meta.get("cook_time"),
        date_added=str(meta.get("date_added")) if meta.get("date_added") else None,
        source=meta.get("source"),
        image=meta.get("image"),
        content=content,
    )
```

**Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_parser.py -v
```

Expected: All 5 tests PASS.

**Step 5: Commit**

```bash
git add backend/app/parser.py backend/tests/test_parser.py
git commit -m "feat: add recipe parser with frontmatter extraction"
```

---

### Task 6: In-Memory Index (TDD)

**Files:**
- Create: `backend/app/index.py`
- Create: `backend/tests/test_index.py`

**Step 1: Write the failing tests**

Create `backend/tests/test_index.py`:
```python
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
    """Simulate adding a new file and updating the index."""
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
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_index.py -v
```

Expected: FAIL — `cannot import name 'RecipeIndex'`

**Step 3: Write index.py**

Create `backend/app/index.py`:
```python
import logging
import re
from pathlib import Path

import frontmatter

from app.models import RecipeSummary, Recipe
from app.parser import parse_frontmatter, parse_recipe

logger = logging.getLogger(__name__)


class RecipeIndex:
    def __init__(self, recipes_dir: Path):
        self.recipes_dir = recipes_dir
        self._index: dict[str, RecipeSummary] = {}
        self._ingredients: dict[str, list[str]] = {}  # slug -> ingredient lines

    def build(self) -> None:
        """Scan recipes directory and build the in-memory index."""
        self._index.clear()
        self._ingredients.clear()
        if not self.recipes_dir.exists():
            logger.warning(f"Recipes directory not found: {self.recipes_dir}")
            return
        for path in self.recipes_dir.glob("*.md"):
            self._index_file(path)
        logger.info(f"Indexed {len(self._index)} recipes from {self.recipes_dir}")

    def _index_file(self, path: Path) -> None:
        """Parse and index a single recipe file."""
        summary = parse_frontmatter(path)
        self._index[summary.slug] = summary
        self._ingredients[summary.slug] = self._extract_ingredients(path)

    def _extract_ingredients(self, path: Path) -> list[str]:
        """Extract ingredient lines from the markdown body for search."""
        try:
            post = frontmatter.load(path)
            content = post.content
        except Exception:
            content = path.read_text()

        lines = []
        in_ingredients = False
        for line in content.split("\n"):
            if re.match(r"^##\s+Ingredients", line, re.IGNORECASE):
                in_ingredients = True
                continue
            if in_ingredients and re.match(r"^##\s+", line):
                break
            if in_ingredients and line.strip().startswith("- "):
                lines.append(line.strip().lstrip("- ").lower())
        return lines

    def list_slugs(self) -> list[str]:
        return list(self._index.keys())

    def list_all(self) -> list[RecipeSummary]:
        return sorted(self._index.values(), key=lambda r: r.title.lower())

    def filter_by_tags(self, tags: list[str]) -> list[RecipeSummary]:
        results = [
            r for r in self._index.values()
            if all(tag in r.tags for tag in tags)
        ]
        return sorted(results, key=lambda r: r.title.lower())

    def get(self, slug: str) -> Recipe | None:
        if slug not in self._index:
            return None
        path = self.recipes_dir / f"{slug}.md"
        if not path.exists():
            return None
        return parse_recipe(path)

    def search(self, query: str) -> list[RecipeSummary]:
        if not query.strip():
            return self.list_all()

        q = query.lower()
        results = []
        for slug, summary in self._index.items():
            if q in summary.title.lower():
                results.append(summary)
                continue
            if any(q in tag.lower() for tag in summary.tags):
                results.append(summary)
                continue
            if any(q in ing for ing in self._ingredients.get(slug, [])):
                results.append(summary)
                continue
        return sorted(results, key=lambda r: r.title.lower())

    def add_or_update(self, path: Path) -> None:
        """Add or update a single recipe in the index."""
        self._index_file(path)

    def remove(self, slug: str) -> None:
        """Remove a recipe from the index."""
        self._index.pop(slug, None)
        self._ingredients.pop(slug, None)
```

**Step 4: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_index.py -v
```

Expected: All 14 tests PASS.

**Step 5: Commit**

```bash
git add backend/app/index.py backend/tests/test_index.py
git commit -m "feat: add in-memory recipe index with search and tag filtering"
```

---

### Task 7: File Watcher

**Files:**
- Create: `backend/app/watcher.py`

**Step 1: Write watcher.py**

Create `backend/app/watcher.py`:
```python
import logging
import threading
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from app.index import RecipeIndex

logger = logging.getLogger(__name__)


class RecipeEventHandler(FileSystemEventHandler):
    def __init__(self, index: RecipeIndex):
        self.index = index
        self._debounce_timers: dict[str, threading.Timer] = {}

    def _debounced_update(self, path: Path) -> None:
        key = str(path)
        if key in self._debounce_timers:
            self._debounce_timers[key].cancel()

        timer = threading.Timer(0.5, self._handle_update, args=[path])
        self._debounce_timers[key] = timer
        timer.start()

    def _handle_update(self, path: Path) -> None:
        if path.exists():
            logger.info(f"Recipe updated: {path.name}")
            self.index.add_or_update(path)
        else:
            slug = path.stem
            logger.info(f"Recipe deleted: {slug}")
            self.index.remove(slug)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix == ".md":
            self._debounced_update(path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix == ".md":
            self._debounced_update(path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix == ".md":
            self._debounced_update(path)


def start_watcher(index: RecipeIndex, recipes_dir: Path) -> Observer:
    """Start watching the recipes directory for changes."""
    handler = RecipeEventHandler(index)
    observer = Observer()
    observer.schedule(handler, str(recipes_dir), recursive=False)
    observer.daemon = True
    observer.start()
    logger.info(f"Watching for recipe changes in {recipes_dir}")
    return observer
```

**Step 2: Commit**

```bash
git add backend/app/watcher.py
git commit -m "feat: add file watcher for live recipe index updates"
```

---

### Task 8: API Routes (TDD)

**Files:**
- Create: `backend/app/routes/recipes.py`
- Create: `backend/tests/test_routes.py`

**Step 1: Write the failing tests**

Create `backend/tests/test_routes.py`:
```python
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


SAMPLE_DIR = Path(__file__).resolve().parent.parent.parent / "recipes"


@pytest.fixture
def client():
    app = create_app(recipes_dir=SAMPLE_DIR)
    return TestClient(app)


def test_list_recipes(client):
    resp = client.get("/api/recipes")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 3
    slugs = [r["slug"] for r in data]
    assert "birria-tacos" in slugs


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
    resp = client.get("/api/recipes/birria-tacos")
    assert resp.status_code == 200
    data = resp.json()
    assert data["slug"] == "birria-tacos"
    assert data["title"] == "Birria Tacos"
    assert "content" in data
    assert "## Ingredients" in data["content"]


def test_get_recipe_not_found(client):
    resp = client.get("/api/recipes/does-not-exist")
    assert resp.status_code == 404


def test_search_by_title(client):
    resp = client.get("/api/search?q=carbonara")
    assert resp.status_code == 200
    data = resp.json()
    assert any(r["slug"] == "pasta-carbonara" for r in data)


def test_search_by_ingredient(client):
    resp = client.get("/api/search?q=coconut milk")
    data = resp.json()
    assert any(r["slug"] == "thai-green-curry" for r in data)


def test_search_empty_returns_all(client):
    resp = client.get("/api/search?q=")
    data = resp.json()
    assert len(data) >= 3


def test_search_no_results(client):
    resp = client.get("/api/search?q=xyznonexistent")
    data = resp.json()
    assert len(data) == 0
```

**Step 2: Run tests to verify they fail**

```bash
cd backend && python -m pytest tests/test_routes.py -v
```

Expected: FAIL — `cannot import name 'create_app'`

**Step 3: Write routes/recipes.py**

Create `backend/app/routes/recipes.py`:
```python
from fastapi import APIRouter, HTTPException, Query

from app.index import RecipeIndex
from app.models import Recipe, RecipeSummary

router = APIRouter(prefix="/api")


def create_recipe_router(index: RecipeIndex) -> APIRouter:
    r = APIRouter(prefix="/api")

    @r.get("/recipes", response_model=list[RecipeSummary])
    def list_recipes(tags: str | None = Query(None)):
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
            return index.filter_by_tags(tag_list)
        return index.list_all()

    @r.get("/recipes/{slug}", response_model=Recipe)
    def get_recipe(slug: str):
        recipe = index.get(slug)
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return recipe

    @r.get("/search", response_model=list[RecipeSummary])
    def search_recipes(q: str = Query("")):
        return index.search(q)

    return r
```

**Step 4: Write main.py**

Create `backend/app/main.py`:
```python
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.index import RecipeIndex
from app.routes.recipes import create_recipe_router
from app.watcher import start_watcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(recipes_dir: Path | None = None) -> FastAPI:
    app = FastAPI(title="Forks", version="0.1.0")

    recipes_path = recipes_dir or settings.recipes_dir

    # Build recipe index
    index = RecipeIndex(recipes_path)
    index.build()

    # Register API routes
    app.include_router(create_recipe_router(index))

    # Serve recipe images
    images_dir = recipes_path / "images"
    if images_dir.exists():
        app.mount("/api/images", StaticFiles(directory=str(images_dir)), name="images")

    # Start file watcher
    @app.on_event("startup")
    def startup():
        start_watcher(index, recipes_path)

    # Serve frontend static files (in production)
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")

    return app


app = create_app()
```

**Step 5: Run tests to verify they pass**

```bash
cd backend && python -m pytest tests/test_routes.py -v
```

Expected: All 11 tests PASS.

**Step 6: Run all tests**

```bash
cd backend && python -m pytest -v
```

Expected: All tests PASS (parser + index + routes).

**Step 7: Commit**

```bash
git add backend/app/routes/recipes.py backend/app/main.py backend/tests/test_routes.py
git commit -m "feat: add API routes and FastAPI app assembly"
```

---

### Task 9: Frontend Scaffolding

**Files:**
- Create: SvelteKit project in `frontend/`

**Step 1: Create SvelteKit project**

```bash
cd /path/to/forks && npx sv create frontend --template minimal --types ts
```

When prompted, select:
- Template: minimal (SvelteKit)
- Type checking: TypeScript
- No additional options needed

**Step 2: Install dependencies**

```bash
cd frontend && npm install
npm install -D @sveltejs/adapter-static
npm install marked
```

**Step 3: Configure adapter-static**

Replace `frontend/svelte.config.js`:
```javascript
import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: 'index.html'
		})
	}
};

export default config;
```

The `fallback: 'index.html'` is critical — it enables client-side routing so `/recipe/birria-tacos` works without a server-side route.

**Step 4: Configure Vite proxy for dev**

Replace `frontend/vite.config.ts`:
```typescript
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			'/api': 'http://localhost:8000'
		}
	}
});
```

**Step 5: Add prerender setting**

Create `frontend/src/routes/+layout.ts`:
```typescript
export const prerender = false;
export const ssr = false;
```

This tells SvelteKit to build a pure client-side SPA (no server-side rendering since FastAPI serves the static files).

**Step 6: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold SvelteKit frontend with adapter-static"
```

---

### Task 10: Frontend — API Client & Markdown Rendering

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/markdown.ts`
- Create: `frontend/src/lib/types.ts`

**Step 1: Create types**

Create `frontend/src/lib/types.ts`:
```typescript
export interface RecipeSummary {
  slug: string;
  title: string;
  tags: string[];
  servings: string | null;
  prep_time: string | null;
  cook_time: string | null;
  date_added: string | null;
  source: string | null;
  image: string | null;
}

export interface Recipe extends RecipeSummary {
  content: string;
}
```

**Step 2: Create API client**

Create `frontend/src/lib/api.ts`:
```typescript
import type { Recipe, RecipeSummary } from './types';

const BASE = '/api';

export async function listRecipes(tags?: string[]): Promise<RecipeSummary[]> {
  const params = new URLSearchParams();
  if (tags && tags.length > 0) {
    params.set('tags', tags.join(','));
  }
  const url = `${BASE}/recipes${params.toString() ? '?' + params.toString() : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch recipes');
  return res.json();
}

export async function getRecipe(slug: string): Promise<Recipe> {
  const res = await fetch(`${BASE}/recipes/${slug}`);
  if (!res.ok) throw new Error('Recipe not found');
  return res.json();
}

export async function searchRecipes(query: string): Promise<RecipeSummary[]> {
  const res = await fetch(`${BASE}/search?q=${encodeURIComponent(query)}`);
  if (!res.ok) throw new Error('Search failed');
  return res.json();
}
```

**Step 3: Create markdown renderer**

Create `frontend/src/lib/markdown.ts`:
```typescript
import { marked } from 'marked';

export function renderMarkdown(content: string): string {
  return marked.parse(content, { async: false }) as string;
}
```

**Step 4: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat: add API client, types, and markdown renderer"
```

---

### Task 11: Frontend — Layout & Styling

**Files:**
- Create: `frontend/src/routes/+layout.svelte`
- Create: `frontend/src/app.css`

**Step 1: Create global styles**

Create `frontend/src/app.css`:
```css
:root {
  --color-bg: #faf9f6;
  --color-surface: #ffffff;
  --color-text: #2d2d2d;
  --color-text-muted: #6b6b6b;
  --color-accent: #d35400;
  --color-accent-light: #fdf0e6;
  --color-border: #e8e5e0;
  --color-tag: #f0ece6;
  --color-tag-active: #d35400;
  --font-body: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --font-heading: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --radius: 8px;
  --shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  --sidebar-width: 240px;
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: var(--font-body);
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

a {
  color: var(--color-accent);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}
```

**Step 2: Create layout**

Create `frontend/src/routes/+layout.svelte`:
```svelte
<script lang="ts">
  import '../app.css';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { listRecipes } from '$lib/api';
  import { onMount } from 'svelte';

  let searchQuery = '';
  let allTags: { name: string; count: number }[] = [];
  let sidebarOpen = false;

  // Reactive: get active tags from URL params
  $: activeTags = $page.url.searchParams.get('tags')?.split(',').filter(Boolean) || [];

  onMount(async () => {
    const recipes = await listRecipes();
    const tagMap = new Map<string, number>();
    for (const r of recipes) {
      for (const tag of r.tags) {
        tagMap.set(tag, (tagMap.get(tag) || 0) + 1);
      }
    }
    allTags = Array.from(tagMap.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  });

  function handleSearch() {
    if (searchQuery.trim()) {
      goto(`/?q=${encodeURIComponent(searchQuery.trim())}`);
    } else {
      goto('/');
    }
  }

  function toggleTag(tag: string) {
    let tags = [...activeTags];
    if (tags.includes(tag)) {
      tags = tags.filter(t => t !== tag);
    } else {
      tags.push(tag);
    }
    if (tags.length > 0) {
      goto(`/?tags=${tags.join(',')}`);
    } else {
      goto('/');
    }
    sidebarOpen = false;
  }
</script>

<div class="app">
  <header class="topbar">
    <div class="topbar-left">
      <button class="menu-btn" on:click={() => sidebarOpen = !sidebarOpen} aria-label="Toggle menu">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>
      <a href="/" class="logo">Forks</a>
    </div>
    <form class="search-form" on:submit|preventDefault={handleSearch}>
      <input
        type="text"
        placeholder="Search recipes..."
        bind:value={searchQuery}
        class="search-input"
      />
    </form>
  </header>

  <div class="layout">
    <aside class="sidebar" class:open={sidebarOpen}>
      <nav class="tag-list">
        <h3 class="sidebar-heading">Tags</h3>
        {#each allTags as tag}
          <button
            class="tag-btn"
            class:active={activeTags.includes(tag.name)}
            on:click={() => toggleTag(tag.name)}
          >
            {tag.name}
            <span class="tag-count">{tag.count}</span>
          </button>
        {/each}
      </nav>
    </aside>

    {#if sidebarOpen}
      <button class="overlay" on:click={() => sidebarOpen = false} aria-label="Close menu"></button>
    {/if}

    <main class="content">
      <slot />
    </main>
  </div>
</div>

<style>
  .app {
    min-height: 100vh;
  }

  .topbar {
    position: sticky;
    top: 0;
    z-index: 100;
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.75rem 1.5rem;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    box-shadow: var(--shadow);
  }

  .topbar-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .menu-btn {
    display: none;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-text);
    padding: 0.25rem;
  }

  .logo {
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--color-accent);
    text-decoration: none;
    letter-spacing: -0.02em;
  }

  .logo:hover {
    text-decoration: none;
  }

  .search-form {
    flex: 1;
    max-width: 400px;
  }

  .search-input {
    width: 100%;
    padding: 0.5rem 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.9rem;
    background: var(--color-bg);
    color: var(--color-text);
    outline: none;
    transition: border-color 0.2s;
  }

  .search-input:focus {
    border-color: var(--color-accent);
  }

  .layout {
    display: flex;
  }

  .sidebar {
    position: sticky;
    top: 57px;
    width: var(--sidebar-width);
    height: calc(100vh - 57px);
    overflow-y: auto;
    padding: 1.5rem 1rem;
    border-right: 1px solid var(--color-border);
    background: var(--color-surface);
    flex-shrink: 0;
  }

  .sidebar-heading {
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.75rem;
  }

  .tag-list {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .tag-btn {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.4rem 0.75rem;
    border: none;
    border-radius: var(--radius);
    background: transparent;
    color: var(--color-text);
    font-size: 0.85rem;
    cursor: pointer;
    transition: background 0.15s;
    text-align: left;
  }

  .tag-btn:hover {
    background: var(--color-tag);
  }

  .tag-btn.active {
    background: var(--color-accent-light);
    color: var(--color-accent);
    font-weight: 600;
  }

  .tag-count {
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  .tag-btn.active .tag-count {
    color: var(--color-accent);
  }

  .content {
    flex: 1;
    padding: 2rem;
    max-width: 1200px;
  }

  .overlay {
    display: none;
  }

  @media (max-width: 768px) {
    .menu-btn {
      display: block;
    }

    .sidebar {
      position: fixed;
      top: 57px;
      left: 0;
      z-index: 50;
      transform: translateX(-100%);
      transition: transform 0.2s ease;
      box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
    }

    .sidebar.open {
      transform: translateX(0);
    }

    .overlay {
      display: block;
      position: fixed;
      inset: 0;
      top: 57px;
      z-index: 40;
      background: rgba(0, 0, 0, 0.3);
      border: none;
      cursor: pointer;
    }

    .content {
      padding: 1rem;
    }
  }
</style>
```

**Step 3: Commit**

```bash
git add frontend/src/app.css frontend/src/routes/+layout.svelte
git commit -m "feat: add app layout with sidebar, search bar, and responsive design"
```

---

### Task 12: Frontend — Recipe Card Component & Home Page

**Files:**
- Create: `frontend/src/lib/components/RecipeCard.svelte`
- Modify: `frontend/src/routes/+page.svelte`

**Step 1: Create RecipeCard component**

Create `frontend/src/lib/components/RecipeCard.svelte`:
```svelte
<script lang="ts">
  import type { RecipeSummary } from '$lib/types';

  export let recipe: RecipeSummary;
</script>

<a href="/recipe/{recipe.slug}" class="card">
  <div class="card-image">
    {#if recipe.image}
      <img src="/api/images/{recipe.image.replace('images/', '')}" alt={recipe.title} />
    {:else}
      <div class="placeholder">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"/>
        </svg>
      </div>
    {/if}
  </div>
  <div class="card-body">
    <h3 class="card-title">{recipe.title}</h3>
    <div class="card-meta">
      {#if recipe.prep_time}
        <span class="meta-item">Prep: {recipe.prep_time}</span>
      {/if}
      {#if recipe.cook_time}
        <span class="meta-item">Cook: {recipe.cook_time}</span>
      {/if}
      {#if recipe.servings}
        <span class="meta-item">Serves: {recipe.servings}</span>
      {/if}
    </div>
    {#if recipe.tags.length > 0}
      <div class="card-tags">
        {#each recipe.tags.slice(0, 4) as tag}
          <span class="tag">{tag}</span>
        {/each}
      </div>
    {/if}
  </div>
</a>

<style>
  .card {
    display: flex;
    flex-direction: column;
    background: var(--color-surface);
    border-radius: var(--radius);
    border: 1px solid var(--color-border);
    overflow: hidden;
    text-decoration: none;
    color: var(--color-text);
    transition: box-shadow 0.2s, transform 0.2s;
  }

  .card:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    transform: translateY(-2px);
    text-decoration: none;
  }

  .card-image {
    aspect-ratio: 16 / 10;
    overflow: hidden;
    background: var(--color-tag);
  }

  .card-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .card-body {
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .card-title {
    font-size: 1.1rem;
    font-weight: 600;
    line-height: 1.3;
  }

  .card-meta {
    display: flex;
    gap: 0.75rem;
    flex-wrap: wrap;
  }

  .meta-item {
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .card-tags {
    display: flex;
    gap: 0.375rem;
    flex-wrap: wrap;
  }

  .tag {
    font-size: 0.7rem;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    background: var(--color-tag);
    color: var(--color-text-muted);
  }
</style>
```

**Step 2: Create home page**

Replace `frontend/src/routes/+page.svelte`:
```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { listRecipes, searchRecipes } from '$lib/api';
  import type { RecipeSummary } from '$lib/types';
  import RecipeCard from '$lib/components/RecipeCard.svelte';

  let recipes: RecipeSummary[] = [];
  let loading = true;

  $: query = $page.url.searchParams.get('q') || '';
  $: tags = $page.url.searchParams.get('tags') || '';

  $: loadRecipes(query, tags);

  async function loadRecipes(q: string, t: string) {
    loading = true;
    try {
      if (q) {
        recipes = await searchRecipes(q);
      } else if (t) {
        recipes = await listRecipes(t.split(',').filter(Boolean));
      } else {
        recipes = await listRecipes();
      }
    } catch (e) {
      console.error('Failed to load recipes:', e);
      recipes = [];
    }
    loading = false;
  }

  onMount(() => {
    loadRecipes(query, tags);
  });
</script>

<svelte:head>
  <title>Forks — Recipe Manager</title>
</svelte:head>

<div class="home">
  {#if query}
    <p class="result-info">Search results for "{query}"</p>
  {/if}

  {#if loading}
    <p class="loading">Loading recipes...</p>
  {:else if recipes.length === 0}
    <p class="empty">No recipes found.</p>
  {:else}
    <div class="grid">
      {#each recipes as recipe (recipe.slug)}
        <RecipeCard {recipe} />
      {/each}
    </div>
  {/if}
</div>

<style>
  .home {
    max-width: 1000px;
  }

  .result-info {
    font-size: 0.9rem;
    color: var(--color-text-muted);
    margin-bottom: 1.5rem;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 1.5rem;
  }

  .loading, .empty {
    color: var(--color-text-muted);
    text-align: center;
    padding: 4rem 1rem;
    font-size: 1.1rem;
  }

  @media (max-width: 768px) {
    .grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }
  }
</style>
```

**Step 3: Commit**

```bash
git add frontend/src/lib/components/RecipeCard.svelte frontend/src/routes/+page.svelte
git commit -m "feat: add recipe card component and home page grid"
```

---

### Task 13: Frontend — Recipe Detail Page

**Files:**
- Create: `frontend/src/routes/recipe/[slug]/+page.svelte`

**Step 1: Create recipe detail page**

Create `frontend/src/routes/recipe/[slug]/+page.svelte`:
```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getRecipe } from '$lib/api';
  import { renderMarkdown } from '$lib/markdown';
  import type { Recipe } from '$lib/types';

  let recipe: Recipe | null = null;
  let loading = true;
  let error = false;

  $: slug = $page.params.slug;

  onMount(async () => {
    try {
      recipe = await getRecipe(slug);
    } catch (e) {
      error = true;
    }
    loading = false;
  });
</script>

<svelte:head>
  <title>{recipe ? recipe.title : 'Recipe'} — Forks</title>
</svelte:head>

{#if loading}
  <p class="loading">Loading recipe...</p>
{:else if error || !recipe}
  <div class="error">
    <h2>Recipe not found</h2>
    <a href="/">Back to recipes</a>
  </div>
{:else}
  <article class="recipe">
    <a href="/" class="back-link">&larr; All recipes</a>

    {#if recipe.image}
      <img
        src="/api/images/{recipe.image.replace('images/', '')}"
        alt={recipe.title}
        class="hero-image"
      />
    {/if}

    <header class="recipe-header">
      <h1>{recipe.title}</h1>

      <div class="meta">
        {#if recipe.prep_time}
          <span class="meta-item">
            <strong>Prep:</strong> {recipe.prep_time}
          </span>
        {/if}
        {#if recipe.cook_time}
          <span class="meta-item">
            <strong>Cook:</strong> {recipe.cook_time}
          </span>
        {/if}
        {#if recipe.servings}
          <span class="meta-item">
            <strong>Serves:</strong> {recipe.servings}
          </span>
        {/if}
      </div>

      {#if recipe.tags.length > 0}
        <div class="tags">
          {#each recipe.tags as tag}
            <a href="/?tags={tag}" class="tag">{tag}</a>
          {/each}
        </div>
      {/if}

      {#if recipe.source}
        <a href={recipe.source} class="source-link" target="_blank" rel="noopener">
          View original source &rarr;
        </a>
      {/if}
    </header>

    <div class="recipe-body">
      {@html renderMarkdown(recipe.content)}
    </div>
  </article>
{/if}

<style>
  .recipe {
    max-width: 720px;
  }

  .back-link {
    display: inline-block;
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 1.5rem;
  }

  .back-link:hover {
    color: var(--color-accent);
  }

  .hero-image {
    width: 100%;
    max-height: 400px;
    object-fit: cover;
    border-radius: var(--radius);
    margin-bottom: 1.5rem;
  }

  .recipe-header {
    margin-bottom: 2rem;
  }

  .recipe-header h1 {
    font-size: 2rem;
    font-weight: 700;
    line-height: 1.2;
    margin-bottom: 0.75rem;
  }

  .meta {
    display: flex;
    gap: 1.25rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
  }

  .meta-item {
    font-size: 0.9rem;
    color: var(--color-text-muted);
  }

  .meta-item strong {
    color: var(--color-text);
  }

  .tags {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 0.75rem;
  }

  .tag {
    font-size: 0.8rem;
    padding: 0.25rem 0.65rem;
    border-radius: 4px;
    background: var(--color-tag);
    color: var(--color-text-muted);
    text-decoration: none;
    transition: background 0.15s;
  }

  .tag:hover {
    background: var(--color-accent-light);
    color: var(--color-accent);
    text-decoration: none;
  }

  .source-link {
    font-size: 0.85rem;
    color: var(--color-accent);
  }

  .recipe-body {
    font-size: 1.05rem;
    line-height: 1.75;
  }

  .recipe-body :global(h1) {
    display: none; /* Title already shown in header */
  }

  .recipe-body :global(h2) {
    font-size: 1.3rem;
    font-weight: 600;
    margin-top: 2rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--color-border);
  }

  .recipe-body :global(ul) {
    padding-left: 1.25rem;
    margin-bottom: 1rem;
  }

  .recipe-body :global(li) {
    margin-bottom: 0.4rem;
  }

  .recipe-body :global(ol) {
    padding-left: 1.25rem;
    margin-bottom: 1rem;
  }

  .recipe-body :global(ol li) {
    margin-bottom: 0.75rem;
    padding-left: 0.25rem;
  }

  .loading, .error {
    text-align: center;
    padding: 4rem 1rem;
    color: var(--color-text-muted);
  }

  .error h2 {
    margin-bottom: 1rem;
  }

  @media (max-width: 768px) {
    .recipe-header h1 {
      font-size: 1.5rem;
    }

    .recipe-body {
      font-size: 1.1rem;
      line-height: 1.8;
    }

    .recipe-body :global(li) {
      margin-bottom: 0.6rem;
    }

    .recipe-body :global(ol li) {
      margin-bottom: 1rem;
    }
  }
</style>
```

**Step 2: Commit**

```bash
git add frontend/src/routes/recipe/
git commit -m "feat: add recipe detail page with markdown rendering"
```

---

### Task 14: Docker Setup

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

**Step 1: Create .dockerignore**

Create `.dockerignore`:
```
.git
**/__pycache__
**/node_modules
**/.svelte-kit
**/venv
backend/tests
*.md
!recipes/*.md
docs/
```

**Step 2: Create Dockerfile**

Create `Dockerfile`:
```dockerfile
# Stage 1: Build frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Production
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

# Copy built frontend into backend static directory
COPY --from=frontend-build /app/frontend/build ./app/static

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Step 3: Create docker-compose.yml**

Create `docker-compose.yml`:
```yaml
services:
  forks:
    build: .
    ports:
      - "8420:8000"
    volumes:
      - ./recipes:/data/recipes
    environment:
      - FORKS_RECIPES_DIR=/data/recipes
    restart: unless-stopped
```

**Step 4: Commit**

```bash
git add Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: add Docker setup with multi-stage build"
```

---

### Task 15: Integration Test — Verify Everything Works

**Step 1: Start backend and verify API**

```bash
cd backend && source venv/bin/activate && uvicorn app.main:app --reload &
sleep 2
curl http://localhost:8000/api/recipes | python -m json.tool
curl http://localhost:8000/api/recipes/birria-tacos | python -m json.tool
curl "http://localhost:8000/api/search?q=chicken" | python -m json.tool
```

Verify: All endpoints return expected JSON.

**Step 2: Start frontend dev server**

```bash
cd frontend && npm run dev
```

Open `http://localhost:5173` in a browser. Verify:
- Recipe cards appear in a grid
- Tag sidebar shows tags with counts
- Clicking a tag filters recipes
- Search works
- Clicking a card shows the recipe detail page
- Recipe markdown renders correctly
- Mobile layout works (resize browser)

**Step 3: Test Docker build**

```bash
docker compose up --build
```

Open `http://localhost:8420`. Verify same behavior as dev mode.

**Step 4: Run all backend tests**

```bash
cd backend && python -m pytest -v
```

Expected: All tests PASS.

**Step 5: Final commit with any fixes**

If integration testing reveals issues, fix them and commit.

---

## Summary

| Task | Description | Tests |
|------|-------------|-------|
| 1 | Backend scaffolding + deps | - |
| 2 | Sample recipes | - |
| 3 | Config module | - |
| 4 | Pydantic models | - |
| 5 | Recipe parser | 5 tests |
| 6 | In-memory index | 14 tests |
| 7 | File watcher | - |
| 8 | API routes + main.py | 11 tests |
| 9 | Frontend scaffolding | - |
| 10 | API client + markdown | - |
| 11 | Layout + styling | - |
| 12 | Recipe cards + home page | - |
| 13 | Recipe detail page | - |
| 14 | Docker setup | - |
| 15 | Integration test | manual |

**Total: 15 tasks, ~30 tests, Phase 1 complete.**
