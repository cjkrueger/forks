# Phase 4: Cook Mode — Design Document

**Goal:** Transform the recipe detail page into a kitchen-optimized cooking experience with step-by-step navigation, ingredient checkboxes, inline timers, screen wake lock, cook history tracking, and recipe favorites.

**Deliverable:** Prop your phone up in the kitchen and actually cook from it.

---

## Entry & Exit

Cook mode is triggered by a "Start Cooking" button on the recipe detail page. It transforms the current page in-place — no new route, no modal. The recipe and fork data are already loaded, so cook mode re-renders the same content in a kitchen-optimized layout.

**On entry:**
- Wake Lock API is requested to prevent screen sleep
- Recipe content is parsed into structured data: ingredients list, numbered instruction steps, notes
- URL gets a `?cook` query param appended (refresh stays in cook mode)
- All page chrome (nav bar, version selector, tags, edit buttons) is hidden — replaced by a minimal top bar with recipe title and "Exit" button
- A `POST /api/recipes/{slug}/cook-history` call records today's date and the current fork (if any)

**On exit:**
- Wake lock is released
- `?cook` param is removed
- Normal recipe view is restored
- Running timers continue (managed independently of cook mode toggle)

Cook mode respects the current fork selection — if viewing "CJ's Vegan Version", cook mode shows that merged content.

---

## Layout — Two-Panel Design

### Desktop/Tablet (landscape)
Side-by-side. Ingredients panel on the left (~35% width), current instruction step on the right (~65% width). Both panels are independently scrollable.

### Mobile/Portrait
Stacked. The current instruction step takes the full screen. Ingredients are accessible via a pull-up drawer from the bottom — a small tab reads "Ingredients (3/12 checked)" that can be dragged up to reveal the full list, then dragged down to dismiss.

### Ingredients Panel
- Each ingredient rendered as a tappable row with a checkbox
- Checked items get a strikethrough + dimmed opacity (not hidden)
- Checkbox state is local only (not persisted)
- List scrolls independently from the step panel

### Instruction Step Panel
- One step at a time in large text (~1.4rem desktop, ~1.2rem mobile)
- Step number displayed prominently ("Step 3 of 8")
- Previous/Next buttons at the bottom, large enough for wet hands (~48px min touch target)
- Swipe left/right navigates steps on touch devices
- Time references rendered as tappable timer chips
- After the last step, a "Notes" card appears (if the recipe has notes)

### Top Bar
Recipe title (truncated if long), step progress indicator, "Exit" button on the right.

---

## Inline Timers

### Detection
A utility function `parseTimers(stepText)` scans for time patterns using regex:
- Simple: `20 minutes`, `1 hour`, `30 seconds`, `5 min`, `2 hrs`, `45 sec`
- Ranges: `15-20 minutes` (uses higher value)
- Combined: `1 hour and 30 minutes`, `1 hr 15 min` (summed)
- Fractional: `1.5 hours`, `1/2 hour`

### Rendering
Detected times are wrapped in styled chips (pill-shaped, accent-colored border) inline with the step text. Each chip shows the duration with a small play icon.

### Starting a Timer
Tap the chip to start. The chip changes to show a live countdown. Simultaneously, a compact timer entry appears in the floating timer bar.

### Timer Bar
Persistent at the bottom of the screen, above the step navigation buttons. Shows all active timers as compact pills with labels and countdowns. Labels are auto-generated from context (e.g. "Step 3 — simmer").

### Timer Completion
When a timer reaches zero:
- The pill flashes/pulses with an alert color
- Browser audio alert plays (short chime)
- Browser notification fires (if permission granted)
- Timer stays visible in "done" state until dismissed with a tap

### Limits
Max 5 concurrent timers. Starting a 6th auto-dismisses the oldest completed timer. If all 5 are running, a brief toast says "Too many timers."

### Timer Match Output
```typescript
interface TimerMatch {
  startIndex: number;
  endIndex: number;
  originalText: string; // "20 minutes"
  totalSeconds: number; // 1200
  label: string;        // "20 min"
}
```

---

## Wake Lock & Browser APIs

### Wake Lock
Request `navigator.wakeLock.request('screen')` on entering cook mode. If the API isn't available (older browsers), cook mode works fine without it — degrades silently. Re-acquire on `visibilitychange` when the tab becomes visible again (browsers auto-release wake lock on tab switch). Release explicitly on exit.

### Notifications
Request `Notification.permission` on first timer start. If denied, timers rely on in-page audio and visual flash. Ask once, respect the answer.

### Audio
A single chime file (`/static/sounds/timer-chime.mp3`). On first timer start, create an `AudioContext` and decode the buffer (satisfies user-gesture requirement). Play on timer completion. Fail silently if blocked.

### No Service Worker
Timers run in-page via `setInterval`. Closing the tab kills timers. The wake lock keeps the screen on, so the tab stays active during normal cooking. Background timers via service worker is a future nice-to-have.

---

## Data Flow & State

### No Backend Changes for Core Cook Mode
Cook mode state lives entirely in the frontend. The recipe/fork data is already loaded before cook mode is entered.

### Parsing
On entering cook mode, `displayContent` markdown is parsed via the existing `parseSections()` utility:
- Ingredients: from `## Ingredients`, split into items (strip `- ` prefix)
- Steps: from `## Instructions`, split into steps (strip `1. ` prefix)
- Notes: from `## Notes`, displayed as collapsible section after the last step

### Component State
- `cookMode: boolean` — active state (component-level)
- `currentStep: number` — index of current instruction step
- `checkedIngredients: Set<number>` — indices of checked ingredients
- `activeTimers: Timer[]` — `{ id, label, durationMs, remainingMs, startedAt, status }`

All state is ephemeral — nothing persists across cook mode sessions. Each cooking session starts fresh.

### Timer Ticks
A single `setInterval(1000)` drives all active timers. Created when the first timer starts, cleared when the last finishes or cook mode exits.

---

## Cook History

### Storage
Stored in the base recipe's YAML frontmatter as a list of objects:

```yaml
cook_history:
  - date: 2026-02-09
    fork: vegan
  - date: 2026-01-25
```

The `fork` field is optional — omitted when cooking the original. Cook history lives on the base recipe only, even when a fork was used. This keeps fork files focused on recipe modifications.

### API
- `POST /api/recipes/{slug}/cook-history` — Body: `{ "fork": "vegan" }` (fork optional). Appends entry. Deduplicates same date + fork.
- `DELETE /api/recipes/{slug}/cook-history/{index}` — Removes entry at index. Returns updated list.

### Display
On the recipe detail page, below the meta info: "Last cooked Feb 9, 2026 (Vegan)". Tapping expands to show the full history list with X buttons to delete individual entries. Sorted newest-first.

### Model Changes
- `CookHistoryEntry`: `{ date: str, fork: Optional[str] }`
- `RecipeSummary` gains `cook_history: List[CookHistoryEntry] = []`
- Parser extracts `cook_history` from frontmatter during indexing

---

## Favorites

### Storage
Uses the existing tag system. Favoriting a recipe adds `"favorite"` to the `tags` list in frontmatter. Unfavoriting removes it.

### API
- `POST /api/recipes/{slug}/favorite` — Adds `"favorite"` tag. Returns `{ "favorited": true }`.
- `DELETE /api/recipes/{slug}/favorite` — Removes `"favorite"` tag. Returns `{ "favorited": false }`.

Both rewrite the recipe's markdown file via `python-frontmatter`.

### Display
- Recipe detail page: heart icon toggle button next to the title. Filled when favorited.
- Recipe card (home page): small filled heart icon on favorited recipes.
- Filtering: `/?tags=favorite` already works with the existing tag filter system.

---

## Frontend Components

### New Components
- **CookMode.svelte** — Main cook mode view. Receives parsed ingredients, steps, notes. Manages internal state (current step, checkboxes, timers). The biggest new component.
- **TimerBar.svelte** — Floating bar at bottom showing active timers as compact pills with countdowns. Handles alarm audio and notification dispatch.
- **TimerChip.svelte** — Inline tappable chip within step text. Shows detected duration with play icon. Dispatches `start-timer` event on tap.
- **CookHistory.svelte** — Shows "Last cooked X" on recipe detail page with expandable history and delete buttons.
- **FavoriteButton.svelte** — Heart icon toggle. Checks tags for `"favorite"`, calls API on click with optimistic update.

### Modified Files
- `recipe/[slug]/+page.svelte` — Start Cooking button, conditional CookMode render, CookHistory, FavoriteButton
- `RecipeCard.svelte` — Small heart icon on favorited recipes
- `types.ts` — `CookHistoryEntry` interface, `cook_history` on `RecipeSummary`
- `api.ts` — `addCookHistory`, `deleteCookHistory`, `addFavorite`, `removeFavorite`

### New Utilities
- `$lib/timers.ts` — `parseTimers(text)` function, `TimerMatch` interface

---

## Mobile Polish

- All interactive elements: 48px minimum touch target
- Prev/next step buttons: full-width bars at bottom of step panel
- Ingredient checkboxes: generous padding
- Timer bar pills: at least 44px tall
- Swipe navigation: 50px threshold, disabled on ingredients panel to allow scrolling
- Swipe animation: subtle 150ms CSS slide transition
- Ingredients drawer (mobile): bottom sheet, collapsed tab showing "Ingredients (3/12)", drag up to expand, tap backdrop to collapse
