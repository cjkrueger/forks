# Phase 5: "It knows me" — Design Document

**Goal:** Add discovery features (surprise me, never tried, cook again, quick meals), a grocery list with ingredient parsing and manual combine, and serving scaling with a +/- stepper.

**Architecture:** Discovery is backend sort/filter on existing frontmatter data. Grocery list and scaling are frontend-only, sharing a common ingredient parser. No new data storage — grocery list uses localStorage, scaling is ephemeral.

---

## 1. Discovery Features

Four suggestion chips above the recipe grid on the home page. Each is a toggle — click to activate, click again to deactivate. Only one active at a time. Coexists with tag filtering and search.

**Chips:**

- **"Surprise me"** — Calls `GET /api/recipes/random`, navigates directly to the recipe. No grid filtering.
- **"Never tried"** — `GET /api/recipes?sort=never-cooked`. Recipes with empty `cook_history`, sorted by `date_added` descending.
- **"Cook again"** — `GET /api/recipes?sort=least-recent`. Recipes with non-empty `cook_history`, sorted by oldest last-cook date first.
- **"Quick meals"** — `GET /api/recipes?sort=quick`. Recipes where `prep_time + cook_time <= 30 min`, sorted alphabetically.

Style: horizontal row of pill buttons matching the fork version pill style. Active chip highlighted with accent color.

---

## 2. Ingredient Parser

Shared frontend TypeScript utility (`$lib/ingredients.ts`) powering both grocery list and scaling.

**Input:** Raw ingredient string (e.g., `"2 1/2 cups chicken broth, warmed"`)

**Output:**
```typescript
{
  quantity: number | null,
  unit: string | null,    // normalized canonical form
  name: string,           // cleaned, lowercased
  original: string        // unmodified input
}
```

**Parsing pipeline:**
1. Strip parenthetical notes and trailing prep words ("diced", "minced", "warmed", "to taste")
2. Extract quantity — integers, decimals, fractions (`1/2`), mixed (`2 1/2`), ranges (`2-3` → higher value), unicode fractions (`½`), word numbers ("one", "two", "half")
3. Normalize unit — synonyms to canonical: `cups/c/C → cup`, `tablespoons/tbsp/Tbsp/T → tbsp`, `teaspoons/tsp/t → tsp`, `ounces/oz → oz`, `pounds/lbs/lb → lb`. Unitless items get `unit: null`.
4. Remaining text becomes `name`, lowercased and trimmed.

**Edge cases:**
- `"1 (14 oz) can crushed tomatoes"` → quantity 1, unit "can", name "crushed tomatoes" (parenthetical stripped)
- `"Salt and pepper to taste"` → quantity null, unit null, name "salt and pepper"
- `"3 eggs"` → quantity 3, unit null, name "eggs"

No semantic understanding — "chicken broth" and "broth" are different names. Manual combine on the grocery page fills that gap.

---

## 3. Grocery List

### Data Model (localStorage)

```typescript
{
  recipes: {
    [slug: string]: {
      title: string,
      fork: string | null,
      servings: string | null,
      items: ParsedIngredient[]
    }
  },
  checked: string[]  // item keys for checked-off items
}
```

### Adding to the List

"Add to grocery list" button on recipe detail page in the actions row. Uses the current fork's merged ingredients if a fork is selected. Uses scaled quantities if scaling is active. Button changes to "On grocery list" with remove option when already added. Badge in nav bar shows count of recipes on the list.

### The `/grocery` Page

- Ingredients merged across all recipes, split into "To buy" (unchecked) and "Got it" (checked)
- Auto-matched items (same normalized name + compatible unit) pre-combined with summed quantities
- Each item shows combined quantity/unit/name with subtle label showing source recipes
- Checkbox to mark items as bought

**Manual combine:** User taps two items to select them (highlight border), "Combine" button appears. App adds quantities if units match, shows inline text input pre-filled with suggested name. User confirms or edits. If units don't match, quantities are concatenated and user sorts it out.

**Actions:** "Clear checked" to remove bought items, "Clear all" to reset, per-recipe remove (X button to drop a recipe's ingredients).

---

## 4. Serving Scaling

+/- stepper next to servings display in recipe header. Shows "Serves: 4" with minus/plus buttons.

**Behavior:**
- Increments match original servings (if original is 4: 2, 4, 6, 8...)
- Minimum: half the original. No upper cap.
- "Reset" link appears when scale isn't 1x.
- If `servings` can't be parsed to a number, stepper doesn't render.

**Scaling logic:**
- `scaleFactor = newServings / originalServings`
- Each ingredient run through parser; quantity multiplied by scale factor
- Formatting: fractions where natural (0.25 → "1/4", 0.5 → "1/2", 0.33 → "1/3"), otherwise one decimal. Whole numbers stay whole.
- Non-numeric ingredients pass through unchanged.

**Scope:** View-only, purely frontend, never writes to file. Applies to ingredient section only — instruction text unchanged. Scale factor resets on page navigation. Works with forks (scales the merged ingredients).

**Grocery interaction:** When adding a scaled recipe to the grocery list, scaled quantities are stored. Entry records adjusted servings.

---

## 5. API Changes

### New Endpoint

- `GET /api/recipes/random` — Returns single random `RecipeSummary`

### Extended Endpoint

- `GET /api/recipes` — New `sort` query parameter:
  - `sort=never-cooked` — Empty cook_history, sorted by date_added desc
  - `sort=least-recent` — Non-empty cook_history, sorted by oldest last-cook first
  - `sort=quick` — prep_time + cook_time <= 30 min, alphabetical
  - No sort param — existing alphabetical behavior

### No Backend Needed For

- Grocery list (localStorage)
- Serving scaling (frontend-only)
- Ingredient parser (frontend utility)
- Manual combine (frontend UI)

---

## 6. File Changes

### New Files
- `frontend/src/lib/ingredients.ts` — Shared ingredient parser
- `frontend/src/lib/components/GroceryList.svelte` — Grocery page component
- `frontend/src/lib/components/ServingScaler.svelte` — +/- stepper component
- `frontend/src/routes/grocery/+page.svelte` — Grocery list page

### Modified Files
- `backend/app/routes/recipes.py` — Add `sort` param + random endpoint
- `frontend/src/routes/+page.svelte` — Discovery chips
- `frontend/src/routes/recipe/[slug]/+page.svelte` — Scaling stepper + grocery button
- `frontend/src/routes/+layout.svelte` — Grocery badge in nav
- `frontend/src/lib/api.ts` — New API functions
