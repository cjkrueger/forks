# Phase 2 Design: "I can save recipes"

## Overview

Phase 2 adds the ability to create recipes — by scraping a URL or manual entry — and to edit and delete existing ones. Scraping uses a preview-before-save flow so users can tweak extracted data before committing.

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Scrape flow | Preview-before-save | User catches bad scrapes before they hit the filesystem |
| Image download | On save, not preview | Avoids cluttering images folder with abandoned scrapes |
| Image format | Preserve original | Simpler than re-encoding, most are jpg/webp anyway |
| Editor UI | Single shared component | Same form for create (empty/scraped) and edit (loaded) |
| Form style | Structured fields + textareas | Not a full markdown editor — power users edit .md files directly |

## New Files

### Backend
- `backend/app/scraper.py` — URL scraping with recipe-scrapers library
- `backend/app/generator.py` — Structured data → markdown file generation
- `backend/app/routes/editor.py` — CRUD + scrape API endpoints
- `backend/tests/test_scraper.py`
- `backend/tests/test_generator.py`
- `backend/tests/test_editor_routes.py`

### Frontend
- `frontend/src/routes/add/+page.svelte` — Add recipe page (URL scrape or manual)
- `frontend/src/routes/edit/[slug]/+page.svelte` — Edit recipe page
- `frontend/src/lib/components/RecipeEditor.svelte` — Shared editor form component

## New API Endpoints

```
POST   /api/scrape          — Scrape URL, return preview data (no save)
POST   /api/recipes         — Create new recipe from form data
PUT    /api/recipes/{slug}  — Update existing recipe
DELETE /api/recipes/{slug}  — Delete recipe and its image
```

## Scraper Module (`scraper.py`)

- Uses `recipe-scrapers` library (400+ site-specific drivers)
- Extracts: title, ingredients, instructions, prep_time, cook_time, servings, image_url, source, notes/description
- Returns structured dict for the API to forward to the frontend
- Separate function for image download: fetches URL, saves to `recipes/images/{slug}.ext`
- Uses `httpx` (already installed) for HTTP requests
- Graceful fallback — returns whatever it can extract, doesn't crash on partial data

## Markdown Generator (`generator.py`)

Takes structured recipe data, produces a clean `.md` file string:
- YAML frontmatter with all metadata fields
- `date_added` set to today's date automatically
- Ingredients as `- item` bullet list
- Instructions as `1. step` numbered list
- Notes as `- note` bullet list (section omitted if empty)
- Human-readable output — beautiful as plain text

## API Route Details

### `POST /api/scrape`
- Input: `{ "url": "https://..." }`
- Calls recipe-scrapers to extract data
- Returns: `{ title, ingredients, instructions, prep_time, cook_time, servings, image_url, source, notes }`
- No side effects — nothing saved
- Returns 422 if URL is unparseable

### `POST /api/recipes`
- Input: full recipe data from editor form (title, tags, servings, times, ingredients, instructions, notes, optional image_url)
- Generates slug from title (lowercase, hyphens, strip special chars)
- Downloads image if image_url provided
- Renders markdown via generator
- Saves .md file to recipes directory
- Index auto-updates via watchdog
- Returns 409 if slug already exists

### `PUT /api/recipes/{slug}`
- Input: updated recipe data
- Overwrites existing .md file
- Returns 404 if slug doesn't exist

### `DELETE /api/recipes/{slug}`
- Deletes .md file and associated image
- Returns 204 on success
- Returns 404 if slug doesn't exist

## Frontend Flow

### Add Recipe (`/add`)
- Two options: "From URL" or "Manual"
- From URL: paste URL → hit Scrape → loading spinner → editor form populated with extracted data, remote image preview shown
- Manual: editor form opens blank
- Both flows use the same RecipeEditor component

### RecipeEditor Component
- Structured fields: title, tags (comma-separated), servings, prep_time, cook_time, source
- Ingredients textarea (one per line)
- Instructions textarea (one per line)
- Notes textarea (one per line)
- Image preview
- Save button → POST (new) or PUT (edit)
- On success → navigate to recipe detail page

### Edit Recipe (`/edit/{slug}`)
- "Edit" button added to recipe detail page
- Loads existing recipe into RecipeEditor
- Delete button with confirmation prompt
- Delete → DELETE API → navigate home

## New Dependencies

- `recipe-scrapers` — add to requirements.txt
