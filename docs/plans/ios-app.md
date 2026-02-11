# Forks for iOS — High-Level Plan

## Vision

A native iOS companion app for your self-hosted Forks instance. The phone is where you actually cook — standing in the kitchen with messy hands, shopping at the grocery store, or saving a recipe link from social media. The iOS app should excel at these real-world moments rather than replicate the full web UI.

---

## Architecture

### Connectivity Model

Forks is self-hosted, not a cloud SaaS. The iOS app connects to the user's own Forks server.

- **Server discovery**: User enters their Forks URL once (e.g., `http://192.168.1.50:8420` or a domain like `forks.myhouse.local`)
- **Local network**: Works over LAN when home; optionally via Tailscale/Wireguard/Cloudflare Tunnel when away
- **No account system needed**: Single-user, same as the web app. No auth for v1 (matches current backend). Future: optional API key or token header.

### Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| UI | SwiftUI | Declarative, modern, less boilerplate. Forks has no legacy iOS code. |
| Navigation | NavigationStack | iOS 16+ path-based navigation |
| Networking | Swift concurrency + URLSession | No need for Alamofire — the API is simple REST |
| Local cache | SwiftData | Lightweight on-device persistence for offline recipe access |
| Min target | iOS 17 | Gives us SwiftData, interactive widgets, StandBy mode, Live Activities |

### Data Flow

```
Forks Server (FastAPI)
    ↕  REST JSON (existing API, no changes needed)
iOS App
    ↕  SwiftData (local cache)
On-screen UI
```

The existing backend API is already well-structured for a mobile client — every feature the web app uses goes through `/api/*` endpoints that return clean JSON. No backend changes are needed for v1.

---

## Phased Rollout

### Phase 1 — Cook & Browse (MVP)

The features you reach for your phone to do.

| Feature | Notes |
|---------|-------|
| **Server setup** | Enter URL, validate connection, persist in app settings |
| **Recipe list** | Grid of recipe cards with images, search, tag filtering |
| **Recipe detail** | Full recipe view with ingredients, instructions, notes, metadata |
| **Cook mode** | Full-screen step-by-step, ingredient checklist, swipe navigation |
| **Timers** | Auto-parsed from instructions, multiple simultaneous, Live Activity on lock screen |
| **Serving scaler** | Adjust servings, scaled ingredients reflected in cook mode |
| **Offline cache** | Recipes cached in SwiftData for cooking without network (read-only) |
| **Favorites** | Toggle favorite, filter by favorites |

### Phase 2 — Capture & Shop

| Feature | Notes |
|---------|-------|
| **Share Sheet import** | Share a recipe URL from Safari/Instagram/TikTok → Forks scrapes and saves it |
| **Grocery list** | View, check off, clear items. Add recipes with serving count. |
| **Meal planner** | Weekly view, add/remove recipes from slots |
| **Cook history** | Log a cook, view past cooks |
| **Search** | Full-text search with recent/suggested queries |

### Phase 3 — Edit & Fork

| Feature | Notes |
|---------|-------|
| **Edit recipe** | Modify ingredients, instructions, notes, metadata |
| **Create fork** | Fork a recipe with a name and modifications |
| **Fork selector** | Switch between original and fork versions |
| **Merge/fail forks** | With required notes, matching web UI behavior |
| **Add recipe manually** | Full recipe creation form |
| **Image capture** | Take photo of finished dish → upload as recipe image |

### Phase 4 — Delight

| Feature | Notes |
|---------|-------|
| **Widgets** | "What's for dinner?" widget showing today's meal plan slot |
| **Siri Shortcuts** | "Start cooking [recipe name]" → opens cook mode |
| **StandBy mode** | Timer display optimized for iPhone on its side while charging |
| **Apple Watch** | Timer companion — see active cook timers on wrist |
| **Spotlight indexing** | Recipes searchable from iOS home screen |
| **Haptics** | Subtle feedback on timer completion, step transitions, checklist taps |
| **iPad layout** | Multi-column layout for iPad — sidebar + recipe detail |

---

## Key Design Decisions

### 1. Offline-first for cooking

Once a recipe is opened, it should be fully usable without network. Cache recipe content + images in SwiftData. Sync is opportunistic — pull latest when online, but never block the UI waiting for network.

Mutations (favorite, log cook, edit) queue locally and sync when connection is available.

### 2. Cook mode is the hero

This is the reason the app exists. Design priorities:
- Large, high-contrast text readable at arm's length
- Tap anywhere to advance step (no tiny buttons with flour-covered hands)
- Voice control via Siri for hands-free step navigation
- Screen stays on (UIApplication.shared.isIdleTimerDisabled)
- Timers survive app backgrounding via Live Activities

### 3. Don't rebuild the web app

The web UI is better for deep tasks like editing complex recipes, managing forks, viewing the stream graph, and configuring settings. The iOS app should link out to the web UI for these rather than poorly recreating them. A simple "Open in browser" action covers edge cases.

### 4. Share Sheet is the import mechanism

Nobody wants to copy-paste URLs on their phone. The iOS Share Sheet is how recipes get captured:

1. User finds recipe on Instagram / TikTok / food blog
2. Taps Share → "Save to Forks"
3. App calls the existing `/api/scrape` endpoint
4. Quick confirmation screen → saved

This is a Share Extension, which runs in a separate process with minimal UI.

---

## Data Model (SwiftData)

```swift
@Model class CachedRecipe {
    @Attribute(.unique) var slug: String
    var title: String
    var tags: [String]
    var servings: String?
    var prepTime: String?
    var cookTime: String?
    var author: String?
    var source: String?
    var imageURL: String?
    var cachedImageData: Data?
    var content: String
    var forks: [CachedFork]
    var isFavorite: Bool
    var likes: Int
    var lastSynced: Date
}

@Model class CachedFork {
    @Attribute(.unique) var id: String  // "{slug}/{fork_name}"
    var name: String
    var forkName: String
    var author: String?
    var content: String
    var mergedAt: String?
    var failedAt: String?
    var failedReason: String?
}
```

### Sync Strategy

- **On app launch**: Pull full recipe list (lightweight — just summaries)
- **On recipe open**: Pull full recipe detail if stale (>5 min since last sync)
- **Background refresh**: iOS Background App Refresh pulls recipe list periodically
- **Mutations**: POST immediately if online, queue in SwiftData if offline, retry on reconnect

---

## Project Structure

```
ForksApp/
├── ForksApp.swift              # App entry point, server URL config
├── Models/
│   ├── Recipe.swift            # API response models (Codable)
│   ├── CachedRecipe.swift      # SwiftData models
│   └── GroceryItem.swift
├── Services/
│   ├── ForksAPI.swift          # REST client wrapping all /api/* calls
│   ├── SyncEngine.swift        # Cache invalidation, background refresh
│   └── TimerManager.swift      # Manages multiple cook timers + Live Activities
├── Views/
│   ├── Setup/
│   │   └── ServerSetupView.swift
│   ├── RecipeList/
│   │   ├── RecipeListView.swift
│   │   ├── RecipeCardView.swift
│   │   └── TagFilterView.swift
│   ├── RecipeDetail/
│   │   ├── RecipeDetailView.swift
│   │   ├── IngredientListView.swift
│   │   └── ForkSelectorView.swift
│   ├── CookMode/
│   │   ├── CookModeView.swift
│   │   ├── StepView.swift
│   │   ├── IngredientChecklistView.swift
│   │   └── TimerBarView.swift
│   ├── Grocery/
│   │   └── GroceryListView.swift
│   └── Planner/
│       └── MealPlannerView.swift
├── Widgets/
│   └── MealPlanWidget.swift
├── ShareExtension/
│   └── ShareViewController.swift   # Share Sheet → scrape → save
└── LiveActivity/
    └── CookTimerActivity.swift     # Lock screen timer display
```

---

## What's NOT Needed on iOS

These features live on the web only:

- **Stream graph visualization** — Complex SVG rendering, better on desktop
- **Settings / sync configuration** — One-time setup, do it on the web
- **Recipe history diffs** — Detailed content diffs are a desktop task
- **Export to markdown** — File management is awkward on iOS
- **Git remote configuration** — Definitely a web/desktop task

---

## Open Questions

1. **Auth**: If the server is exposed to the internet (via Cloudflare Tunnel, etc.), should the app support basic auth or API keys? Could add a simple `Authorization: Bearer <token>` header.

2. **Multiple servers**: Should the app support connecting to more than one Forks instance? (Probably not for v1 — keep it simple.)

3. **Push notifications**: Could the server notify the app when a recipe is updated by another device? Requires infrastructure (APNs). Probably overkill for personal use — polling is fine.

4. **TestFlight distribution**: For personal use, can distribute via Xcode directly to your own device without an App Store listing. If sharing with others, TestFlight (requires Apple Developer Program, $99/yr).
