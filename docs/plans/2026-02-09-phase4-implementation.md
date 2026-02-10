# Phase 4: Cook Mode Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a kitchen-optimized cook mode with step-by-step navigation, ingredient checkboxes, inline auto-detected timers, screen wake lock, cook history tracking, and recipe favorites.

**Architecture:** Cook mode is a frontend-only view toggled by a button on the recipe detail page — no new routes. The backend gets four new endpoints: cook history add/delete and favorite add/remove, all of which modify recipe frontmatter. Timer detection is a frontend utility using regex. All cook mode state is ephemeral (resets on exit).

**Tech Stack:** Python/FastAPI + python-frontmatter (backend), SvelteKit + TypeScript (frontend), Wake Lock API, Web Audio API, Notification API

---

### Task 1: Cook History & Favorite Models + Parser

Add `CookHistoryEntry` model, `cook_history` field to `RecipeSummary`/`Recipe`, and update the parser to extract `cook_history` from frontmatter.

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/parser.py`
- Create: `backend/tests/test_cook_history.py`

**Code:**

Add to `backend/app/models.py` (after `ForkSummary`, before `RecipeSummary`):

```python
class CookHistoryEntry(BaseModel):
    date: str
    fork: Optional[str] = None
```

Add `cook_history` field to `RecipeSummary`:

```python
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
    cook_history: List[CookHistoryEntry] = []
```

Update `backend/app/parser.py` — import `CookHistoryEntry` and parse it in both `parse_frontmatter` and `parse_recipe`. Add this helper at module level:

```python
def _parse_cook_history(meta: dict) -> List[CookHistoryEntry]:
    raw = meta.get("cook_history", [])
    entries = []
    for item in raw:
        if isinstance(item, dict):
            entries.append(CookHistoryEntry(
                date=str(item.get("date", "")),
                fork=item.get("fork"),
            ))
        elif isinstance(item, str):
            entries.append(CookHistoryEntry(date=item))
    return entries
```

Add `cook_history=_parse_cook_history(meta)` to both `RecipeSummary(...)` and `Recipe(...)` constructor calls in `parse_frontmatter` and `parse_recipe`.

Update import in parser.py:
```python
from app.models import Recipe, RecipeSummary, ForkSummary, CookHistoryEntry
```

Also need `from typing import List` in parser.py (if not already imported).

**Tests** (`backend/tests/test_cook_history.py`):

```python
"""Tests for cook history model and parsing."""
import textwrap
from pathlib import Path

from app.parser import parse_frontmatter, parse_recipe


def _write(path, content):
    path.write_text(textwrap.dedent(content))


class TestCookHistoryParsing:
    def test_parse_cook_history_from_frontmatter(self, tmp_path):
        _write(tmp_path / "soup.md", """\
            ---
            title: Soup
            tags: [soup]
            cook_history:
              - date: 2026-02-09
                fork: vegan
              - date: 2026-01-25
            ---

            # Soup

            ## Ingredients

            - water
        """)
        summary = parse_frontmatter(tmp_path / "soup.md")
        assert len(summary.cook_history) == 2
        assert summary.cook_history[0].date == "2026-02-09"
        assert summary.cook_history[0].fork == "vegan"
        assert summary.cook_history[1].date == "2026-01-25"
        assert summary.cook_history[1].fork is None

    def test_parse_empty_cook_history(self, tmp_path):
        _write(tmp_path / "soup.md", """\
            ---
            title: Soup
            tags: [soup]
            ---

            # Soup
        """)
        summary = parse_frontmatter(tmp_path / "soup.md")
        assert summary.cook_history == []

    def test_parse_recipe_includes_cook_history(self, tmp_path):
        _write(tmp_path / "soup.md", """\
            ---
            title: Soup
            tags: [soup]
            cook_history:
              - date: 2026-02-09
            ---

            # Soup

            ## Ingredients

            - water
        """)
        recipe = parse_recipe(tmp_path / "soup.md")
        assert len(recipe.cook_history) == 1
        assert recipe.cook_history[0].date == "2026-02-09"
```

**Run:** `backend/venv/bin/python -m pytest backend/tests/test_cook_history.py -v`

**Commit:** `git add backend/app/models.py backend/app/parser.py backend/tests/test_cook_history.py && git commit -m "feat: add cook history model and frontmatter parsing"`

---

### Task 2: Cook History & Favorite API Routes

Add four new API endpoints: cook history add/delete, favorite add/remove.

**Files:**
- Create: `backend/app/routes/cook.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_cook_routes.py`

**Code** (`backend/app/routes/cook.py`):

```python
import logging
from datetime import date
from pathlib import Path
from typing import Optional

import frontmatter
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.index import RecipeIndex

logger = logging.getLogger(__name__)


class CookHistoryInput(BaseModel):
    fork: Optional[str] = None


def create_cook_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/recipes/{slug}")

    def _load_post(slug: str):
        path = recipes_dir / f"{slug}.md"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Recipe not found")
        return path, frontmatter.load(path)

    def _save(path: Path, post) -> None:
        path.write_text(frontmatter.dumps(post))
        index.add_or_update(path)

    @router.post("/cook-history", status_code=201)
    def add_cook_history(slug: str, data: CookHistoryInput):
        path, post = _load_post(slug)
        today = str(date.today())

        history = post.metadata.get("cook_history", [])
        if not isinstance(history, list):
            history = []

        # Deduplicate: same date + fork
        for entry in history:
            if isinstance(entry, dict):
                if entry.get("date") == today and entry.get("fork") == data.fork:
                    return {"cook_history": history}
            elif isinstance(entry, str) and entry == today and data.fork is None:
                return {"cook_history": history}

        new_entry = {"date": today}
        if data.fork:
            new_entry["fork"] = data.fork
        history.insert(0, new_entry)

        post.metadata["cook_history"] = history
        _save(path, post)
        return {"cook_history": history}

    @router.delete("/cook-history/{entry_index}")
    def delete_cook_history(slug: str, entry_index: int):
        path, post = _load_post(slug)
        history = post.metadata.get("cook_history", [])
        if not isinstance(history, list):
            history = []

        if entry_index < 0 or entry_index >= len(history):
            raise HTTPException(status_code=404, detail="Cook history entry not found")

        history.pop(entry_index)
        post.metadata["cook_history"] = history
        _save(path, post)
        return {"cook_history": history}

    @router.post("/favorite", status_code=200)
    def add_favorite(slug: str):
        path, post = _load_post(slug)
        tags = post.metadata.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        if "favorite" not in tags:
            tags.append("favorite")
            post.metadata["tags"] = tags
            _save(path, post)

        return {"favorited": True}

    @router.delete("/favorite")
    def remove_favorite(slug: str):
        path, post = _load_post(slug)
        tags = post.metadata.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        if "favorite" in tags:
            tags = [t for t in tags if t != "favorite"]
            post.metadata["tags"] = tags
            _save(path, post)

        return {"favorited": False}

    return router
```

Register in `backend/app/main.py` — add import and `app.include_router(...)`:

```python
from app.routes.cook import create_cook_router
# ... after existing include_router calls:
app.include_router(create_cook_router(index, recipes_path))
```

**Tests** (`backend/tests/test_cook_routes.py`):

```python
"""Tests for cook history and favorite API routes."""
import textwrap
from pathlib import Path

import frontmatter
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


BASE_RECIPE = textwrap.dedent("""\
    ---
    title: Test Soup
    tags: [soup, dinner]
    ---

    # Test Soup

    ## Ingredients

    - water
    - salt

    ## Instructions

    1. Boil water
    2. Add salt
""")


@pytest.fixture
def setup(tmp_path):
    (tmp_path / "test-soup.md").write_text(BASE_RECIPE)
    app = create_app(recipes_dir=tmp_path)
    client = TestClient(app)
    return client, tmp_path


class TestAddCookHistory:
    def test_add_cook_entry(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/test-soup/cook-history", json={})
        assert resp.status_code == 201
        data = resp.json()
        assert len(data["cook_history"]) == 1
        assert "date" in data["cook_history"][0]

    def test_add_cook_entry_with_fork(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/test-soup/cook-history", json={"fork": "vegan"})
        assert resp.status_code == 201
        assert resp.json()["cook_history"][0]["fork"] == "vegan"

    def test_deduplicate_same_day(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/cook-history", json={})
        resp = client.post("/api/recipes/test-soup/cook-history", json={})
        assert len(resp.json()["cook_history"]) == 1

    def test_different_forks_same_day_not_deduplicated(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/cook-history", json={})
        client.post("/api/recipes/test-soup/cook-history", json={"fork": "spicy"})
        resp = client.post("/api/recipes/test-soup/cook-history", json={"fork": "vegan"})
        assert len(resp.json()["cook_history"]) == 3

    def test_cook_history_persisted_to_file(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/cook-history", json={})
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert len(post.metadata["cook_history"]) == 1

    def test_recipe_not_found(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/nonexistent/cook-history", json={})
        assert resp.status_code == 404


class TestDeleteCookHistory:
    def test_delete_entry(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/cook-history", json={})
        resp = client.delete("/api/recipes/test-soup/cook-history/0")
        assert resp.status_code == 200
        assert len(resp.json()["cook_history"]) == 0

    def test_delete_invalid_index(self, setup):
        client, tmp_path = setup
        resp = client.delete("/api/recipes/test-soup/cook-history/5")
        assert resp.status_code == 404

    def test_delete_persisted_to_file(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/cook-history", json={})
        client.delete("/api/recipes/test-soup/cook-history/0")
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert post.metadata.get("cook_history", []) == []


class TestFavorite:
    def test_add_favorite(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/test-soup/favorite")
        assert resp.status_code == 200
        assert resp.json()["favorited"] is True
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert "favorite" in post.metadata["tags"]

    def test_add_favorite_idempotent(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/favorite")
        client.post("/api/recipes/test-soup/favorite")
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert post.metadata["tags"].count("favorite") == 1

    def test_remove_favorite(self, setup):
        client, tmp_path = setup
        client.post("/api/recipes/test-soup/favorite")
        resp = client.delete("/api/recipes/test-soup/favorite")
        assert resp.json()["favorited"] is False
        post = frontmatter.load(tmp_path / "test-soup.md")
        assert "favorite" not in post.metadata["tags"]

    def test_remove_favorite_when_not_set(self, setup):
        client, tmp_path = setup
        resp = client.delete("/api/recipes/test-soup/favorite")
        assert resp.status_code == 200
        assert resp.json()["favorited"] is False

    def test_favorite_not_found(self, setup):
        client, tmp_path = setup
        resp = client.post("/api/recipes/nonexistent/favorite")
        assert resp.status_code == 404
```

**Run:** `backend/venv/bin/python -m pytest backend/tests/test_cook_routes.py -v`

**Commit:** `git add backend/app/routes/cook.py backend/app/main.py backend/tests/test_cook_routes.py && git commit -m "feat: add cook history and favorite API endpoints"`

---

### Task 3: Frontend Types & API Client Updates

Add TypeScript types and API functions for cook history and favorites.

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

**Code:**

Add to `frontend/src/lib/types.ts`:

```typescript
export interface CookHistoryEntry {
  date: string;
  fork: string | null;
}
```

Add `cook_history` to `RecipeSummary`:

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
  forks: ForkSummary[];
  cook_history: CookHistoryEntry[];
}
```

Add to `frontend/src/lib/api.ts`:

```typescript
import type { ..., CookHistoryEntry } from './types';

export async function addCookHistory(slug: string, fork?: string): Promise<{ cook_history: CookHistoryEntry[] }> {
  const body: Record<string, string> = {};
  if (fork) body.fork = fork;
  const res = await fetch(`${BASE}/recipes/${slug}/cook-history`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error('Failed to log cook');
  return res.json();
}

export async function deleteCookHistory(slug: string, index: number): Promise<{ cook_history: CookHistoryEntry[] }> {
  const res = await fetch(`${BASE}/recipes/${slug}/cook-history/${index}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete cook history entry');
  return res.json();
}

export async function addFavorite(slug: string): Promise<{ favorited: boolean }> {
  const res = await fetch(`${BASE}/recipes/${slug}/favorite`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to favorite');
  return res.json();
}

export async function removeFavorite(slug: string): Promise<{ favorited: boolean }> {
  const res = await fetch(`${BASE}/recipes/${slug}/favorite`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to unfavorite');
  return res.json();
}
```

**Commit:** `git add frontend/src/lib/types.ts frontend/src/lib/api.ts && git commit -m "feat: add cook history and favorite types and API client"`

---

### Task 4: Timer Parser Utility

A pure function that detects time references in step text and returns structured matches.

**Files:**
- Create: `frontend/src/lib/timers.ts`

**Code** (`frontend/src/lib/timers.ts`):

```typescript
export interface TimerMatch {
  startIndex: number;
  endIndex: number;
  originalText: string;
  totalSeconds: number;
  label: string;
}

const TIME_PATTERN = /(\d+(?:[./]\d+)?)\s*(?:-\s*(\d+(?:[./]\d+)?)\s*)?(seconds?|secs?|minutes?|mins?|hours?|hrs?)(?:\s+and\s+(\d+(?:[./]\d+)?)\s*(minutes?|mins?|seconds?|secs?))?/gi;

function parseNumber(s: string): number {
  if (s.includes('/')) {
    const [num, den] = s.split('/');
    return parseFloat(num) / parseFloat(den);
  }
  return parseFloat(s);
}

function unitToSeconds(unit: string): number {
  const u = unit.toLowerCase().replace(/s$/, '');
  if (u === 'hour' || u === 'hr') return 3600;
  if (u === 'minute' || u === 'min') return 60;
  if (u === 'second' || u === 'sec') return 1;
  return 60; // default to minutes
}

function formatLabel(totalSeconds: number): string {
  if (totalSeconds >= 3600) {
    const h = Math.floor(totalSeconds / 3600);
    const m = Math.round((totalSeconds % 3600) / 60);
    return m > 0 ? `${h} hr ${m} min` : `${h} hr`;
  }
  if (totalSeconds >= 60) {
    const m = Math.round(totalSeconds / 60);
    return `${m} min`;
  }
  return `${Math.round(totalSeconds)} sec`;
}

export function parseTimers(text: string): TimerMatch[] {
  const matches: TimerMatch[] = [];
  let match: RegExpExecArray | null;

  // Reset lastIndex for global regex
  TIME_PATTERN.lastIndex = 0;

  while ((match = TIME_PATTERN.exec(text)) !== null) {
    const num1 = parseNumber(match[1]);
    const num2 = match[2] ? parseNumber(match[2]) : null;
    const unit1 = match[3];
    const andNum = match[4] ? parseNumber(match[4]) : null;
    const andUnit = match[5] || null;

    // Use higher value for ranges
    const primaryValue = num2 !== null ? num2 : num1;
    let totalSeconds = primaryValue * unitToSeconds(unit1);

    // Add combined time ("1 hour and 30 minutes")
    if (andNum !== null && andUnit !== null) {
      totalSeconds += andNum * unitToSeconds(andUnit);
    }

    totalSeconds = Math.round(totalSeconds);
    if (totalSeconds <= 0) continue;

    matches.push({
      startIndex: match.index,
      endIndex: match.index + match[0].length,
      originalText: match[0],
      totalSeconds,
      label: formatLabel(totalSeconds),
    });
  }

  return matches;
}
```

**Commit:** `git add frontend/src/lib/timers.ts && git commit -m "feat: add timer detection parser utility"`

---

### Task 5: FavoriteButton & CookHistory Components

Small, self-contained components for the recipe detail page.

**Files:**
- Create: `frontend/src/lib/components/FavoriteButton.svelte`
- Create: `frontend/src/lib/components/CookHistory.svelte`

**Code** (`frontend/src/lib/components/FavoriteButton.svelte`):

```svelte
<script lang="ts">
  import { addFavorite, removeFavorite } from '$lib/api';

  export let slug: string;
  export let tags: string[];

  let favorited = tags.includes('favorite');
  let toggling = false;

  async function toggle() {
    if (toggling) return;
    toggling = true;
    const prev = favorited;
    favorited = !favorited; // optimistic
    try {
      if (favorited) {
        await addFavorite(slug);
      } else {
        await removeFavorite(slug);
      }
    } catch (e) {
      favorited = prev; // revert
    }
    toggling = false;
  }
</script>

<button
  class="favorite-btn"
  class:active={favorited}
  on:click={toggle}
  aria-label={favorited ? 'Remove from favorites' : 'Add to favorites'}
>
  <svg width="20" height="20" viewBox="0 0 24 24" fill={favorited ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
  </svg>
</button>

<style>
  .favorite-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-text-muted);
    padding: 0.25rem;
    transition: color 0.15s;
    display: flex;
    align-items: center;
  }

  .favorite-btn:hover,
  .favorite-btn.active {
    color: #e74c3c;
  }
</style>
```

**Code** (`frontend/src/lib/components/CookHistory.svelte`):

```svelte
<script lang="ts">
  import { deleteCookHistory } from '$lib/api';
  import type { CookHistoryEntry } from '$lib/types';

  export let slug: string;
  export let cookHistory: CookHistoryEntry[];

  let expanded = false;
  let deleting: number | null = null;

  function formatDate(dateStr: string): string {
    try {
      const d = new Date(dateStr + 'T00:00:00');
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return dateStr;
    }
  }

  async function handleDelete(index: number) {
    deleting = index;
    try {
      const result = await deleteCookHistory(slug, index);
      cookHistory = result.cook_history;
    } catch (e) {
      // ignore
    }
    deleting = null;
  }
</script>

{#if cookHistory.length > 0}
  <div class="cook-history">
    <button class="history-toggle" on:click={() => expanded = !expanded}>
      Last cooked {formatDate(cookHistory[0].date)}{cookHistory[0].fork ? ` (${cookHistory[0].fork})` : ''}
      {#if cookHistory.length > 1}
        <span class="history-count">({cookHistory.length} total)</span>
      {/if}
      <span class="chevron" class:open={expanded}></span>
    </button>

    {#if expanded}
      <ul class="history-list">
        {#each cookHistory as entry, i}
          <li class="history-entry">
            <span>{formatDate(entry.date)}{entry.fork ? ` - ${entry.fork}` : ''}</span>
            <button
              class="delete-entry"
              on:click={() => handleDelete(i)}
              disabled={deleting === i}
              aria-label="Delete entry"
            >x</button>
          </li>
        {/each}
      </ul>
    {/if}
  </div>
{/if}

<style>
  .cook-history {
    margin-bottom: 0.75rem;
  }

  .history-toggle {
    background: none;
    border: none;
    color: var(--color-text-muted);
    font-size: 0.85rem;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }

  .history-toggle:hover {
    color: var(--color-accent);
  }

  .history-count {
    color: var(--color-text-muted);
    font-size: 0.8rem;
  }

  .chevron {
    display: inline-block;
    width: 0;
    height: 0;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid currentColor;
    transition: transform 0.15s;
  }

  .chevron.open {
    transform: rotate(180deg);
  }

  .history-list {
    list-style: none;
    padding: 0;
    margin-top: 0.5rem;
    margin-left: 0.5rem;
  }

  .history-entry {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.25rem 0;
    font-size: 0.8rem;
    color: var(--color-text-muted);
  }

  .delete-entry {
    background: none;
    border: none;
    color: var(--color-text-muted);
    cursor: pointer;
    font-size: 0.75rem;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
  }

  .delete-entry:hover {
    background: #fdf0f0;
    color: #c0392b;
  }
</style>
```

**Commit:** `git add frontend/src/lib/components/FavoriteButton.svelte frontend/src/lib/components/CookHistory.svelte && git commit -m "feat: add FavoriteButton and CookHistory components"`

---

### Task 6: Timer Components (TimerChip + TimerBar)

The inline timer chips and the floating timer bar.

**Files:**
- Create: `frontend/src/lib/components/TimerChip.svelte`
- Create: `frontend/src/lib/components/TimerBar.svelte`

**Code** (`frontend/src/lib/components/TimerChip.svelte`):

```svelte
<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let label: string;
  export let totalSeconds: number;
  export let running = false;
  export let remainingSeconds: number | null = null;

  const dispatch = createEventDispatcher();

  function formatTime(secs: number): string {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function handleClick() {
    if (!running) {
      dispatch('start', { totalSeconds, label });
    }
  }
</script>

<button class="timer-chip" class:running on:click={handleClick} disabled={running}>
  {#if running && remainingSeconds !== null}
    {formatTime(remainingSeconds)}
  {:else}
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
      <polygon points="5,3 19,12 5,21" />
    </svg>
    {label}
  {/if}
</button>

<style>
  .timer-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.15rem 0.5rem;
    border: 1.5px solid var(--color-accent);
    border-radius: 999px;
    background: var(--color-accent-light, #fdf0e6);
    color: var(--color-accent);
    font-size: 0.85em;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
    vertical-align: middle;
    line-height: 1.4;
  }

  .timer-chip:hover:not(:disabled) {
    background: var(--color-accent);
    color: white;
  }

  .timer-chip.running {
    background: var(--color-accent);
    color: white;
    cursor: default;
    font-variant-numeric: tabular-nums;
  }

  .timer-chip:disabled {
    opacity: 0.9;
  }
</style>
```

**Code** (`frontend/src/lib/components/TimerBar.svelte`):

```svelte
<script lang="ts">
  export interface Timer {
    id: number;
    label: string;
    totalSeconds: number;
    remainingSeconds: number;
    status: 'running' | 'done' | 'dismissed';
  }

  export let timers: Timer[] = [];

  import { createEventDispatcher } from 'svelte';
  const dispatch = createEventDispatcher();

  function formatTime(secs: number): string {
    const h = Math.floor(secs / 3600);
    const m = Math.floor((secs % 3600) / 60);
    const s = secs % 60;
    if (h > 0) return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function dismiss(id: number) {
    dispatch('dismiss', { id });
  }

  $: activeTimers = timers.filter(t => t.status !== 'dismissed');
</script>

{#if activeTimers.length > 0}
  <div class="timer-bar">
    {#each activeTimers as timer (timer.id)}
      <div class="timer-pill" class:done={timer.status === 'done'}>
        <span class="timer-label">{timer.label}</span>
        <span class="timer-time">
          {#if timer.status === 'done'}
            Done!
          {:else}
            {formatTime(timer.remainingSeconds)}
          {/if}
        </span>
        <button class="timer-dismiss" on:click={() => dismiss(timer.id)} aria-label="Dismiss timer">x</button>
      </div>
    {/each}
  </div>
{/if}

<style>
  .timer-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    display: flex;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    background: var(--color-surface);
    border-top: 1px solid var(--color-border);
    box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.08);
    z-index: 200;
    overflow-x: auto;
    justify-content: center;
  }

  .timer-pill {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.75rem;
    background: var(--color-accent);
    color: white;
    border-radius: 999px;
    font-size: 0.85rem;
    min-height: 44px;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
  }

  .timer-pill.done {
    background: #e74c3c;
    animation: pulse 1s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }

  .timer-label {
    font-weight: 600;
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .timer-time {
    font-variant-numeric: tabular-nums;
  }

  .timer-dismiss {
    background: rgba(255, 255, 255, 0.3);
    border: none;
    color: white;
    border-radius: 50%;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 0.7rem;
    font-weight: bold;
  }

  .timer-dismiss:hover {
    background: rgba(255, 255, 255, 0.5);
  }
</style>
```

**Commit:** `git add frontend/src/lib/components/TimerChip.svelte frontend/src/lib/components/TimerBar.svelte && git commit -m "feat: add TimerChip and TimerBar components"`

---

### Task 7: CookMode Component

The main cook mode view with two-panel layout, step navigation, ingredient checkboxes, swipe, wake lock, and timer integration.

**Files:**
- Create: `frontend/src/lib/components/CookMode.svelte`

**Code** (`frontend/src/lib/components/CookMode.svelte`):

```svelte
<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { parseTimers } from '$lib/timers';
  import type { TimerMatch } from '$lib/timers';
  import TimerChip from './TimerChip.svelte';
  import TimerBar from './TimerBar.svelte';
  import type { Timer } from './TimerBar.svelte';

  export let title: string;
  export let ingredients: string[];
  export let steps: string[];
  export let notes: string[];

  const dispatch = createEventDispatcher();

  let currentStep = 0;
  let checkedIngredients: Set<number> = new Set();
  let timers: Timer[] = [];
  let nextTimerId = 1;
  let tickInterval: ReturnType<typeof setInterval> | null = null;
  let wakeLock: WakeLockSentinel | null = null;
  let audioContext: AudioContext | null = null;
  let audioBuffer: AudioBuffer | null = null;
  let notificationPermission: NotificationPermission = 'default';

  // Mobile drawer state
  let drawerOpen = false;

  // Swipe tracking
  let touchStartX = 0;
  let touchStartY = 0;
  let swiping = false;

  $: totalSteps = steps.length;
  $: showNotes = currentStep >= totalSteps && notes.length > 0;
  $: currentStepText = currentStep < totalSteps ? steps[currentStep] : '';
  $: stepTimers = currentStep < totalSteps ? parseTimers(currentStepText) : [];
  $: checkedCount = checkedIngredients.size;
  $: hasTimerBar = timers.some(t => t.status !== 'dismissed');

  // Build segments for the current step (text + timer chips interleaved)
  $: stepSegments = buildSegments(currentStepText, stepTimers);

  interface TextSegment { type: 'text'; text: string; }
  interface TimerSegment { type: 'timer'; match: TimerMatch; }
  type Segment = TextSegment | TimerSegment;

  function buildSegments(text: string, matches: TimerMatch[]): Segment[] {
    if (matches.length === 0) return [{ type: 'text', text }];
    const segments: Segment[] = [];
    let lastEnd = 0;
    for (const m of matches) {
      if (m.startIndex > lastEnd) {
        segments.push({ type: 'text', text: text.slice(lastEnd, m.startIndex) });
      }
      segments.push({ type: 'timer', match: m });
      lastEnd = m.endIndex;
    }
    if (lastEnd < text.length) {
      segments.push({ type: 'text', text: text.slice(lastEnd) });
    }
    return segments;
  }

  // Track which timers are running for which step+match
  let runningTimerMap: Map<string, number> = new Map(); // "step-startIndex" -> timerId

  function timerKeyForMatch(m: TimerMatch): string {
    return `${currentStep}-${m.startIndex}`;
  }

  function isMatchRunning(m: TimerMatch): boolean {
    const key = timerKeyForMatch(m);
    const id = runningTimerMap.get(key);
    if (id === undefined) return false;
    const t = timers.find(t => t.id === id);
    return t !== undefined && t.status === 'running';
  }

  function getMatchRemaining(m: TimerMatch): number | null {
    const key = timerKeyForMatch(m);
    const id = runningTimerMap.get(key);
    if (id === undefined) return null;
    const t = timers.find(t => t.id === id);
    return t ? t.remainingSeconds : null;
  }

  function startTimer(totalSeconds: number, label: string, match: TimerMatch | null) {
    if (timers.filter(t => t.status !== 'dismissed').length >= 5) {
      // Auto-dismiss oldest done timer
      const done = timers.find(t => t.status === 'done');
      if (done) {
        done.status = 'dismissed';
        timers = timers;
      } else {
        return; // all 5 running
      }
    }

    const id = nextTimerId++;
    timers = [...timers, {
      id,
      label: `Step ${currentStep + 1} — ${label}`,
      totalSeconds,
      remainingSeconds: totalSeconds,
      status: 'running',
    }];

    if (match) {
      runningTimerMap.set(timerKeyForMatch(match), id);
      runningTimerMap = runningTimerMap;
    }

    ensureTicking();
    requestNotificationPermission();
    initAudio();
  }

  function dismissTimer(id: number) {
    timers = timers.map(t => t.id === id ? { ...t, status: 'dismissed' as const } : t);
    // Clean up map
    for (const [key, tid] of runningTimerMap) {
      if (tid === id) {
        runningTimerMap.delete(key);
      }
    }
    runningTimerMap = runningTimerMap;
  }

  function ensureTicking() {
    if (tickInterval) return;
    tickInterval = setInterval(() => {
      let updated = false;
      timers = timers.map(t => {
        if (t.status !== 'running') return t;
        const remaining = t.remainingSeconds - 1;
        if (remaining <= 0) {
          updated = true;
          playAlarm();
          fireNotification(t.label);
          return { ...t, remainingSeconds: 0, status: 'done' as const };
        }
        updated = true;
        return { ...t, remainingSeconds: remaining };
      });

      if (!timers.some(t => t.status === 'running')) {
        if (tickInterval) {
          clearInterval(tickInterval);
          tickInterval = null;
        }
      }
    }, 1000);
  }

  // Wake lock
  async function acquireWakeLock() {
    try {
      if ('wakeLock' in navigator) {
        wakeLock = await navigator.wakeLock.request('screen');
      }
    } catch (e) {
      // Silently degrade
    }
  }

  async function releaseWakeLock() {
    if (wakeLock) {
      try { await wakeLock.release(); } catch (e) {}
      wakeLock = null;
    }
  }

  function handleVisibilityChange() {
    if (document.visibilityState === 'visible' && !wakeLock) {
      acquireWakeLock();
    }
  }

  // Audio
  async function initAudio() {
    if (audioContext) return;
    try {
      audioContext = new AudioContext();
      // Generate a simple chime programmatically (no external file needed)
      const sampleRate = audioContext.sampleRate;
      const duration = 0.5;
      const buffer = audioContext.createBuffer(1, sampleRate * duration, sampleRate);
      const data = buffer.getChannelData(0);
      for (let i = 0; i < data.length; i++) {
        const t = i / sampleRate;
        // Two-tone chime
        data[i] = 0.3 * Math.sin(2 * Math.PI * 880 * t) * Math.exp(-3 * t)
                 + 0.2 * Math.sin(2 * Math.PI * 1320 * t) * Math.exp(-4 * t);
      }
      audioBuffer = buffer;
    } catch (e) {}
  }

  function playAlarm() {
    if (!audioContext || !audioBuffer) return;
    try {
      const source = audioContext.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioContext.destination);
      source.start();
    } catch (e) {}
  }

  // Notifications
  async function requestNotificationPermission() {
    if (notificationPermission !== 'default') return;
    if (!('Notification' in window)) return;
    try {
      notificationPermission = await Notification.requestPermission();
    } catch (e) {}
  }

  function fireNotification(label: string) {
    if (notificationPermission !== 'granted') return;
    try {
      new Notification('Timer done!', { body: `${label} is done`, icon: '/favicon.png' });
    } catch (e) {}
  }

  // Navigation
  function nextStep() {
    if (currentStep < totalSteps) currentStep++;
  }

  function prevStep() {
    if (currentStep > 0) currentStep--;
  }

  function toggleIngredient(index: number) {
    if (checkedIngredients.has(index)) {
      checkedIngredients.delete(index);
    } else {
      checkedIngredients.add(index);
    }
    checkedIngredients = checkedIngredients;
  }

  function exit() {
    dispatch('exit');
  }

  // Swipe handling
  function handleTouchStart(e: TouchEvent) {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    swiping = false;
  }

  function handleTouchMove(e: TouchEvent) {
    const dx = e.touches[0].clientX - touchStartX;
    const dy = e.touches[0].clientY - touchStartY;
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 20) {
      swiping = true;
    }
  }

  function handleTouchEnd(e: TouchEvent) {
    if (!swiping) return;
    const dx = e.changedTouches[0].clientX - touchStartX;
    if (Math.abs(dx) > 50) {
      if (dx < 0) nextStep();
      else prevStep();
    }
  }

  onMount(() => {
    acquireWakeLock();
    document.addEventListener('visibilitychange', handleVisibilityChange);
  });

  onDestroy(() => {
    releaseWakeLock();
    if (tickInterval) clearInterval(tickInterval);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
  });
</script>

<div class="cook-mode">
  <div class="cook-topbar">
    <h2 class="cook-title">{title}</h2>
    <span class="cook-progress">
      {#if showNotes}
        Notes
      {:else}
        Step {currentStep + 1} of {totalSteps}
      {/if}
    </span>
    <button class="cook-exit" on:click={exit}>Exit</button>
  </div>

  <div class="cook-layout">
    <!-- Ingredients panel (desktop) -->
    <aside class="ingredients-panel">
      <h3 class="panel-heading">Ingredients ({checkedCount}/{ingredients.length})</h3>
      <ul class="ingredient-list">
        {#each ingredients as item, i}
          <li class="ingredient-item" class:checked={checkedIngredients.has(i)}>
            <label>
              <input type="checkbox" checked={checkedIngredients.has(i)} on:change={() => toggleIngredient(i)} />
              <span>{item}</span>
            </label>
          </li>
        {/each}
      </ul>
    </aside>

    <!-- Step panel -->
    <div
      class="step-panel"
      on:touchstart={handleTouchStart}
      on:touchmove={handleTouchMove}
      on:touchend={handleTouchEnd}
    >
      {#if showNotes}
        <div class="step-content">
          <h3 class="notes-heading">Notes</h3>
          <ul class="notes-list">
            {#each notes as note}
              <li>{note}</li>
            {/each}
          </ul>
        </div>
      {:else}
        <div class="step-content">
          <p class="step-text">
            {#each stepSegments as segment}
              {#if segment.type === 'text'}
                {segment.text}
              {:else}
                <TimerChip
                  label={segment.match.label}
                  totalSeconds={segment.match.totalSeconds}
                  running={isMatchRunning(segment.match)}
                  remainingSeconds={getMatchRemaining(segment.match)}
                  on:start={(e) => startTimer(e.detail.totalSeconds, e.detail.label, segment.match)}
                />
              {/if}
            {/each}
          </p>
        </div>
      {/if}

      <div class="step-nav" class:has-timer-bar={hasTimerBar}>
        <button class="nav-btn" on:click={prevStep} disabled={currentStep === 0}>
          Previous
        </button>
        <button
          class="nav-btn nav-next"
          on:click={nextStep}
          disabled={showNotes}
        >
          {currentStep === totalSteps - 1 ? (notes.length > 0 ? 'View Notes' : 'Done') : 'Next'}
        </button>
      </div>
    </div>
  </div>

  <!-- Mobile ingredient drawer toggle -->
  <button class="drawer-toggle" class:has-timer-bar={hasTimerBar} on:click={() => drawerOpen = !drawerOpen}>
    Ingredients ({checkedCount}/{ingredients.length})
  </button>

  {#if drawerOpen}
    <button class="drawer-backdrop" on:click={() => drawerOpen = false}></button>
    <div class="drawer">
      <div class="drawer-handle"></div>
      <h3 class="panel-heading">Ingredients ({checkedCount}/{ingredients.length})</h3>
      <ul class="ingredient-list">
        {#each ingredients as item, i}
          <li class="ingredient-item" class:checked={checkedIngredients.has(i)}>
            <label>
              <input type="checkbox" checked={checkedIngredients.has(i)} on:change={() => toggleIngredient(i)} />
              <span>{item}</span>
            </label>
          </li>
        {/each}
      </ul>
    </div>
  {/if}

  <TimerBar {timers} on:dismiss={(e) => dismissTimer(e.detail.id)} />
</div>

<style>
  .cook-mode {
    position: fixed;
    inset: 0;
    z-index: 300;
    background: var(--color-bg);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .cook-topbar {
    display: flex;
    align-items: center;
    padding: 0.75rem 1rem;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    gap: 1rem;
    flex-shrink: 0;
  }

  .cook-title {
    font-size: 1rem;
    font-weight: 600;
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .cook-progress {
    font-size: 0.85rem;
    color: var(--color-text-muted);
    white-space: nowrap;
  }

  .cook-exit {
    padding: 0.4rem 0.8rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: 0.85rem;
    cursor: pointer;
    white-space: nowrap;
  }

  .cook-exit:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .cook-layout {
    display: flex;
    flex: 1;
    overflow: hidden;
  }

  .ingredients-panel {
    width: 35%;
    max-width: 320px;
    padding: 1.5rem 1rem;
    border-right: 1px solid var(--color-border);
    overflow-y: auto;
    flex-shrink: 0;
  }

  .panel-heading {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 1rem;
  }

  .ingredient-list {
    list-style: none;
    padding: 0;
  }

  .ingredient-item {
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
  }

  .ingredient-item label {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    cursor: pointer;
    font-size: 1rem;
    min-height: 48px;
    align-items: center;
  }

  .ingredient-item input[type="checkbox"] {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
    accent-color: var(--color-accent);
  }

  .ingredient-item.checked span {
    text-decoration: line-through;
    opacity: 0.5;
  }

  .step-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .step-content {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    overflow-y: auto;
  }

  .step-text {
    font-size: 1.4rem;
    line-height: 1.8;
    max-width: 600px;
    text-align: center;
  }

  .notes-heading {
    font-size: 1.2rem;
    margin-bottom: 1rem;
  }

  .notes-list {
    font-size: 1.1rem;
    line-height: 1.8;
    padding-left: 1.5rem;
  }

  .notes-list li {
    margin-bottom: 0.75rem;
  }

  .step-nav {
    display: flex;
    gap: 0.5rem;
    padding: 1rem;
    border-top: 1px solid var(--color-border);
    flex-shrink: 0;
  }

  .step-nav.has-timer-bar {
    padding-bottom: calc(1rem + 60px);
  }

  .nav-btn {
    flex: 1;
    padding: 1rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    font-size: 1rem;
    cursor: pointer;
    min-height: 48px;
    transition: all 0.15s;
  }

  .nav-btn:hover:not(:disabled) {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .nav-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .nav-next {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .nav-next:hover:not(:disabled) {
    opacity: 0.9;
    color: white;
  }

  /* Mobile drawer */
  .drawer-toggle {
    display: none;
  }

  .drawer-backdrop {
    display: none;
  }

  .drawer {
    display: none;
  }

  @media (max-width: 768px) {
    .ingredients-panel {
      display: none;
    }

    .step-text {
      font-size: 1.2rem;
    }

    .drawer-toggle {
      display: block;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 0.75rem;
      background: var(--color-surface);
      border-top: 1px solid var(--color-border);
      text-align: center;
      font-size: 0.85rem;
      color: var(--color-text-muted);
      cursor: pointer;
      z-index: 250;
      border: none;
    }

    .drawer-toggle.has-timer-bar {
      bottom: 60px;
    }

    .step-nav {
      padding-bottom: calc(1rem + 48px);
    }

    .step-nav.has-timer-bar {
      padding-bottom: calc(1rem + 108px);
    }

    .drawer-backdrop {
      display: block;
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.3);
      z-index: 260;
      border: none;
      cursor: pointer;
    }

    .drawer {
      display: block;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      max-height: 60vh;
      background: var(--color-surface);
      border-top-left-radius: 12px;
      border-top-right-radius: 12px;
      box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.12);
      z-index: 270;
      padding: 1rem 1.5rem;
      overflow-y: auto;
    }

    .drawer-handle {
      width: 32px;
      height: 4px;
      background: var(--color-border);
      border-radius: 2px;
      margin: 0 auto 1rem;
    }
  }
</style>
```

**Commit:** `git add frontend/src/lib/components/CookMode.svelte && git commit -m "feat: add CookMode component with step navigation, timers, and wake lock"`

---

### Task 8: Integrate Everything into Recipe Detail Page

Wire up CookMode, FavoriteButton, CookHistory, and the "Start Cooking" button into the recipe detail page. Update RecipeCard with favorite heart.

**Files:**
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte`
- Modify: `frontend/src/lib/components/RecipeCard.svelte`

**Changes to `frontend/src/routes/recipe/[slug]/+page.svelte`:**

Add imports at the top of the `<script>`:

```typescript
import { addCookHistory } from '$lib/api';
import { parseSections } from '$lib/sections';
import CookMode from '$lib/components/CookMode.svelte';
import CookHistory from '$lib/components/CookHistory.svelte';
import FavoriteButton from '$lib/components/FavoriteButton.svelte';
```

(Note: `parseSections` is already imported — just add the other three imports and `addCookHistory`.)

Add cook mode state variables:

```typescript
let cookMode = false;
```

Add a function to parse content into cook mode data:

```typescript
function parseCookData(content: string) {
  const sections = parseSections(content);
  let ingredients: string[] = [];
  let steps: string[] = [];
  let notes: string[] = [];

  for (const section of sections) {
    if (section.name.toLowerCase() === 'ingredients') {
      ingredients = section.content.split('\n')
        .map(l => l.trim())
        .filter(l => l.startsWith('- '))
        .map(l => l.replace(/^-\s*/, ''));
    } else if (section.name.toLowerCase() === 'instructions') {
      steps = section.content.split('\n')
        .map(l => l.trim())
        .filter(l => /^\d+\./.test(l))
        .map(l => l.replace(/^\d+\.\s*/, ''));
    } else if (section.name.toLowerCase() === 'notes') {
      notes = section.content.split('\n')
        .map(l => l.trim())
        .filter(l => l.startsWith('- '))
        .map(l => l.replace(/^-\s*/, ''));
    }
  }

  return { ingredients, steps, notes };
}

async function enterCookMode() {
  cookMode = true;
  // Log cook history
  if (recipe) {
    try {
      const result = await addCookHistory(slug, selectedFork || undefined);
      recipe = { ...recipe, cook_history: result.cook_history };
    } catch (e) {}
  }
  // Update URL
  const url = new URL(window.location.href);
  url.searchParams.set('cook', '1');
  window.history.replaceState({}, '', url.toString());
}

function exitCookMode() {
  cookMode = false;
  const url = new URL(window.location.href);
  url.searchParams.delete('cook');
  window.history.replaceState({}, '', url.toString());
}
```

In the `onMount`, after loading the recipe and fork, check for `?cook` param:

```typescript
// After selectFork / loading:
if ($page.url.searchParams.get('cook')) {
  cookMode = true;
}
```

Add reactive cook data:

```typescript
$: cookData = parseCookData(displayContent);
```

In the template, wrap the existing content with cook mode conditional:

```svelte
{#if cookMode && recipe}
  <CookMode
    title={displayTitle}
    ingredients={cookData.ingredients}
    steps={cookData.steps}
    notes={cookData.notes}
    on:exit={exitCookMode}
  />
{:else if loading}
  <!-- existing loading/error/recipe template -->
```

In the recipe header, add FavoriteButton next to the title:

```svelte
<div class="title-row">
  <h1>{displayTitle}</h1>
  {#if recipe}
    <FavoriteButton slug={recipe.slug} tags={recipe.tags} />
  {/if}
</div>
```

Add CookHistory after the meta section:

```svelte
{#if recipe.cook_history}
  <CookHistory slug={recipe.slug} cookHistory={recipe.cook_history} />
{/if}
```

Add "Start Cooking" button in the recipe-actions div:

```svelte
<button class="cook-btn" on:click={enterCookMode}>Start Cooking</button>
```

Add CSS for `.title-row` and `.cook-btn`:

```css
.title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.title-row h1 {
  margin-bottom: 0;
}

.cook-btn {
  display: inline-block;
  padding: 0.4rem 1rem;
  background: var(--color-accent);
  color: white;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius);
  font-size: 0.85rem;
  cursor: pointer;
  transition: opacity 0.15s;
}

.cook-btn:hover {
  opacity: 0.9;
}
```

**Changes to `frontend/src/lib/components/RecipeCard.svelte`:**

Add a small heart icon for favorited recipes. After the card-tags section, if the recipe has the 'favorite' tag:

The `.fork-count` styling already shows fork badges. The `favorite` tag will naturally appear in the tags displayed on the card. The existing tag filter `/?tags=favorite` already works. No additional changes needed to RecipeCard beyond what's already there — the `favorite` tag renders like any other tag, and users can filter by it.

**Run:** `npx svelte-check --threshold error`

**Commit:** `git add frontend/src/routes/recipe/[slug]/+page.svelte && git commit -m "feat: integrate cook mode, favorites, and cook history into recipe page"`

---

### Task 9: Run Full Test Suite & Polish

Verify everything works end to end.

**Run backend tests:**
```bash
backend/venv/bin/python -m pytest backend/tests/ -v
```

Expected: All tests pass (125 existing + ~20 new = ~145 total).

**Run frontend type check:**
```bash
cd frontend && npx svelte-check --threshold error
```

Expected: 0 errors.

**Final commit (if any fixes needed):**
```bash
git add -A && git commit -m "fix: resolve test and type check issues from Phase 4"
```
