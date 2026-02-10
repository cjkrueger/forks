# Phase 6: Meal Planner, Print View & Fork History — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a weekly meal planner with markdown storage, a print-friendly recipe view, and git-powered fork history with auto-commit.

**Architecture:** Meal planner uses a single `meal-plan.md` file with YAML frontmatter. Print view is pure CSS (@media print). Fork history reads git log from the recipes directory, with auto-commit on every file write.

**Tech Stack:** Python 3.9 (typing imports), FastAPI, python-frontmatter, subprocess (git), SvelteKit, CSS @media print

---

## Task 1: Git Helper Module

**Files:**
- Create: `backend/app/git.py`
- Create: `backend/tests/test_git.py`

**Code for `backend/app/git.py`:**

```python
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def git_init_if_needed(recipes_dir: Path) -> None:
    """Initialize a git repo in recipes_dir if one doesn't exist."""
    git_dir = recipes_dir / ".git"
    if git_dir.exists():
        return
    try:
        subprocess.run(
            ["git", "init"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        # Initial commit so we have a HEAD
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit", "--allow-empty"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
        )
        logger.info("Initialized git repo in %s", recipes_dir)
    except Exception:
        logger.exception("Failed to initialize git repo")


def git_commit(recipes_dir: Path, path: Path, message: str) -> None:
    """Stage a file and commit. Fire-and-forget: failures logged, never raised."""
    try:
        subprocess.run(
            ["git", "add", str(path.relative_to(recipes_dir))],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        logger.exception("Git commit failed: %s", message)


def git_rm(recipes_dir: Path, path: Path, message: str) -> None:
    """Remove a file from git and commit. Fire-and-forget."""
    try:
        subprocess.run(
            ["git", "rm", str(path.relative_to(recipes_dir))],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        logger.exception("Git rm failed: %s", message)


def git_log(recipes_dir: Path, path: Path, max_entries: int = 20):
    """Return list of {hash, date, message} for a file's git history."""
    try:
        result = subprocess.run(
            [
                "git", "log",
                "--format=%H|%aI|%s",
                "-n", str(max_entries),
                "--", str(path.relative_to(recipes_dir)),
            ],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        entries = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                entries.append({
                    "hash": parts[0],
                    "date": parts[1],
                    "message": parts[2],
                })
        return entries
    except Exception:
        logger.exception("Git log failed for %s", path)
        return []


def git_show(recipes_dir: Path, revision: str, path: Path) -> str:
    """Return file content at a specific git revision."""
    try:
        rel = str(path.relative_to(recipes_dir))
        result = subprocess.run(
            ["git", "show", f"{revision}:{rel}"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except Exception:
        logger.exception("Git show failed for %s at %s", path, revision)
        return ""
```

**Code for `backend/tests/test_git.py`:**

```python
import subprocess
from pathlib import Path

import pytest

from app.git import git_init_if_needed, git_commit, git_rm, git_log, git_show


@pytest.fixture
def git_repo(tmp_path):
    """Create a temp dir and init git."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmp_path), capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path), capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=str(tmp_path), capture_output=True,
    )
    return tmp_path


class TestGitInitIfNeeded:
    def test_inits_when_no_git_dir(self, tmp_path):
        git_init_if_needed(tmp_path)
        assert (tmp_path / ".git").exists()

    def test_skips_if_already_init(self, git_repo):
        git_init_if_needed(git_repo)  # should not error


class TestGitCommit:
    def test_commits_file(self, git_repo):
        f = git_repo / "test.md"
        f.write_text("hello")
        git_commit(git_repo, f, "Add test")
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=str(git_repo), capture_output=True, text=True,
        )
        assert "Add test" in result.stdout

    def test_does_not_raise_on_failure(self, git_repo):
        fake = git_repo / "nonexistent.md"
        git_commit(git_repo, fake, "Should not crash")  # no exception


class TestGitRm:
    def test_removes_and_commits(self, git_repo):
        f = git_repo / "to-delete.md"
        f.write_text("bye")
        git_commit(git_repo, f, "Add file")
        git_rm(git_repo, f, "Remove file")
        assert not f.exists()
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=str(git_repo), capture_output=True, text=True,
        )
        assert "Remove file" in result.stdout


class TestGitLog:
    def test_returns_history(self, git_repo):
        f = git_repo / "recipe.md"
        f.write_text("v1")
        git_commit(git_repo, f, "Version 1")
        f.write_text("v2")
        git_commit(git_repo, f, "Version 2")
        entries = git_log(git_repo, f)
        assert len(entries) == 2
        assert entries[0]["message"] == "Version 2"
        assert entries[1]["message"] == "Version 1"
        assert "hash" in entries[0]
        assert "date" in entries[0]

    def test_empty_for_untracked(self, git_repo):
        f = git_repo / "untracked.md"
        entries = git_log(git_repo, f)
        assert entries == []


class TestGitShow:
    def test_shows_content_at_revision(self, git_repo):
        f = git_repo / "recipe.md"
        f.write_text("version 1 content")
        git_commit(git_repo, f, "v1")
        v1_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(git_repo), capture_output=True, text=True,
        ).stdout.strip()
        f.write_text("version 2 content")
        git_commit(git_repo, f, "v2")
        content = git_show(git_repo, v1_hash, f)
        assert "version 1 content" in content

    def test_returns_empty_on_bad_revision(self, git_repo):
        f = git_repo / "recipe.md"
        content = git_show(git_repo, "badrev", f)
        assert content == ""
```

**Run:** `cd backend && python -m pytest tests/test_git.py -v`

---

## Task 2: Auto-Commit Integration

**Files:**
- Modify: `backend/app/main.py` — import git_init_if_needed, call on startup
- Modify: `backend/app/routes/editor.py` — add git_commit/git_rm after writes
- Modify: `backend/app/routes/forks.py` — add git_commit/git_rm after writes
- Modify: `backend/app/routes/cook.py` — add git_commit after writes

### main.py changes

Add import and call `git_init_if_needed` in the startup event:

```python
# Add import at top:
from app.git import git_init_if_needed

# In create_app, change the startup event:
@app.on_event("startup")
def startup():
    git_init_if_needed(recipes_path)
    start_watcher(index, recipes_path)
```

### editor.py changes

Add import at top:
```python
from app.git import git_commit, git_rm
```

Change `create_editor_router` to accept `recipes_dir` (already does). Add these calls:

After `filepath.write_text(markdown)` in `create_recipe` (line 76):
```python
git_commit(recipes_dir, filepath, f"Create recipe: {data.title}")
```

After `filepath.write_text(markdown)` in `update_recipe` (line 101):
```python
git_commit(recipes_dir, filepath, f"Update recipe: {data.title}")
```

After `index.remove(slug)` in `delete_recipe` (line 120), replace the file deletion with git_rm:
Actually, since the file is already unlinked by `filepath.unlink()` on line 112, and images aren't tracked, we need to stage the deletion. Change approach: do `git_rm` instead of `filepath.unlink()` for the recipe file. The image cleanup stays as-is.

Replace lines 112-120 with:
```python
# Remove from git (also deletes the file)
git_rm(recipes_dir, filepath, f"Delete recipe: {slug}")

# Also delete image if it exists
images_dir = recipes_dir / "images"
if images_dir.exists():
    for img in images_dir.glob(f"{slug}.*"):
        img.unlink()

index.remove(slug)
```

### forks.py changes

Add import at top:
```python
from app.git import git_commit, git_rm
```

After `path.write_text(md)` in `create_fork` (line 73):
```python
git_commit(recipes_dir, path, f"Create fork: {data.fork_name} ({slug})")
```

After `path.write_text(md)` in `update_fork` (line 101):
```python
git_commit(recipes_dir, path, f"Update fork: {data.fork_name} ({slug})")
```

Replace `path.unlink()` in `delete_fork` (line 112) with:
```python
git_rm(recipes_dir, path, f"Delete fork: {fork_name_slug} ({slug})")
```

### cook.py changes

Add import at top:
```python
from app.git import git_commit
```

After `_save(path, post)` in `add_cook_history` (line 55):
```python
git_commit(recipes_dir, path, f"Log cook: {slug}")
```

After `_save(path, post)` in `delete_cook_history` (line 70):
```python
git_commit(recipes_dir, path, f"Delete cook entry: {slug}")
```

After `_save(path, post)` in `add_favorite` (line 83):
```python
git_commit(recipes_dir, path, f"Favorite: {slug}")
```

After `_save(path, post)` in `remove_favorite` (line 97):
```python
git_commit(recipes_dir, path, f"Unfavorite: {slug}")
```

**Run:** `cd backend && python -m pytest -v` (all existing tests should still pass)

---

## Task 3: Meal Planner Backend

**Files:**
- Create: `backend/app/routes/planner.py`
- Create: `backend/tests/test_planner.py`
- Modify: `backend/app/main.py` — register planner router

**Code for `backend/app/routes/planner.py`:**

```python
import logging
from pathlib import Path
from typing import Dict, List, Optional

import frontmatter
from fastapi import APIRouter
from pydantic import BaseModel

from app.git import git_commit

logger = logging.getLogger(__name__)


class MealSlot(BaseModel):
    slug: str
    fork: Optional[str] = None


class WeekPlan(BaseModel):
    days: Dict[str, List[MealSlot]]


class SavePlanRequest(BaseModel):
    weeks: Dict[str, List[MealSlot]]


def create_planner_router(recipes_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/meal-plan")

    def _plan_path() -> Path:
        return recipes_dir / "meal-plan.md"

    def _load_plan() -> dict:
        path = _plan_path()
        if not path.exists():
            return {}
        try:
            post = frontmatter.load(path)
            return post.metadata.get("weeks", {})
        except Exception:
            logger.exception("Failed to load meal plan")
            return {}

    def _save_plan(weeks: dict) -> None:
        path = _plan_path()
        post = frontmatter.Post(content="", **{"weeks": weeks})

        # Generate human-readable body
        lines = ["# Meal Plan\n"]
        for day in sorted(weeks.keys()):
            meals = weeks[day]
            if meals:
                lines.append(f"## {day}\n")
                for meal in meals:
                    slug = meal if isinstance(meal, str) else meal.get("slug", "")
                    fork = None if isinstance(meal, str) else meal.get("fork")
                    if fork:
                        lines.append(f"- {slug} (fork: {fork})")
                    else:
                        lines.append(f"- {slug}")
                lines.append("")

        post.content = "\n".join(lines)
        path.write_text(frontmatter.dumps(post))
        git_commit(recipes_dir, path, "Update meal plan")

    @router.get("")
    def get_meal_plan(week: Optional[str] = None):
        """Get meal plan. Optional week param like '2026-W07' filters to that week's Mon-Sun."""
        weeks = _load_plan()

        if week:
            # Parse ISO week to get Mon-Sun date range
            import datetime
            try:
                # Parse "2026-W07" format
                parts = week.split("-W")
                year = int(parts[0])
                week_num = int(parts[1])
                # Monday of that week
                monday = datetime.date.fromisocalendar(year, week_num, 1)
                date_range = [(monday + datetime.timedelta(days=i)).isoformat() for i in range(7)]
                filtered = {}
                for d in date_range:
                    if d in weeks:
                        filtered[d] = weeks[d]
                    else:
                        filtered[d] = []
                return {"weeks": filtered}
            except (ValueError, IndexError):
                pass

        return {"weeks": weeks}

    @router.put("")
    def save_meal_plan(data: SavePlanRequest):
        """Save the entire meal plan. Merges with existing data."""
        existing = _load_plan()

        # Merge: update days that are provided, keep others
        for day, meals in data.weeks.items():
            serialized = []
            for meal in meals:
                entry = {"slug": meal.slug}
                if meal.fork:
                    entry["fork"] = meal.fork
                serialized.append(entry)
            if serialized:
                existing[day] = serialized
            elif day in existing:
                del existing[day]

        _save_plan(existing)
        return {"weeks": existing}

    return router
```

**Register in main.py — add import:**
```python
from app.routes.planner import create_planner_router
```

**Add router registration after cook router:**
```python
app.include_router(create_planner_router(recipes_path))
```

**Code for `backend/tests/test_planner.py`:**

```python
"""Tests for meal planner API routes."""
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def tmp_recipes(tmp_path):
    recipe = tmp_path / "birria-tacos.md"
    recipe.write_text(
        "---\ntitle: Birria Tacos\ntags: [mexican]\nservings: 6\n---\n\n"
        "# Birria Tacos\n\n## Ingredients\n\n- 2 lbs beef\n\n"
        "## Instructions\n\n1. Cook beef\n"
    )
    recipe2 = tmp_path / "chicken-soup.md"
    recipe2.write_text(
        "---\ntitle: Chicken Soup\ntags: [soup]\nservings: 8\n---\n\n"
        "# Chicken Soup\n\n## Ingredients\n\n- 1 chicken\n\n"
        "## Instructions\n\n1. Boil chicken\n"
    )
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    with patch("app.routes.planner.git_commit"):
        app = create_app(recipes_dir=tmp_recipes)
        yield TestClient(app)


class TestGetMealPlan:
    def test_empty_plan(self, client):
        resp = client.get("/api/meal-plan")
        assert resp.status_code == 200
        assert resp.json() == {"weeks": {}}

    def test_get_with_week_filter(self, client, tmp_recipes):
        # Save some data first
        client.put("/api/meal-plan", json={
            "weeks": {
                "2026-02-09": [{"slug": "birria-tacos"}],
                "2026-02-10": [{"slug": "chicken-soup"}],
                "2026-02-20": [{"slug": "birria-tacos"}],  # different week
            }
        })
        # Week 7 of 2026: Feb 9-15
        resp = client.get("/api/meal-plan?week=2026-W07")
        assert resp.status_code == 200
        data = resp.json()["weeks"]
        assert "2026-02-09" in data
        assert "2026-02-10" in data
        assert "2026-02-20" not in data

    def test_get_week_fills_empty_days(self, client, tmp_recipes):
        client.put("/api/meal-plan", json={
            "weeks": {
                "2026-02-09": [{"slug": "birria-tacos"}],
            }
        })
        resp = client.get("/api/meal-plan?week=2026-W07")
        data = resp.json()["weeks"]
        # Should have 7 days
        assert len(data) == 7
        assert data["2026-02-09"] == [{"slug": "birria-tacos"}]
        assert data["2026-02-11"] == []


class TestSaveMealPlan:
    def test_save_and_retrieve(self, client):
        resp = client.put("/api/meal-plan", json={
            "weeks": {
                "2026-02-09": [{"slug": "birria-tacos"}],
                "2026-02-10": [{"slug": "chicken-soup", "fork": "vegan"}],
            }
        })
        assert resp.status_code == 200
        data = resp.json()["weeks"]
        assert len(data["2026-02-09"]) == 1
        assert data["2026-02-09"][0]["slug"] == "birria-tacos"
        assert data["2026-02-10"][0]["fork"] == "vegan"

    def test_merge_preserves_other_days(self, client):
        client.put("/api/meal-plan", json={
            "weeks": {"2026-02-09": [{"slug": "birria-tacos"}]}
        })
        client.put("/api/meal-plan", json={
            "weeks": {"2026-02-10": [{"slug": "chicken-soup"}]}
        })
        resp = client.get("/api/meal-plan")
        data = resp.json()["weeks"]
        assert "2026-02-09" in data
        assert "2026-02-10" in data

    def test_empty_day_removes_it(self, client):
        client.put("/api/meal-plan", json={
            "weeks": {"2026-02-09": [{"slug": "birria-tacos"}]}
        })
        client.put("/api/meal-plan", json={
            "weeks": {"2026-02-09": []}
        })
        resp = client.get("/api/meal-plan")
        data = resp.json()["weeks"]
        assert "2026-02-09" not in data

    def test_multiple_meals_per_day(self, client):
        resp = client.put("/api/meal-plan", json={
            "weeks": {
                "2026-02-09": [
                    {"slug": "birria-tacos"},
                    {"slug": "chicken-soup"},
                ]
            }
        })
        assert resp.status_code == 200
        assert len(resp.json()["weeks"]["2026-02-09"]) == 2

    def test_writes_meal_plan_file(self, client, tmp_recipes):
        client.put("/api/meal-plan", json={
            "weeks": {"2026-02-09": [{"slug": "birria-tacos"}]}
        })
        plan_file = tmp_recipes / "meal-plan.md"
        assert plan_file.exists()
        content = plan_file.read_text()
        assert "birria-tacos" in content
```

**Run:** `cd backend && python -m pytest tests/test_planner.py -v`

---

## Task 4: Fork History Backend Endpoint

**Files:**
- Modify: `backend/app/routes/forks.py` — add history endpoint
- Create: `backend/tests/test_fork_history.py`

**Add to forks.py** — import `git_log` and `git_show`, add endpoint inside `create_fork_router`:

```python
# Add to imports:
from app.git import git_commit, git_rm, git_log, git_show

# Add this endpoint after export_fork, before return router:
@router.get("/{fork_name_slug}/history")
def fork_history(slug: str, fork_name_slug: str, content: bool = False):
    """Return git history for a fork file. Set content=true to include file content at each revision."""
    path = _fork_path(slug, fork_name_slug)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fork not found")

    entries = git_log(recipes_dir, path)
    if content:
        for entry in entries:
            entry["content"] = git_show(recipes_dir, entry["hash"], path)
    return {"history": entries}
```

**Code for `backend/tests/test_fork_history.py`:**

```python
"""Tests for fork history endpoint."""
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


BASE_RECIPE = textwrap.dedent("""\
    ---
    title: Test Recipe
    tags: [test]
    servings: 4
    ---

    # Test Recipe

    ## Ingredients

    - 1 cup flour
    - 2 eggs

    ## Instructions

    1. Mix ingredients
    2. Bake

    ## Notes

    - Serve warm
""")


@pytest.fixture
def tmp_recipes(tmp_path):
    recipe = tmp_path / "test-recipe.md"
    recipe.write_text(BASE_RECIPE)
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


class TestForkHistory:
    def test_404_for_missing_fork(self, client):
        resp = client.get("/api/recipes/test-recipe/forks/nonexistent/history")
        assert resp.status_code == 404

    def test_empty_history_for_new_fork(self, client, tmp_recipes):
        # Create fork without git (no git repo means empty history)
        resp = client.post("/api/recipes/test-recipe/forks", json={
            "fork_name": "Spicy",
            "author": None,
            "title": "Test Recipe",
            "tags": ["test"],
            "servings": "4",
            "prep_time": None,
            "cook_time": None,
            "source": None,
            "image": None,
            "ingredients": ["1 cup flour", "2 eggs", "1 tsp chili"],
            "instructions": ["Mix ingredients", "Bake"],
            "notes": ["Serve warm"],
        })
        assert resp.status_code == 201

        # History depends on whether git was initialized
        resp = client.get("/api/recipes/test-recipe/forks/spicy/history")
        assert resp.status_code == 200
        assert "history" in resp.json()

    def test_history_with_mock_git(self, client, tmp_recipes):
        """Test history endpoint with mocked git operations."""
        # Create the fork file manually
        fork_path = tmp_recipes / "test-recipe.fork.spicy.md"
        fork_path.write_text("---\nfork_name: Spicy\nforked_from: test-recipe\n---\n\n## Ingredients\n\n- chili\n")

        # Rebuild index
        from app.index import RecipeIndex
        mock_entries = [
            {"hash": "abc123", "date": "2026-02-09T10:00:00", "message": "Create fork: Spicy"},
            {"hash": "def456", "date": "2026-02-08T10:00:00", "message": "Update fork: Spicy"},
        ]
        with patch("app.routes.forks.git_log", return_value=mock_entries):
            resp = client.get("/api/recipes/test-recipe/forks/spicy/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["history"]) == 2
        assert data["history"][0]["hash"] == "abc123"

    def test_history_with_content(self, client, tmp_recipes):
        """Test content flag includes file content at each revision."""
        fork_path = tmp_recipes / "test-recipe.fork.spicy.md"
        fork_path.write_text("---\nfork_name: Spicy\nforked_from: test-recipe\n---\n\n## Ingredients\n\n- chili\n")

        mock_entries = [
            {"hash": "abc123", "date": "2026-02-09T10:00:00", "message": "v2"},
        ]
        with patch("app.routes.forks.git_log", return_value=mock_entries):
            with patch("app.routes.forks.git_show", return_value="old content"):
                resp = client.get("/api/recipes/test-recipe/forks/spicy/history?content=true")
        assert resp.status_code == 200
        assert resp.json()["history"][0]["content"] == "old content"
```

**Run:** `cd backend && python -m pytest tests/test_fork_history.py -v`

---

## Task 5: Print-Friendly CSS & Print Button

**Files:**
- Modify: `frontend/src/app.css` — add @media print rules
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte` — add print button

### CSS @media print rules

Append to `frontend/src/app.css`:

```css
@media print {
  /* Hide UI chrome */
  .topbar,
  .sidebar,
  .overlay,
  .back-link,
  .version-selector,
  .version-pill,
  .set-default-link,
  .recipe-actions,
  .cook-btn,
  .edit-btn,
  .fork-btn,
  .grocery-btn,
  .cook-history,
  .discovery-chips,
  .tag,
  .fork-author {
    display: none !important;
  }

  /* Remove fork highlight borders */
  .fork-modified {
    border-left: none !important;
    padding-left: 0 !important;
    margin-left: 0 !important;
  }

  /* Layout resets */
  .content {
    padding: 0 !important;
    max-width: 100% !important;
  }

  .layout {
    display: block !important;
  }

  /* Typography optimization */
  .recipe {
    max-width: 100% !important;
  }

  .recipe-body {
    font-size: 11pt !important;
    line-height: 1.6 !important;
  }

  /* Show source URL as text */
  .source-link::after {
    content: " (" attr(href) ")";
    font-size: 9pt;
    color: #666;
  }

  /* No backgrounds/shadows */
  * {
    box-shadow: none !important;
  }

  body {
    background: white !important;
    color: black !important;
  }

  /* Avoid page breaks inside lists */
  li, .recipe-body ol li {
    break-inside: avoid;
  }

  ul, ol {
    break-inside: avoid-column;
  }

  h2 {
    break-after: avoid;
  }

  /* Show tags as comma text */
  .tags {
    display: block !important;
  }

  .tags .tag {
    display: inline !important;
    background: none !important;
    padding: 0 !important;
    color: #666 !important;
    font-size: 9pt !important;
  }

  .tags .tag::after {
    content: ", ";
  }

  .tags .tag:last-child::after {
    content: "";
  }
}
```

### Print button in recipe detail

Add a print button in the `recipe-actions` div in `+page.svelte`. Add after the "Fork This Recipe" link:

```svelte
<button class="print-btn" on:click={() => window.print()}>Print</button>
```

And add the CSS for it (inside the `<style>` block):

```css
.print-btn {
  display: inline-block;
  padding: 0.4rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.85rem;
  color: var(--color-text-muted);
  background: var(--color-surface);
  cursor: pointer;
  transition: all 0.15s;
}

.print-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
```

**Verify:** `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`

---

## Task 6: Meal Planner Frontend

**Files:**
- Create: `frontend/src/routes/planner/+page.svelte`
- Create: `frontend/src/lib/components/RecipePicker.svelte`
- Modify: `frontend/src/lib/api.ts` — add meal plan API functions
- Modify: `frontend/src/lib/types.ts` — add MealSlot type
- Modify: `frontend/src/routes/+layout.svelte` — add Planner link in nav

### Types in `frontend/src/lib/types.ts`

Add at end:

```typescript
export interface MealSlot {
  slug: string;
  fork?: string | null;
}

export interface WeekPlan {
  [date: string]: MealSlot[];
}
```

### API functions in `frontend/src/lib/api.ts`

Add at end:

```typescript
export async function getMealPlan(week?: string): Promise<{ weeks: Record<string, { slug: string; fork?: string }[]> }> {
  const params = week ? `?week=${encodeURIComponent(week)}` : '';
  const res = await fetch(`${BASE}/meal-plan${params}`);
  if (!res.ok) throw new Error('Failed to fetch meal plan');
  return res.json();
}

export async function saveMealPlan(weeks: Record<string, { slug: string; fork?: string | null }[]>): Promise<{ weeks: Record<string, { slug: string; fork?: string }[]> }> {
  const res = await fetch(`${BASE}/meal-plan`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ weeks }),
  });
  if (!res.ok) throw new Error('Failed to save meal plan');
  return res.json();
}

export async function getForkHistory(slug: string, forkName: string, includeContent = false): Promise<{ history: { hash: string; date: string; message: string; content?: string }[] }> {
  const params = includeContent ? '?content=true' : '';
  const res = await fetch(`${BASE}/recipes/${slug}/forks/${forkName}/history${params}`);
  if (!res.ok) throw new Error('Failed to fetch fork history');
  return res.json();
}
```

### RecipePicker component

Create `frontend/src/lib/components/RecipePicker.svelte`:

```svelte
<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { listRecipes } from '$lib/api';
  import type { RecipeSummary } from '$lib/types';

  export let exclude: string[] = [];

  const dispatch = createEventDispatcher();

  let query = '';
  let allRecipes: RecipeSummary[] = [];
  let open = false;
  let loading = true;

  $: filtered = allRecipes
    .filter(r => !exclude.includes(r.slug))
    .filter(r => !query || r.title.toLowerCase().includes(query.toLowerCase()));

  async function load() {
    loading = true;
    allRecipes = await listRecipes();
    loading = false;
  }

  function toggle() {
    if (!open) {
      load();
    }
    open = !open;
  }

  function select(recipe: RecipeSummary) {
    dispatch('select', { slug: recipe.slug, title: recipe.title });
    open = false;
    query = '';
  }
</script>

<div class="picker">
  <button class="add-btn" on:click={toggle} aria-label="Add recipe">+</button>
  {#if open}
    <div class="dropdown">
      <input
        type="text"
        placeholder="Search recipes..."
        bind:value={query}
        class="picker-search"
      />
      <div class="picker-list">
        {#if loading}
          <p class="picker-empty">Loading...</p>
        {:else if filtered.length === 0}
          <p class="picker-empty">No recipes found</p>
        {:else}
          {#each filtered as recipe}
            <button class="picker-item" on:click={() => select(recipe)}>
              {recipe.title}
            </button>
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .picker {
    position: relative;
  }

  .add-btn {
    width: 100%;
    padding: 0.35rem;
    border: 1px dashed var(--color-border);
    border-radius: var(--radius);
    background: transparent;
    color: var(--color-text-muted);
    font-size: 1.1rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .add-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    min-width: 200px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    z-index: 10;
    margin-top: 0.25rem;
  }

  .picker-search {
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: none;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.85rem;
    outline: none;
    background: transparent;
    color: var(--color-text);
  }

  .picker-list {
    max-height: 200px;
    overflow-y: auto;
  }

  .picker-item {
    display: block;
    width: 100%;
    padding: 0.5rem 0.75rem;
    border: none;
    background: transparent;
    text-align: left;
    font-size: 0.85rem;
    color: var(--color-text);
    cursor: pointer;
    transition: background 0.1s;
  }

  .picker-item:hover {
    background: var(--color-accent-light);
    color: var(--color-accent);
  }

  .picker-empty {
    padding: 0.75rem;
    font-size: 0.8rem;
    color: var(--color-text-muted);
    text-align: center;
  }
</style>
```

### Planner page

Create `frontend/src/routes/planner/+page.svelte`:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { getMealPlan, saveMealPlan, listRecipes } from '$lib/api';
  import type { RecipeSummary } from '$lib/types';
  import RecipePicker from '$lib/components/RecipePicker.svelte';

  interface PlanSlot {
    slug: string;
    title: string;
    fork?: string | null;
  }

  let weekOffset = 0;
  let days: { date: string; label: string; meals: PlanSlot[] }[] = [];
  let loading = true;
  let saving = false;
  let allRecipes: RecipeSummary[] = [];

  const DAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  function getWeekDates(offset: number): { isoWeek: string; dates: string[] } {
    const now = new Date();
    const day = now.getDay();
    const mondayOffset = day === 0 ? -6 : 1 - day;
    const monday = new Date(now);
    monday.setDate(now.getDate() + mondayOffset + offset * 7);

    const dates: string[] = [];
    for (let i = 0; i < 7; i++) {
      const d = new Date(monday);
      d.setDate(monday.getDate() + i);
      dates.push(d.toISOString().split('T')[0]);
    }

    // ISO week number
    const jan4 = new Date(monday.getFullYear(), 0, 4);
    const weekNum = Math.ceil(((monday.getTime() - jan4.getTime()) / 86400000 + jan4.getDay() + 1) / 7);
    const isoWeek = `${monday.getFullYear()}-W${String(weekNum).padStart(2, '0')}`;

    return { isoWeek, dates };
  }

  function titleForSlug(slug: string): string {
    const recipe = allRecipes.find(r => r.slug === slug);
    return recipe?.title || slug;
  }

  async function loadWeek() {
    loading = true;
    const { isoWeek, dates } = getWeekDates(weekOffset);
    try {
      const data = await getMealPlan(isoWeek);
      days = dates.map((date, i) => ({
        date,
        label: DAY_NAMES[i],
        meals: (data.weeks[date] || []).map(m => ({
          slug: m.slug,
          title: titleForSlug(m.slug),
          fork: m.fork || null,
        })),
      }));
    } catch (e) {
      days = dates.map((date, i) => ({ date, label: DAY_NAMES[i], meals: [] }));
    }
    loading = false;
  }

  async function save() {
    saving = true;
    const weeks: Record<string, { slug: string; fork?: string | null }[]> = {};
    for (const day of days) {
      weeks[day.date] = day.meals.map(m => {
        const entry: { slug: string; fork?: string | null } = { slug: m.slug };
        if (m.fork) entry.fork = m.fork;
        return entry;
      });
    }
    try {
      await saveMealPlan(weeks);
    } catch (e) {
      console.error('Failed to save meal plan', e);
    }
    saving = false;
  }

  function addMeal(dayIndex: number, detail: { slug: string; title: string }) {
    days[dayIndex].meals = [...days[dayIndex].meals, { slug: detail.slug, title: detail.title }];
    days = days;
    save();
  }

  function removeMeal(dayIndex: number, mealIndex: number) {
    days[dayIndex].meals = days[dayIndex].meals.filter((_, i) => i !== mealIndex);
    days = days;
    save();
  }

  onMount(async () => {
    allRecipes = await listRecipes();
    await loadWeek();
  });

  $: if (weekOffset !== undefined && allRecipes.length > 0) {
    loadWeek();
  }

  $: weekLabel = (() => {
    if (days.length === 0) return '';
    const first = days[0].date;
    const last = days[6].date;
    return `${first} – ${last}`;
  })();
</script>

<svelte:head>
  <title>Meal Planner - Forks</title>
</svelte:head>

<div class="planner">
  <div class="planner-header">
    <h1>Meal Planner</h1>
    <div class="week-nav">
      <button on:click={() => weekOffset--}>&larr;</button>
      <span class="week-label">{weekLabel}</span>
      <button on:click={() => weekOffset++}>&rarr;</button>
    </div>
  </div>

  {#if loading}
    <p class="loading">Loading...</p>
  {:else}
    <div class="week-grid">
      {#each days as day, dayIndex}
        <div class="day-column">
          <div class="day-header">
            <span class="day-name">{day.label}</span>
            <span class="day-date">{day.date.slice(5)}</span>
          </div>
          <div class="day-meals">
            {#each day.meals as meal, mealIndex}
              <div class="meal-slot">
                <a href="/recipe/{meal.slug}" class="meal-link">{meal.title}</a>
                {#if meal.fork}
                  <span class="meal-fork">({meal.fork})</span>
                {/if}
                <button class="meal-remove" on:click={() => removeMeal(dayIndex, mealIndex)} aria-label="Remove">×</button>
              </div>
            {/each}
            <RecipePicker
              exclude={day.meals.map(m => m.slug)}
              on:select={(e) => addMeal(dayIndex, e.detail)}
            />
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .planner {
    max-width: 1100px;
  }

  .planner-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .planner-header h1 {
    font-size: 1.5rem;
    font-weight: 700;
  }

  .week-nav {
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .week-nav button {
    padding: 0.3rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text);
    cursor: pointer;
    font-size: 1rem;
    transition: all 0.15s;
  }

  .week-nav button:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .week-label {
    font-size: 0.9rem;
    color: var(--color-text-muted);
    min-width: 140px;
    text-align: center;
  }

  .week-grid {
    display: grid;
    grid-template-columns: repeat(7, 1fr);
    gap: 0.75rem;
  }

  .day-column {
    min-height: 200px;
  }

  .day-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 0.5rem;
    border-bottom: 2px solid var(--color-border);
    margin-bottom: 0.5rem;
  }

  .day-name {
    font-weight: 600;
    font-size: 0.85rem;
  }

  .day-date {
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  .day-meals {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .meal-slot {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.35rem 0.5rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.8rem;
  }

  .meal-link {
    flex: 1;
    color: var(--color-text);
    text-decoration: none;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .meal-link:hover {
    color: var(--color-accent);
    text-decoration: none;
  }

  .meal-fork {
    font-size: 0.7rem;
    color: var(--color-text-muted);
    flex-shrink: 0;
  }

  .meal-remove {
    background: none;
    border: none;
    color: var(--color-text-muted);
    cursor: pointer;
    font-size: 1rem;
    line-height: 1;
    padding: 0 0.15rem;
    flex-shrink: 0;
  }

  .meal-remove:hover {
    color: var(--color-accent);
  }

  .loading {
    text-align: center;
    padding: 4rem;
    color: var(--color-text-muted);
  }

  @media (max-width: 768px) {
    .week-grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }

    .day-column {
      min-height: auto;
    }

    .day-header {
      flex-direction: row;
      justify-content: space-between;
    }
  }
</style>
```

### Layout nav link

In `frontend/src/routes/+layout.svelte`, add a Planner link in the topbar, after the `+ Add` link and before the grocery link:

```svelte
<a href="/planner" class="planner-link">Planner</a>
```

With CSS:
```css
.planner-link {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  text-decoration: none;
  transition: color 0.15s;
}

.planner-link:hover {
  color: var(--color-accent);
  text-decoration: none;
}
```

**Verify:** `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`

---

## Task 7: Fork History Frontend

**Files:**
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte` — add history button and panel
- Modify: `frontend/src/lib/api.ts` — getForkHistory (already in Task 6)

### Recipe detail page changes

Add imports:
```typescript
import { getForkHistory } from '$lib/api';
```

Add state variables:
```typescript
let historyOpen = false;
let historyEntries: { hash: string; date: string; message: string; content?: string }[] = [];
let historyLoading = false;
```

Add function:
```typescript
async function toggleHistory() {
  if (historyOpen) {
    historyOpen = false;
    return;
  }
  if (!selectedFork || !recipe) return;
  historyLoading = true;
  historyOpen = true;
  try {
    const data = await getForkHistory(recipe.slug, selectedFork);
    historyEntries = data.history;
  } catch (e) {
    historyEntries = [];
  }
  historyLoading = false;
}
```

Add "History" button in the recipe-actions div (only when a fork is selected):
```svelte
{#if selectedFork}
  <button class="history-btn" on:click={toggleHistory}>
    {historyOpen ? 'Hide History' : 'History'}
  </button>
{/if}
```

Add history panel after the recipe-actions div (inside the header):
```svelte
{#if historyOpen}
  <div class="history-panel">
    <h3>Fork History</h3>
    {#if historyLoading}
      <p class="history-loading">Loading history...</p>
    {:else if historyEntries.length === 0}
      <p class="history-empty">No history available</p>
    {:else}
      <div class="history-timeline">
        {#each historyEntries as entry}
          <div class="history-entry">
            <span class="history-date">{new Date(entry.date).toLocaleDateString()}</span>
            <span class="history-message">{entry.message}</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>
{/if}
```

CSS for history panel:
```css
.history-btn {
  display: inline-block;
  padding: 0.4rem 1rem;
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
  font-size: 0.85rem;
  color: var(--color-text-muted);
  background: var(--color-surface);
  cursor: pointer;
  transition: all 0.15s;
}

.history-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.history-panel {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius);
}

.history-panel h3 {
  font-size: 0.95rem;
  font-weight: 600;
  margin-bottom: 0.75rem;
}

.history-timeline {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.history-entry {
  display: flex;
  gap: 0.75rem;
  align-items: baseline;
  padding: 0.4rem 0;
  border-bottom: 1px solid var(--color-border);
}

.history-entry:last-child {
  border-bottom: none;
}

.history-date {
  font-size: 0.8rem;
  color: var(--color-text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}

.history-message {
  font-size: 0.85rem;
  color: var(--color-text);
}

.history-loading, .history-empty {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}
```

**Verify:** `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`

---

## Task 8: Final Integration & Tests

**Steps:**

1. Run all backend tests: `cd backend && python -m pytest -v`
2. Run frontend type check: `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`
3. Verify no regressions in existing functionality
4. Commit all changes

---

## Summary of All File Changes

### New Backend Files
- `backend/app/git.py` — Git helper (init, commit, rm, log, show)
- `backend/app/routes/planner.py` — Meal plan endpoints
- `backend/tests/test_git.py` — Git helper tests
- `backend/tests/test_planner.py` — Meal plan tests
- `backend/tests/test_fork_history.py` — Fork history tests

### New Frontend Files
- `frontend/src/routes/planner/+page.svelte` — Meal planner page
- `frontend/src/lib/components/RecipePicker.svelte` — Search dropdown

### Modified Backend Files
- `backend/app/main.py` — Register planner router, git init on startup
- `backend/app/routes/editor.py` — Add git_commit/git_rm calls
- `backend/app/routes/forks.py` — Add git_commit/git_rm calls, add history endpoint
- `backend/app/routes/cook.py` — Add git_commit calls

### Modified Frontend Files
- `frontend/src/routes/recipe/[slug]/+page.svelte` — Print button, fork history panel
- `frontend/src/routes/+layout.svelte` — Planner link in nav
- `frontend/src/lib/api.ts` — New API functions (getMealPlan, saveMealPlan, getForkHistory)
- `frontend/src/lib/types.ts` — MealSlot, WeekPlan types
- `frontend/src/app.css` — @media print rules
