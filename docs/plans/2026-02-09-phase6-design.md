# Phase 6: Meal Planner, Print View & Fork History — Design Document

**Goal:** Add a weekly meal planner with markdown storage, a print-friendly recipe view, and git-powered fork history with auto-commit.

**Architecture:** Meal planner uses a single `meal-plan.md` file with YAML frontmatter. Print view is pure CSS (@media print). Fork history reads git log from the recipes directory, with auto-commit on every file write.

---

## 1. Meal Planner

### Storage

Single `meal-plan.md` file in the recipes directory. YAML frontmatter maps ISO dates to recipe lists:

```yaml
---
weeks:
  2026-02-09:
    - slug: birria-tacos
    - slug: chicken-alfredo-soup
      fork: vegan
  2026-02-10:
    - slug: french-onion-chicken-pot-pie
  2026-02-12:
    - slug: birria-tacos
---
```

Markdown body is auto-generated as human-readable summary. Frontmatter is source of truth.

### UI

Route: `/planner`. 7-day column grid (Mon–Sun) for the current week. Previous/next week arrows. Each day is a column with flexible unlabeled slots — add as many recipes as you want.

Click "+" button on a day to open a search picker dropdown. Text field filters recipes as you type. Select a recipe to add it. Click X on a slot to remove. Recipe names link to their detail page.

### API

- `GET /api/meal-plan?week=2026-W07` — Returns the week's plan (7 days of recipe slug lists)
- `PUT /api/meal-plan` — Saves the entire plan file

Backend reads/writes `meal-plan.md` directly using python-frontmatter.

---

## 2. Print-Friendly View

No new routes. A print icon button in the recipe-actions row calls `window.print()`.

### CSS @media print rules (in app.css)

**Hide:**
- Top nav bar, sidebar, overlay
- Back link, version pills, action buttons
- Cook history, favorite button
- Fork modified highlight borders (show content only)

**Optimize:**
- Recipe title at full width
- Meta info (prep, cook, servings) inline
- Tags as comma-separated text
- Generous line spacing for ingredients/instructions
- Source URL printed as visible text
- No background colors or shadows
- Avoid page breaks inside ingredient lists or steps

Scaled ingredients print as displayed (already in the DOM). Fork content prints as displayed.

---

## 3. Fork History

### Auto-Commit System

New module: `backend/app/git.py`

- `git_init_if_needed(recipes_dir)` — Called on app startup. If recipes dir exists but isn't a git repo, run `git init`.
- `git_commit(recipes_dir, path, message)` — Run `git add <path> && git commit -m <message>`. Fire-and-forget: failures logged, never raised.
- `git_rm(recipes_dir, path, message)` — Run `git rm <path> && git commit -m <message>`. For deletes.

All git operations use `subprocess.run` with `cwd=recipes_dir`.

### Integration Points

Every file-writing endpoint gets a `git_commit` call after its write:

- `editor.py`: create/update/delete recipe
- `forks.py`: create/update/delete fork
- `cook.py`: cook history add/delete, favorite add/remove
- `planner.py`: save meal plan

Commit messages are descriptive: `"Create recipe: Birria Tacos"`, `"Update fork: vegan (Birria Tacos)"`, etc.

### History Endpoint

`GET /api/recipes/{slug}/forks/{fork_name}/history`

Runs `git log --format` on the fork file. Returns last 20 commits with: hash, date, message. Each entry can include the file content at that revision via `git show <hash>:<path>`.

### Frontend

"History" button on recipe detail page when a fork is selected. Opens expandable timeline panel showing date and commit message per entry. Clicking an entry shows the fork content at that point with changed sections highlighted.

History applies to forks only (not base recipes). Base recipe history can be added later with the same mechanism.

---

## 4. File Changes

### New Backend Files
- `backend/app/git.py` — Auto-commit helper
- `backend/app/routes/planner.py` — Meal plan endpoints
- `backend/tests/test_planner.py` — Meal plan tests
- `backend/tests/test_fork_history.py` — Fork history tests
- `backend/tests/test_git.py` — Git helper tests

### New Frontend Files
- `frontend/src/routes/planner/+page.svelte` — Meal planner page
- `frontend/src/lib/components/RecipePicker.svelte` — Search dropdown

### Modified Backend Files
- `backend/app/main.py` — Register planner router, git init on startup
- `backend/app/routes/editor.py` — Add git_commit calls
- `backend/app/routes/forks.py` — Add git_commit/git_rm calls, add history endpoint
- `backend/app/routes/cook.py` — Add git_commit calls

### Modified Frontend Files
- `frontend/src/routes/recipe/[slug]/+page.svelte` — Print button, fork history panel
- `frontend/src/routes/+layout.svelte` — Planner link in nav
- `frontend/src/lib/api.ts` — New API functions
- `frontend/src/app.css` — @media print rules
