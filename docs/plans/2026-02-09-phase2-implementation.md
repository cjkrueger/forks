# Phase 2 Implementation Plan: "I can save recipes"

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add recipe creation (URL scraping + manual entry), editing, and deletion to Forks.

**Architecture:** New scraper module uses recipe-scrapers library. Generator module converts structured data to markdown. New CRUD + scrape API endpoints. Frontend gets an editor form component and add/edit pages.

**Tech Stack:** recipe-scrapers, httpx (already installed), existing FastAPI + SvelteKit stack.

---

### Task 1: Add recipe-scrapers dependency

**Files:**
- Modify: `backend/requirements.txt`

**Step 1:** Add `recipe-scrapers` to requirements.txt and install.

**Step 2:** Commit.

---

### Task 2: Markdown Generator (TDD)

**Files:**
- Create: `backend/app/generator.py`
- Create: `backend/tests/test_generator.py`

Generator takes structured recipe data and produces a clean markdown string with YAML frontmatter.

Tests should cover:
- Full recipe with all fields generates correct markdown
- Missing optional fields (no notes, no image) are handled gracefully
- Tags rendered as YAML list
- Ingredients as bullet list
- Instructions as numbered list
- date_added set automatically
- Slugification of title

---

### Task 3: Scraper Module (TDD)

**Files:**
- Create: `backend/app/scraper.py`
- Create: `backend/tests/test_scraper.py`

Scraper takes a URL, returns structured data using recipe-scrapers library. Separate function for image downloading.

Tests should cover:
- Scraping returns structured data dict
- Graceful handling when scraper can't parse a site
- Image download function saves to correct path
- Slugify function generates valid filenames

---

### Task 4: Editor API Routes (TDD)

**Files:**
- Create: `backend/app/routes/editor.py`
- Create: `backend/tests/test_editor_routes.py`
- Modify: `backend/app/main.py` (register new router)

Four new endpoints: POST /api/scrape, POST /api/recipes, PUT /api/recipes/{slug}, DELETE /api/recipes/{slug}.

Tests should cover:
- Scrape endpoint returns structured data
- Create recipe saves .md file and returns recipe
- Create with duplicate slug returns 409
- Update recipe modifies existing file
- Update nonexistent returns 404
- Delete recipe removes file
- Delete nonexistent returns 404

---

### Task 5: Frontend — API Client Updates

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/lib/types.ts`

Add new API functions: scrapeRecipe, createRecipe, updateRecipe, deleteRecipe. Add types for scrape response and recipe input.

---

### Task 6: Frontend — RecipeEditor Component

**Files:**
- Create: `frontend/src/lib/components/RecipeEditor.svelte`

Shared form component with structured fields for all recipe metadata, textareas for ingredients/instructions/notes, image preview, save button.

---

### Task 7: Frontend — Add Recipe Page

**Files:**
- Create: `frontend/src/routes/add/+page.svelte`

Page with "From URL" and "Manual" tabs. URL tab has input + scrape button. Both populate the RecipeEditor component.

Add an "Add Recipe" button/link to the layout or home page for navigation.

---

### Task 8: Frontend — Edit Recipe Page

**Files:**
- Create: `frontend/src/routes/edit/[slug]/+page.svelte`
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte` (add Edit button)

Edit page loads existing recipe into RecipeEditor. Delete button with confirmation. Edit button added to recipe detail page header.

---

### Task 9: Integration Test

Verify end-to-end:
- All backend tests pass
- Frontend builds
- Scrape → preview → save flow works
- Manual entry works
- Edit and delete work

---

## Summary

| Task | Description |
|------|-------------|
| 1 | Add recipe-scrapers dependency |
| 2 | Markdown generator (TDD) |
| 3 | Scraper module (TDD) |
| 4 | Editor API routes (TDD) |
| 5 | Frontend API client updates |
| 6 | RecipeEditor component |
| 7 | Add recipe page |
| 8 | Edit recipe page |
| 9 | Integration test |
