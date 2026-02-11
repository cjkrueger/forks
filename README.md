<p align="center">
  <img src="forks_logo.png" alt="Forks" width="200" />
</p>

<h1 align="center">Forks</h1>

<p align="center">
  <strong>A git-backed recipe manager where your recipes are just markdown files in a repo.</strong>
</p>

<p align="center">
  Scrape any recipe from the web into clean markdown. Fork it to make it your own.<br>
  Share your library by sharing a repo. No database, no lock-in.
</p>

---

## The Problem

Recipe management is broken. Your bookmarks are a graveyard. Recipe apps lock your data in proprietary databases. Every recipe site buries the actual recipe under 14 paragraphs of SEO-optimized life story. And when you modify a recipe -- sub in ancho chiles, cut the sugar in half, double the garlic like a civilized person -- that knowledge lives in your head or on a sticky note, not in the recipe itself.

## The Solution

Forks stores recipes as **plain markdown files** in a **git repository**. That's it. That's the whole architecture.

- **Scrape any recipe** from the web. Forks strips away the noise and saves a clean, human-readable markdown file -- title, ingredients, steps, notes.
- **Fork any recipe** to make it your own. Your modifications are stored as inline forks. The original is always preserved. Toggle between the original, your version, or a diff of what you changed.
- **Share by sharing a repo.** Your recipe library is a git repository. Clone someone's collection and start forking.
- **Cook with it.** A dedicated cook mode with big text, step-by-step navigation, inline timers, and ingredient checkboxes.

## Why Git?

Because git already solved every problem a recipe app has:

| Recipe Concept | Git Concept |
|----------------|-------------|
| Save a recipe | Commit |
| Modify a recipe | Fork |
| Undo a change | Revert |
| Share your collection | Push / Clone |
| Use someone's modification | Merge |
| See what changed | Diff |
| Full history of every edit | Log |

You don't need to know git to use Forks. The app handles everything. But if you do know git, the entire system is transparent -- your recipes are just files, your history is just commits, your forks are just inline edits in markdown.

## Features

### Recipe Management
- **Web scraping** -- Paste a URL from any recipe site to import a clean markdown recipe
- **Rich recipe view** -- Hero images, structured ingredients and instructions, metadata (servings, prep time, cook time, source)
- **Inline editing** -- Full recipe editor with live preview
- **Search** -- Search by title, tag, or ingredient
- **Tags and filtering** -- Filter by tag, sort by never-cooked, least-recent, or quick recipes
- **Favorites** -- Star the recipes you love

### The Fork System
- **Fork any recipe** to create your own version without touching the original
- **Visual diffs** -- See exactly what you changed, highlighted inline (added/removed/modified)
- **Merge forks** -- When your fork is better than the original, merge it back with a note
- **Mark as failed** -- Tried a fork and it didn't work? Mark it as failed with a reason so you don't repeat the experiment
- **Recipe Stream** -- A git-style timeline showing every fork, merge, edit, and failure

### Cooking
- **Cook mode** -- Fullscreen step-by-step view with large text, optimized for kitchen use
- **Inline timers** -- Timers detected automatically from recipe text ("cook for 10 minutes")
- **Ingredient scaling** -- Adjust servings and all quantities update automatically (fractions, unit conversions)
- **Cook history** -- Log when you cooked a recipe and which fork you used

### Meal Planning
- **Weekly planner** -- Drag recipes onto a 7-day grid
- **Fork-aware** -- Plan with a specific fork of a recipe
- **Add all to grocery list** -- One click to add every ingredient from your week's meals

### Grocery List
- **Server-side grocery list** -- Shared across devices, backed by the API
- **Smart ingredient merging** -- "2 cups flour" from two recipes becomes "4 cups flour"
- **Check-off items** -- Mark items as you shop
- **Export** -- Export as plain text for sharing or printing

### Sync and Sharing
- **Git sync** -- Connect to a remote repository (GitHub, GitLab, or any git remote) and sync automatically
- **Configurable sync intervals** -- Set how often to pull and push
- **Conflict-free** -- Each fork is its own file, so multiple people can fork the same recipe without conflicts

## Recipe Format

Recipes are markdown files with YAML frontmatter. They're readable in any text editor, on GitHub, in Obsidian, on your phone.

```markdown
---
title: Italian Penicillin Soup (Pastina Soup)
tags: [italian, mediterranean, soup]
servings: 6 servings
prep_time: 10min
cook_time: 60min
source: https://www.tasteofhome.com/recipes/italian-penicillin-soup-pastina-soup/
image: images/italian-penicillin-soup-pastina-soup.jpg
---

# Italian Penicillin Soup (Pastina Soup)

## Ingredients

- 2 tablespoons olive oil
- 1-1/2 cups chopped onion
- 8 cups reduced-sodium chicken broth
- 3 cups cooked shredded chicken breast
- 1 cup uncooked pastina

## Instructions

1. Heat olive oil in a large soup pot over medium-high heat...
2. Add broth and bay leaf. Bring to a boil...
3. Stir in chicken and pastina; cook until al dente...
```

Forks are stored as separate markdown files alongside the original:

```
recipes/
  chicken-tikka-masala.md                          # base recipe
  chicken-tikka-masala.fork.try-lamb.md             # a fork
  chicken-tikka-masala.fork.jeffs-version.md        # another fork
  images/
    chicken-tikka-masala.jpg
```

## Getting Started

### Docker (recommended)

```bash
git clone https://github.com/cjkrueger/forks.git
cd forks
docker compose up -d
```

Forks will be running at `http://localhost:8420`. Your recipes are stored in `./recipes/`.

### Manual Setup

**Prerequisites:** Python 3.12+, Node.js 20+, git

```bash
git clone https://github.com/cjkrueger/forks.git
cd forks
```

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend** (separate terminal):
```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173` (Vite dev server) with the API at `http://localhost:8000`.

### Configuration

Forks is configured via environment variables (prefixed with `FORKS_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `FORKS_RECIPES_DIR` | `./recipes` | Path to the recipe directory |
| `FORKS_HOST` | `0.0.0.0` | Server bind address |
| `FORKS_PORT` | `8000` | Server port |

## API

Forks exposes a full REST API, making it easy to integrate with AI agents, scripts, or other tools.

### Recipes
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/recipes` | List all recipes (filter by `?tags=`, `?sort=`) |
| `GET` | `/api/recipes/{slug}` | Get recipe with structured ingredients/instructions/notes |
| `POST` | `/api/recipes` | Create a recipe |
| `PUT` | `/api/recipes/{slug}` | Update a recipe |
| `DELETE` | `/api/recipes/{slug}` | Delete a recipe |
| `GET` | `/api/recipes/{slug}/export` | Download raw markdown |
| `GET` | `/api/recipes/{slug}/history` | Git history with content at each version |
| `GET` | `/api/search?q=` | Full-text search |
| `GET` | `/api/tags` | List all tags with counts |
| `POST` | `/api/scrape` | Scrape a recipe from a URL |

### Forks
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/recipes/{slug}/forks/{fork}` | Get fork detail |
| `POST` | `/api/recipes/{slug}/forks` | Create a fork |
| `PUT` | `/api/recipes/{slug}/forks/{fork}` | Update a fork |
| `DELETE` | `/api/recipes/{slug}/forks/{fork}` | Delete a fork |
| `POST` | `/api/recipes/{slug}/forks/{fork}/merge` | Merge fork into base |
| `POST` | `/api/recipes/{slug}/forks/{fork}/fail` | Mark fork as failed |

### Meal Planning
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/meal-plan?week=YYYY-WXX` | Get meal plan for a week |
| `PUT` | `/api/meal-plan` | Save meal plan (bulk) |
| `POST` | `/api/meal-plan/{date}` | Add a meal to a specific day |
| `DELETE` | `/api/meal-plan/{date}` | Clear all meals for a day |
| `DELETE` | `/api/meal-plan/{date}/{index}` | Remove a specific meal |

### Grocery List
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/grocery` | Get full grocery list |
| `POST` | `/api/grocery/recipes` | Add a recipe's ingredients |
| `DELETE` | `/api/grocery/recipes/{slug}` | Remove a recipe's ingredients |
| `POST` | `/api/grocery/check/{key}` | Toggle item checked |
| `DELETE` | `/api/grocery/items/{key}` | Remove a single item |
| `DELETE` | `/api/grocery/checked` | Clear checked items |
| `DELETE` | `/api/grocery` | Clear entire list |
| `GET` | `/api/grocery/export` | Export as plain text |

## Tech Stack

- **Backend:** Python, FastAPI, Pydantic, python-frontmatter, recipe-scrapers
- **Frontend:** SvelteKit, TypeScript
- **Storage:** Markdown files + git
- **Deployment:** Docker

## Why Markdown?

- **Portable.** Move your recipes anywhere. No export needed -- they're already text files.
- **Human-readable.** Open a recipe in any text editor, on GitHub, in Obsidian, on your phone. It reads like a recipe, not a database dump.
- **Future-proof.** Markdown has been around for 20 years. Your great-grandkids can read these files.
- **Hackable.** Want to build your own frontend? Parse the files. Want to search with grep? Go for it. The data is yours.

## The Name

**Forks.** As in forking a recipe to make it your own. As in forking a repo to build on someone else's work. As in: you eat with them.

---

*"Your recipes are just files. Your kitchen is a repo. Fork everything."*
