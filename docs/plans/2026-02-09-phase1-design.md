# Phase 1 Design: "I can read recipes"

## Overview

Phase 1 delivers the foundation: a self-hosted web app that reads `.md` recipe files from a folder and renders them in a clean, mobile-friendly UI with tag filtering and search.

No database. No scraping yet. Drop markdown files in a folder, browse them beautifully.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Frontend | SvelteKit (adapter-static) | Lightweight, fast, small bundle. Content-focused app. |
| Backend | FastAPI (Python) | Best scraping ecosystem for Phase 2. Simple and fast. |
| Deployment | Single Docker container | FastAPI serves built Svelte static files. One container on Unraid. |
| Storage | Mounted folder of `.md` files | No database. Portable, git-friendly, human-readable. |
| Search | Server-side over in-memory index | One implementation, no index transfer to client. |
| Markdown delivery | Raw markdown to frontend | Frontend renders with `marked`. Full control for fork system later. |
| Index | In-memory dict + watchdog | Fast reads, no DB, rebuilds on restart in milliseconds. |
| Images | Stored in `recipes/images/` | Co-located with markdown files. Portable. |

## Project Structure

```
forks/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, mounts static files
│   │   ├── config.py            # Settings (recipes dir, host, port)
│   │   ├── models.py            # Pydantic models (Recipe, RecipeSummary)
│   │   ├── index.py             # In-memory recipe index + watchdog
│   │   ├── parser.py            # Frontmatter + markdown parsing
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── recipes.py       # API endpoints
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── +layout.svelte   # Shell: top bar + sidebar + content
│   │   │   ├── +page.svelte     # Home: recipe card grid
│   │   │   └── recipe/
│   │   │       └── [slug]/
│   │   │           └── +page.svelte  # Recipe detail view
│   │   ├── lib/
│   │   │   ├── api.ts           # Fetch wrapper for /api/*
│   │   │   ├── components/      # RecipeCard, TagFilter, SearchBar
│   │   │   └── markdown.ts      # Client-side markdown rendering
│   │   └── app.html
│   ├── static/
│   ├── svelte.config.js
│   ├── package.json
│   └── vite.config.ts
├── recipes/                     # Sample recipes + images/
│   └── images/
├── Dockerfile
├── docker-compose.yml
└── plan.md
```

## Data Models

```python
class RecipeSummary(BaseModel):
    slug: str              # filename without .md
    title: str
    tags: list[str]
    servings: str | None
    prep_time: str | None
    cook_time: str | None
    date_added: str | None
    source: str | None
    image: str | None      # relative path: images/{slug}.jpg

class Recipe(RecipeSummary):
    content: str           # raw markdown body (after frontmatter)
```

## Parser

- `python-frontmatter` splits YAML frontmatter from markdown body
- Slug derived from filename: `birria-tacos.md` -> `birria-tacos`
- Malformed files: use filename as title, log a warning, don't crash

## In-Memory Index

**On startup:**
1. Scan recipes directory for `.md` files
2. Parse frontmatter only (not body) for each file
3. Store `dict[slug, RecipeSummary]` in memory

**File watching (watchdog):**
- Create/modify: re-parse that file's frontmatter, update dict
- Delete: remove from dict
- Debounce rapid changes (~500ms) to handle editor save patterns

**Detail view reads full file on demand** — body is never cached. Keeps memory low and content always fresh.

## API Routes

```
GET  /api/recipes          # List all recipes (RecipeSummary[])
                           # ?tags=mexican,beef — filter by ALL specified tags
                           # Sorted alphabetically by title

GET  /api/recipes/{slug}   # Full recipe detail (Recipe)
                           # 404 if not found

GET  /api/search?q=        # Search title, tags, ingredient lines
                           # Returns RecipeSummary[]
```

**Static serving:**
- `/api/*` -> FastAPI routes
- `/api/images/*` -> mounted from recipes/images/ directory
- Everything else -> built SvelteKit static files

No pagination. Household collections won't exceed a few hundred recipes.

## Frontend

**Layout:**
- Top bar: "Forks" branding + search input
- Sidebar: tag list with counts, clickable to filter
- Responsive: sidebar collapses to hamburger on mobile

**Home page (recipe grid):**
- Cards showing image thumbnail (or placeholder), title, tags, prep/cook time
- Active tag filters shown as dismissible chips above grid
- Click card -> navigate to `/recipe/{slug}`

**Recipe detail:**
- Hero image at top (if available)
- Header: title, source link, tag chips, servings, prep/cook time
- Body: markdown rendered to HTML via `marked`
- Clean styling: ingredients with breathing room, numbered steps with spacing
- Back button to browse

**Mobile recipe view:**
- Single column, no sidebar
- Large text (18-20px body)
- Extra padding on ingredients/instructions for thumb-scrolling
- Comfortable to read at arm's length from a propped-up phone

**Styling:** Custom CSS, no component library. Calm and focused.

## Docker

**Multi-stage Dockerfile:**

```
Stage 1: frontend-build
  - Node image
  - npm install + npm run build
  - Output: static files

Stage 2: production
  - Python slim image
  - pip install from requirements.txt
  - Copy backend app code
  - Copy built frontend static files
  - Expose 8000
  - CMD: uvicorn app.main:app --host 0.0.0.0
```

**docker-compose.yml:**

```yaml
services:
  forks:
    build: .
    ports:
      - "8420:8000"
    volumes:
      - /path/to/recipes:/data/recipes
    environment:
      - RECIPES_DIR=/data/recipes
```

Single volume mount. No database, no config volume. Just the recipes folder.

## Config

- `RECIPES_DIR` — env var, defaults to `./recipes` for local dev
- `HOST` / `PORT` — uvicorn bind, defaults to `0.0.0.0:8000`

## Local Development

- **Backend:** `uvicorn app.main:app --reload` (auto-reload on changes)
- **Frontend:** `npm run dev` (Vite HMR, proxies `/api/*` to backend)
- Run both simultaneously. No Docker needed for dev.
- 3-4 sample recipes in `recipes/` for testing

## Dependencies

**Backend:** fastapi, uvicorn, python-frontmatter, watchdog, pydantic

**Frontend:** svelte, sveltekit, @sveltejs/adapter-static, marked

## Phase 1 Deliverable

Drop `.md` recipe files (with optional images) in a folder and browse them in a polished, mobile-friendly web UI with tag filtering and search. Ready to build Phase 2 (scraping) on top.
