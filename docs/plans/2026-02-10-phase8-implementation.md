# Phase 8: UI Overhaul, Embedded History, Likes & Attribution — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add hero banner layout, tile/table view switching, customizable columns, embedded fork history, cumulative like counter, and author attribution.

**Architecture:** All new data lives in markdown frontmatter (likes, changelog, author). Stream visualization reads from embedded changelogs instead of git log. View preferences stored in localStorage. No new backend dependencies.

**Tech Stack:** Python/FastAPI backend, SvelteKit/TypeScript frontend, markdown with YAML frontmatter.

---

### Task 1: Author Attribution — Backend

Add `author` field to scraper, models, parser, and generator.

**Files:**
- Modify: `backend/app/scraper.py`
- Modify: `backend/app/models.py`
- Modify: `backend/app/parser.py`
- Modify: `backend/app/generator.py`
- Modify: `backend/tests/test_scraper.py`

**Context:**

The scraper (`backend/app/scraper.py`) currently returns a dict with these fields: title, ingredients, instructions, prep_time, cook_time, total_time, servings, image_url, source, notes. It uses the `recipe_scrapers` library which exposes a `scraper.author()` method. The scraper object is created at line ~40-52 (either via `scrape_html` or online mode fallback).

The parser (`backend/app/parser.py`) function `parse_frontmatter` at line 27 reads YAML frontmatter from recipe files. It currently extracts: title, tags, servings, prep_time, cook_time, date_added, source, image, cook_history. Each field is read from the `meta` dict (frontmatter).

The generator (`backend/app/generator.py`) function `generate_markdown` at line 38 writes YAML frontmatter. The `RecipeInput` model at line 8 defines the fields. Frontmatter is built as a list of strings (lines 44-68) like `parts.append(f"source: {data.source}")`.

Models are in `backend/app/models.py`. `RecipeSummary` (line 20) and `Recipe` (line 34) are the main models. `ScrapeResponse` is defined in `backend/app/routes/editor.py` (line 22).

**Step 1: Add author to scraper result dict**

In `backend/app/scraper.py`, add `"author": None` to the result dict (after `"notes": None` at line 29). Then after the existing field extraction blocks (after the image block ending at line ~102), add:

```python
    try:
        result["author"] = scraper.author()
    except Exception:
        pass
```

**Step 2: Add author to ScrapeResponse**

In `backend/app/routes/editor.py`, add to the `ScrapeResponse` model (after `notes` at line 33):

```python
    author: Optional[str] = None
```

**Step 3: Add author to RecipeInput and generate_markdown**

In `backend/app/generator.py`, add `author: Optional[str] = None` to the `RecipeInput` model (after `notes` at line 18). In `generate_markdown`, add after the source line (after line ~48):

```python
    if data.author:
        parts.append(f"author: {data.author}")
```

**Step 4: Add author to models and parser**

In `backend/app/models.py`, add `author: Optional[str] = None` to `RecipeSummary` (after `source` at line ~27).

In `backend/app/parser.py`, in `parse_frontmatter` add after `source` extraction (after line ~47):

```python
        author=meta.get("author"),
```

**Step 5: Update scraper tests**

In `backend/tests/test_scraper.py`, update `_make_mock_scraper` to include `author`:

```python
def _make_mock_scraper(..., author="Test Author"):
    ...
    scraper.author.return_value = author
```

In `test_scrape_recipe_with_mock`, add assertion:

```python
    assert result["author"] == "Test Author"
```

**Step 6: Run tests**

```bash
python3 -m pytest backend/tests/test_scraper.py -v
```

**Step 7: Commit**

```bash
git add backend/app/scraper.py backend/app/models.py backend/app/parser.py backend/app/generator.py backend/app/routes/editor.py backend/tests/test_scraper.py
git commit -m "feat: scrape and store author attribution in recipe frontmatter"
```

---

### Task 2: Author Attribution — Frontend

Display author below source link, add author field to editor, pass from scrape.

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/components/RecipeEditor.svelte`
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte`
- Modify: `frontend/src/routes/add/+page.svelte`

**Context:**

Types are in `frontend/src/lib/types.ts`. `RecipeSummary` (line 15) has source at line ~24. `ScrapeResponse` (line 52) has source at line ~63. `RecipeInput` (line 66) has source at line ~71.

The recipe detail page (`frontend/src/routes/recipe/[slug]/+page.svelte`) shows the source link. Look for the source display section — it renders `recipe.source` as a clickable link.

The RecipeEditor (`frontend/src/lib/components/RecipeEditor.svelte`) has a source URL input at line ~127. The component accepts `initialData` prop and binds form fields.

The add page (`frontend/src/routes/add/+page.svelte`) has `getInitialData()` at line 49 which maps scraped data to editor fields.

**Step 1: Add author to TypeScript types**

In `frontend/src/lib/types.ts`:
- Add `author: string | null;` to `RecipeSummary` (after `source`)
- Add `author: string | null;` to `ScrapeResponse` (after `source`)
- Add `author?: string | null;` to `RecipeInput` (after `source`)

**Step 2: Add author field to RecipeEditor**

In `frontend/src/lib/components/RecipeEditor.svelte`:
- Add to script: `let author = initialData.author || '';`
- Add to `handleSubmit` data object: `author: author || null,`
- Add an input field after the Source URL field:

```svelte
<div class="field">
  <label for="author">Author</label>
  <input id="author" type="text" bind:value={author} placeholder="Recipe author" />
</div>
```

**Step 3: Pass author from scrape to editor**

In `frontend/src/routes/add/+page.svelte`, in `getInitialData()`, add:

```typescript
author: scrapedData.author,
```

**Step 4: Display author on recipe detail page**

In `frontend/src/routes/recipe/[slug]/+page.svelte`, find where `recipe.source` is displayed. Add below it:

```svelte
{#if recipe.author}
  <p class="recipe-author">by {recipe.author}</p>
{/if}
```

Style it:

```css
.recipe-author {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  font-style: italic;
}
```

**Step 5: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/components/RecipeEditor.svelte frontend/src/routes/recipe/[slug]/+page.svelte frontend/src/routes/add/+page.svelte
git commit -m "feat: display author attribution on recipe detail and editor"
```

---

### Task 3: Like Counter — Backend

Add likes field to models/parser/generator, create like endpoint.

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/parser.py`
- Modify: `backend/app/generator.py`
- Modify: `backend/app/routes/cook.py`
- Create: `backend/tests/test_likes.py`

**Context:**

The favorite endpoints in `backend/app/routes/cook.py` provide a pattern to follow. The `add_favorite` function (line 76) loads the recipe file using `_load_post` (which reads frontmatter with `python-frontmatter`), modifies the frontmatter, writes the file, updates the index, and commits.

The `_load_post` helper (line 23) calls `frontmatter.load(filepath)` and returns a `Post` object. The `_save` helper (line 29) calls `filepath.write_text(frontmatter.dumps(post))` then `index.add_or_update(filepath)`.

`cook.py` creates its router at line 19: `def create_cook_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:` with prefix `/api/recipes/{slug}`.

**Step 1: Add likes to models**

In `backend/app/models.py`, add `likes: int = 0` to `RecipeSummary` (after `cook_history` or at end of fields).

**Step 2: Add likes to parser**

In `backend/app/parser.py`, in `parse_frontmatter` (line 27), add after the cook_history line:

```python
        likes=meta.get("likes", 0),
```

**Step 3: Add likes to generator**

In `backend/app/generator.py`, add `likes: int = 0` to `RecipeInput` model. In `generate_markdown`, add:

```python
    if data.likes:
        parts.append(f"likes: {data.likes}")
```

**Step 4: Create like endpoint**

In `backend/app/routes/cook.py`, add after the `remove_favorite` function:

```python
    @router.post("/like")
    def add_like(slug: str):
        post, filepath = _load_post(slug)
        current = post.metadata.get("likes", 0)
        post.metadata["likes"] = current + 1
        _save(post, filepath)
        git_commit(recipes_dir, filepath, f"Like: {slug}")
        return {"likes": post.metadata["likes"]}
```

**Step 5: Write tests**

Create `backend/tests/test_likes.py`:

```python
import pytest
from fastapi.testclient import TestClient


def test_like_increments_count(client, sample_recipe_path):
    """POST /like increments the likes count."""
    response = client.post("/api/recipes/test-recipe/like")
    assert response.status_code == 200
    data = response.json()
    assert data["likes"] == 1

    # Like again
    response = client.post("/api/recipes/test-recipe/like")
    data = response.json()
    assert data["likes"] == 2


def test_like_nonexistent_recipe(client):
    """POST /like on missing recipe returns 404."""
    response = client.post("/api/recipes/no-such-recipe/like")
    assert response.status_code == 404
```

Note: Use the same test fixtures as other route tests. Check `backend/tests/test_routes.py` for the `client` and recipe fixtures pattern.

**Step 6: Run tests**

```bash
python3 -m pytest backend/tests/test_likes.py -v
```

**Step 7: Commit**

```bash
git add backend/app/models.py backend/app/parser.py backend/app/generator.py backend/app/routes/cook.py backend/tests/test_likes.py
git commit -m "feat: add cumulative like counter with endpoint and storage"
```

---

### Task 4: Like Counter — Frontend

Add LikeButton component, display on recipe detail and cards, add "Most loved" sort.

**Files:**
- Create: `frontend/src/lib/components/LikeButton.svelte`
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte`
- Modify: `frontend/src/lib/components/RecipeCard.svelte`
- Modify: `frontend/src/routes/+page.svelte`

**Context:**

The `FavoriteButton.svelte` component is a good reference. It accepts `slug` and `tags` props, maintains local state, and calls an API function on click with optimistic update.

`RecipeCard.svelte` shows recipe cards in a grid. It displays the image, title, meta (prep/cook/servings), and tags. The card body starts at line 19.

The home page `+page.svelte` has discoveryChips defined at line 42 as an array of objects with `label`, `icon`, and `action`. Current chips: "Surprise me", "Never tried", "Cook again", "Quick meals".

**Step 1: Add likes to types**

In `frontend/src/lib/types.ts`, add `likes: number;` to `RecipeSummary` (at end of fields).

**Step 2: Add likeRecipe API function**

In `frontend/src/lib/api.ts`, add:

```typescript
export async function likeRecipe(slug: string): Promise<{ likes: number }> {
  const res = await fetch(`${BASE}/recipes/${slug}/like`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to like recipe');
  return res.json();
}
```

**Step 3: Create LikeButton component**

Create `frontend/src/lib/components/LikeButton.svelte`:

```svelte
<script lang="ts">
  import { likeRecipe } from '$lib/api';

  export let slug: string;
  export let likes: number = 0;

  let count = likes;
  let animating = false;

  async function handleLike() {
    count += 1;
    animating = true;
    setTimeout(() => { animating = false; }, 300);
    try {
      const result = await likeRecipe(slug);
      count = result.likes;
    } catch {
      count -= 1;
    }
  }
</script>

<button class="like-btn" class:animating on:click|stopPropagation={handleLike} title="Like this recipe">
  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
  </svg>
  <span class="like-count">{count}</span>
</button>

<style>
  .like-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-text-muted);
    font-size: 0.8rem;
    padding: 0.25rem 0.4rem;
    border-radius: var(--radius);
    transition: color 0.15s;
  }

  .like-btn:hover {
    color: var(--color-danger);
  }

  .like-btn.animating {
    color: var(--color-danger);
  }

  .like-count {
    font-weight: 600;
    min-width: 1ch;
  }
</style>
```

**Step 4: Add LikeButton to recipe detail page**

In `frontend/src/routes/recipe/[slug]/+page.svelte`, import `LikeButton` and add it near the `FavoriteButton` in the title row:

```svelte
<LikeButton slug={recipe.slug} likes={recipe.likes} />
```

**Step 5: Add like count to RecipeCard**

In `frontend/src/lib/components/RecipeCard.svelte`, add a small like count display in the card body (bottom area, after tags):

```svelte
{#if recipe.likes > 0}
  <span class="card-likes">
    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
    {recipe.likes}
  </span>
{/if}
```

**Step 6: Add "Most loved" discovery chip**

In `frontend/src/routes/+page.svelte`, add to the `discoveryChips` array:

```typescript
{ label: 'Most loved', icon: '❤️', action: () => applySort('likes') },
```

The backend list endpoint (`backend/app/routes/recipes.py` or wherever list sorting is handled) needs a `likes` sort option. Check how existing sorts like `never-cooked` and `quick` are implemented and add `likes` sorting (descending).

**Step 7: Commit**

```bash
git add frontend/src/lib/components/LikeButton.svelte frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/routes/recipe/[slug]/+page.svelte frontend/src/lib/components/RecipeCard.svelte frontend/src/routes/+page.svelte
git commit -m "feat: add like button component with counter display and Most Loved sort"
```

---

### Task 5: Embedded Changelog — Backend Models & Storage

Add changelog to models, parser, generator. Write changelog entries on recipe/fork create and edit.

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/parser.py`
- Modify: `backend/app/generator.py`
- Modify: `backend/app/routes/editor.py`
- Modify: `backend/app/routes/forks.py`
- Modify: `backend/app/sections.py`
- Create: `backend/tests/test_changelog.py`

**Context:**

The changelog is a list of dicts in frontmatter:

```yaml
changelog:
  - date: '2026-02-10'
    action: created
    summary: Created
  - date: '2026-02-11'
    action: edited
    summary: Updated ingredients, instructions
```

**Step 1: Add ChangelogEntry model**

In `backend/app/models.py`, add a new model:

```python
class ChangelogEntry(BaseModel):
    date: str
    action: str  # "created", "edited", "merged"
    summary: str
```

Add `changelog: List[ChangelogEntry] = []` to `RecipeSummary` and `ForkSummary`.

**Step 2: Parse changelog in parser**

In `backend/app/parser.py`, add a helper to parse changelog entries (similar to `_parse_cook_history`):

```python
def _parse_changelog(meta: dict) -> list:
    raw = meta.get("changelog", [])
    if not raw or not isinstance(raw, list):
        return []
    entries = []
    for item in raw:
        if isinstance(item, dict):
            entries.append({
                "date": str(item.get("date", "")),
                "action": item.get("action", ""),
                "summary": item.get("summary", ""),
            })
    return entries
```

Call this in `parse_frontmatter` and `parse_fork_frontmatter`, adding `changelog=_parse_changelog(meta)` to the returned model.

**Step 3: Add changelog helper for writing entries**

In `backend/app/sections.py`, add a function to detect changed sections:

```python
def detect_changed_sections(old_content: str, new_content: str) -> list[str]:
    """Compare two markdown strings and return names of changed sections."""
    old_sections = parse_sections(old_content)
    new_sections = parse_sections(new_content)
    changed = []
    all_keys = set(list(old_sections.keys()) + list(new_sections.keys()))
    for key in sorted(all_keys):
        if key == "_preamble":
            continue
        old_val = _normalize(old_sections.get(key, ""))
        new_val = _normalize(new_sections.get(key, ""))
        if old_val != new_val:
            changed.append(key)
    return changed
```

Also add a small utility function (can go in a new helper or in editor.py) for appending a changelog entry to a frontmatter post:

```python
def append_changelog_entry(post, action: str, summary: str):
    """Append a changelog entry to a frontmatter post object."""
    from datetime import date
    if "changelog" not in post.metadata:
        post.metadata["changelog"] = []
    post.metadata["changelog"].append({
        "date": date.today().isoformat(),
        "action": action,
        "summary": summary,
    })
```

**Step 4: Write changelog on recipe create**

In `backend/app/routes/editor.py`, in `create_recipe` (line 53), after writing the markdown file and before git commit: load the file with `frontmatter.load`, call `append_changelog_entry(post, "created", "Created")`, write it back.

**Step 5: Write changelog on recipe update**

In `backend/app/routes/editor.py`, in `update_recipe` (line 95), before writing the new content: read the old file content, generate the new markdown, diff them with `detect_changed_sections`, build a summary like "Updated ingredients, instructions", then after writing: load with frontmatter, append the changelog entry, write back.

**Step 6: Write changelog on fork create**

In `backend/app/routes/forks.py`, in `create_fork` (line 48), after writing the fork file: load it, append `("created", "Forked from original")`, write back.

**Step 7: Write changelog on fork update**

In `backend/app/routes/forks.py`, in `update_fork` (line 83), diff old/new content, append `("edited", summary)`.

**Step 8: Write changelog on fork merge**

In `backend/app/routes/forks.py`, in `merge_fork` (line 176), append `("merged", "Merged into original")` to the fork's changelog, and append `("merged", f"Merged fork '{fork_name}'")` to the base recipe's changelog.

**Step 9: Write tests**

Create `backend/tests/test_changelog.py` testing:
- Recipe create adds "created" entry
- Recipe update adds "edited" entry with section names
- Fork create adds "created" entry
- Fork merge adds "merged" entries to both files
- `detect_changed_sections` returns correct section names

**Step 10: Run tests**

```bash
python3 -m pytest backend/tests/test_changelog.py -v
```

**Step 11: Commit**

```bash
git add backend/app/models.py backend/app/parser.py backend/app/generator.py backend/app/routes/editor.py backend/app/routes/forks.py backend/app/sections.py backend/tests/test_changelog.py
git commit -m "feat: embed changelog in recipe and fork frontmatter"
```

---

### Task 6: Embedded Changelog — Stream Rewrite

Rewrite stream endpoint to read from changelogs instead of git log.

**Files:**
- Modify: `backend/app/routes/stream.py`
- Modify: `backend/tests/test_stream.py`

**Context:**

The current stream endpoint (`backend/app/routes/stream.py`, line 21) reads from `git_log` and fork metadata. It assembles `StreamEvent` objects.

The new implementation reads changelog entries from the base recipe and all its forks. Each changelog entry maps directly to a `StreamEvent`. Fork changelog entries include the fork name for branch visualization.

The `StreamEvent` model (in `models.py`, line 65) has: type, date, message, commit (optional), fork_name (optional), fork_slug (optional).

**Step 1: Rewrite stream endpoint**

Replace the body of `get_stream` in `backend/app/routes/stream.py`:

```python
@router.get("/api/recipes/{slug}/stream")
def get_stream(slug: str):
    recipe = index.get(slug)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    events = []

    # Base recipe changelog
    for entry in recipe.changelog:
        events.append(StreamEvent(
            type=entry.action,
            date=entry.date,
            message=entry.summary,
        ))

    # Fork changelogs
    for fork in recipe.forks:
        fork_detail = ...  # load fork to get its changelog
        for entry in fork_detail.changelog:
            event_type = entry.action
            if event_type == "created":
                event_type = "forked"
            events.append(StreamEvent(
                type=event_type,
                date=entry.date,
                message=entry.summary,
                fork_name=fork.fork_name,
                fork_slug=fork.name,
            ))

    # Sort chronologically
    events.sort(key=lambda e: e.date)
    return {"events": events}
```

Adapt this to the actual file structure. The index has fork summaries but you may need to read fork files to get their changelogs. Check how `parse_fork_frontmatter` works and use the parser to read fork changelogs.

**Step 2: Remove git_log dependency**

Remove imports of `git_log` from `stream.py`. The endpoint should work without git.

**Step 3: Update tests**

Rewrite `backend/tests/test_stream.py` to test against changelog data instead of git history. Create recipe files with changelog entries in frontmatter and verify the stream endpoint returns correct events.

**Step 4: Run tests**

```bash
python3 -m pytest backend/tests/test_stream.py -v
```

**Step 5: Commit**

```bash
git add backend/app/routes/stream.py backend/tests/test_stream.py
git commit -m "feat: rewrite stream timeline to read from embedded changelogs"
```

---

### Task 7: Home Screen — View Toggle & Table View

Add tile/table view switcher, create table component with sortable columns.

**Files:**
- Create: `frontend/src/lib/components/RecipeTable.svelte`
- Modify: `frontend/src/routes/+page.svelte`

**Context:**

The home page (`frontend/src/routes/+page.svelte`) currently renders a grid of `RecipeCard` components (line ~107-111). The `recipes` array contains `RecipeSummary` objects with all the fields we need for the table.

The page manages state via URL search params: `q` (query), `tags`, `sort`. The `loadRecipes` function (line 18) fetches based on these params.

**Step 1: Create RecipeTable component**

Create `frontend/src/lib/components/RecipeTable.svelte`:

A sortable table component that:
- Accepts `recipes: RecipeSummary[]` and `visibleColumns: string[]` props
- Renders a `<table>` with clickable column headers for sorting
- Sorts locally (client-side) when a column header is clicked
- Each row links to `/recipe/{slug}`
- Columns: Title, Tags (as comma-separated), Prep Time, Cook Time, Total Time (if available), Servings, Likes, Last Cooked (most recent cook_history entry), Date Added, Source

Column definitions:

```typescript
const allColumns = [
  { key: 'title', label: 'Title' },
  { key: 'tags', label: 'Tags' },
  { key: 'prep_time', label: 'Prep' },
  { key: 'cook_time', label: 'Cook' },
  { key: 'servings', label: 'Servings' },
  { key: 'likes', label: 'Likes' },
  { key: 'last_cooked', label: 'Last Cooked' },
  { key: 'date_added', label: 'Added' },
  { key: 'source', label: 'Source' },
];
```

Style the table with the app's CSS variables. Rows should have hover highlighting. Tags render as small inline pills. The table scrolls horizontally on mobile.

**Step 2: Add view toggle to home page**

In `frontend/src/routes/+page.svelte`:

Add state:
```typescript
let viewMode: 'grid' | 'table' = (typeof localStorage !== 'undefined' && localStorage.getItem('viewMode') as any) || 'grid';
$: if (typeof localStorage !== 'undefined') localStorage.setItem('viewMode', viewMode);
```

Add two icon buttons (grid and list icons) in the header area near the discovery chips. Use simple SVG icons.

Conditionally render either the existing card grid or the new `RecipeTable`:

```svelte
{#if viewMode === 'grid'}
  <div class="recipe-grid">
    {#each recipes as recipe}
      <RecipeCard {recipe} />
    {/each}
  </div>
{:else}
  <RecipeTable {recipes} {visibleColumns} />
{/if}
```

**Step 3: Commit**

```bash
git add frontend/src/lib/components/RecipeTable.svelte frontend/src/routes/+page.svelte
git commit -m "feat: add tile/table view toggle on home screen"
```

---

### Task 8: Home Screen — Column Customization & Filter Bar

Add column picker dropdown and consolidated filter bar.

**Files:**
- Create: `frontend/src/lib/components/ColumnPicker.svelte`
- Modify: `frontend/src/routes/+page.svelte`

**Context:**

The home page currently has discovery chips (line ~79-89) and separate handling for tags/search/sort via URL params. We need to consolidate filtering into a proper filter bar and add a column customization dropdown.

**Step 1: Create ColumnPicker component**

Create `frontend/src/lib/components/ColumnPicker.svelte`:

A dropdown that shows checkboxes for each available column. "Title" is always checked and disabled. Other columns toggle on/off. Selections are passed up via a callback prop.

```svelte
<script lang="ts">
  export let columns: { key: string; label: string }[];
  export let visible: string[];
  export let onChange: (visible: string[]) => void;

  let open = false;

  function toggle(key: string) {
    if (key === 'title') return;
    const next = visible.includes(key)
      ? visible.filter(k => k !== key)
      : [...visible, key];
    onChange(next);
  }
</script>
```

Renders as a gear icon button that opens a positioned dropdown with checkboxes. Closes on click outside.

**Step 2: Add filter bar to home page**

In `frontend/src/routes/+page.svelte`, add below the discovery chips:

A collapsible filter row containing:
- **Tag pills**: Fetch all unique tags from recipes. Render as clickable pills that toggle selection. Active pills get accent styling.
- **Sort dropdown**: `<select>` with options: Default, Quick meals, Never tried, Least recent, Most loved
- **Search input**: Move the existing search into this bar

The filter bar state drives URL params the same way the current chips do.

**Step 3: Add column picker to home page**

Import `ColumnPicker` and render it next to the view toggle buttons (only visible in table mode). Store selected columns in localStorage:

```typescript
const defaultColumns = ['title', 'tags', 'cook_time', 'likes', 'last_cooked'];
let visibleColumns: string[] = JSON.parse(localStorage.getItem('tableColumns') || 'null') || defaultColumns;
```

**Step 4: Commit**

```bash
git add frontend/src/lib/components/ColumnPicker.svelte frontend/src/routes/+page.svelte
git commit -m "feat: add column customization and filter bar to home screen"
```

---

### Task 9: Recipe Detail — Hero Banner Layout

Rework the recipe detail page with a full-width hero image, gradient overlay, and sticky action bar.

**Files:**
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte`
- Modify: `frontend/src/app.css` (print rules)

**Context:**

The recipe detail page (`frontend/src/routes/recipe/[slug]/+page.svelte`) currently shows:
- Back link
- Hero image (max-height 400px) at line ~307-313
- Title + FavoriteButton at line ~318
- Version selector pills at line ~322-348
- Meta info at line ~352-376
- Action buttons at line ~396-431
- Recipe body (rendered markdown)

The page uses scoped `<style>` for its CSS. The app's global CSS is in `frontend/src/app.css` which already has `@media print` rules.

**Step 1: Restructure the hero section**

Replace the current image display and title area with a hero banner:

```svelte
{#if recipe.image}
  <div class="hero-banner">
    <img src="/api/images/{recipe.image.replace('images/', '')}" alt={recipe.title} class="hero-image" />
    <div class="hero-overlay">
      <div class="hero-content">
        <h1 class="hero-title">{recipe.title}</h1>
        <div class="hero-meta">
          {#if displayRecipe.prep_time}<span>Prep: {displayRecipe.prep_time}</span>{/if}
          {#if displayRecipe.cook_time}<span>Cook: {displayRecipe.cook_time}</span>{/if}
          {#if displayRecipe.servings}<span>Serves: {currentServings}</span>{/if}
        </div>
      </div>
      <div class="hero-actions">
        <FavoriteButton slug={recipe.slug} tags={recipe.tags} />
        <LikeButton slug={recipe.slug} likes={recipe.likes} />
      </div>
    </div>
  </div>
{:else}
  <h1>{recipe.title}</h1>
{/if}
```

**Step 2: Style the hero banner**

```css
.hero-banner {
  position: relative;
  width: 100vw;
  margin-left: calc(-50vw + 50%);
  height: 50vh;
  max-height: 500px;
  overflow: hidden;
}

.hero-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.hero-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.7) 0%, transparent 60%);
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  padding: 2rem;
}

.hero-title {
  color: white;
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
  text-shadow: 0 1px 4px rgba(0,0,0,0.3);
}

.hero-meta {
  display: flex;
  gap: 1rem;
  color: rgba(255,255,255,0.85);
  font-size: 0.9rem;
}

.hero-actions {
  display: flex;
  gap: 0.5rem;
  align-self: flex-start;
  padding-top: 1rem;
}
```

Override button colors in hero context so they're visible on dark background (white text/icons).

**Step 3: Make the action bar sticky**

Wrap the version selector and action buttons in a sticky bar:

```css
.action-bar {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 0.75rem 0;
  margin: 0 calc(-50vw + 50%);
  padding-left: calc(50vw - 50%);
  padding-right: calc(50vw - 50%);
}
```

**Step 4: Mobile adjustments**

```css
@media (max-width: 768px) {
  .hero-banner {
    height: 35vh;
  }
  .hero-title {
    font-size: 1.5rem;
  }
  .action-bar {
    overflow-x: auto;
    white-space: nowrap;
  }
}
```

**Step 5: Update print rules**

In `frontend/src/app.css`, update `@media print` to hide the hero gradient overlay and show the image naturally, hide the sticky action bar.

**Step 6: Commit**

```bash
git add frontend/src/routes/recipe/[slug]/+page.svelte frontend/src/app.css
git commit -m "feat: hero banner layout with sticky action bar on recipe detail"
```

---

### Task 10: Integration Testing & Polish

Test all features end-to-end, fix edge cases, ensure frontend builds clean.

**Files:**
- Various files for fixes
- Run: `npm run build` in frontend
- Run: `python3 -m pytest backend/tests/ -v`

**Step 1: Run full backend test suite**

```bash
cd /Users/cj.krueger/Documents/GitHub/forks/backend
python3 -m pytest tests/ -v
```

Fix any failures.

**Step 2: Build frontend**

```bash
cd /Users/cj.krueger/Documents/GitHub/forks/frontend
npm run build
```

Fix any TypeScript errors.

**Step 3: Test edge cases**

- Recipe with no image: verify no hero banner, title shows as plain heading
- Recipe with no changelog: verify stream shows empty state
- Recipe with 0 likes: verify like button shows 0
- New recipe creation: verify changelog "created" entry appears
- Fork creation and edit: verify changelog entries
- Author field: verify it appears when scraped, absent when not
- Table view: verify all columns render, sorting works, column picker persists
- Mobile: verify hero shrinks, action bar scrolls, table scrolls

**Step 4: Final commit**

```bash
git add -A
git commit -m "fix: integration fixes and polish for phase 8"
```
