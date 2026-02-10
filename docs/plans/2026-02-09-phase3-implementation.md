# Phase 3: Fork System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let users create named versions (forks) of any recipe with line-level diff highlighting, version switching, export, and default version preferences.

**Architecture:** Fork files live alongside base recipes as `slug.fork.name.md`, containing only modified sections with fork metadata in frontmatter. The backend handles section diffing and merge; the frontend renders diff highlights. No auth — just an optional author field. Primary version stored in browser localStorage.

**Tech Stack:** Python/FastAPI (backend), SvelteKit (frontend), python-frontmatter (parsing), existing RecipeIndex (extended for fork tracking)

---

### Task 1: Fork Models

Add Pydantic models for fork metadata and extend RecipeSummary with a forks list.

**Files:**
- Modify: `backend/app/models.py`

**Code:**

```python
from typing import List, Optional

from pydantic import BaseModel


class ForkSummary(BaseModel):
    name: str  # slug portion, e.g. "vegan"
    fork_name: str  # display name, e.g. "Vegan Chocolate Chip Cookies"
    author: Optional[str] = None
    date_added: Optional[str] = None


class RecipeSummary(BaseModel):
    slug: str
    title: str
    tags: List[str] = []
    servings: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    date_added: Optional[str] = None
    source: Optional[str] = None
    image: Optional[str] = None
    forks: List[ForkSummary] = []


class Recipe(RecipeSummary):
    content: str


class ForkDetail(ForkSummary):
    content: str  # raw markdown of modified sections


class ForkInput(BaseModel):
    fork_name: str
    author: Optional[str] = None
    title: str
    tags: List[str] = []
    servings: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    source: Optional[str] = None
    image: Optional[str] = None
    ingredients: List[str] = []
    instructions: List[str] = []
    notes: List[str] = []
```

**Tests:** None needed — these are just data models. They'll be tested implicitly by later tasks.

**Commit:** `feat: add fork models (ForkSummary, ForkDetail, ForkInput)`

---

### Task 2: Section Parser Utility

A utility module for parsing markdown into sections, comparing sections, generating fork markdown, and merging base+fork content.

**Files:**
- Create: `backend/app/sections.py`
- Create: `backend/tests/test_sections.py`

**Key functions:**

```python
"""Section-level parsing, diffing, and merging for the fork system."""

import datetime
import re
from typing import Dict, List, Optional, Tuple


def parse_sections(content: str) -> Dict[str, str]:
    """Parse markdown body (after frontmatter) into {section_name: content}.

    Splits on '## ' headers. Content before the first ## header is stored
    under the key '_preamble' (usually the '# Title' line).

    Returns:
        {"_preamble": "# Title\n", "Ingredients": "- flour\n- sugar\n", ...}
    """
    sections = {}
    current_key = "_preamble"
    current_lines = []

    for line in content.split("\n"):
        match = re.match(r"^##\s+(.+)$", line)
        if match:
            # Save previous section
            sections[current_key] = "\n".join(current_lines).strip()
            current_key = match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)

    # Save final section
    sections[current_key] = "\n".join(current_lines).strip()

    # Remove empty sections
    return {k: v for k, v in sections.items() if v}


def sections_from_recipe_data(
    ingredients: List[str],
    instructions: List[str],
    notes: List[str],
) -> Dict[str, str]:
    """Convert structured recipe data to section content strings.

    Used to compare submitted fork data against base recipe sections.
    """
    sections = {}
    if ingredients:
        sections["Ingredients"] = "\n".join(f"- {item}" for item in ingredients)
    if instructions:
        sections["Instructions"] = "\n".join(
            f"{i}. {step}" for i, step in enumerate(instructions, 1)
        )
    if notes:
        sections["Notes"] = "\n".join(f"- {note}" for note in notes)
    return sections


def diff_sections(
    base_content: str,
    fork_ingredients: List[str],
    fork_instructions: List[str],
    fork_notes: List[str],
) -> Dict[str, str]:
    """Compare fork data against base recipe content.

    Returns only the sections that differ from the base.
    """
    base_sections = parse_sections(base_content)
    fork_sections = sections_from_recipe_data(
        fork_ingredients, fork_instructions, fork_notes
    )

    changed = {}
    for key in ("Ingredients", "Instructions", "Notes"):
        base_text = _normalize(base_sections.get(key, ""))
        fork_text = _normalize(fork_sections.get(key, ""))
        if fork_text != base_text:
            if fork_text:  # Only include if fork has content
                changed[key] = fork_sections[key]
            elif base_text:  # Fork removed the section entirely
                changed[key] = ""
    return changed


def generate_fork_markdown(
    forked_from: str,
    fork_name: str,
    changed_sections: Dict[str, str],
    author: Optional[str] = None,
) -> str:
    """Generate a fork markdown file with frontmatter and changed sections."""
    lines = []

    # Frontmatter
    lines.append("---")
    lines.append(f"forked_from: {forked_from}")
    lines.append(f"fork_name: {fork_name}")
    if author:
        lines.append(f"author: {author}")
    lines.append(f"date_added: {datetime.date.today().isoformat()}")
    lines.append("---")

    # Changed sections
    for section_name, content in changed_sections.items():
        if content:  # Skip empty sections (removals)
            lines.append("")
            lines.append(f"## {section_name}")
            lines.append("")
            lines.append(content)

    lines.append("")
    return "\n".join(lines)


def merge_content(base_content: str, fork_content: str) -> str:
    """Merge base recipe content with fork modifications.

    For each section: use fork version if present, otherwise use base.
    Returns complete merged markdown body.
    """
    base_sections = parse_sections(base_content)
    fork_sections = parse_sections(fork_content)

    # Start with preamble from base
    lines = []
    preamble = base_sections.get("_preamble", "")
    if preamble:
        lines.append(preamble)

    # Merge each section — maintain base section order, overlay fork
    seen_sections = set()
    for section_name in base_sections:
        if section_name == "_preamble":
            continue
        seen_sections.add(section_name)
        content = fork_sections.get(section_name, base_sections[section_name])
        if content:  # Skip sections that fork explicitly emptied
            lines.append("")
            lines.append(f"## {section_name}")
            lines.append("")
            lines.append(content)

    # Add any fork-only sections not in base
    for section_name in fork_sections:
        if section_name == "_preamble" or section_name in seen_sections:
            continue
        content = fork_sections[section_name]
        if content:
            lines.append("")
            lines.append(f"## {section_name}")
            lines.append("")
            lines.append(content)

    lines.append("")
    return "\n".join(lines)


def _normalize(text: str) -> str:
    """Normalize section text for comparison — strip, collapse whitespace."""
    return re.sub(r"\s+", " ", text.strip())
```

**Tests:**

```python
"""Tests for the sections utility module."""

from app.sections import (
    parse_sections,
    sections_from_recipe_data,
    diff_sections,
    generate_fork_markdown,
    merge_content,
)


class TestParseSections:
    def test_splits_on_h2_headers(self):
        content = "# Title\n\n## Ingredients\n\n- flour\n- sugar\n\n## Instructions\n\n1. Mix"
        sections = parse_sections(content)
        assert "Ingredients" in sections
        assert "Instructions" in sections
        assert "- flour" in sections["Ingredients"]

    def test_preamble_captured(self):
        content = "# My Recipe\n\nSome intro text\n\n## Ingredients\n\n- flour"
        sections = parse_sections(content)
        assert "_preamble" in sections
        assert "My Recipe" in sections["_preamble"]

    def test_empty_content(self):
        sections = parse_sections("")
        assert sections == {}

    def test_no_sections(self):
        sections = parse_sections("# Just a title")
        assert "_preamble" in sections


class TestSectionsFromRecipeData:
    def test_ingredients_formatted(self):
        result = sections_from_recipe_data(["flour", "sugar"], [], [])
        assert result["Ingredients"] == "- flour\n- sugar"

    def test_instructions_numbered(self):
        result = sections_from_recipe_data([], ["Mix", "Bake"], [])
        assert result["Instructions"] == "1. Mix\n2. Bake"

    def test_notes_formatted(self):
        result = sections_from_recipe_data([], [], ["Great recipe"])
        assert result["Notes"] == "- Great recipe"

    def test_empty_lists_excluded(self):
        result = sections_from_recipe_data([], [], [])
        assert result == {}


class TestDiffSections:
    def test_detects_changed_ingredients(self):
        base = "# Title\n\n## Ingredients\n\n- flour\n- 2 eggs\n\n## Instructions\n\n1. Mix"
        changed = diff_sections(base, ["flour", "2 flax eggs"], ["Mix"], [])
        assert "Ingredients" in changed
        assert "Instructions" not in changed

    def test_no_changes_returns_empty(self):
        base = "# Title\n\n## Ingredients\n\n- flour\n\n## Instructions\n\n1. Mix"
        changed = diff_sections(base, ["flour"], ["Mix"], [])
        assert changed == {}

    def test_added_notes_detected(self):
        base = "# Title\n\n## Ingredients\n\n- flour"
        changed = diff_sections(base, ["flour"], [], ["New note"])
        assert "Notes" in changed


class TestGenerateForkMarkdown:
    def test_produces_valid_frontmatter(self):
        result = generate_fork_markdown(
            "chocolate-chip-cookies", "Vegan Version",
            {"Ingredients": "- coconut oil"},
            author="CJ",
        )
        assert "forked_from: chocolate-chip-cookies" in result
        assert "fork_name: Vegan Version" in result
        assert "author: CJ" in result

    def test_includes_changed_sections(self):
        result = generate_fork_markdown(
            "test", "Fork",
            {"Ingredients": "- flour\n- sugar", "Notes": "- Tasty"},
        )
        assert "## Ingredients" in result
        assert "## Notes" in result
        assert "- flour" in result

    def test_no_author_omitted(self):
        result = generate_fork_markdown("test", "Fork", {"Ingredients": "- flour"})
        assert "author:" not in result


class TestMergeContent:
    def test_fork_section_replaces_base(self):
        base = "# Title\n\n## Ingredients\n\n- flour\n- 2 eggs\n\n## Instructions\n\n1. Mix"
        fork = "## Ingredients\n\n- flour\n- 2 flax eggs"
        merged = merge_content(base, fork)
        assert "2 flax eggs" in merged
        assert "2 eggs" not in merged
        assert "1. Mix" in merged  # Instructions inherited

    def test_base_sections_preserved_when_no_fork(self):
        base = "# Title\n\n## Ingredients\n\n- flour\n\n## Instructions\n\n1. Mix\n\n## Notes\n\n- Good"
        fork = "## Notes\n\n- Even better"
        merged = merge_content(base, fork)
        assert "- flour" in merged
        assert "1. Mix" in merged
        assert "Even better" in merged
        assert "- Good" not in merged

    def test_preamble_from_base(self):
        base = "# My Recipe\n\n## Ingredients\n\n- flour"
        fork = "## Ingredients\n\n- whole wheat flour"
        merged = merge_content(base, fork)
        assert "# My Recipe" in merged
```

**Commit:** `feat: add section parser utility for fork diffing and merging`

---

### Task 3: Fork File Parsing & Index Integration

Extend the parser and index to detect fork files (`*.fork.*.md`), parse their frontmatter, and associate them with base recipes.

**Files:**
- Modify: `backend/app/parser.py` — add `parse_fork_frontmatter(path)` function
- Modify: `backend/app/index.py` — skip fork files during normal indexing, scan and associate forks
- Create: `backend/tests/test_fork_index.py`

**Parser addition:**

```python
# Add to parser.py

from app.models import ForkSummary


def parse_fork_frontmatter(path: Path) -> ForkSummary:
    """Parse fork file frontmatter into a ForkSummary."""
    # Extract fork name slug from filename: slug.fork.name.md -> name
    stem = path.stem  # e.g. "chocolate-chip-cookies.fork.vegan"
    parts = stem.split(".fork.")
    name = parts[-1] if len(parts) > 1 else stem

    try:
        post = frontmatter.load(path)
        meta = post.metadata
    except Exception:
        logger.warning(f"Failed to parse fork frontmatter: {path}")
        return ForkSummary(name=name, fork_name=name)

    return ForkSummary(
        name=name,
        fork_name=meta.get("fork_name", name),
        author=meta.get("author"),
        date_added=str(meta.get("date_added")) if meta.get("date_added") else None,
    )
```

**Index changes:**

```python
# Modifications to index.py

import re
from app.parser import parse_frontmatter, parse_recipe, parse_fork_frontmatter
from app.models import RecipeSummary, Recipe, ForkSummary

class RecipeIndex:
    def __init__(self, recipes_dir: Path):
        self.recipes_dir = recipes_dir
        self._index: Dict[str, RecipeSummary] = {}
        self._ingredients: Dict[str, List[str]] = {}
        self._forks: Dict[str, List[ForkSummary]] = {}  # base_slug -> [ForkSummary]

    def build(self) -> None:
        self._index.clear()
        self._ingredients.clear()
        self._forks.clear()
        if not self.recipes_dir.exists():
            logger.warning(f"Recipes directory not found: {self.recipes_dir}")
            return
        for path in self.recipes_dir.glob("*.md"):
            if self._is_fork_file(path):
                self._index_fork(path)
            else:
                self._index_file(path)
        # Attach fork lists to recipe summaries
        self._attach_forks()
        logger.info(f"Indexed {len(self._index)} recipes from {self.recipes_dir}")

    def _is_fork_file(self, path: Path) -> bool:
        return ".fork." in path.name

    def _index_fork(self, path: Path) -> None:
        base_slug = path.stem.split(".fork.")[0]
        summary = parse_fork_frontmatter(path)
        if base_slug not in self._forks:
            self._forks[base_slug] = []
        # Replace existing fork with same name
        self._forks[base_slug] = [
            f for f in self._forks[base_slug] if f.name != summary.name
        ]
        self._forks[base_slug].append(summary)

    def _attach_forks(self) -> None:
        """Attach fork summaries to their base recipe entries."""
        for slug, recipe in self._index.items():
            forks = sorted(self._forks.get(slug, []), key=lambda f: f.fork_name)
            self._index[slug] = recipe.model_copy(update={"forks": forks})

    # Updated add_or_update to handle fork files:
    def add_or_update(self, path: Path) -> None:
        if self._is_fork_file(path):
            self._index_fork(path)
            base_slug = path.stem.split(".fork.")[0]
            if base_slug in self._index:
                forks = sorted(self._forks.get(base_slug, []), key=lambda f: f.fork_name)
                self._index[base_slug] = self._index[base_slug].model_copy(
                    update={"forks": forks}
                )
        else:
            self._index_file(path)
            self._attach_forks()

    # Updated remove to handle fork files:
    def remove(self, slug_or_stem: str) -> None:
        if ".fork." in slug_or_stem:
            # It's a fork file stem: "base-slug.fork.name"
            parts = slug_or_stem.split(".fork.")
            base_slug = parts[0]
            fork_name = parts[-1]
            if base_slug in self._forks:
                self._forks[base_slug] = [
                    f for f in self._forks[base_slug] if f.name != fork_name
                ]
                if base_slug in self._index:
                    forks = sorted(self._forks.get(base_slug, []), key=lambda f: f.fork_name)
                    self._index[base_slug] = self._index[base_slug].model_copy(
                        update={"forks": forks}
                    )
        else:
            self._index.pop(slug_or_stem, None)
            self._ingredients.pop(slug_or_stem, None)
```

**Tests (`backend/tests/test_fork_index.py`):**

```python
"""Tests for fork indexing."""
import textwrap
from pathlib import Path

from app.index import RecipeIndex


def _write_recipe(path: Path, title: str, ingredients: str = "- flour"):
    path.write_text(textwrap.dedent(f"""\
        ---
        title: {title}
        tags: [test]
        ---

        # {title}

        ## Ingredients

        {ingredients}

        ## Instructions

        1. Mix everything
    """))


def _write_fork(path: Path, forked_from: str, fork_name: str, ingredients: str):
    path.write_text(textwrap.dedent(f"""\
        ---
        forked_from: {forked_from}
        fork_name: {fork_name}
        author: Test
        ---

        ## Ingredients

        {ingredients}
    """))


class TestForkIndexing:
    def test_fork_files_not_listed_as_recipes(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        _write_fork(tmp_path / "cookies.fork.vegan.md", "cookies", "Vegan Cookies", "- coconut oil")
        index = RecipeIndex(tmp_path)
        index.build()
        recipes = index.list_all()
        assert len(recipes) == 1
        assert recipes[0].slug == "cookies"

    def test_forks_attached_to_base_recipe(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        _write_fork(tmp_path / "cookies.fork.vegan.md", "cookies", "Vegan Cookies", "- coconut oil")
        _write_fork(tmp_path / "cookies.fork.gf.md", "cookies", "Gluten Free Cookies", "- gf flour")
        index = RecipeIndex(tmp_path)
        index.build()
        recipe = index.list_all()[0]
        assert len(recipe.forks) == 2
        fork_names = [f.name for f in recipe.forks]
        assert "vegan" in fork_names
        assert "gf" in fork_names

    def test_fork_summary_fields(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        _write_fork(tmp_path / "cookies.fork.vegan.md", "cookies", "Vegan Cookies", "- coconut oil")
        index = RecipeIndex(tmp_path)
        index.build()
        fork = index.list_all()[0].forks[0]
        assert fork.name == "vegan"
        assert fork.fork_name == "Vegan Cookies"
        assert fork.author == "Test"

    def test_add_fork_updates_index(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        index = RecipeIndex(tmp_path)
        index.build()
        assert len(index.list_all()[0].forks) == 0
        fork_path = tmp_path / "cookies.fork.vegan.md"
        _write_fork(fork_path, "cookies", "Vegan Cookies", "- coconut oil")
        index.add_or_update(fork_path)
        assert len(index.list_all()[0].forks) == 1

    def test_remove_fork_updates_index(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        _write_fork(tmp_path / "cookies.fork.vegan.md", "cookies", "Vegan Cookies", "- coconut oil")
        index = RecipeIndex(tmp_path)
        index.build()
        assert len(index.list_all()[0].forks) == 1
        index.remove("cookies.fork.vegan")
        assert len(index.list_all()[0].forks) == 0

    def test_recipe_without_forks_has_empty_list(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        index = RecipeIndex(tmp_path)
        index.build()
        assert index.list_all()[0].forks == []
```

**Commit:** `feat: add fork file parsing and index integration`

---

### Task 4: Fork API Routes

Backend CRUD endpoints for forks plus export.

**Files:**
- Create: `backend/app/routes/forks.py`
- Modify: `backend/app/main.py` — register fork router
- Create: `backend/tests/test_fork_routes.py`

**Routes (`backend/app/routes/forks.py`):**

```python
import logging
from pathlib import Path
from typing import Optional

import frontmatter
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.generator import slugify
from app.index import RecipeIndex
from app.models import ForkDetail, ForkInput
from app.parser import parse_recipe
from app.sections import diff_sections, generate_fork_markdown, merge_content

logger = logging.getLogger(__name__)


def create_fork_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/recipes/{slug}/forks")

    def _get_base_path(slug: str) -> Path:
        path = recipes_dir / f"{slug}.md"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Base recipe not found")
        return path

    def _get_fork_path(slug: str, fork_name_slug: str) -> Path:
        return recipes_dir / f"{slug}.fork.{fork_name_slug}.md"

    @router.get("/{fork_name_slug}")
    def get_fork(slug: str, fork_name_slug: str):
        fork_path = _get_fork_path(slug, fork_name_slug)
        if not fork_path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")
        try:
            post = frontmatter.load(fork_path)
            meta = post.metadata
            return ForkDetail(
                name=fork_name_slug,
                fork_name=meta.get("fork_name", fork_name_slug),
                author=meta.get("author"),
                date_added=str(meta.get("date_added")) if meta.get("date_added") else None,
                content=post.content,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("", status_code=201)
    def create_fork(slug: str, data: ForkInput):
        base_path = _get_base_path(slug)
        fork_name_slug = slugify(data.fork_name)
        if not fork_name_slug:
            raise HTTPException(status_code=400, detail="Invalid fork name")

        fork_path = _get_fork_path(slug, fork_name_slug)
        if fork_path.exists():
            raise HTTPException(
                status_code=409,
                detail=f"Fork '{fork_name_slug}' already exists",
            )

        # Read base recipe content
        post = frontmatter.load(base_path)
        base_content = post.content

        # Diff to find changed sections
        changed = diff_sections(
            base_content, data.ingredients, data.instructions, data.notes
        )
        if not changed:
            raise HTTPException(
                status_code=400,
                detail="No changes detected compared to the base recipe",
            )

        # Generate and write fork file
        markdown = generate_fork_markdown(
            forked_from=slug,
            fork_name=data.fork_name,
            changed_sections=changed,
            author=data.author,
        )
        fork_path.write_text(markdown)
        index.add_or_update(fork_path)

        return {"name": fork_name_slug, "fork_name": data.fork_name}

    @router.put("/{fork_name_slug}")
    def update_fork(slug: str, fork_name_slug: str, data: ForkInput):
        base_path = _get_base_path(slug)
        fork_path = _get_fork_path(slug, fork_name_slug)
        if not fork_path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        post = frontmatter.load(base_path)
        base_content = post.content

        changed = diff_sections(
            base_content, data.ingredients, data.instructions, data.notes
        )
        if not changed:
            raise HTTPException(
                status_code=400,
                detail="No changes detected compared to the base recipe",
            )

        markdown = generate_fork_markdown(
            forked_from=slug,
            fork_name=data.fork_name,
            changed_sections=changed,
            author=data.author,
        )
        fork_path.write_text(markdown)
        index.add_or_update(fork_path)

        return {"name": fork_name_slug, "fork_name": data.fork_name}

    @router.delete("/{fork_name_slug}", status_code=204)
    def delete_fork(slug: str, fork_name_slug: str):
        fork_path = _get_fork_path(slug, fork_name_slug)
        if not fork_path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")
        fork_path.unlink()
        index.remove(f"{slug}.fork.{fork_name_slug}")

    @router.get("/{fork_name_slug}/export")
    def export_fork(slug: str, fork_name_slug: str):
        base_path = _get_base_path(slug)
        fork_path = _get_fork_path(slug, fork_name_slug)
        if not fork_path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        base_post = frontmatter.load(base_path)
        fork_post = frontmatter.load(fork_path)

        merged = merge_content(base_post.content, fork_post.content)

        # Build standalone markdown with base frontmatter
        meta = dict(base_post.metadata)
        meta["title"] = fork_post.metadata.get("fork_name", meta.get("title", ""))
        if fork_post.metadata.get("author"):
            meta["author"] = fork_post.metadata["author"]

        lines = ["---"]
        for key, value in meta.items():
            if isinstance(value, list):
                lines.append(f"{key}: [{', '.join(str(v) for v in value)}]")
            else:
                lines.append(f"{key}: {value}")
        lines.append("---")
        lines.append("")
        lines.append(merged)

        filename = f"{slug}-{fork_name_slug}.md"
        return PlainTextResponse(
            "\n".join(lines),
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    return router
```

**Register in main.py — add these lines:**

```python
from app.routes.forks import create_fork_router

# In create_app(), after existing router registrations:
app.include_router(create_fork_router(index, recipes_path))
```

**Tests (`backend/tests/test_fork_routes.py`):**

```python
"""Tests for fork API routes."""
import textwrap
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def setup(tmp_path):
    recipes_dir = tmp_path / "recipes"
    recipes_dir.mkdir()
    recipe = recipes_dir / "cookies.md"
    recipe.write_text(textwrap.dedent("""\
        ---
        title: Chocolate Chip Cookies
        tags: [dessert]
        ---

        # Chocolate Chip Cookies

        ## Ingredients

        - 2 cups flour
        - 1 cup butter
        - 2 eggs
        - 1 cup chocolate chips

        ## Instructions

        1. Cream butter and sugar
        2. Add eggs
        3. Mix in flour
        4. Fold in chocolate chips
        5. Bake at 350F for 12 minutes
    """))
    app = create_app(recipes_dir=recipes_dir)
    client = TestClient(app)
    return client, recipes_dir


class TestCreateFork:
    def test_creates_fork_file(self, setup):
        client, recipes_dir = setup
        res = client.post("/api/recipes/cookies/forks", json={
            "fork_name": "Vegan Cookies",
            "author": "CJ",
            "title": "Chocolate Chip Cookies",
            "ingredients": ["2 cups flour", "1 cup coconut oil", "2 flax eggs", "1 cup dark chocolate chips"],
            "instructions": ["Cream butter and sugar", "Add eggs", "Mix in flour", "Fold in chocolate chips", "Bake at 350F for 12 minutes"],
            "notes": [],
        })
        assert res.status_code == 201
        assert res.json()["name"] == "vegan-cookies"
        assert (recipes_dir / "cookies.fork.vegan-cookies.md").exists()

    def test_rejects_no_changes(self, setup):
        client, _ = setup
        res = client.post("/api/recipes/cookies/forks", json={
            "fork_name": "Same Recipe",
            "title": "Chocolate Chip Cookies",
            "ingredients": ["2 cups flour", "1 cup butter", "2 eggs", "1 cup chocolate chips"],
            "instructions": ["Cream butter and sugar", "Add eggs", "Mix in flour", "Fold in chocolate chips", "Bake at 350F for 12 minutes"],
            "notes": [],
        })
        assert res.status_code == 400

    def test_rejects_duplicate_fork_name(self, setup):
        client, _ = setup
        data = {
            "fork_name": "Vegan Cookies",
            "title": "Chocolate Chip Cookies",
            "ingredients": ["2 cups flour", "1 cup coconut oil"],
            "instructions": ["Mix"],
            "notes": [],
        }
        client.post("/api/recipes/cookies/forks", json=data)
        res = client.post("/api/recipes/cookies/forks", json=data)
        assert res.status_code == 409

    def test_404_for_nonexistent_base(self, setup):
        client, _ = setup
        res = client.post("/api/recipes/nope/forks", json={
            "fork_name": "Test",
            "title": "Test",
            "ingredients": ["flour"],
            "instructions": ["mix"],
            "notes": [],
        })
        assert res.status_code == 404


class TestGetFork:
    def test_returns_fork_content(self, setup):
        client, _ = setup
        client.post("/api/recipes/cookies/forks", json={
            "fork_name": "Vegan Cookies",
            "author": "CJ",
            "title": "Chocolate Chip Cookies",
            "ingredients": ["2 cups flour", "coconut oil"],
            "instructions": ["Cream butter and sugar", "Add eggs", "Mix in flour", "Fold in chocolate chips", "Bake at 350F for 12 minutes"],
            "notes": [],
        })
        res = client.get("/api/recipes/cookies/forks/vegan-cookies")
        assert res.status_code == 200
        data = res.json()
        assert data["fork_name"] == "Vegan Cookies"
        assert data["author"] == "CJ"
        assert "coconut oil" in data["content"]

    def test_404_for_nonexistent_fork(self, setup):
        client, _ = setup
        res = client.get("/api/recipes/cookies/forks/nope")
        assert res.status_code == 404


class TestDeleteFork:
    def test_deletes_fork(self, setup):
        client, recipes_dir = setup
        client.post("/api/recipes/cookies/forks", json={
            "fork_name": "Vegan Cookies",
            "title": "Chocolate Chip Cookies",
            "ingredients": ["coconut oil"],
            "instructions": ["Mix"],
            "notes": [],
        })
        assert (recipes_dir / "cookies.fork.vegan-cookies.md").exists()
        res = client.delete("/api/recipes/cookies/forks/vegan-cookies")
        assert res.status_code == 204
        assert not (recipes_dir / "cookies.fork.vegan-cookies.md").exists()


class TestExportFork:
    def test_exports_merged_markdown(self, setup):
        client, _ = setup
        client.post("/api/recipes/cookies/forks", json={
            "fork_name": "Vegan Cookies",
            "author": "CJ",
            "title": "Chocolate Chip Cookies",
            "ingredients": ["2 cups flour", "coconut oil"],
            "instructions": ["Cream butter and sugar", "Add eggs", "Mix in flour", "Fold in chocolate chips", "Bake at 350F for 12 minutes"],
            "notes": [],
        })
        res = client.get("/api/recipes/cookies/forks/vegan-cookies/export")
        assert res.status_code == 200
        body = res.text
        assert "coconut oil" in body
        assert "Cream butter and sugar" in body  # Instructions inherited from base
        assert "Vegan Cookies" in body


class TestForksInRecipeList:
    def test_recipe_includes_fork_list(self, setup):
        client, _ = setup
        client.post("/api/recipes/cookies/forks", json={
            "fork_name": "Vegan Cookies",
            "title": "Chocolate Chip Cookies",
            "ingredients": ["coconut oil"],
            "instructions": ["Mix"],
            "notes": [],
        })
        res = client.get("/api/recipes")
        recipes = res.json()
        assert len(recipes) == 1
        assert len(recipes[0]["forks"]) == 1
        assert recipes[0]["forks"][0]["fork_name"] == "Vegan Cookies"
```

**Commit:** `feat: add fork CRUD API routes with export`

---

### Task 5: Watcher Support for Fork Files

The existing watcher already handles all `.md` files, but the `_handle_update` method uses `path.stem` as the slug for removal. Update it to pass the full stem (which includes `.fork.name`) so the index can distinguish fork files from base recipes.

**Files:**
- Modify: `backend/app/watcher.py`

**Change in `_handle_update`:**

```python
def _handle_update(self, path: Path) -> None:
    if path.exists():
        logger.info(f"File updated: {path.name}")
        self.index.add_or_update(path)
    else:
        stem = path.stem  # e.g. "cookies.fork.vegan" or "cookies"
        logger.info(f"File deleted: {stem}")
        self.index.remove(stem)
```

This is a minimal change — the watcher already triggers on `.md` file events. The `add_or_update` call works because `RecipeIndex.add_or_update` now checks `_is_fork_file()`. The `remove` call works because `RecipeIndex.remove` now handles both `slug` and `slug.fork.name` stems.

**Commit:** `feat: update watcher to handle fork file events`

---

### Task 6: Frontend Types & API Client

Update TypeScript types and add fork API functions.

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

**Updated types.ts:**

```typescript
export interface ForkSummary {
  name: string;
  fork_name: string;
  author: string | null;
  date_added: string | null;
}

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
  forks: ForkSummary[];
}

export interface Recipe extends RecipeSummary {
  content: string;
}

export interface ForkDetail extends ForkSummary {
  content: string;
}

export interface ForkInput {
  fork_name: string;
  author: string | null;
  title: string;
  tags: string[];
  servings: string | null;
  prep_time: string | null;
  cook_time: string | null;
  source: string | null;
  image: string | null;
  ingredients: string[];
  instructions: string[];
  notes: string[];
}

// Keep existing types:
export interface ScrapeResponse {
  title: string | null;
  tags: string[];
  ingredients: string[];
  instructions: string[];
  prep_time: string | null;
  cook_time: string | null;
  total_time: string | null;
  servings: string | null;
  image_url: string | null;
  source: string;
  notes: string | null;
}

export interface RecipeInput {
  title: string;
  tags: string[];
  servings: string | null;
  prep_time: string | null;
  cook_time: string | null;
  source: string | null;
  image: string | null;
  ingredients: string[];
  instructions: string[];
  notes: string[];
}
```

**New API functions (add to api.ts):**

```typescript
import type { ForkDetail, ForkInput } from './types';

export async function getFork(slug: string, forkName: string): Promise<ForkDetail> {
  const res = await fetch(`${BASE}/recipes/${slug}/forks/${forkName}`);
  if (!res.ok) throw new Error('Fork not found');
  return res.json();
}

export async function createFork(slug: string, data: ForkInput): Promise<{ name: string; fork_name: string }> {
  const res = await fetch(`${BASE}/recipes/${slug}/forks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Create fork failed' }));
    throw new Error(err.detail || 'Create fork failed');
  }
  return res.json();
}

export async function updateFork(slug: string, forkName: string, data: ForkInput): Promise<{ name: string; fork_name: string }> {
  const res = await fetch(`${BASE}/recipes/${slug}/forks/${forkName}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Update fork failed' }));
    throw new Error(err.detail || 'Update fork failed');
  }
  return res.json();
}

export async function deleteFork(slug: string, forkName: string): Promise<void> {
  const res = await fetch(`${BASE}/recipes/${slug}/forks/${forkName}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Delete fork failed');
}

export function exportForkUrl(slug: string, forkName: string): string {
  return `${BASE}/recipes/${slug}/forks/${forkName}/export`;
}
```

**Commit:** `feat: add fork types and API client functions`

---

### Task 7: Recipe Detail Page — Version Selector & Fork Viewing

Add a version selector to the recipe detail page that lets users switch between the original recipe and its forks. When viewing a fork, merge the content and highlight changed sections.

**Files:**
- Create: `frontend/src/lib/sections.ts` — client-side section parsing and merge
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte` — add version selector

**Section utilities (`frontend/src/lib/sections.ts`):**

```typescript
export interface Section {
  name: string;
  content: string;
}

/**
 * Parse markdown body into sections.
 * Returns array of {name, content} preserving order.
 */
export function parseSections(markdown: string): Section[] {
  const sections: Section[] = [];
  let currentName = '_preamble';
  let currentLines: string[] = [];

  for (const line of markdown.split('\n')) {
    const match = line.match(/^##\s+(.+)$/);
    if (match) {
      const content = currentLines.join('\n').trim();
      if (content) {
        sections.push({ name: currentName, content });
      }
      currentName = match[1].trim();
      currentLines = [];
    } else {
      currentLines.push(line);
    }
  }

  const content = currentLines.join('\n').trim();
  if (content) {
    sections.push({ name: currentName, content });
  }

  return sections;
}

/**
 * Merge base content with fork content.
 * Fork sections replace base sections; unmodified sections inherited.
 */
export function mergeContent(baseMarkdown: string, forkMarkdown: string): string {
  const baseSections = parseSections(baseMarkdown);
  const forkSections = parseSections(forkMarkdown);
  const forkMap = new Map(forkSections.map(s => [s.name, s.content]));

  const lines: string[] = [];
  for (const section of baseSections) {
    const content = forkMap.get(section.name) ?? section.content;
    if (section.name === '_preamble') {
      lines.push(content);
    } else {
      lines.push('');
      lines.push(`## ${section.name}`);
      lines.push('');
      lines.push(content);
    }
  }

  return lines.join('\n');
}

/**
 * Get set of section names that the fork modifies.
 */
export function getModifiedSections(forkMarkdown: string): Set<string> {
  const sections = parseSections(forkMarkdown);
  return new Set(sections.filter(s => s.name !== '_preamble').map(s => s.name));
}
```

**Updated recipe detail page (`frontend/src/routes/recipe/[slug]/+page.svelte`):**

The page needs to:
1. Show a version selector when `recipe.forks.length > 0`
2. Load fork content when a fork is selected
3. Merge base + fork content and render
4. Highlight modified sections with a subtle CSS class
5. Persist the default fork in localStorage
6. Add "Fork this recipe" and "Export" buttons

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { getRecipe, getFork, exportForkUrl } from '$lib/api';
  import { renderMarkdown } from '$lib/markdown';
  import { mergeContent, getModifiedSections, parseSections } from '$lib/sections';
  import type { Recipe, ForkDetail } from '$lib/types';

  let recipe: Recipe | null = null;
  let loading = true;
  let error = false;

  // Fork state
  let selectedFork: string | null = null; // null = original
  let forkDetail: ForkDetail | null = null;
  let forkLoading = false;
  let modifiedSections: Set<string> = new Set();

  $: slug = $page.params.slug;

  onMount(async () => {
    try {
      recipe = await getRecipe(slug);
      // Check localStorage for default fork
      const defaultFork = localStorage.getItem(`forks-default-${slug}`);
      if (defaultFork && recipe.forks.some(f => f.name === defaultFork)) {
        await selectFork(defaultFork);
      }
    } catch (e) {
      error = true;
    }
    loading = false;
  });

  async function selectFork(forkName: string | null) {
    selectedFork = forkName;
    forkDetail = null;
    modifiedSections = new Set();
    if (forkName && recipe) {
      forkLoading = true;
      try {
        forkDetail = await getFork(slug, forkName);
        modifiedSections = getModifiedSections(forkDetail.content);
      } catch (e) {
        forkDetail = null;
      }
      forkLoading = false;
    }
  }

  function setAsDefault() {
    if (selectedFork) {
      localStorage.setItem(`forks-default-${slug}`, selectedFork);
    } else {
      localStorage.removeItem(`forks-default-${slug}`);
    }
  }

  $: displayContent = (() => {
    if (!recipe) return '';
    if (forkDetail) {
      return mergeContent(recipe.content, forkDetail.content);
    }
    return recipe.content;
  })();

  $: displayTitle = forkDetail ? forkDetail.fork_name : recipe?.title ?? '';

  function renderWithHighlights(content: string, modified: Set<string>): string {
    if (modified.size === 0) return renderMarkdown(content);

    // Parse into sections, wrap modified ones with a marker div
    const sections = parseSections(content);
    let html = '';
    for (const section of sections) {
      if (section.name === '_preamble') {
        html += renderMarkdown(section.content);
      } else {
        const isModified = modified.has(section.name);
        const sectionMd = `## ${section.name}\n\n${section.content}`;
        if (isModified) {
          html += `<div class="fork-modified">${renderMarkdown(sectionMd)}</div>`;
        } else {
          html += renderMarkdown(sectionMd);
        }
      }
    }
    return html;
  }

  $: renderedBody = renderWithHighlights(displayContent, modifiedSections);

  $: isDefault = selectedFork
    ? localStorage.getItem(`forks-default-${slug}`) === selectedFork
    : !localStorage.getItem(`forks-default-${slug}`);
</script>

<svelte:head>
  <title>{displayTitle} - Forks</title>
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
      <h1>{displayTitle}</h1>

      {#if recipe.forks.length > 0}
        <div class="version-selector">
          <button
            class="version-pill"
            class:active={selectedFork === null}
            on:click={() => selectFork(null)}
          >
            Original
          </button>
          {#each recipe.forks as fork}
            <button
              class="version-pill"
              class:active={selectedFork === fork.name}
              on:click={() => selectFork(fork.name)}
            >
              {fork.fork_name}
            </button>
          {/each}
        </div>
        {#if !isDefault}
          <button class="set-default-link" on:click={setAsDefault}>
            Set as my default
          </button>
        {/if}
      {/if}

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

      <div class="recipe-actions">
        {#if selectedFork}
          <a href="/edit/{recipe.slug}?fork={selectedFork}" class="edit-btn">Edit Fork</a>
          <a href={exportForkUrl(recipe.slug, selectedFork)} class="edit-btn" download>Export</a>
        {:else}
          <a href="/edit/{recipe.slug}" class="edit-btn">Edit Recipe</a>
        {/if}
        <a href="/fork/{recipe.slug}" class="fork-btn">Fork This Recipe</a>
      </div>

      {#if selectedFork && forkDetail?.author}
        <p class="fork-author">by {forkDetail.author}</p>
      {/if}
    </header>

    {#if forkLoading}
      <p class="loading">Loading fork...</p>
    {:else}
      <div class="recipe-body">
        {@html renderedBody}
      </div>
    {/if}
  </article>
{/if}
```

**Additional styles to add:**

```css
  .version-selector {
    display: flex;
    gap: 0.4rem;
    flex-wrap: wrap;
    margin-bottom: 0.5rem;
  }

  .version-pill {
    padding: 0.3rem 0.8rem;
    border: 1px solid var(--color-border);
    border-radius: 999px;
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .version-pill.active {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .version-pill:hover:not(.active) {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .set-default-link {
    background: none;
    border: none;
    color: var(--color-accent);
    font-size: 0.8rem;
    cursor: pointer;
    padding: 0;
    margin-bottom: 0.75rem;
  }

  .set-default-link:hover {
    text-decoration: underline;
  }

  .fork-btn {
    display: inline-block;
    padding: 0.4rem 1rem;
    border: 1px solid var(--color-accent);
    border-radius: var(--radius);
    font-size: 0.85rem;
    color: var(--color-accent);
    text-decoration: none;
    transition: all 0.15s;
  }

  .fork-btn:hover {
    background: var(--color-accent);
    color: white;
    text-decoration: none;
  }

  .fork-author {
    font-size: 0.85rem;
    color: var(--color-text-muted);
    font-style: italic;
    margin-top: 0.25rem;
  }

  .recipe-body :global(.fork-modified) {
    border-left: 3px solid var(--color-accent);
    padding-left: 1rem;
    margin-left: -1rem;
    background: rgba(var(--color-accent-rgb, 76, 110, 245), 0.04);
    border-radius: 0 var(--radius) var(--radius) 0;
  }
```

**Commit:** `feat: add version selector and fork viewing to recipe detail page`

---

### Task 8: Fork Creation Page

A new page at `/fork/[slug]` that opens the RecipeEditor pre-populated with the base recipe data, plus fork-specific fields (fork name, author).

**Files:**
- Create: `frontend/src/routes/fork/[slug]/+page.svelte`

**Code:**

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getRecipe, createFork } from '$lib/api';
  import RecipeEditor from '$lib/components/RecipeEditor.svelte';
  import type { Recipe, RecipeInput, ForkInput } from '$lib/types';

  let recipe: Recipe | null = null;
  let loading = true;
  let error = '';
  let saving = false;
  let saveError = '';

  let forkName = '';
  let author = '';

  $: slug = $page.params.slug;

  onMount(async () => {
    try {
      recipe = await getRecipe(slug);
      // Pre-load last used author from localStorage
      author = localStorage.getItem('forks-author') || '';
    } catch (e) {
      error = 'Recipe not found';
    }
    loading = false;
  });

  function getInitialData(): Partial<RecipeInput> {
    if (!recipe) return {};
    // Parse the markdown content to extract ingredients, instructions, notes
    const content = recipe.content;
    const ingredients: string[] = [];
    const instructions: string[] = [];
    const notes: string[] = [];

    let currentSection = '';
    for (const line of content.split('\n')) {
      const headerMatch = line.match(/^##\s+(.+)$/);
      if (headerMatch) {
        currentSection = headerMatch[1].trim().toLowerCase();
        continue;
      }
      if (currentSection === 'ingredients' && line.trim().startsWith('- ')) {
        ingredients.push(line.trim().replace(/^-\s+/, ''));
      } else if (currentSection === 'instructions') {
        const stepMatch = line.trim().match(/^\d+\.\s+(.+)$/);
        if (stepMatch) instructions.push(stepMatch[1]);
      } else if (currentSection === 'notes' && line.trim().startsWith('- ')) {
        notes.push(line.trim().replace(/^-\s+/, ''));
      }
    }

    return {
      title: recipe.title,
      tags: recipe.tags,
      servings: recipe.servings,
      prep_time: recipe.prep_time,
      cook_time: recipe.cook_time,
      source: recipe.source,
      image: recipe.image,
      ingredients,
      instructions,
      notes,
    };
  }

  async function handleSave(data: RecipeInput) {
    if (!forkName.trim()) {
      saveError = 'Fork name is required';
      return;
    }
    saving = true;
    saveError = '';

    // Remember author for next time
    if (author.trim()) {
      localStorage.setItem('forks-author', author.trim());
    }

    const forkInput: ForkInput = {
      ...data,
      fork_name: forkName.trim(),
      author: author.trim() || null,
    };

    try {
      const result = await createFork(slug, forkInput);
      goto(`/recipe/${slug}?fork=${result.name}`);
    } catch (e: any) {
      saveError = e.message || 'Failed to create fork';
      saving = false;
    }
  }
</script>

<svelte:head>
  <title>Fork {recipe?.title || 'Recipe'} - Forks</title>
</svelte:head>

<div class="fork-page">
  <a href="/recipe/{slug}" class="back-link">&larr; Back to recipe</a>
  <h1>Fork Recipe</h1>

  {#if loading}
    <p class="loading">Loading recipe...</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else if recipe}
    <p class="fork-base">Based on: <strong>{recipe.title}</strong></p>

    <div class="fork-fields">
      <div class="field">
        <label for="fork-name">Version Name <span class="required">*</span></label>
        <input
          id="fork-name"
          type="text"
          bind:value={forkName}
          placeholder="e.g. Vegan Version, Extra Spicy, Mom's Way"
          required
        />
      </div>
      <div class="field">
        <label for="author">Author <span class="optional">(optional)</span></label>
        <input
          id="author"
          type="text"
          bind:value={author}
          placeholder="Your name"
        />
      </div>
    </div>

    {#if saveError}
      <p class="error">{saveError}</p>
    {/if}

    <RecipeEditor
      initialData={getInitialData()}
      imagePreviewUrl={recipe.image ? `/api/images/${recipe.image.replace('images/', '')}` : null}
      onSave={handleSave}
      {saving}
    />
  {/if}
</div>

<style>
  .fork-page {
    max-width: 720px;
  }

  .back-link {
    display: inline-block;
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 1rem;
  }

  .back-link:hover {
    color: var(--color-accent);
  }

  h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
  }

  .fork-base {
    font-size: 0.9rem;
    color: var(--color-text-muted);
    margin-bottom: 1.5rem;
  }

  .fork-fields {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid var(--color-border);
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  label {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-text);
  }

  .required {
    color: #c0392b;
  }

  .optional {
    font-weight: 400;
    color: var(--color-text-muted);
  }

  input {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.9rem;
    background: var(--color-surface);
    color: var(--color-text);
    outline: none;
  }

  input:focus {
    border-color: var(--color-accent);
  }

  .error {
    color: #c0392b;
    font-size: 0.9rem;
    margin-bottom: 0.75rem;
  }

  .loading {
    color: var(--color-text-muted);
    padding: 2rem 0;
  }
</style>
```

**Commit:** `feat: add fork creation page`

---

### Task 9: Fork Editing Page

Update the existing edit page to handle editing forks. When the URL has `?fork=name`, it loads the merged content into the editor and saves as a fork update.

**Files:**
- Modify: `frontend/src/routes/edit/[slug]/+page.svelte`

The edit page currently parses markdown content back into structured fields. When editing a fork, it should:
1. Load the base recipe
2. Load the fork content
3. Merge them
4. Parse the merged content into editor fields
5. On save, call `updateFork` instead of `updateRecipe`

The key change: detect `?fork=` query param, load fork data, merge, and route save to fork API.

**Code changes to the edit page script section:**

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { getRecipe, updateRecipe, deleteRecipe, getFork, updateFork, deleteFork } from '$lib/api';
  import { mergeContent } from '$lib/sections';
  import RecipeEditor from '$lib/components/RecipeEditor.svelte';
  import type { Recipe, RecipeInput, ForkInput, ForkDetail } from '$lib/types';

  let recipe: Recipe | null = null;
  let forkDetail: ForkDetail | null = null;
  let loading = true;
  let error = '';
  let saving = false;
  let saveError = '';

  $: slug = $page.params.slug;
  $: forkName = $page.url.searchParams.get('fork');

  let author = '';

  onMount(async () => {
    try {
      recipe = await getRecipe(slug);
      if (forkName) {
        forkDetail = await getFork(slug, forkName);
        author = forkDetail.author || localStorage.getItem('forks-author') || '';
      }
    } catch (e) {
      error = 'Recipe not found';
    }
    loading = false;
  });

  function getInitialData(): Partial<RecipeInput> {
    if (!recipe) return {};

    // If editing a fork, merge content first
    let content = recipe.content;
    if (forkDetail) {
      content = mergeContent(recipe.content, forkDetail.content);
    }

    const ingredients: string[] = [];
    const instructions: string[] = [];
    const notes: string[] = [];

    let currentSection = '';
    for (const line of content.split('\n')) {
      const headerMatch = line.match(/^##\s+(.+)$/);
      if (headerMatch) {
        currentSection = headerMatch[1].trim().toLowerCase();
        continue;
      }
      if (currentSection === 'ingredients' && line.trim().startsWith('- ')) {
        ingredients.push(line.trim().replace(/^-\s+/, ''));
      } else if (currentSection === 'instructions') {
        const stepMatch = line.trim().match(/^\d+\.\s+(.+)$/);
        if (stepMatch) instructions.push(stepMatch[1]);
      } else if (currentSection === 'notes' && line.trim().startsWith('- ')) {
        notes.push(line.trim().replace(/^-\s+/, ''));
      }
    }

    return {
      title: recipe.title,
      tags: recipe.tags,
      servings: recipe.servings,
      prep_time: recipe.prep_time,
      cook_time: recipe.cook_time,
      source: recipe.source,
      image: recipe.image,
      ingredients,
      instructions,
      notes,
    };
  }

  async function handleSave(data: RecipeInput) {
    saving = true;
    saveError = '';
    try {
      if (forkName && forkDetail) {
        // Save as fork update
        if (author.trim()) {
          localStorage.setItem('forks-author', author.trim());
        }
        const forkInput: ForkInput = {
          ...data,
          fork_name: forkDetail.fork_name,
          author: author.trim() || null,
        };
        await updateFork(slug, forkName, forkInput);
        goto(`/recipe/${slug}?fork=${forkName}`);
      } else {
        // Save as base recipe update
        await updateRecipe(slug, data);
        goto(`/recipe/${slug}`);
      }
    } catch (e: any) {
      saveError = e.message || 'Failed to save';
      saving = false;
    }
  }

  async function handleDelete() {
    const target = forkName ? `fork "${forkDetail?.fork_name}"` : `recipe "${recipe?.title}"`;
    if (!confirm(`Delete ${target}? This cannot be undone.`)) return;
    try {
      if (forkName) {
        await deleteFork(slug, forkName);
        goto(`/recipe/${slug}`);
      } else {
        await deleteRecipe(slug);
        goto('/');
      }
    } catch (e: any) {
      saveError = e.message || 'Failed to delete';
    }
  }
</script>
```

**Template updates:**
- Change the heading to show fork name when editing a fork
- Add author field when editing a fork
- Wire up delete to handle both cases

**Commit:** `feat: update edit page to support fork editing and deletion`

---

### Task 10: Query Param Handling & Final Polish

Handle the `?fork=name` query parameter on the recipe detail page (when redirected from fork creation), and add the `forks` field default to prevent errors on pages that read `recipe.forks`.

**Files:**
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte` — read `?fork=` param on mount
- Modify: `frontend/src/routes/+page.svelte` — handle `forks` field in recipe list (ensure it renders without errors)

**Recipe detail page change — add query param handling in onMount:**

```typescript
onMount(async () => {
  try {
    recipe = await getRecipe(slug);
    // Check query param first, then localStorage
    const queryFork = $page.url.searchParams.get('fork');
    const defaultFork = queryFork || localStorage.getItem(`forks-default-${slug}`);
    if (defaultFork && recipe.forks.some(f => f.name === defaultFork)) {
      await selectFork(defaultFork);
    }
  } catch (e) {
    error = true;
  }
  loading = false;
});
```

**Home page — ensure RecipeCard handles forks field gracefully.** The RecipeSummary now includes `forks` but the card component doesn't need to display it — just needs to not break. Optionally, show a small fork count badge.

**Commit:** `feat: handle fork query params and polish fork UI`

---

## Summary

| Task | Component | New/Modified Files |
|------|-----------|--------------------|
| 1 | Fork models | `backend/app/models.py` |
| 2 | Section parser | `backend/app/sections.py`, `backend/tests/test_sections.py` |
| 3 | Fork parsing & index | `backend/app/parser.py`, `backend/app/index.py`, `backend/tests/test_fork_index.py` |
| 4 | Fork API routes | `backend/app/routes/forks.py`, `backend/app/main.py`, `backend/tests/test_fork_routes.py` |
| 5 | Watcher updates | `backend/app/watcher.py` |
| 6 | Frontend types & API | `frontend/src/lib/types.ts`, `frontend/src/lib/api.ts` |
| 7 | Version selector & viewing | `frontend/src/lib/sections.ts`, `frontend/src/routes/recipe/[slug]/+page.svelte` |
| 8 | Fork creation page | `frontend/src/routes/fork/[slug]/+page.svelte` |
| 9 | Fork editing | `frontend/src/routes/edit/[slug]/+page.svelte` |
| 10 | Query params & polish | Multiple frontend files |
