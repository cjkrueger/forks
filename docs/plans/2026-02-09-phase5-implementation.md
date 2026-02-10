# Phase 5: Discovery, Grocery List & Scaling — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add discovery chips (surprise me, never tried, cook again, quick meals), a grocery list with ingredient parsing and manual combine, and serving scaling with a +/- stepper.

**Architecture:** Discovery uses new backend sort/filter params. Grocery list and scaling are frontend-only, sharing a common ingredient parser. Grocery list persists in localStorage.

**Tech Stack:** Python/FastAPI (backend), SvelteKit + TypeScript (frontend)

---

### Task 1: Backend Discovery Endpoints

Add `sort` param to `/api/recipes` and a new `/api/recipes/random` endpoint.

**Files:**
- Modify: `backend/app/routes/recipes.py`
- Modify: `backend/app/index.py`
- Create: `backend/tests/test_discovery.py`

**Code:**

Update `backend/app/index.py` — add imports and three new methods:

```python
import random as _random
from app.tagger import _parse_minutes
```

Add these methods to `RecipeIndex`:

```python
def random(self) -> Optional[RecipeSummary]:
    if not self._index:
        return None
    return _random.choice(list(self._index.values()))

def filter_never_cooked(self, tags: Optional[List[str]] = None) -> List[RecipeSummary]:
    results = self._apply_tags(tags)
    results = [r for r in results if len(r.cook_history) == 0]
    return sorted(results, key=lambda r: r.date_added or "", reverse=True)

def filter_least_recent(self, tags: Optional[List[str]] = None) -> List[RecipeSummary]:
    results = self._apply_tags(tags)
    results = [r for r in results if len(r.cook_history) > 0]
    return sorted(results, key=lambda r: r.cook_history[0].date if r.cook_history else "")

def filter_quick(self, tags: Optional[List[str]] = None) -> List[RecipeSummary]:
    results = self._apply_tags(tags)
    quick = []
    for r in results:
        total = _parse_minutes(r.prep_time) + _parse_minutes(r.cook_time)
        if 0 < total <= 30:
            quick.append(r)
    return sorted(quick, key=lambda r: r.title.lower())

def _apply_tags(self, tags: Optional[List[str]] = None) -> List[RecipeSummary]:
    if tags:
        return [r for r in self._index.values() if all(t in r.tags for t in tags)]
    return list(self._index.values())
```

Update `backend/app/routes/recipes.py`:

```python
import random as _random
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.index import RecipeIndex
from app.models import Recipe, RecipeSummary


def create_recipe_router(index: RecipeIndex) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/recipes/random", response_model=RecipeSummary)
    def random_recipe():
        result = index.random()
        if result is None:
            raise HTTPException(status_code=404, detail="No recipes found")
        return result

    @router.get("/recipes", response_model=List[RecipeSummary])
    def list_recipes(
        tags: Optional[str] = Query(None),
        sort: Optional[str] = Query(None),
    ):
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None

        if sort == "never-cooked":
            return index.filter_never_cooked(tag_list)
        elif sort == "least-recent":
            return index.filter_least_recent(tag_list)
        elif sort == "quick":
            return index.filter_quick(tag_list)

        if tag_list:
            return index.filter_by_tags(tag_list)
        return index.list_all()

    @router.get("/recipes/{slug}", response_model=Recipe)
    def get_recipe(slug: str):
        recipe = index.get(slug)
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return recipe

    @router.get("/search", response_model=List[RecipeSummary])
    def search_recipes(q: str = Query("")):
        return index.search(q)

    return router
```

**IMPORTANT:** The `/recipes/random` route MUST be defined before `/recipes/{slug}` or FastAPI will match "random" as a slug.

**Tests** (`backend/tests/test_discovery.py`):

```python
"""Tests for discovery endpoints."""
import textwrap

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


def _write(path, content):
    path.write_text(textwrap.dedent(content))


@pytest.fixture
def setup(tmp_path):
    _write(tmp_path / "quick-salad.md", """\
        ---
        title: Quick Salad
        tags: [salad, quick]
        prep_time: 10min
        cook_time: 0min
        ---

        # Quick Salad

        ## Ingredients

        - lettuce
    """)
    _write(tmp_path / "slow-braise.md", """\
        ---
        title: Slow Braise
        tags: [beef, weekend]
        prep_time: 20min
        cook_time: 3hr
        cook_history:
          - date: "2026-01-01"
        ---

        # Slow Braise

        ## Ingredients

        - beef
    """)
    _write(tmp_path / "never-tried.md", """\
        ---
        title: Never Tried
        tags: [soup]
        prep_time: 15min
        cook_time: 30min
        date_added: "2026-02-01"
        ---

        # Never Tried

        ## Ingredients

        - water
    """)
    app = create_app(recipes_dir=tmp_path)
    client = TestClient(app)
    return client, tmp_path


class TestRandomEndpoint:
    def test_returns_a_recipe(self, setup):
        client, _ = setup
        resp = client.get("/api/recipes/random")
        assert resp.status_code == 200
        assert "slug" in resp.json()

    def test_empty_index(self, tmp_path):
        app = create_app(recipes_dir=tmp_path)
        client = TestClient(app)
        resp = client.get("/api/recipes/random")
        assert resp.status_code == 404


class TestSortNeverCooked:
    def test_returns_only_uncooked(self, setup):
        client, _ = setup
        resp = client.get("/api/recipes?sort=never-cooked")
        assert resp.status_code == 200
        slugs = [r["slug"] for r in resp.json()]
        assert "slow-braise" not in slugs
        assert "quick-salad" in slugs
        assert "never-tried" in slugs

    def test_with_tag_filter(self, setup):
        client, _ = setup
        resp = client.get("/api/recipes?sort=never-cooked&tags=soup")
        slugs = [r["slug"] for r in resp.json()]
        assert slugs == ["never-tried"]


class TestSortLeastRecent:
    def test_returns_only_cooked(self, setup):
        client, _ = setup
        resp = client.get("/api/recipes?sort=least-recent")
        slugs = [r["slug"] for r in resp.json()]
        assert slugs == ["slow-braise"]


class TestSortQuick:
    def test_returns_quick_recipes(self, setup):
        client, _ = setup
        resp = client.get("/api/recipes?sort=quick")
        slugs = [r["slug"] for r in resp.json()]
        assert "quick-salad" in slugs
        assert "slow-braise" not in slugs

    def test_no_sort_returns_all(self, setup):
        client, _ = setup
        resp = client.get("/api/recipes")
        assert len(resp.json()) == 3
```

**Run:** `backend/venv/bin/python -m pytest backend/tests/test_discovery.py -v`

**Commit:** `git add backend/app/routes/recipes.py backend/app/index.py backend/tests/test_discovery.py && git commit -m "feat: add discovery sort endpoints (random, never-cooked, least-recent, quick)"`

---

### Task 2: Frontend Discovery Chips

Add discovery chip buttons to the home page and wire up the API.

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/routes/+page.svelte`

**Code:**

Add to `frontend/src/lib/api.ts`:

```typescript
export async function listRecipesWithSort(sort: string, tags?: string[]): Promise<RecipeSummary[]> {
  const params = new URLSearchParams();
  params.set('sort', sort);
  if (tags && tags.length > 0) {
    params.set('tags', tags.join(','));
  }
  const res = await fetch(`${BASE}/recipes?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch recipes');
  return res.json();
}

export async function getRandomRecipe(): Promise<RecipeSummary> {
  const res = await fetch(`${BASE}/recipes/random`);
  if (!res.ok) throw new Error('No recipes found');
  return res.json();
}
```

Replace `frontend/src/routes/+page.svelte` entirely:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import { listRecipes, searchRecipes, listRecipesWithSort, getRandomRecipe } from '$lib/api';
  import type { RecipeSummary } from '$lib/types';
  import RecipeCard from '$lib/components/RecipeCard.svelte';

  let recipes: RecipeSummary[] = [];
  let loading = true;

  $: query = $page.url.searchParams.get('q') || '';
  $: tags = $page.url.searchParams.get('tags') || '';
  $: sort = $page.url.searchParams.get('sort') || '';

  $: loadRecipes(query, tags, sort);

  async function loadRecipes(q: string, t: string, s: string) {
    loading = true;
    try {
      if (q) {
        recipes = await searchRecipes(q);
      } else if (s) {
        const tagList = t ? t.split(',').filter(Boolean) : undefined;
        recipes = await listRecipesWithSort(s, tagList);
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
    loadRecipes(query, tags, sort);
  });

  const discoveryChips = [
    { label: 'Surprise me', sort: '_random' },
    { label: 'Never tried', sort: 'never-cooked' },
    { label: 'Cook again', sort: 'least-recent' },
    { label: 'Quick meals', sort: 'quick' },
  ];

  async function handleChip(chip: typeof discoveryChips[0]) {
    if (chip.sort === '_random') {
      try {
        const recipe = await getRandomRecipe();
        goto(`/recipe/${recipe.slug}`);
      } catch (e) {
        // no recipes
      }
      return;
    }
    const params = new URLSearchParams($page.url.searchParams);
    if (sort === chip.sort) {
      params.delete('sort');
    } else {
      params.set('sort', chip.sort);
    }
    params.delete('q');
    const qs = params.toString();
    goto(qs ? `/?${qs}` : '/');
  }
</script>

<svelte:head>
  <title>Forks - Recipe Manager</title>
</svelte:head>

<div class="home">
  {#if query}
    <p class="result-info">Search results for "{query}"</p>
  {:else}
    <div class="discovery-chips">
      {#each discoveryChips as chip}
        <button
          class="chip"
          class:active={sort === chip.sort}
          on:click={() => handleChip(chip)}
        >
          {chip.label}
        </button>
      {/each}
    </div>
  {/if}

  {#if loading}
    <p class="loading">Loading recipes...</p>
  {:else if recipes.length === 0}
    <p class="empty">
      {#if sort === 'never-cooked'}
        You've tried everything! Nice work.
      {:else if sort === 'least-recent'}
        No cook history yet. Start cooking to see suggestions here.
      {:else if sort === 'quick'}
        No quick recipes found (under 30 min).
      {:else}
        No recipes found.
      {/if}
    </p>
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

  .discovery-chips {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-bottom: 1.5rem;
  }

  .chip {
    padding: 0.35rem 0.85rem;
    border: 1px solid var(--color-border);
    border-radius: 999px;
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .chip:hover:not(.active) {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .chip.active {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
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

**Commit:** `git add frontend/src/lib/api.ts frontend/src/routes/+page.svelte && git commit -m "feat: add discovery chips to home page"`

---

### Task 3: Ingredient Parser

Create the shared ingredient parser used by both grocery list and scaling.

**Files:**
- Create: `frontend/src/lib/ingredients.ts`

**Code** (`frontend/src/lib/ingredients.ts`):

```typescript
export interface ParsedIngredient {
  quantity: number | null;
  unit: string | null;
  name: string;
  original: string;
}

const UNIT_MAP: Record<string, string> = {
  cup: 'cup', cups: 'cup', c: 'cup',
  tablespoon: 'tbsp', tablespoons: 'tbsp', tbsp: 'tbsp', tbs: 'tbsp', t: 'tbsp',
  teaspoon: 'tsp', teaspoons: 'tsp', tsp: 'tsp',
  ounce: 'oz', ounces: 'oz', oz: 'oz',
  pound: 'lb', pounds: 'lb', lb: 'lb', lbs: 'lb',
  gram: 'g', grams: 'g', g: 'g',
  kilogram: 'kg', kilograms: 'kg', kg: 'kg',
  liter: 'l', liters: 'l', l: 'l',
  milliliter: 'ml', milliliters: 'ml', ml: 'ml',
  pint: 'pint', pints: 'pint',
  quart: 'quart', quarts: 'quart',
  gallon: 'gallon', gallons: 'gallon',
  can: 'can', cans: 'can',
  clove: 'clove', cloves: 'clove',
  slice: 'slice', slices: 'slice',
  piece: 'piece', pieces: 'piece',
  bunch: 'bunch', bunches: 'bunch',
  head: 'head', heads: 'head',
  sprig: 'sprig', sprigs: 'sprig',
  pinch: 'pinch',
  dash: 'dash',
  stick: 'stick', sticks: 'stick',
};

const WORD_NUMBERS: Record<string, number> = {
  one: 1, two: 2, three: 3, four: 4, five: 5,
  six: 6, seven: 7, eight: 8, nine: 9, ten: 10,
  half: 0.5, a: 1, an: 1,
};

const UNICODE_FRACTIONS: Record<string, number> = {
  '\u00BC': 0.25, '\u00BD': 0.5, '\u00BE': 0.75,
  '\u2150': 1/7, '\u2151': 1/9, '\u2152': 1/10,
  '\u2153': 1/3, '\u2154': 2/3, '\u2155': 1/5,
  '\u2156': 2/5, '\u2157': 3/5, '\u2158': 4/5,
  '\u2159': 1/6, '\u215A': 5/6, '\u215B': 1/8,
  '\u215C': 3/8, '\u215D': 5/8, '\u215E': 7/8,
};

const PREP_WORDS = /,?\s*\b(diced|minced|chopped|sliced|thinly sliced|grated|shredded|crushed|ground|melted|softened|warmed|cooled|room temperature|to taste|for garnish|for serving|optional|divided|packed|sifted|peeled|seeded|trimmed|halved|quartered|cubed|julienned|roughly chopped|finely chopped|finely diced|finely minced)\b.*$/i;

const PARENTHETICAL = /\s*\([^)]*\)\s*/g;

function parseFraction(s: string): number | null {
  // Unicode fractions
  for (const [char, val] of Object.entries(UNICODE_FRACTIONS)) {
    if (s.includes(char)) {
      const prefix = s.replace(char, '').trim();
      const whole = prefix ? parseFloat(prefix) : 0;
      return isNaN(whole) ? val : whole + val;
    }
  }

  // Mixed number: "2 1/2"
  const mixedMatch = s.match(/^(\d+)\s+(\d+)\/(\d+)$/);
  if (mixedMatch) {
    return parseInt(mixedMatch[1]) + parseInt(mixedMatch[2]) / parseInt(mixedMatch[3]);
  }

  // Simple fraction: "1/2"
  const fracMatch = s.match(/^(\d+)\/(\d+)$/);
  if (fracMatch) {
    return parseInt(fracMatch[1]) / parseInt(fracMatch[2]);
  }

  // Range: "2-3"
  const rangeMatch = s.match(/^(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)$/);
  if (rangeMatch) {
    return parseFloat(rangeMatch[2]);
  }

  // Plain number
  const num = parseFloat(s);
  return isNaN(num) ? null : num;
}

export function parseIngredient(line: string): ParsedIngredient {
  const original = line.trim();
  let text = original;

  // Strip leading "- "
  text = text.replace(/^-\s*/, '');

  // Strip parentheticals like "(14 oz)"
  text = text.replace(PARENTHETICAL, ' ').trim();

  // Strip prep words
  text = text.replace(PREP_WORDS, '').trim();

  // Try to extract quantity
  let quantity: number | null = null;
  let rest = text;

  // Check for word numbers first: "one large onion", "half a lemon"
  const wordMatch = text.match(/^(one|two|three|four|five|six|seven|eight|nine|ten|half|a|an)\b\s*/i);
  if (wordMatch) {
    const word = wordMatch[1].toLowerCase();
    if (word in WORD_NUMBERS) {
      quantity = WORD_NUMBERS[word];
      rest = text.slice(wordMatch[0].length);
    }
  }

  if (quantity === null) {
    // Try numeric patterns: "2 1/2", "1/3", "2-3", "2.5", unicode fractions
    // Match as much numeric content as possible from the start
    const numMatch = text.match(/^(\d+\s+\d+\/\d+|\d+\/\d+|\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?|\d+(?:\.\d+)?|[^\x00-\x7F])/);
    if (numMatch) {
      const parsed = parseFraction(numMatch[1].trim());
      if (parsed !== null) {
        quantity = parsed;
        rest = text.slice(numMatch[0].length).trim();
      }
    }
  }

  // Try to extract unit
  let unit: string | null = null;
  const unitMatch = rest.match(/^(\S+)\s+/);
  if (unitMatch) {
    const candidate = unitMatch[1].toLowerCase().replace(/\.$/, '');
    if (candidate in UNIT_MAP) {
      unit = UNIT_MAP[candidate];
      rest = rest.slice(unitMatch[0].length);
    }
  }

  // Also check if the rest starts with "of " after unit extraction
  rest = rest.replace(/^of\s+/i, '');

  const name = rest.toLowerCase().trim() || original.toLowerCase();

  return { quantity, unit, name, original };
}

export function formatQuantity(qty: number): string {
  if (qty === Math.floor(qty)) return String(qty);

  const fractions: [number, string][] = [
    [0.125, '1/8'], [0.25, '1/4'], [0.333, '1/3'], [0.375, '3/8'],
    [0.5, '1/2'], [0.625, '5/8'], [0.667, '2/3'], [0.75, '3/4'], [0.875, '7/8'],
  ];

  const whole = Math.floor(qty);
  const frac = qty - whole;

  for (const [val, str] of fractions) {
    if (Math.abs(frac - val) < 0.05) {
      return whole > 0 ? `${whole} ${str}` : str;
    }
  }

  return qty.toFixed(1).replace(/\.0$/, '');
}

export function formatIngredient(parsed: ParsedIngredient, scaleFactor: number = 1): string {
  if (parsed.quantity === null) return parsed.original;

  const scaled = parsed.quantity * scaleFactor;
  const qtyStr = formatQuantity(scaled);
  const unit = parsed.unit || '';
  const sep = unit ? ' ' : '';

  // Pluralize unit if quantity > 1 and unit is singular
  let displayUnit = unit;
  if (scaled > 1 && unit && !unit.endsWith('s') && unit !== 'oz' && unit !== 'tsp' && unit !== 'tbsp') {
    displayUnit = unit + 's';
  }

  return `${qtyStr}${sep}${displayUnit}${displayUnit ? ' ' : ''}${parsed.name}`;
}

export function ingredientKey(parsed: ParsedIngredient): string {
  return `${parsed.unit || '_'}:${parsed.name}`;
}
```

**Commit:** `git add frontend/src/lib/ingredients.ts && git commit -m "feat: add ingredient parser with quantity, unit, and name extraction"`

---

### Task 4: Serving Scaler Component

Create the +/- stepper and wire ingredient scaling into the recipe page.

**Files:**
- Create: `frontend/src/lib/components/ServingScaler.svelte`
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte`

**Code** (`frontend/src/lib/components/ServingScaler.svelte`):

```svelte
<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let originalServings: number;
  export let currentServings: number;

  const dispatch = createEventDispatcher();

  function decrease() {
    const step = originalServings;
    const next = currentServings - step;
    if (next >= Math.ceil(step / 2)) {
      dispatch('change', { servings: next });
    }
  }

  function increase() {
    dispatch('change', { servings: currentServings + originalServings });
  }

  $: isDefault = currentServings === originalServings;
</script>

<span class="scaler">
  <button class="scale-btn" on:click={decrease} aria-label="Decrease servings">&minus;</button>
  <span class="scale-value">{currentServings}</span>
  <button class="scale-btn" on:click={increase} aria-label="Increase servings">&plus;</button>
  {#if !isDefault}
    <button class="reset-link" on:click={() => dispatch('change', { servings: originalServings })}>reset</button>
  {/if}
</span>

<style>
  .scaler {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }

  .scale-btn {
    width: 26px;
    height: 26px;
    border: 1px solid var(--color-border);
    border-radius: 50%;
    background: var(--color-surface);
    color: var(--color-text);
    font-size: 1rem;
    line-height: 1;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s;
  }

  .scale-btn:hover {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .scale-value {
    font-weight: 600;
    min-width: 1.5rem;
    text-align: center;
  }

  .reset-link {
    background: none;
    border: none;
    color: var(--color-accent);
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0;
    margin-left: 0.25rem;
  }

  .reset-link:hover {
    text-decoration: underline;
  }
</style>
```

**Modify `frontend/src/routes/recipe/[slug]/+page.svelte`:**

Add imports at top of script:

```typescript
import ServingScaler from '$lib/components/ServingScaler.svelte';
import { parseIngredient, formatIngredient } from '$lib/ingredients';
```

Add scaling state after the existing state variables:

```typescript
// Scaling state
let currentServings: number | null = null;
let originalServings: number | null = null;

$: {
  if (recipe?.servings) {
    const parsed = parseInt(recipe.servings);
    if (!isNaN(parsed) && parsed > 0) {
      originalServings = parsed;
      if (currentServings === null) currentServings = parsed;
    } else {
      originalServings = null;
    }
  }
}

$: scaleFactor = (originalServings && currentServings) ? currentServings / originalServings : 1;
```

In the `renderWithHighlights` function, after rendering each section, apply scaling to ingredients:

```typescript
function renderWithHighlights(content: string, modified: Set<string>): string {
  if (modified.size === 0 && scaleFactor === 1) return renderMarkdown(content);

  const sections = parseSections(content);
  let html = '';
  for (const section of sections) {
    let sectionContent = section.content;

    // Scale ingredient quantities
    if (section.name.toLowerCase() === 'ingredients' && scaleFactor !== 1) {
      sectionContent = sectionContent.split('\n').map(line => {
        if (line.trim().startsWith('- ')) {
          const parsed = parseIngredient(line.trim());
          return `- ${formatIngredient(parsed, scaleFactor)}`;
        }
        return line;
      }).join('\n');
    }

    if (section.name === '_preamble') {
      html += renderMarkdown(sectionContent);
    } else {
      const isModified = modified.has(section.name);
      const sectionMd = `## ${section.name}\n\n${sectionContent}`;
      if (isModified) {
        html += `<div class="fork-modified">${renderMarkdown(sectionMd)}</div>`;
      } else {
        html += renderMarkdown(sectionMd);
      }
    }
  }
  return html;
}
```

Update the renderedBody reactive to include scaleFactor:

```typescript
$: renderedBody = renderWithHighlights(displayContent, modifiedSections);
```

(The function now reads `scaleFactor` from closure, so it will re-run when scaleFactor changes.)

In the template, replace the servings meta-item:

```svelte
{#if recipe.servings}
  <span class="meta-item">
    <strong>Serves:</strong>
    {#if originalServings}
      <ServingScaler
        {originalServings}
        currentServings={currentServings || originalServings}
        on:change={(e) => currentServings = e.detail.servings}
      />
    {:else}
      {recipe.servings}
    {/if}
  </span>
{/if}
```

Also reset scaling when fork changes — add to the `selectFork` function:

```typescript
currentServings = originalServings;
```

**Commit:** `git add frontend/src/lib/components/ServingScaler.svelte "frontend/src/routes/recipe/[slug]/+page.svelte" && git commit -m "feat: add serving scaler with ingredient quantity adjustment"`

---

### Task 5: Grocery List Store

Create the localStorage-backed grocery list store.

**Files:**
- Create: `frontend/src/lib/grocery.ts`

**Code** (`frontend/src/lib/grocery.ts`):

```typescript
import { writable, derived } from 'svelte/store';
import { parseIngredient, ingredientKey, formatQuantity } from './ingredients';
import type { ParsedIngredient } from './ingredients';

export interface GroceryRecipe {
  title: string;
  fork: string | null;
  servings: string | null;
  items: ParsedIngredient[];
}

export interface GroceryStore {
  recipes: Record<string, GroceryRecipe>;
  checked: string[];
  customCombines: Array<{ keys: string[]; quantity: number | null; unit: string | null; name: string }>;
}

const STORAGE_KEY = 'forks-grocery-list';

function loadStore(): GroceryStore {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return { recipes: {}, checked: [], customCombines: [] };
}

function saveStore(store: GroceryStore) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

export const groceryStore = writable<GroceryStore>(loadStore());

groceryStore.subscribe(saveStore);

export function addRecipeToGrocery(
  slug: string,
  title: string,
  ingredients: string[],
  fork: string | null = null,
  servings: string | null = null,
) {
  groceryStore.update(store => {
    store.recipes[slug] = {
      title,
      fork,
      servings,
      items: ingredients.map(parseIngredient),
    };
    return store;
  });
}

export function removeRecipeFromGrocery(slug: string) {
  groceryStore.update(store => {
    delete store.recipes[slug];
    return store;
  });
}

export function toggleChecked(key: string) {
  groceryStore.update(store => {
    const idx = store.checked.indexOf(key);
    if (idx >= 0) {
      store.checked.splice(idx, 1);
    } else {
      store.checked.push(key);
    }
    return store;
  });
}

export function clearChecked() {
  groceryStore.update(store => {
    store.checked = [];
    return store;
  });
}

export function clearAll() {
  groceryStore.set({ recipes: {}, checked: [], customCombines: [] });
}

export function addCustomCombine(keys: string[], quantity: number | null, unit: string | null, name: string) {
  groceryStore.update(store => {
    store.customCombines.push({ keys, quantity, unit, name });
    return store;
  });
}

export interface MergedItem {
  key: string;
  quantity: number | null;
  unit: string | null;
  name: string;
  displayText: string;
  sources: string[];
  checked: boolean;
}

export function getMergedItems(store: GroceryStore): MergedItem[] {
  const map = new Map<string, { quantity: number | null; unit: string | null; name: string; sources: string[] }>();

  // Collect keys that have been custom-combined
  const combinedKeys = new Set<string>();
  for (const combine of store.customCombines) {
    for (const k of combine.keys) combinedKeys.add(k);
  }

  for (const [slug, recipe] of Object.entries(store.recipes)) {
    for (const item of recipe.items) {
      const key = ingredientKey(item);
      if (combinedKeys.has(`${slug}:${key}`)) continue;

      if (map.has(key)) {
        const existing = map.get(key)!;
        if (existing.quantity !== null && item.quantity !== null && existing.unit === item.unit) {
          existing.quantity += item.quantity;
        }
        if (!existing.sources.includes(recipe.title)) {
          existing.sources.push(recipe.title);
        }
      } else {
        map.set(key, {
          quantity: item.quantity,
          unit: item.unit,
          name: item.name,
          sources: [recipe.title],
        });
      }
    }
  }

  // Add custom combines
  for (const combine of store.customCombines) {
    const key = `custom:${combine.name}`;
    map.set(key, {
      quantity: combine.quantity,
      unit: combine.unit,
      name: combine.name,
      sources: [],
    });
  }

  const items: MergedItem[] = [];
  for (const [key, val] of map) {
    const qtyStr = val.quantity !== null ? formatQuantity(val.quantity) : '';
    const unitStr = val.unit || '';
    const displayText = [qtyStr, unitStr, val.name].filter(Boolean).join(' ');

    items.push({
      key,
      quantity: val.quantity,
      unit: val.unit,
      name: val.name,
      displayText,
      sources: val.sources,
      checked: store.checked.includes(key),
    });
  }

  return items.sort((a, b) => a.name.localeCompare(b.name));
}

export const recipeCount = derived(groceryStore, $store => Object.keys($store.recipes).length);
```

**Commit:** `git add frontend/src/lib/grocery.ts && git commit -m "feat: add grocery list store with ingredient merging and localStorage persistence"`

---

### Task 6: Grocery List Page

Create the `/grocery` route with merged item display, checkboxes, and manual combine.

**Files:**
- Create: `frontend/src/routes/grocery/+page.svelte`

**Code** (`frontend/src/routes/grocery/+page.svelte`):

```svelte
<script lang="ts">
  import {
    groceryStore,
    getMergedItems,
    toggleChecked,
    clearChecked,
    clearAll,
    removeRecipeFromGrocery,
    addCustomCombine,
  } from '$lib/grocery';
  import type { MergedItem } from '$lib/grocery';

  let selected: Set<string> = new Set();
  let combineMode = false;
  let combineName = '';
  let combineQuantity = '';

  $: items = getMergedItems($groceryStore);
  $: toBuy = items.filter(i => !i.checked);
  $: gotIt = items.filter(i => i.checked);
  $: recipeEntries = Object.entries($groceryStore.recipes);

  function toggleSelect(key: string) {
    if (selected.has(key)) {
      selected.delete(key);
    } else {
      selected.add(key);
    }
    selected = new Set(selected);
  }

  function startCombine() {
    if (selected.size < 2) return;
    const selectedItems = items.filter(i => selected.has(i.key));
    // Try to auto-sum quantities
    let totalQty: number | null = 0;
    let commonUnit: string | null = selectedItems[0]?.unit || null;
    let canSum = true;
    for (const item of selectedItems) {
      if (item.quantity === null || item.unit !== commonUnit) {
        canSum = false;
        break;
      }
      totalQty = (totalQty || 0) + item.quantity;
    }
    if (!canSum) totalQty = null;

    combineQuantity = totalQty !== null ? String(totalQty) : '';
    combineName = selectedItems[0]?.name || '';
    combineMode = true;
  }

  function confirmCombine() {
    const keys = Array.from(selected).map(k => k);
    const qty = combineQuantity ? parseFloat(combineQuantity) : null;
    const selectedItems = items.filter(i => selected.has(i.key));
    const unit = selectedItems[0]?.unit || null;
    addCustomCombine(keys, isNaN(qty as number) ? null : qty, unit, combineName.trim());
    selected = new Set();
    combineMode = false;
    combineName = '';
    combineQuantity = '';
  }

  function cancelCombine() {
    combineMode = false;
    selected = new Set();
    combineName = '';
    combineQuantity = '';
  }
</script>

<svelte:head>
  <title>Grocery List - Forks</title>
</svelte:head>

<div class="grocery">
  <h1>Grocery List</h1>

  {#if items.length === 0}
    <p class="empty">Your grocery list is empty. Add recipes from their detail pages.</p>
  {:else}
    <div class="actions-bar">
      {#if selected.size >= 2 && !combineMode}
        <button class="action-btn combine-btn" on:click={startCombine}>Combine ({selected.size})</button>
      {/if}
      <button class="action-btn" on:click={clearChecked} disabled={gotIt.length === 0}>Clear checked</button>
      <button class="action-btn danger" on:click={clearAll}>Clear all</button>
    </div>

    {#if combineMode}
      <div class="combine-panel">
        <p class="combine-label">Combine selected items:</p>
        <div class="combine-fields">
          <input type="text" bind:value={combineQuantity} placeholder="Qty" class="combine-qty" />
          <input type="text" bind:value={combineName} placeholder="Ingredient name" class="combine-name" />
        </div>
        <div class="combine-actions">
          <button class="action-btn" on:click={confirmCombine} disabled={!combineName.trim()}>Confirm</button>
          <button class="action-btn" on:click={cancelCombine}>Cancel</button>
        </div>
      </div>
    {/if}

    {#if toBuy.length > 0}
      <h2 class="section-heading">To buy</h2>
      <ul class="item-list">
        {#each toBuy as item (item.key)}
          <li class="item" class:selected={selected.has(item.key)}>
            <label class="item-label">
              <input type="checkbox" checked={item.checked} on:change={() => toggleChecked(item.key)} />
              <span class="item-text">{item.displayText}</span>
            </label>
            {#if item.sources.length > 0}
              <span class="item-sources">{item.sources.join(', ')}</span>
            {/if}
            <button class="select-btn" class:active={selected.has(item.key)} on:click={() => toggleSelect(item.key)} aria-label="Select for combining">
              {selected.has(item.key) ? '✓' : '○'}
            </button>
          </li>
        {/each}
      </ul>
    {/if}

    {#if gotIt.length > 0}
      <h2 class="section-heading got-it">Got it</h2>
      <ul class="item-list">
        {#each gotIt as item (item.key)}
          <li class="item checked">
            <label class="item-label">
              <input type="checkbox" checked={item.checked} on:change={() => toggleChecked(item.key)} />
              <span class="item-text">{item.displayText}</span>
            </label>
          </li>
        {/each}
      </ul>
    {/if}

    {#if recipeEntries.length > 0}
      <h2 class="section-heading">Recipes on list</h2>
      <ul class="recipe-list">
        {#each recipeEntries as [slug, recipe]}
          <li class="recipe-entry">
            <a href="/recipe/{slug}">{recipe.title}</a>
            {#if recipe.fork}
              <span class="fork-tag">({recipe.fork})</span>
            {/if}
            {#if recipe.servings}
              <span class="servings-tag">{recipe.servings}</span>
            {/if}
            <button class="remove-btn" on:click={() => removeRecipeFromGrocery(slug)}>Remove</button>
          </li>
        {/each}
      </ul>
    {/if}
  {/if}
</div>

<style>
  .grocery {
    max-width: 600px;
  }

  h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 1.5rem;
  }

  .empty {
    color: var(--color-text-muted);
    text-align: center;
    padding: 4rem 1rem;
  }

  .actions-bar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }

  .action-btn {
    padding: 0.35rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text-muted);
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.15s;
  }

  .action-btn:hover:not(:disabled) {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .action-btn:disabled {
    opacity: 0.5;
    cursor: default;
  }

  .action-btn.danger:hover {
    border-color: #e74c3c;
    color: #e74c3c;
  }

  .combine-btn {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .combine-panel {
    padding: 1rem;
    border: 1px solid var(--color-accent);
    border-radius: var(--radius);
    margin-bottom: 1rem;
    background: var(--color-surface);
  }

  .combine-label {
    font-size: 0.85rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .combine-fields {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
  }

  .combine-qty {
    width: 60px;
    padding: 0.4rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.85rem;
  }

  .combine-name {
    flex: 1;
    padding: 0.4rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.85rem;
  }

  .combine-actions {
    display: flex;
    gap: 0.5rem;
  }

  .section-heading {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-text-muted);
    margin-bottom: 0.5rem;
    margin-top: 1.5rem;
    padding-bottom: 0.3rem;
    border-bottom: 1px solid var(--color-border);
  }

  .section-heading.got-it {
    opacity: 0.6;
  }

  .item-list {
    list-style: none;
    padding: 0;
  }

  .item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--color-border);
    font-size: 0.95rem;
  }

  .item.selected {
    background: var(--color-accent-light, #fdf0e6);
    margin: 0 -0.5rem;
    padding: 0.5rem;
    border-radius: var(--radius);
  }

  .item.checked {
    opacity: 0.5;
  }

  .item.checked .item-text {
    text-decoration: line-through;
  }

  .item-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex: 1;
    cursor: pointer;
  }

  .item-sources {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    white-space: nowrap;
  }

  .select-btn {
    background: none;
    border: 1px solid var(--color-border);
    border-radius: 50%;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 0.7rem;
    color: var(--color-text-muted);
    flex-shrink: 0;
  }

  .select-btn.active {
    background: var(--color-accent);
    color: white;
    border-color: var(--color-accent);
  }

  .recipe-list {
    list-style: none;
    padding: 0;
  }

  .recipe-entry {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0;
    font-size: 0.9rem;
  }

  .recipe-entry a {
    color: var(--color-accent);
  }

  .fork-tag, .servings-tag {
    font-size: 0.75rem;
    color: var(--color-text-muted);
  }

  .remove-btn {
    margin-left: auto;
    background: none;
    border: none;
    color: var(--color-text-muted);
    font-size: 0.8rem;
    cursor: pointer;
  }

  .remove-btn:hover {
    color: #e74c3c;
  }
</style>
```

**Commit:** `git add frontend/src/routes/grocery/+page.svelte && git commit -m "feat: add grocery list page with manual combine and checkboxes"`

---

### Task 7: Grocery Integration (Nav Badge + Recipe Page Button)

Wire the grocery list into the layout nav bar and recipe detail page.

**Files:**
- Modify: `frontend/src/routes/+layout.svelte`
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte`

**Code:**

In `frontend/src/routes/+layout.svelte`, add the grocery badge. Add import:

```typescript
import { recipeCount } from '$lib/grocery';
```

After the `<a href="/add" ...>+ Add</a>` link, add:

```svelte
<a href="/grocery" class="grocery-link" aria-label="Grocery list">
  🛒
  {#if $recipeCount > 0}
    <span class="grocery-badge">{$recipeCount}</span>
  {/if}
</a>
```

Add styles:

```css
.grocery-link {
  position: relative;
  text-decoration: none;
  font-size: 1.2rem;
  line-height: 1;
}

.grocery-badge {
  position: absolute;
  top: -6px;
  right: -8px;
  background: var(--color-accent);
  color: white;
  font-size: 0.65rem;
  font-weight: 700;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
```

In `frontend/src/routes/recipe/[slug]/+page.svelte`, add grocery button. Add imports:

```typescript
import { groceryStore, addRecipeToGrocery, removeRecipeFromGrocery } from '$lib/grocery';
```

Add reactive:

```typescript
$: onGroceryList = recipe ? recipe.slug in $groceryStore.recipes : false;
```

Add helper to extract raw ingredient lines:

```typescript
function getIngredientLines(content: string): string[] {
  const sections = parseSections(content);
  for (const section of sections) {
    if (section.name.toLowerCase() === 'ingredients') {
      return section.content.split('\n')
        .map(l => l.trim())
        .filter(l => l.startsWith('- '))
        .map(l => l.replace(/^-\s*/, ''));
    }
  }
  return [];
}
```

In the `recipe-actions` div, add the grocery button after the cook button:

```svelte
{#if onGroceryList}
  <button class="grocery-btn on-list" on:click={() => removeRecipeFromGrocery(recipe.slug)}>
    On Grocery List ✓
  </button>
{:else}
  <button class="grocery-btn" on:click={() => {
    if (recipe) {
      const lines = getIngredientLines(displayContent);
      addRecipeToGrocery(recipe.slug, displayTitle, lines, selectedFork, currentServings ? String(currentServings) : recipe.servings);
    }
  }}>
    Add to Grocery List
  </button>
{/if}
```

Add style:

```css
.grocery-btn {
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

.grocery-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.grocery-btn.on-list {
  border-color: var(--color-accent);
  color: var(--color-accent);
}
```

**Commit:** `git add frontend/src/routes/+layout.svelte "frontend/src/routes/recipe/[slug]/+page.svelte" && git commit -m "feat: add grocery list button on recipe page and badge in nav"`

---

### Task 8: Full Test Suite & Polish

Run all backend tests and frontend type checks. Fix any issues.

**Run:**
- `backend/venv/bin/python -m pytest backend/tests/ -v`
- `cd frontend && npx svelte-check --tsconfig ./tsconfig.json`

Fix any type errors or test failures. Commit fixes if needed.

**Commit:** `git commit -m "chore: fix type errors and test issues from Phase 5"`
