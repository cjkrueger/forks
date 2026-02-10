# Phase 3: "I can make it mine" — Fork System Design

## Goal

Let users create named versions (forks) of any recipe, view them with diff highlighting, set a preferred default version, and export complete standalone recipe files.

## Key Design Decisions

- **No auth system.** Fork identity comes from the version name, not a user account. An optional author field covers attribution when needed.
- **Separate fork files.** Base recipe stays clean and readable. Forks live alongside as `slug.fork.name.md` files containing only modified sections.
- **Section-level storage, line-level display.** Fork files store complete modified sections (Ingredients, Instructions, Notes). The frontend computes line-level diffs at render time for highlighting.
- **Primary version in local storage.** Each browser remembers which fork to show by default per recipe. No backend state needed.

## File Format

### Base recipe (unchanged)

```
recipes/chocolate-chip-cookies.md
```

### Fork files

```
recipes/chocolate-chip-cookies.fork.vegan.md
recipes/chocolate-chip-cookies.fork.brown-butter.md
```

Fork file contents — only modified sections, with fork metadata in frontmatter:

```markdown
---
forked_from: chocolate-chip-cookies
fork_name: Vegan Chocolate Chip Cookies
author: CJ
date_added: 2026-02-10
---

## Ingredients

- 2 1/4 cups all-purpose flour
- 1 tsp baking soda
- 1 cup coconut oil
- 3/4 cup granulated sugar
- 2 flax eggs
- 1 cup dark chocolate chips (dairy-free)

## Notes

- Coconut oil needs to be solid, not melted
```

Sections not present in the fork (e.g. Instructions) are inherited from the base at render time.

## Merge & Diff Logic

**Merge (rendering a fork view):**
1. Parse base recipe into sections (split on `## ` headers)
2. Parse fork file into sections
3. For each section header: use fork version if present, otherwise base
4. Combine into final markdown for rendering

**Diff (highlighting changes):**
1. For each section present in the fork, compare line-by-line against the same base section
2. Mark lines as added, removed, or changed
3. Frontend renders highlights (subtle left border or background tint)

Both merge and diff happen client-side since the frontend already receives raw markdown.

## API

Existing endpoints unchanged. New fork endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/recipes/{slug}` | Unchanged, but response adds `forks: [{name, fork_name, author, date_added}]` |
| GET | `/api/recipes/{slug}/forks/{name}` | Returns fork metadata + raw content (modified sections only) |
| POST | `/api/recipes/{slug}/forks` | Create fork. Body: full recipe data + fork_name + optional author. Backend diffs against base, writes only changed sections. |
| PUT | `/api/recipes/{slug}/forks/{name}` | Update fork. Same diff logic as create. |
| DELETE | `/api/recipes/{slug}/forks/{name}` | Delete fork file. |
| GET | `/api/recipes/{slug}/forks/{name}/export` | Returns complete merged markdown (base + fork) as downloadable file. |

## Frontend UI

### Recipe detail page changes

- **Version selector** appears below the title when forks exist — a dropdown or pill group: "Original", "Vegan", "Brown Butter", etc.
- Default view is "Original" unless the user has set a primary in localStorage.
- When viewing a fork: recipe renders with fork sections merged in. Changed lines get a subtle highlight.
- "Set as default" link saves preference to localStorage.

### Creating a fork

- "Fork this recipe" button on recipe detail page.
- Opens RecipeEditor pre-populated with base recipe data.
- Additional fields: "Fork name" (required), "Author" (optional).
- On save: backend diffs against base, writes fork file with only changed sections.

### Editing a fork

- When viewing a fork, the "Edit" button edits the fork (not the base).
- Editor shows the merged view (base + fork) so you see the full recipe.
- On save: backend re-diffs against base, updates the fork file.

### Exporting a fork

- "Export" button when viewing a fork.
- Downloads a complete standalone `.md` file (base + fork merged, no forked_from metadata).

## Index Changes

- The in-memory index needs to track forks per recipe.
- On startup and file change, detect `*.fork.*.md` files and associate them with their base recipe.
- `RecipeSummary` gains a `forks` field: list of `{name, fork_name, author, date_added}`.
- Fork files are NOT listed as standalone recipes in the main recipe list.

## Section Diffing Algorithm

For computing which sections changed (on fork creation/update):

1. Parse base recipe markdown into sections: `{"Ingredients": "...", "Instructions": "...", "Notes": "..."}`
2. Parse submitted recipe the same way
3. Compare each section's content (stripped/normalized)
4. Write only sections where content differs
5. If no sections differ, reject the fork (nothing changed)

## Data Flow

```
Create fork:
  Editor (full recipe) → POST /api/recipes/{slug}/forks
  → Backend diffs against base → writes slug.fork.name.md (changed sections only)
  → Updates index → returns fork metadata

View fork:
  GET /api/recipes/{slug} (base + fork list)
  GET /api/recipes/{slug}/forks/{name} (fork content)
  → Frontend merges sections → renders with diff highlights

Export fork:
  GET /api/recipes/{slug}/forks/{name}/export
  → Backend merges base + fork → returns complete markdown
