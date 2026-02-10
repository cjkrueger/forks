# Phase 8: UI Overhaul, Embedded History, Likes & Attribution — Design Document

**Goal:** Upgrade the recipe detail layout with a hero banner, add tile/table view switching with customizable columns on the home screen, embed fork history directly in files so it works without git, add a cumulative like counter, and scrape author names for attribution.

**Architecture:** All new data lives in markdown frontmatter — likes, changelog, author. The stream visualization reads from embedded changelogs instead of git log. View preferences persist in localStorage. No new backend dependencies.

---

## 1. Recipe Detail — Hero Banner Layout

### Layout

The recipe detail page gets a full-width hero image that bleeds edge-to-edge. The image fills the viewport width at 50vh height (capped at 500px) using `object-fit: cover`. A dark gradient fades up from the bottom third. The recipe title, prep/cook time, and servings are overlaid on the gradient in white text. The favorite button and like counter sit in the top-right corner of the banner.

Below the hero, a sticky action bar holds: version selector pills (Original + forks), Start Cooking, Edit, Fork, Print, and other action buttons. This bar sticks to the top of the viewport as the user scrolls.

The recipe body (ingredients, instructions, notes) renders below the action bar, same structure as today.

### No-Image Fallback

When a recipe has no image, skip the hero entirely. Show the title as a plain heading — no empty placeholder or generic stock image.

### Mobile

Hero height shrinks to 35vh. Title font scales down. The sticky action bar becomes horizontally scrollable.

### Files Changed

- `frontend/src/routes/recipe/[slug]/+page.svelte` — Hero banner, gradient overlay, sticky action bar
- `frontend/src/app.css` — Print rules updated to hide hero gradient/overlay

---

## 2. Home Screen — Tile/Table Toggle & Filtering

### View Toggle

Two icon buttons (grid icon, list icon) in the top-right of the page, next to the discovery chips. Selected view persists in `localStorage`.

### Tile View (Enhanced)

Same card grid as today. Cards gain a small like count (heart + number) in the corner and a subtle "last cooked" date if available.

### Table View

A data table with sortable column headers. Click a column header to sort ascending; click again for descending. Default visible columns: Title, Tags, Cook Time, Likes, Last Cooked.

### Column Customization

A gear icon next to the view toggle opens a dropdown checklist of available columns:

| Column | Default visible |
|---|---|
| Title | Always on |
| Tags | Yes |
| Cook Time | Yes |
| Likes | Yes |
| Last Cooked | Yes |
| Prep Time | No |
| Total Time | No |
| Servings | No |
| Date Added | No |
| Source | No |

Column selections saved to `localStorage`. No backend changes needed — the list endpoint already returns all this data.

### Filter Bar

Below the discovery chips, a collapsible filter row:

- **Tag pills** — populated from all tags across recipes, click to toggle (multi-select)
- **Sort dropdown** — replaces the implicit sort-by-chip approach, all sort options in one place
- **Search input** — the existing search moves into the filter bar

URL params still drive state (`?tags=...&sort=...&q=...`) so filters are shareable and bookmarkable.

### Files Changed

- `frontend/src/routes/+page.svelte` — View toggle, filter bar, table view
- `frontend/src/lib/components/RecipeTable.svelte` — New table component
- `frontend/src/lib/components/ColumnPicker.svelte` — New column customization dropdown

---

## 3. Like Counter

### Frontmatter

New `likes` field in recipe frontmatter. Integer, defaults to 0.

```yaml
title: Birria Tacos
likes: 12
tags:
  - beef
  - favorite
```

### Behavior

Every click increments by 1. No debounce, no undo, no identity tracking. Unlimited clicks per person. The number is the point — a recipe cooked and loved 50 times by the family naturally accumulates likes.

### Separate from Favorites

The existing favorite toggle stays as a personal boolean (filled/unfilled heart for "this is my go-to"). The like button is a different affordance — a smaller outlined heart with the count displayed next to it.

### Placement

- **Recipe detail:** top-right corner of the hero banner, alongside the favorite button
- **Tile view cards:** bottom-right corner, small and muted
- **Table view:** sortable "Likes" column

### API

`POST /api/recipes/{slug}/like` — reads frontmatter, increments `likes` by 1, writes file, git commits. The list and detail endpoints already return frontmatter fields, so `likes` flows through automatically.

### Sorting

New sort option: `sort=likes` (descending). New discovery chip: "Most loved."

### Files Changed

- `backend/app/routes/cook.py` — New like endpoint
- `backend/app/parser.py` — Parse `likes` from frontmatter
- `backend/app/models.py` — Add `likes` to Recipe/RecipeSummary models
- `frontend/src/lib/components/LikeButton.svelte` — New component
- `frontend/src/lib/api.ts` — New `likeRecipe()` function
- `frontend/src/routes/recipe/[slug]/+page.svelte` — Like button in hero
- `frontend/src/routes/+page.svelte` — Like count on cards, "Most loved" chip

---

## 4. Embedded Fork History (Changelog)

### Core Concept

Every recipe and fork file gets a `changelog` array in its frontmatter. Each entry records what changed and when. This is the primary source of truth for history — works without git, survives file copies, travels with the file.

### Frontmatter Format

```yaml
fork_name: "Mom's smoky version"
forked_from: pasta-carbonara
changelog:
  - date: '2026-02-05'
    action: created
    summary: Forked from original
  - date: '2026-02-07'
    action: edited
    summary: Updated ingredients, instructions
  - date: '2026-02-10'
    action: merged
    summary: Merged into original
```

### When Entries Are Written

| Event | Action | Summary |
|---|---|---|
| Fork created | `created` | "Forked from original" |
| Fork edited | `edited` | Auto-generated from changed sections (e.g. "Updated ingredients, instructions") |
| Fork merged into base | `merged` | "Merged into original" |
| Base recipe edited | `edited` | Auto-generated from changed sections |
| Base recipe created | `created` | "Created" |

Base recipes also get changelogs, tracking their own edits and when forks merged into them.

### Auto-Generated Summaries

When a recipe or fork is edited, the backend diffs the old and new content to identify which sections changed (ingredients, instructions, notes, metadata). The summary lists the changed sections: "Updated ingredients, instructions" or "Updated cook time, tags."

### Stream Visualization Rewrite

The `StreamGraph` component and `/api/recipes/{slug}/stream` endpoint read from changelog arrays instead of git log. The endpoint assembles the timeline by combining the base recipe's changelog with all fork changelogs, sorting chronologically. Same visual output, same node types (created, edited, forked, merged), but now works for everyone.

### Git as Optional Enrichment

If git is available, commit hashes can be attached to changelog entries (`commit` field). Users with git can diff between versions. But the stream works without them — the changelog is self-sufficient.

### Files Changed

- `backend/app/routes/editor.py` — Write changelog entries on create/update
- `backend/app/routes/forks.py` — Write changelog entries on fork create/edit/merge
- `backend/app/routes/stream.py` — Rewrite to read from changelogs instead of git log
- `backend/app/parser.py` — Parse `changelog` from frontmatter
- `backend/app/models.py` — Add `ChangelogEntry` model, update `StreamEvent`
- `backend/app/sections.py` — Add section-level diff for auto-generated summaries
- `frontend/src/lib/components/StreamGraph.svelte` — No changes needed (data format stays the same)

---

## 5. Author Attribution

### Scraping

Call `scraper.author()` from the `recipe_scrapers` library during scrape. Store it in a new `author` frontmatter field.

```yaml
title: 7-Layer Casserole
source: https://www.foodnetwork.com/recipes/...
author: Ree Drummond
```

### Display

Small "by Ree Drummond" line directly below the source link on the recipe detail page. Muted text, same font size as the source URL. If no author was scraped, nothing renders.

### Editor

The scrape response includes `author`, which pre-fills an optional "Author" text field in the recipe editor. Users can edit or clear it.

### Existing Recipes

No migration needed. The field is optional. Recipes without `author` simply don't show the attribution line.

### Files Changed

- `backend/app/scraper.py` — Call `scraper.author()`, add to result dict
- `backend/app/models.py` — Add `author` to Recipe model, ScrapeResponse
- `backend/app/parser.py` — Parse `author` from frontmatter
- `backend/app/generator.py` — Write `author` to frontmatter
- `frontend/src/lib/types.ts` — Add `author` to types
- `frontend/src/routes/recipe/[slug]/+page.svelte` — Render attribution line
- `frontend/src/lib/components/RecipeEditor.svelte` — Author text field
- `frontend/src/routes/add/+page.svelte` — Pass `author` from scrape to editor
