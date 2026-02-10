# Phase 7: Git Sync, Fork Merging & Stream Visualization — Design Document

**Goal:** Add remote git sync for collaborative recipe sharing across households, fork merging back into base recipes, and a visual stream/timeline showing a recipe's lineage.

**Architecture:** A sync engine wraps git push/pull on top of the existing auto-commit system. Conflict resolution creates forks automatically — no manual merge dialogs. GitHub OAuth provides smooth setup; manual token config supports other providers. A stream visualization built from git history and fork metadata shows each recipe's life story. All remote features are opt-in — the app works fully offline with local storage.

---

## 1. Remote Sync Engine

### Core Concept

The backend gains a sync module that manages a git remote. It sits on top of the existing auto-commit system — every local commit (recipe created, edited, forked, cook logged) gets pushed to the remote automatically. Remote changes get pulled in on a schedule.

### Sync Timing

- **On startup:** pull from remote to get latest changes
- **After every commit:** push to remote immediately
- **Periodic poll:** check for remote changes every 90 seconds, pull if any
- **Manual trigger:** sync button in the UI for immediate sync

### What Gets Synced

Everything in the `/recipes` directory — recipe files, fork files, meal plans, images. The entire folder is the repo. Instance-specific config (auth tokens, sync settings) is stored outside the recipes directory and never synced.

### Backend Module: `sync.py`

- `push()` — Push local commits to remote. Log failures, surface to UI via status endpoint.
- `pull()` — Fetch and merge remote changes. On conflict, delegate to `resolve_conflicts()`.
- `resolve_conflicts()` — Auto-create fork files from conflicting incoming changes (see Section 2).
- `get_status()` — Return sync state: last sync time, ahead/behind counts, connection status.
- `start_background_sync(interval)` — Async loop that polls remote on the configured interval.

### API Endpoints

- `GET /api/sync/status` — Returns sync state (last synced, ahead/behind, connected/error)
- `POST /api/sync/trigger` — Manual sync, returns result

### Integration with File Watcher

After a pull writes new/changed files to disk, the existing file watcher picks them up and re-indexes automatically. No special handling needed.

---

## 2. Conflict Resolution & Fork Merging

### Conflict Resolution via Auto-Fork

When a pull encounters a merge conflict (two instances edited the same recipe), the system resolves it without user intervention:

1. Keep the local version as-is (ours wins the git merge)
2. Extract the incoming remote version of the conflicted file
3. Auto-create a fork: `recipe-slug.fork.conflict-2026-02-10.md`
4. Show a toast: "Pasta Carbonara was edited elsewhere — saved as a fork"
5. The user now has both versions visible through the existing fork UI
6. They can compare, keep both, or merge one into the other

Zero conflict dialogs, ever. The fork system absorbs the complexity.

### Merging Forks Back Into Base

New action on the fork detail view — "Merge into original" button, alongside the existing "Make primary" option.

**Merge flow:**

1. User clicks "Merge into original" on a fork
2. UI shows a preview: which sections (ingredients, instructions, notes) will change in the base recipe
3. User confirms
4. Backend runs a section-level merge using the existing `sections.py` diff/merge engine
5. Base recipe is updated with the fork's changed sections
6. Fork file gets a new frontmatter field: `merged_at: 2026-02-10`
7. Git commit: `"Merge fork 'Mom's smoky version' into pasta-carbonara"`
8. Fork remains in the list with a visual "merged" badge

**Post-merge fork behavior:**

- Fork stays in the fork list, marked with a "Merged" badge (muted visual treatment)
- Merged forks sort below active forks
- Still fully viewable and clickable — part of the recipe's history
- If the fork is edited again after merging, `merged_at` is removed and it becomes an active fork again

### New Frontmatter Fields

| Field | File type | Purpose |
|---|---|---|
| `forked_at_commit` | Fork files | Git hash of the base recipe at the time the fork was created. Powers stream visualization placement. |
| `merged_at` | Fork files | ISO date when the fork was merged into base. Removed if fork diverges again after merge. |

---

## 3. Stream Visualization

### Concept

A vertical timeline graph on the recipe detail page showing the recipe's full lineage — when it was created, when forks branched off, when they merged back in. A simplified git graph designed for recipe context.

### Visual Design

Vertical graph, top-to-bottom, oldest to newest. Main line represents the base recipe. Branches fork off to the right at the point where a fork was created. Merge arrows curve back into the main line.

```
  o  Created                     Feb 1
  |
  o  Edited                      Feb 3
  |--o Mom's smoky version       Feb 5
  |  |
  o  |  Added notes              Feb 6
  |  |
  o--+  Merged Mom's smoky       Feb 8
  |
  |--o Dad's extra garlic        Feb 10
  |  |
  o  |  Now
```

### Node Types

- **Circle** — Base recipe edit (content change)
- **Fork icon** — Fork branch point
- **Merge icon** — Fork merged back into base

### Data Source

Built from two sources the backend already has:

1. `git log` on the base recipe file — provides the main line events
2. Fork metadata (`forked_at_commit`, `merged_at`, `date_added`) — provides branch and merge points

### API Endpoint

`GET /api/recipes/{slug}/stream` — Assembles and returns the timeline as a list of `StreamEvent` objects:

```json
[
  {"type": "created", "date": "2026-02-01", "message": "Created"},
  {"type": "edited", "date": "2026-02-03", "message": "Updated ingredients", "commit": "abc123"},
  {"type": "forked", "date": "2026-02-05", "fork_name": "Mom's smoky version", "fork_slug": "moms-smoky-version"},
  {"type": "merged", "date": "2026-02-08", "fork_name": "Mom's smoky version", "commit": "def456"},
  {"type": "forked", "date": "2026-02-10", "fork_name": "Dad's extra garlic", "fork_slug": "dads-extra-garlic"}
]
```

### Filtering

Only significant content changes are shown. Commits that only touch frontmatter (cook history logged, favorite toggled) are filtered out to avoid noise.

### Interactions

- Clicking a node on the main line shows a human-readable summary of what changed at that point
- Clicking a fork branch navigates to the fork view
- Merge nodes show which sections were incorporated

### Placement

Accessible via a "History" section on the recipe detail page. Only rendered when there's meaningful history (more than just the initial creation). No empty-state graph for brand-new recipes.

---

## 4. GitHub OAuth & Settings

### Settings Page

New route: `/settings`. First configuration UI in the app. Minimal, focused entirely on remote sync.

### GitHub Connection Flow

1. User clicks "Connect to GitHub"
2. OAuth flow via a GitHub App (scoped to specific repos, cleaner than personal OAuth apps)
3. After auth, user picks an existing repo or creates a new one
4. Backend stores token and repo URL in instance-local config
5. First sync kicks off immediately

### Non-GitHub Flow

Secondary option: "Use another provider." Form with repo URL + personal access token. Works with GitLab, Gitea, Tangled, or any git remote supporting HTTPS auth.

### Instance Config

Stored outside the recipes directory — credentials must never end up in the synced repo. Location: configurable, defaults to a `.forks-config.json` adjacent to the recipes dir, or overridden via `FORKS_CONFIG_PATH` env var.

```json
{
  "remote": {
    "provider": "github",
    "url": "https://github.com/user/family-recipes.git",
    "token": "ghu_xxxx"
  },
  "sync": {
    "enabled": true,
    "interval_seconds": 90
  }
}
```

### Settings UI

- Connection status and linked repo
- Last synced timestamp, ahead/behind counts
- Manual sync button
- Disconnect option
- For GitHub: direct link to view the repo on GitHub

---

## 5. Frontend Changes

### New Route: `/settings`

Remote connection UI. GitHub OAuth button with the "Connect to GitHub" flow. Manual config form as a secondary option. Sync status display.

### Topbar: Sync Indicator

Small icon added to the topbar. Three states:

- **Connected & synced** — Subtle cloud-check icon, not attention-grabbing
- **Syncing** — Gentle animation (pulse or spin) on the same icon
- **Error/disconnected** — Warning color, clickable to navigate to settings

No indicator rendered when no remote is configured. The feature is invisible until opted into.

### Recipe Detail: Stream Visualization

"History" section on the recipe detail page. Renders the vertical stream graph. Only appears when meaningful history exists.

### New Component: `StreamGraph.svelte`

Renders the timeline from the `/api/recipes/{slug}/stream` response. SVG lines for the stream paths, HTML elements for nodes. No charting library — hand-drawn SVG paths and positioned elements.

### Fork View: Merge Action

"Merge into original" button on the fork detail view. Shows a section-level preview of changes before confirming. After merge: toast confirmation, fork gains "Merged" badge.

### Fork List: Merged State

Merged forks display a muted "Merged" badge. Sort below active forks. Still fully viewable and clickable.

---

## 6. Experience Tiers

The app supports three tiers of usage, all from the same codebase:

| Tier | Setup | Experience |
|---|---|---|
| **Local only** | No config needed | Full app with fork merging, stream history, all existing features. No git concepts exposed. |
| **Remote sync** | Connect via settings | Everything above + automatic background sync, conflict resolution via auto-fork, shared recipes across instances. |
| **GitHub enhanced** | GitHub OAuth | Everything above + smooth OAuth setup, link to repo, future platform-specific features. |

No feature gates or upgrade prompts. Local-only users see the complete app. Remote sync adds a topbar icon and settings page. That's it.

---

## 7. File Changes

### New Backend Files

- `backend/app/sync.py` — Sync engine (push, pull, conflict resolution, background polling)
- `backend/app/remote_config.py` — Instance config read/write, credential management
- `backend/app/oauth.py` — GitHub OAuth token exchange, repo listing/creation
- `backend/app/routes/settings.py` — Settings and sync API endpoints
- `backend/app/routes/stream.py` — Recipe stream/timeline endpoint
- `backend/tests/test_sync.py` — Sync engine tests
- `backend/tests/test_stream.py` — Stream timeline tests
- `backend/tests/test_settings.py` — Settings endpoint tests

### New Frontend Files

- `frontend/src/routes/settings/+page.svelte` — Settings page
- `frontend/src/lib/components/StreamGraph.svelte` — Timeline visualization
- `frontend/src/lib/sync.ts` — Sync status store and polling

### Modified Backend Files

- `backend/app/git.py` — Add remote operations: `git_remote_add()`, `git_push()`, `git_pull()`, `git_merge()`, `git_diff_commits()`. Sync errors surfaced (not fire-and-forget).
- `backend/app/models.py` — New models: `SyncStatus`, `StreamEvent`, `StreamTimeline`, `RemoteConfig`. Add `merged_at` and `forked_at_commit` to fork models.
- `backend/app/main.py` — Start background sync on startup, register new routers.
- `backend/app/routes/forks.py` — Record `forked_at_commit` on fork creation. Add merge endpoint.
- `backend/app/sections.py` — Add `merge_fork_into_base()` for the merge operation.

### Modified Frontend Files

- `frontend/src/routes/+layout.svelte` — Settings link (gear icon) in topbar, sync indicator component.
- `frontend/src/routes/recipe/[slug]/+page.svelte` — Stream visualization section, merge button on fork view, merged badge on fork list.
- `frontend/src/lib/api.ts` — New API functions for sync, settings, stream, and merge endpoints.
- `frontend/src/lib/types.ts` — New types for sync status, stream events, remote config.
