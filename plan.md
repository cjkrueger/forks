
# Forks

*A plaintext markdown recipe manager.*

## Vision

Self-hosted web app that stores recipes as plain markdown files. No database, no lock-in, just files you can move anywhere. The app scrapes recipes from the web into clean markdown, then renders them beautifully in the browser.

**Core philosophy:** Markdown is the source of truth. The browser is the pretty layer. But the markdown itself should be beautiful too — if you open a recipe in a text editor or on GitHub, it should read like a well-formatted document, not a data dump. Human-readable first, machine-parseable second.

## Architecture

- **Runtime:** Docker container on Unraid
- **Storage:** A mounted folder of `.md` files — that's the whole "database"
- **Frontend:** Web UI for browsing, searching, tagging, and reading recipes
- **Scraper:** Paste a URL → extracts recipe (ingredients, steps, notes, source) → saves as markdown
- **Hecate skill:** I can scrape and add recipes on command ("save this recipe", URL in chat)

## Markdown Recipe Format

```markdown
---
title: Birria Tacos
source: https://example.com/birria-tacos
tags: [mexican, beef, tacos, weekend]
servings: 6
prep_time: 30min
cook_time: 3hr
date_added: 2026-02-09
---

# Birria Tacos

## Ingredients

- 3 lbs chuck roast
- 4 dried guajillo chiles
- ...

## Instructions

1. Toast the chiles in a dry skillet...
2. ...

## Notes

- Holly likes extra consomé for dipping
- Works great in the Dutch oven
```

## Forking System

The core differentiator. Users can "fork" any recipe — preserving the original while layering their own modifications on top.

### How It Works in Markdown

Forks are inline blockquotes with a user namespace:

```markdown
## Ingredients

- 3 lbs chuck roast
- 4 dried guajillo chiles
- > **@cj:** 2 guajillo + 2 ancho, better depth
- > **@holly:** skip chiles entirely, use chipotle in adobo
- 1 can crushed tomatoes
```

- Each fork is tied to a username (`@cj`, `@holly`, etc.)
- Forks can modify ingredients, steps, notes — anything
- The file stays readable as plain markdown even without the app

### How It Works in the GUI

**Toggle view** (top of recipe):
- **Original** — the recipe as scraped, no forks applied
- **My Version** — your forks applied, replaces original lines seamlessly
- **Diff** — inline callout boxes showing what changed and who changed it

When cooking, you see YOUR version by default — clean, no clutter. But you can peek at other people's forks ("oh holly swaps the chiles here, let me try hers tonight").

### Multi-User Support

- Each user has a profile/username
- Forks are namespaced per user in the markdown
- Git-friendly by design — you can `git clone` someone's recipe library and start forking
- Household members can browse each other's forks
- Users can "adopt" someone else's fork as their own starting point

## Features

### MVP
- [ ] Recipe scraper (URL → markdown) with structured data extraction (JSON-LD, microdata)
- [ ] File-based storage (mounted volume of .md files)
- [ ] Web UI: browse, read, search
- [ ] Tag system (frontmatter tags rendered as filterable UI)
- [ ] Mobile-friendly recipe view (big text, easy scroll while cooking)
- [ ] Fork system — create, view, and toggle between forks per user
- [ ] Multi-user accounts (at least username-level)

### Nice to Have
- [ ] Grocery list generation from selected recipes (respects your forks)
- [ ] Meal planning (weekly view, drag recipes onto days)
- [ ] Scaling (adjust servings, recalculate ingredients)
- [ ] Import from Mealie / other formats
- [ ] Print-friendly view
- [ ] Photo support (save images alongside .md files)
- [ ] Full-text search across all recipes
- [ ] "Cook mode" — step-by-step with big text, screen stays on
- [ ] Fork adoption — use someone else's fork as your starting point
- [ ] Fork history — git-style diff of how your version evolved

### Hecate Integration
- [ ] Skill: "save this recipe" + URL → scrape → add to folder
- [ ] Skill: "what should we make this week?" → suggest based on tags, history
- [ ] Skill: "add to grocery list" → pull ingredients from selected recipes
- [ ] Integration with meal planning if built

## Input Methods

### URL Scraping (primary)
- Use `recipe-scrapers` Python library (actively maintained, 400+ site-specific drivers)
- JSON-LD / schema.org structured data as primary extraction method
- Bright Data as fallback for bot-protected sites
- Output: structured data → markdown template

### Manual Entry
- Form-based entry in the app (outputs markdown)
- Or just a markdown editor with the frontmatter template pre-filled
- Keep it simple — power users can edit the .md files directly

### Photo Import (future)
- OCR + AI parsing: snap a photo of grandma's index card or a cookbook page
- Extract text, structure into markdown format
- Killer feature for people with physical recipe collections

## Cook Mode

When you're at the stove, the app should get out of your way:
- Big text, high contrast
- Screen stays awake
- Step-by-step navigation (next/prev)
- Inline timers ("simmer 20 min" → tap to start countdown)
- Ingredient checkboxes (track what you've added)
- Respects your fork — shows YOUR version, not the original
- Voice control? (future — "next step", "start timer")

## Discovery & Browsing

Beyond basic tag filtering:
- Ingredient search ("what can I make with chicken thighs and rice?")
- Time/difficulty filters (weeknight quick vs weekend project)
- "Surprise me" — random pick from the library
- "We haven't made this in a while" — surface neglected recipes
- Seasonal suggestions

## Tech Stack

Leaning toward:
- **Backend:** Python (FastAPI) — best scraping ecosystem, `recipe-scrapers` library solves URL extraction
- **Scraper:** `recipe-scrapers` (hhursev) — 400+ site drivers, JSON-LD/Microdata/RDFa, `.to_json()` output
- **Frontend:** TBD — something lightweight and modern. Could be React, Svelte, or even plain JS
- **Search:** Client-side full-text search over frontmatter + content (lunr.js / fuse.js)
- **Storage:** Mounted volume of .md files. Git-friendly — every recipe edit is a commit, history comes free
- **Auth:** Lightweight user system (config file or simple DB) — enough to namespace forks

## Build Phases

### Phase 1: "I can read recipes"
*The foundation. Get the core loop working.*

- [ ] FastAPI backend with markdown parser (read .md files, parse frontmatter + body)
- [ ] File watcher on the recipes folder (detect new/changed/deleted files)
- [ ] Web UI: list all recipes, click to view one, rendered beautifully
- [ ] Tag filtering sidebar
- [ ] Mobile-responsive layout
- [ ] Dockerfile + docker-compose for Unraid deployment

**Deliverable:** Drop .md recipe files in a folder and browse them in a nice web UI.

---

### Phase 2: "I can save recipes"
*Now it creates content, not just reads it.*

- [ ] URL scraper integration (`recipe-scrapers` library)
- [ ] Paste a URL in the app → scrapes → generates .md → saves to folder
- [ ] Manual entry form (markdown editor with frontmatter template pre-filled)
- [ ] Basic full-text search (title, ingredients, tags)
- [ ] Edit existing recipes in the app

**Deliverable:** Paste a URL, get a recipe. Or write one from scratch.

---

### Phase 3: "I can make it mine"
*The fork system — the soul of the app.*

- [ ] User accounts (lightweight — username/password)
- [ ] Fork creation UI (select an ingredient or step → add your modification)
- [ ] Toggle view: Original / My Version / Diff
- [ ] Fork storage in the markdown (inline blockquotes with @username)
- [ ] Browse other users' forks of the same recipe
- [ ] Fork adoption (use someone else's fork as your starting point)

**Deliverable:** Multiple people can fork the same recipe, see each other's changes.

---

### Phase 4: "I can cook with it"
*The kitchen experience.*

- [ ] Cook mode: step-by-step view, big text, high contrast
- [ ] Screen stay-awake (Wake Lock API)
- [ ] Inline timers (parse time references in steps → tap to start countdown)
- [ ] Ingredient checkboxes (track what you've added)
- [ ] Shows your forked version by default in cook mode

**Deliverable:** Prop your phone up in the kitchen and actually cook from it.

---

### Phase 5: "It knows me"
*Intelligence layer.*

- [ ] Hecate skill: "save this recipe" + URL → scrape → add to folder
- [ ] Hecate skill: "what should we make this week?" → suggest based on tags, history
- [ ] Discovery features: ingredient search, "surprise me", "haven't made in a while"
- [ ] Grocery list generation from selected recipes (respects your forks)
- [ ] Serving scaling (adjust servings → recalculate ingredient amounts)

**Deliverable:** Smart recipe suggestions and shopping lists.

---

### Phase 6: "It plans for me"
*The full meal planning loop.*

- [ ] Weekly meal planner (drag recipes onto days)
- [ ] Photo import (OCR + AI → structured markdown)
- [ ] Import from Mealie / other formats
- [ ] Print-friendly view
- [ ] Fork history (git-style diff of how your version evolved)
- [ ] Voice control in cook mode ("next step", "start timer")

**Deliverable:** Full household meal planning system.

---

## Why Not Mealie?

Mealie is great but:
- Database-backed (PostgreSQL/SQLite) — data isn't portable plaintext
- Heavier than needed for the use case
- CJ's instance isn't even loading right now lol
- Markdown files sync anywhere via Syncthing, work offline, can be edited in any text editor

## Name

"Forks" — as in forking a recipe to make it your own. Also: you eat with them.

---

*Started Feb 9, 2026*
