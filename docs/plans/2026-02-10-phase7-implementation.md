# Phase 7: Git Sync, Fork Merging & Stream Visualization — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add remote git sync for collaborative recipe sharing, fork merging back into base recipes, and a visual stream timeline showing recipe lineage.

**Architecture:** A sync engine wraps git push/pull on top of the existing auto-commit system. Conflicts auto-create forks. GitHub OAuth provides smooth setup. A stream visualization is built from git history + fork metadata. All remote features are opt-in.

**Tech Stack:** Python/FastAPI (backend), SvelteKit/TypeScript (frontend), git subprocess calls, GitHub OAuth (GitHub App), SVG for stream graph.

**Design doc:** `docs/plans/2026-02-10-phase7-design.md`

---

## Task 1: Git Remote Operations

Extend `backend/app/git.py` with functions for remote management, push, pull, HEAD hash, and diff stat.

**Files:**
- Modify: `backend/app/git.py`
- Test: `backend/tests/test_git.py`

### Step 1: Write failing tests for new git functions

Add to `backend/tests/test_git.py`:

```python
from app.git import (
    git_init_if_needed, git_commit, git_rm, git_log, git_show,
    git_head_hash, git_remote_add, git_push, git_pull, git_has_remote,
    git_ahead_behind,
)


class TestGitHeadHash:
    def test_returns_hash(self, git_repo):
        f = git_repo / "test.md"
        f.write_text("hello")
        git_commit(git_repo, f, "Add test")
        h = git_head_hash(git_repo)
        assert h and len(h) == 40

    def test_returns_empty_on_no_repo(self, tmp_path):
        assert git_head_hash(tmp_path) == ""


class TestGitRemoteAdd:
    def test_adds_remote(self, git_repo):
        git_remote_add(git_repo, "https://example.com/repo.git")
        result = subprocess.run(
            ["git", "remote", "-v"],
            cwd=str(git_repo), capture_output=True, text=True,
        )
        assert "origin" in result.stdout

    def test_replaces_existing_remote(self, git_repo):
        git_remote_add(git_repo, "https://example.com/old.git")
        git_remote_add(git_repo, "https://example.com/new.git")
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(git_repo), capture_output=True, text=True,
        )
        assert "new.git" in result.stdout


class TestGitHasRemote:
    def test_false_when_no_remote(self, git_repo):
        assert git_has_remote(git_repo) is False

    def test_true_when_remote_configured(self, git_repo):
        git_remote_add(git_repo, "https://example.com/repo.git")
        assert git_has_remote(git_repo) is True


class TestGitPushPull:
    @pytest.fixture
    def remote_and_local(self, tmp_path):
        """Set up a bare remote and a local repo that tracks it."""
        bare = tmp_path / "remote.git"
        bare.mkdir()
        subprocess.run(["git", "init", "--bare"], cwd=str(bare), capture_output=True)

        local = tmp_path / "local"
        local.mkdir()
        subprocess.run(["git", "init"], cwd=str(local), capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(local), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=str(local), capture_output=True)
        f = local / "init.md"
        f.write_text("init")
        subprocess.run(["git", "add", "."], cwd=str(local), capture_output=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(local), capture_output=True)
        subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=str(local), capture_output=True)
        subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=str(local), capture_output=True)
        return bare, local

    def test_push_sends_commits(self, remote_and_local):
        bare, local = remote_and_local
        f = local / "recipe.md"
        f.write_text("new recipe")
        git_commit(local, f, "Add recipe")
        ok = git_push(local)
        assert ok is True
        # Verify remote has the commit
        result = subprocess.run(
            ["git", "log", "--oneline"], cwd=str(bare), capture_output=True, text=True,
        )
        assert "Add recipe" in result.stdout

    def test_push_returns_false_no_remote(self, git_repo):
        assert git_push(git_repo) is False

    def test_pull_fetches_changes(self, remote_and_local, tmp_path):
        bare, local = remote_and_local
        # Create a second clone and push from it
        clone2 = tmp_path / "clone2"
        subprocess.run(["git", "clone", str(bare), str(clone2)], capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(clone2), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test2"], cwd=str(clone2), capture_output=True)
        f2 = clone2 / "from-other.md"
        f2.write_text("from another user")
        subprocess.run(["git", "add", "."], cwd=str(clone2), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Other user recipe"], cwd=str(clone2), capture_output=True)
        subprocess.run(["git", "push"], cwd=str(clone2), capture_output=True)

        # Pull from original local
        result = git_pull(local)
        assert result.success is True
        assert (local / "from-other.md").exists()

    def test_pull_returns_changed_files(self, remote_and_local, tmp_path):
        bare, local = remote_and_local
        clone2 = tmp_path / "clone2"
        subprocess.run(["git", "clone", str(bare), str(clone2)], capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(clone2), capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test2"], cwd=str(clone2), capture_output=True)
        f2 = clone2 / "new-recipe.md"
        f2.write_text("content")
        subprocess.run(["git", "add", "."], cwd=str(clone2), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add new recipe"], cwd=str(clone2), capture_output=True)
        subprocess.run(["git", "push"], cwd=str(clone2), capture_output=True)

        result = git_pull(local)
        assert "new-recipe.md" in result.changed_files


class TestGitAheadBehind:
    def test_zero_when_in_sync(self, remote_and_local):
        _bare, local = remote_and_local
        ahead, behind = git_ahead_behind(local)
        assert ahead == 0 and behind == 0

    def test_ahead_when_local_commits(self, remote_and_local):
        _bare, local = remote_and_local
        f = local / "new.md"
        f.write_text("new")
        git_commit(local, f, "Local commit")
        ahead, behind = git_ahead_behind(local)
        assert ahead == 1 and behind == 0

    def test_returns_zero_no_remote(self, git_repo):
        ahead, behind = git_ahead_behind(git_repo)
        assert ahead == 0 and behind == 0
```

### Step 2: Run tests to verify they fail

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_git.py -v -x 2>&1 | tail -20
```

Expected: ImportError — `git_head_hash`, `git_remote_add`, etc. not found.

### Step 3: Implement new git functions

Add to `backend/app/git.py`:

```python
from dataclasses import dataclass, field


@dataclass
class PullResult:
    success: bool
    changed_files: list = field(default_factory=list)
    conflict_files: list = field(default_factory=list)


def git_head_hash(recipes_dir: Path) -> str:
    """Return the current HEAD commit hash, or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def git_has_remote(recipes_dir: Path) -> bool:
    """Check if the repo has a remote named 'origin'."""
    try:
        result = subprocess.run(
            ["git", "remote"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        return "origin" in result.stdout.split()
    except Exception:
        return False


def git_remote_add(recipes_dir: Path, url: str) -> None:
    """Set the origin remote URL (add or update)."""
    try:
        if git_has_remote(recipes_dir):
            subprocess.run(
                ["git", "remote", "set-url", "origin", url],
                cwd=str(recipes_dir),
                capture_output=True,
                text=True,
                check=True,
            )
        else:
            subprocess.run(
                ["git", "remote", "add", "origin", url],
                cwd=str(recipes_dir),
                capture_output=True,
                text=True,
                check=True,
            )
    except Exception:
        logger.exception("Failed to set remote URL")


def git_push(recipes_dir: Path) -> bool:
    """Push to origin. Returns True on success, False on failure."""
    if not git_has_remote(recipes_dir):
        return False
    try:
        subprocess.run(
            ["git", "push", "origin", "HEAD"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except Exception:
        logger.exception("Git push failed")
        return False


def git_pull(recipes_dir: Path) -> PullResult:
    """Pull from origin. Returns PullResult with changed files list."""
    if not git_has_remote(recipes_dir):
        return PullResult(success=False)
    try:
        # Get hash before pull to diff later
        before = git_head_hash(recipes_dir)

        subprocess.run(
            ["git", "pull", "origin", "HEAD", "--no-edit"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )

        after = git_head_hash(recipes_dir)
        changed = []
        if before and after and before != after:
            diff_result = subprocess.run(
                ["git", "diff", "--name-only", before, after],
                cwd=str(recipes_dir),
                capture_output=True,
                text=True,
            )
            changed = [f for f in diff_result.stdout.strip().split("\n") if f]

        return PullResult(success=True, changed_files=changed)
    except subprocess.CalledProcessError as e:
        # Check for merge conflicts
        if "CONFLICT" in (e.stdout or "") or "CONFLICT" in (e.stderr or ""):
            # Get list of conflicted files
            status = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=U"],
                cwd=str(recipes_dir),
                capture_output=True,
                text=True,
            )
            conflicts = [f for f in status.stdout.strip().split("\n") if f]
            return PullResult(success=False, conflict_files=conflicts)
        logger.exception("Git pull failed")
        return PullResult(success=False)
    except Exception:
        logger.exception("Git pull failed")
        return PullResult(success=False)


def git_ahead_behind(recipes_dir: Path) -> tuple:
    """Return (ahead, behind) commit counts relative to origin. Returns (0, 0) on error."""
    if not git_has_remote(recipes_dir):
        return (0, 0)
    try:
        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...origin/HEAD"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        parts = result.stdout.strip().split()
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]))
        return (0, 0)
    except Exception:
        return (0, 0)
```

### Step 4: Run tests to verify they pass

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_git.py -v 2>&1 | tail -30
```

Expected: All tests PASS.

### Step 5: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add backend/app/git.py backend/tests/test_git.py
git commit -m "feat: add git remote operations (push, pull, ahead/behind)"
```

---

## Task 2: Data Models

Add new Pydantic models for sync status, stream events, and update ForkSummary with merge/commit tracking fields.

**Files:**
- Modify: `backend/app/models.py`
- Test: `backend/tests/test_models.py` (create)

### Step 1: Write failing tests

Create `backend/tests/test_models.py`:

```python
"""Tests for Pydantic data models."""
from app.models import (
    ForkSummary,
    SyncStatus,
    StreamEvent,
    RemoteConfig,
    SyncConfig,
)


class TestForkSummaryNewFields:
    def test_merged_at_default_none(self):
        f = ForkSummary(name="test", fork_name="Test")
        assert f.merged_at is None

    def test_merged_at_set(self):
        f = ForkSummary(name="test", fork_name="Test", merged_at="2026-02-10")
        assert f.merged_at == "2026-02-10"

    def test_forked_at_commit_default_none(self):
        f = ForkSummary(name="test", fork_name="Test")
        assert f.forked_at_commit is None

    def test_forked_at_commit_set(self):
        f = ForkSummary(name="test", fork_name="Test", forked_at_commit="abc123")
        assert f.forked_at_commit == "abc123"


class TestSyncStatus:
    def test_defaults(self):
        s = SyncStatus()
        assert s.connected is False
        assert s.last_synced is None
        assert s.ahead == 0
        assert s.behind == 0
        assert s.error is None

    def test_connected_state(self):
        s = SyncStatus(connected=True, last_synced="2026-02-10T12:00:00", ahead=1, behind=2)
        assert s.connected is True
        assert s.ahead == 1


class TestStreamEvent:
    def test_basic_event(self):
        e = StreamEvent(type="created", date="2026-02-01", message="Created")
        assert e.type == "created"
        assert e.fork_name is None

    def test_fork_event(self):
        e = StreamEvent(
            type="forked", date="2026-02-05",
            message="Forked", fork_name="Mom's version", fork_slug="moms-version",
        )
        assert e.fork_slug == "moms-version"


class TestRemoteConfig:
    def test_defaults(self):
        r = RemoteConfig()
        assert r.provider is None
        assert r.url is None

    def test_github_config(self):
        r = RemoteConfig(provider="github", url="https://github.com/user/recipes.git", token="ghu_xxx")
        assert r.provider == "github"


class TestSyncConfig:
    def test_defaults(self):
        s = SyncConfig()
        assert s.enabled is False
        assert s.interval_seconds == 90
```

### Step 2: Run tests to verify they fail

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_models.py -v -x 2>&1 | tail -10
```

Expected: ImportError — new models not found.

### Step 3: Implement model changes

Update `backend/app/models.py` — add new fields to `ForkSummary` and new model classes:

```python
# Add to ForkSummary:
    merged_at: Optional[str] = None
    forked_at_commit: Optional[str] = None

# Add new classes:
class SyncStatus(BaseModel):
    connected: bool = False
    last_synced: Optional[str] = None
    ahead: int = 0
    behind: int = 0
    error: Optional[str] = None


class StreamEvent(BaseModel):
    type: str  # "created", "edited", "forked", "merged"
    date: str
    message: str
    commit: Optional[str] = None
    fork_name: Optional[str] = None
    fork_slug: Optional[str] = None


class RemoteConfig(BaseModel):
    provider: Optional[str] = None  # "github", "gitlab", "generic"
    url: Optional[str] = None
    token: Optional[str] = None


class SyncConfig(BaseModel):
    enabled: bool = False
    interval_seconds: int = 90
```

### Step 4: Run tests to verify they pass

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_models.py -v 2>&1 | tail -20
```

Expected: All PASS.

### Step 5: Run full test suite to check nothing broke

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/ -v 2>&1 | tail -30
```

Expected: All existing tests still pass. The new optional fields on `ForkSummary` are backwards-compatible.

### Step 6: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add backend/app/models.py backend/tests/test_models.py
git commit -m "feat: add sync, stream, and remote config models; extend ForkSummary"
```

---

## Task 3: Remote Config Module

Create `remote_config.py` to read/write the instance config file for remote settings and sync preferences.

**Files:**
- Create: `backend/app/remote_config.py`
- Test: `backend/tests/test_remote_config.py` (create)

### Step 1: Write failing tests

Create `backend/tests/test_remote_config.py`:

```python
"""Tests for remote config read/write."""
import json
from pathlib import Path

import pytest

from app.remote_config import load_config, save_config, get_config_path
from app.models import RemoteConfig, SyncConfig


class TestGetConfigPath:
    def test_returns_path_beside_recipes_dir(self, tmp_path):
        recipes = tmp_path / "recipes"
        recipes.mkdir()
        path = get_config_path(recipes)
        assert path == tmp_path / ".forks-config.json"

    def test_respects_env_override(self, tmp_path, monkeypatch):
        custom = tmp_path / "custom-config.json"
        monkeypatch.setenv("FORKS_CONFIG_PATH", str(custom))
        path = get_config_path(tmp_path / "recipes")
        assert path == custom


class TestLoadConfig:
    def test_returns_defaults_when_no_file(self, tmp_path):
        remote, sync = load_config(tmp_path / "nonexistent.json")
        assert remote.provider is None
        assert remote.url is None
        assert sync.enabled is False
        assert sync.interval_seconds == 90

    def test_loads_existing_config(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({
            "remote": {"provider": "github", "url": "https://github.com/u/r.git", "token": "tok"},
            "sync": {"enabled": True, "interval_seconds": 60},
        }))
        remote, sync = load_config(path)
        assert remote.provider == "github"
        assert remote.url == "https://github.com/u/r.git"
        assert remote.token == "tok"
        assert sync.enabled is True
        assert sync.interval_seconds == 60

    def test_handles_partial_config(self, tmp_path):
        path = tmp_path / "config.json"
        path.write_text(json.dumps({"remote": {"url": "https://example.com/repo.git"}}))
        remote, sync = load_config(path)
        assert remote.url == "https://example.com/repo.git"
        assert remote.provider is None
        assert sync.enabled is False


class TestSaveConfig:
    def test_writes_config_file(self, tmp_path):
        path = tmp_path / "config.json"
        remote = RemoteConfig(provider="github", url="https://github.com/u/r.git", token="tok")
        sync = SyncConfig(enabled=True, interval_seconds=60)
        save_config(path, remote, sync)

        data = json.loads(path.read_text())
        assert data["remote"]["provider"] == "github"
        assert data["sync"]["enabled"] is True

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "subdir" / "config.json"
        save_config(path, RemoteConfig(), SyncConfig())
        assert path.exists()

    def test_roundtrip(self, tmp_path):
        path = tmp_path / "config.json"
        remote = RemoteConfig(provider="gitlab", url="https://gitlab.com/u/r.git", token="glpat-xxx")
        sync = SyncConfig(enabled=True, interval_seconds=120)
        save_config(path, remote, sync)
        loaded_remote, loaded_sync = load_config(path)
        assert loaded_remote.provider == "gitlab"
        assert loaded_remote.token == "glpat-xxx"
        assert loaded_sync.interval_seconds == 120
```

### Step 2: Run tests to verify they fail

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_remote_config.py -v -x 2>&1 | tail -10
```

### Step 3: Implement remote config module

Create `backend/app/remote_config.py`:

```python
"""Instance-local configuration for remote sync settings.

Config is stored OUTSIDE the recipes directory so credentials
never get committed to the synced repo.
"""

import json
import logging
import os
from pathlib import Path
from typing import Tuple

from app.models import RemoteConfig, SyncConfig

logger = logging.getLogger(__name__)


def get_config_path(recipes_dir: Path) -> Path:
    """Return the config file path. Respects FORKS_CONFIG_PATH env var."""
    env = os.environ.get("FORKS_CONFIG_PATH")
    if env:
        return Path(env)
    return recipes_dir.parent / ".forks-config.json"


def load_config(config_path: Path) -> Tuple[RemoteConfig, SyncConfig]:
    """Load config from file. Returns defaults if file doesn't exist."""
    if not config_path.exists():
        return RemoteConfig(), SyncConfig()
    try:
        data = json.loads(config_path.read_text())
        remote = RemoteConfig(**data.get("remote", {}))
        sync = SyncConfig(**data.get("sync", {}))
        return remote, sync
    except Exception:
        logger.exception("Failed to load config from %s", config_path)
        return RemoteConfig(), SyncConfig()


def save_config(config_path: Path, remote: RemoteConfig, sync: SyncConfig) -> None:
    """Write config to file. Creates parent directories if needed."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "remote": remote.model_dump(exclude_none=False),
        "sync": sync.model_dump(),
    }
    config_path.write_text(json.dumps(data, indent=2))
```

### Step 4: Run tests to verify they pass

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_remote_config.py -v 2>&1 | tail -20
```

### Step 5: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add backend/app/remote_config.py backend/tests/test_remote_config.py
git commit -m "feat: add remote config module for instance-local sync settings"
```

---

## Task 4: Fork Merge Backend

Add `forked_at_commit` recording on fork creation, and a merge endpoint that folds fork changes back into the base recipe.

**Files:**
- Modify: `backend/app/sections.py`
- Modify: `backend/app/routes/forks.py`
- Modify: `backend/app/parser.py`
- Modify: `backend/app/models.py` (ForkSummary already updated in Task 2)
- Test: `backend/tests/test_sections.py` (add tests)
- Test: `backend/tests/test_fork_routes.py` (add tests)

### Step 1: Write failing test for `merge_fork_into_base` in sections.py

Add to `backend/tests/test_sections.py`:

```python
from app.sections import merge_fork_into_base


class TestMergeForkIntoBase:
    def test_merges_changed_ingredients(self):
        base = (
            "# Cookies\n\n"
            "## Ingredients\n\n- 1 cup butter\n- 2 cups flour\n\n"
            "## Instructions\n\n1. Mix\n2. Bake\n"
        )
        fork = "## Ingredients\n\n- 1 cup coconut oil\n- 2 cups flour\n"
        result = merge_fork_into_base(base, fork)
        assert "coconut oil" in result
        assert "butter" not in result
        # Unchanged sections preserved
        assert "## Instructions" in result
        assert "Mix" in result

    def test_preserves_frontmatter_in_base(self):
        """merge_fork_into_base only merges body content, not frontmatter."""
        base = "# Cookies\n\n## Ingredients\n\n- butter\n\n## Notes\n\n- old note\n"
        fork = "## Notes\n\n- new note\n"
        result = merge_fork_into_base(base, fork)
        assert "new note" in result
        assert "old note" not in result
        assert "# Cookies" in result

    def test_no_fork_sections_returns_base(self):
        base = "# Title\n\n## Ingredients\n\n- flour\n"
        fork = ""
        result = merge_fork_into_base(base, fork)
        assert "flour" in result
```

### Step 2: Run to verify failure

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_sections.py::TestMergeForkIntoBase -v -x 2>&1 | tail -10
```

### Step 3: Implement `merge_fork_into_base`

Add to `backend/app/sections.py`:

```python
def merge_fork_into_base(base_content: str, fork_content: str) -> str:
    """Merge fork sections into base recipe content.

    For each section in the fork, replace the corresponding section in the base.
    Sections not present in the fork are kept from the base.
    This is the same as merge_content but named explicitly for the merge-back use case.
    """
    return merge_content(base_content, fork_content)
```

Note: `merge_content` already does exactly what we need. `merge_fork_into_base` is an explicit alias for clarity at the call site. If the logic ever diverges (e.g., merge-back needs conflict markers), this gives us the seam.

### Step 4: Run to verify pass

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_sections.py -v 2>&1 | tail -20
```

### Step 5: Write failing tests for forked_at_commit and merge endpoint

Add to `backend/tests/test_fork_routes.py`:

```python
from unittest.mock import patch


class TestForkCreationTracksCommit:
    def test_fork_file_contains_forked_at_commit(self, client, tmp_recipes):
        """Creating a fork should record the base recipe's current HEAD hash."""
        client.post("/api/recipes/chocolate-cookies/forks", json=_fork_input())
        fork_file = tmp_recipes / "chocolate-cookies.fork.vegan-version.md"
        content = fork_file.read_text()
        assert "forked_at_commit:" in content


class TestMergeFork:
    def test_merge_fork_into_base(self, client, tmp_recipes):
        client.post("/api/recipes/chocolate-cookies/forks", json=_fork_input())
        resp = client.post("/api/recipes/chocolate-cookies/forks/vegan-version/merge")
        assert resp.status_code == 200
        data = resp.json()
        assert data["merged"] is True

        # Base recipe should now contain fork's ingredients
        base_content = (tmp_recipes / "chocolate-cookies.md").read_text()
        assert "coconut oil" in base_content

    def test_merge_sets_merged_at_on_fork(self, client, tmp_recipes):
        client.post("/api/recipes/chocolate-cookies/forks", json=_fork_input())
        client.post("/api/recipes/chocolate-cookies/forks/vegan-version/merge")
        fork_content = (tmp_recipes / "chocolate-cookies.fork.vegan-version.md").read_text()
        assert "merged_at:" in fork_content

    def test_merge_fork_not_found(self, client):
        resp = client.post("/api/recipes/chocolate-cookies/forks/nonexistent/merge")
        assert resp.status_code == 404

    def test_merge_base_not_found(self, client):
        resp = client.post("/api/recipes/nonexistent/forks/some-fork/merge")
        assert resp.status_code == 404

    def test_merged_fork_shows_in_index(self, client):
        client.post("/api/recipes/chocolate-cookies/forks", json=_fork_input())
        client.post("/api/recipes/chocolate-cookies/forks/vegan-version/merge")
        resp = client.get("/api/recipes/chocolate-cookies")
        fork = resp.json()["forks"][0]
        assert fork["merged_at"] is not None
```

### Step 6: Run to verify failure

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_fork_routes.py::TestMergeFork -v -x 2>&1 | tail -10
```

### Step 7: Implement forked_at_commit recording and merge endpoint

**Modify `backend/app/sections.py`** — update `generate_fork_markdown` to accept `forked_at_commit`:

```python
def generate_fork_markdown(
    forked_from: str,
    fork_name: str,
    changed_sections: Dict[str, str],
    author: Optional[str] = None,
    forked_at_commit: Optional[str] = None,
) -> str:
    """Generate a fork markdown file with frontmatter and changed sections."""
    lines = []
    lines.append("---")
    lines.append(f"forked_from: {forked_from}")
    lines.append(f"fork_name: {fork_name}")
    if author:
        lines.append(f"author: {author}")
    lines.append(f"date_added: {datetime.date.today().isoformat()}")
    if forked_at_commit:
        lines.append(f"forked_at_commit: {forked_at_commit}")
    lines.append("---")

    for section_name, content in changed_sections.items():
        if content:
            lines.append("")
            lines.append(f"## {section_name}")
            lines.append("")
            lines.append(content)

    lines.append("")
    return "\n".join(lines)
```

**Modify `backend/app/routes/forks.py`** — pass `forked_at_commit` on create, add merge endpoint:

In `create_fork`, after loading the base, get HEAD hash:

```python
from app.git import git_commit, git_log, git_rm, git_show, git_head_hash
from app.sections import diff_sections, generate_fork_markdown, merge_content, merge_fork_into_base
```

In `create_fork` body, before generating markdown:

```python
        head_hash = git_head_hash(recipes_dir)

        md = generate_fork_markdown(
            forked_from=slug,
            fork_name=data.fork_name,
            changed_sections=changed,
            author=data.author,
            forked_at_commit=head_hash if head_hash else None,
        )
```

Add the merge endpoint:

```python
    @router.post("/{fork_name_slug}/merge")
    def merge_fork(slug: str, fork_name_slug: str):
        """Merge a fork's changes back into the base recipe."""
        base_path = _load_base(slug)
        fork_path = _fork_path(slug, fork_name_slug)
        if not fork_path.exists():
            raise HTTPException(status_code=404, detail="Fork not found")

        base_post = frontmatter.load(base_path)
        fork_post = frontmatter.load(fork_path)

        # Merge fork content into base body
        merged_body = merge_fork_into_base(base_post.content, fork_post.content)

        # Rebuild the base file with original frontmatter + merged body
        base_post.content = merged_body
        base_path.write_text(frontmatter.dumps(base_post))
        git_commit(recipes_dir, base_path, f"Merge fork '{fork_post.metadata.get('fork_name', fork_name_slug)}' into {slug}")

        # Mark fork as merged
        fork_post.metadata["merged_at"] = datetime.date.today().isoformat()
        fork_path.write_text(frontmatter.dumps(fork_post))
        git_commit(recipes_dir, fork_path, f"Mark fork {fork_name_slug} as merged into {slug}")

        # Re-index both
        index.add_or_update(base_path)
        index.add_or_update(fork_path)

        return {"merged": True, "fork_name": fork_name_slug}
```

Add `import datetime` at the top of `routes/forks.py`.

**Modify `backend/app/parser.py`** — update `parse_fork_frontmatter` to extract new fields:

```python
def parse_fork_frontmatter(path: Path) -> ForkSummary:
    """Parse fork file frontmatter into a ForkSummary."""
    stem = path.stem
    parts = stem.split(".fork.")
    name = parts[-1] if len(parts) > 1 else stem

    try:
        post = frontmatter.load(path)
        meta = post.metadata
    except Exception:
        logger.warning(f"Failed to parse fork frontmatter: {path}")
        return ForkSummary(name=name, fork_name=name)

    return ForkSummary(
        name=name,
        fork_name=meta.get("fork_name", name),
        author=meta.get("author"),
        date_added=str(meta.get("date_added")) if meta.get("date_added") else None,
        merged_at=str(meta.get("merged_at")) if meta.get("merged_at") else None,
        forked_at_commit=meta.get("forked_at_commit"),
    )
```

### Step 8: Run tests to verify they pass

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_fork_routes.py -v 2>&1 | tail -30
```

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_sections.py -v 2>&1 | tail -20
```

### Step 9: Run full test suite

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/ -v 2>&1 | tail -30
```

### Step 10: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add backend/app/sections.py backend/app/routes/forks.py backend/app/parser.py backend/tests/test_sections.py backend/tests/test_fork_routes.py
git commit -m "feat: add fork merge endpoint and forked_at_commit tracking"
```

---

## Task 5: Sync Engine

Create the core sync module that orchestrates push/pull with auto-fork conflict resolution.

**Files:**
- Create: `backend/app/sync.py`
- Test: `backend/tests/test_sync.py` (create)

### Step 1: Write failing tests

Create `backend/tests/test_sync.py`:

```python
"""Tests for the sync engine."""
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.sync import SyncEngine
from app.git import git_commit


@pytest.fixture
def sync_env(tmp_path):
    """Set up a bare remote, a local repo, and a SyncEngine."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=str(bare), capture_output=True)

    local = tmp_path / "local"
    local.mkdir()
    subprocess.run(["git", "init"], cwd=str(local), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(local), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(local), capture_output=True)
    f = local / "init.md"
    f.write_text("init")
    subprocess.run(["git", "add", "."], cwd=str(local), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(local), capture_output=True)
    subprocess.run(["git", "remote", "add", "origin", str(bare)], cwd=str(local), capture_output=True)
    subprocess.run(["git", "push", "-u", "origin", "HEAD"], cwd=str(local), capture_output=True)

    engine = SyncEngine(recipes_dir=local, index=None)
    return bare, local, engine


@pytest.fixture
def second_clone(sync_env, tmp_path):
    """Create a second clone of the remote for simulating another user."""
    bare, local, engine = sync_env
    clone2 = tmp_path / "clone2"
    subprocess.run(["git", "clone", str(bare), str(clone2)], capture_output=True)
    subprocess.run(["git", "config", "user.email", "other@test.com"], cwd=str(clone2), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Other"], cwd=str(clone2), capture_output=True)
    return clone2


class TestSyncEnginePush:
    def test_push_after_commit(self, sync_env):
        bare, local, engine = sync_env
        f = local / "recipe.md"
        f.write_text("new recipe")
        git_commit(local, f, "Add recipe")
        result = engine.push()
        assert result is True

    def test_push_no_remote(self, tmp_path):
        local = tmp_path / "no-remote"
        local.mkdir()
        subprocess.run(["git", "init"], cwd=str(local), capture_output=True)
        engine = SyncEngine(recipes_dir=local, index=None)
        assert engine.push() is False


class TestSyncEnginePull:
    def test_pull_gets_new_files(self, sync_env, second_clone):
        bare, local, engine = sync_env
        # Other user adds a recipe
        f = second_clone / "other-recipe.md"
        f.write_text("---\ntitle: Other Recipe\ntags: []\n---\n\n# Other Recipe\n")
        subprocess.run(["git", "add", "."], cwd=str(second_clone), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add other recipe"], cwd=str(second_clone), capture_output=True)
        subprocess.run(["git", "push"], cwd=str(second_clone), capture_output=True)

        result = engine.pull()
        assert result.success is True
        assert (local / "other-recipe.md").exists()

    def test_pull_returns_changed_files(self, sync_env, second_clone):
        bare, local, engine = sync_env
        f = second_clone / "new.md"
        f.write_text("content")
        subprocess.run(["git", "add", "."], cwd=str(second_clone), capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add new"], cwd=str(second_clone), capture_output=True)
        subprocess.run(["git", "push"], cwd=str(second_clone), capture_output=True)

        result = engine.pull()
        assert "new.md" in result.changed_files


class TestSyncEngineStatus:
    def test_status_when_connected(self, sync_env):
        _bare, _local, engine = sync_env
        status = engine.get_status()
        assert status.connected is True
        assert status.ahead == 0
        assert status.behind == 0

    def test_status_when_no_remote(self, tmp_path):
        local = tmp_path / "no-remote"
        local.mkdir()
        subprocess.run(["git", "init"], cwd=str(local), capture_output=True)
        engine = SyncEngine(recipes_dir=local, index=None)
        status = engine.get_status()
        assert status.connected is False
```

### Step 2: Run to verify failure

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_sync.py -v -x 2>&1 | tail -10
```

### Step 3: Implement sync engine

Create `backend/app/sync.py`:

```python
"""Sync engine for pushing/pulling recipes to/from a git remote."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.git import (
    git_has_remote,
    git_push,
    git_pull,
    git_ahead_behind,
    PullResult,
)
from app.models import SyncStatus

logger = logging.getLogger(__name__)


class SyncEngine:
    def __init__(self, recipes_dir: Path, index):
        self.recipes_dir = recipes_dir
        self.index = index
        self._last_synced: Optional[str] = None
        self._last_error: Optional[str] = None

    def push(self) -> bool:
        """Push local commits to remote."""
        ok = git_push(self.recipes_dir)
        if ok:
            self._last_synced = datetime.now(timezone.utc).isoformat()
            self._last_error = None
        return ok

    def pull(self) -> PullResult:
        """Pull from remote. Re-indexes changed recipe files."""
        result = git_pull(self.recipes_dir)
        if result.success:
            self._last_synced = datetime.now(timezone.utc).isoformat()
            self._last_error = None
            if self.index and result.changed_files:
                for filename in result.changed_files:
                    path = self.recipes_dir / filename
                    if path.exists() and path.suffix == ".md":
                        self.index.add_or_update(path)
                    elif not path.exists():
                        slug = path.stem
                        self.index.remove(slug)
        elif result.conflict_files:
            self._last_error = f"Conflicts in {len(result.conflict_files)} file(s)"
            self._resolve_conflicts(result.conflict_files)
        else:
            self._last_error = "Pull failed"
        return result

    def _resolve_conflicts(self, conflict_files: list) -> None:
        """Auto-resolve conflicts by keeping ours and creating forks from theirs."""
        import subprocess
        from datetime import date

        for filename in conflict_files:
            path = self.recipes_dir / filename
            if not path.exists() or not filename.endswith(".md"):
                continue

            try:
                # Get the incoming (theirs) version
                theirs = subprocess.run(
                    ["git", "show", f"MERGE_HEAD:{filename}"],
                    cwd=str(self.recipes_dir),
                    capture_output=True, text=True,
                )
                if theirs.returncode != 0:
                    continue

                # Accept ours
                subprocess.run(
                    ["git", "checkout", "--ours", filename],
                    cwd=str(self.recipes_dir),
                    capture_output=True, text=True,
                )
                subprocess.run(
                    ["git", "add", filename],
                    cwd=str(self.recipes_dir),
                    capture_output=True, text=True,
                )

                # Write theirs as a conflict fork
                stem = Path(filename).stem
                if ".fork." in stem:
                    continue  # Don't create forks of forks for conflicts

                conflict_name = f"conflict-{date.today().isoformat()}"
                fork_filename = f"{stem}.fork.{conflict_name}.md"
                fork_path = self.recipes_dir / fork_filename
                fork_path.write_text(theirs.stdout)

                subprocess.run(
                    ["git", "add", fork_filename],
                    cwd=str(self.recipes_dir),
                    capture_output=True, text=True,
                )

                logger.info("Created conflict fork: %s", fork_filename)

            except Exception:
                logger.exception("Failed to resolve conflict for %s", filename)

        # Complete the merge
        try:
            subprocess.run(
                ["git", "commit", "--no-edit"],
                cwd=str(self.recipes_dir),
                capture_output=True, text=True,
            )
        except Exception:
            logger.exception("Failed to complete merge commit")

    def get_status(self) -> SyncStatus:
        """Return current sync status."""
        connected = git_has_remote(self.recipes_dir)
        ahead, behind = (0, 0)
        if connected:
            ahead, behind = git_ahead_behind(self.recipes_dir)
        return SyncStatus(
            connected=connected,
            last_synced=self._last_synced,
            ahead=ahead,
            behind=behind,
            error=self._last_error,
        )
```

### Step 4: Run tests to verify they pass

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_sync.py -v 2>&1 | tail -20
```

### Step 5: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add backend/app/sync.py backend/tests/test_sync.py
git commit -m "feat: add sync engine with push, pull, conflict resolution"
```

---

## Task 6: Settings & Sync API Routes

Create API endpoints for configuring the remote, triggering sync, and getting sync status.

**Files:**
- Create: `backend/app/routes/settings.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_settings_routes.py` (create)

### Step 1: Write failing tests

Create `backend/tests/test_settings_routes.py`:

```python
"""Tests for settings and sync API routes."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def tmp_recipes(tmp_path):
    recipe = tmp_path / "recipes"
    recipe.mkdir()
    md = tmp_path / "recipes" / "test-recipe.md"
    md.write_text("---\ntitle: Test Recipe\ntags: []\n---\n\n# Test Recipe\n\n## Ingredients\n\n- flour\n")
    return recipe


@pytest.fixture
def config_path(tmp_path):
    return tmp_path / ".forks-config.json"


@pytest.fixture
def client(tmp_recipes, config_path, monkeypatch):
    monkeypatch.setenv("FORKS_CONFIG_PATH", str(config_path))
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


class TestGetSyncStatus:
    def test_returns_status(self, client):
        resp = client.get("/api/sync/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "connected" in data
        assert data["connected"] is False


class TestGetSettings:
    def test_returns_defaults_when_no_config(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["remote"]["provider"] is None
        assert data["sync"]["enabled"] is False


class TestSaveSettings:
    def test_saves_remote_config(self, client, config_path):
        resp = client.put("/api/settings", json={
            "remote": {"provider": "generic", "url": "https://example.com/repo.git", "token": "tok"},
            "sync": {"enabled": True, "interval_seconds": 60},
        })
        assert resp.status_code == 200
        assert config_path.exists()
        data = json.loads(config_path.read_text())
        assert data["remote"]["url"] == "https://example.com/repo.git"

    def test_returns_saved_config(self, client):
        client.put("/api/settings", json={
            "remote": {"provider": "github", "url": "https://github.com/u/r.git"},
            "sync": {"enabled": True},
        })
        resp = client.get("/api/settings")
        data = resp.json()
        assert data["remote"]["provider"] == "github"
        assert data["sync"]["enabled"] is True


class TestDisconnect:
    def test_clears_config(self, client, config_path):
        # First save a config
        client.put("/api/settings", json={
            "remote": {"provider": "github", "url": "https://github.com/u/r.git", "token": "tok"},
            "sync": {"enabled": True},
        })
        assert config_path.exists()

        resp = client.delete("/api/settings/remote")
        assert resp.status_code == 200

        resp = client.get("/api/settings")
        data = resp.json()
        assert data["remote"]["provider"] is None
        assert data["sync"]["enabled"] is False
```

### Step 2: Run to verify failure

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_settings_routes.py -v -x 2>&1 | tail -10
```

### Step 3: Implement settings routes

Create `backend/app/routes/settings.py`:

```python
"""API routes for settings and sync management."""

import logging
from pathlib import Path

from fastapi import APIRouter

from app.models import RemoteConfig, SyncConfig, SyncStatus
from app.remote_config import get_config_path, load_config, save_config
from app.sync import SyncEngine

logger = logging.getLogger(__name__)


def create_settings_router(sync_engine: SyncEngine, recipes_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/api/sync/status", response_model=SyncStatus)
    def sync_status():
        return sync_engine.get_status()

    @router.post("/api/sync/trigger")
    def sync_trigger():
        pull_result = sync_engine.pull()
        push_ok = sync_engine.push()
        return {
            "pull_success": pull_result.success,
            "pull_changed": pull_result.changed_files,
            "push_success": push_ok,
        }

    @router.get("/api/settings")
    def get_settings():
        config_path = get_config_path(recipes_dir)
        remote, sync = load_config(config_path)
        # Redact token for GET responses
        redacted_remote = remote.model_copy(
            update={"token": "***" if remote.token else None}
        )
        return {"remote": redacted_remote.model_dump(), "sync": sync.model_dump()}

    @router.put("/api/settings")
    def save_settings(body: dict):
        config_path = get_config_path(recipes_dir)
        remote = RemoteConfig(**body.get("remote", {}))
        sync = SyncConfig(**body.get("sync", {}))
        save_config(config_path, remote, sync)

        # Apply remote URL to git if provided
        if remote.url:
            from app.git import git_remote_add
            git_remote_add(recipes_dir, remote.url)

        return {"saved": True}

    @router.delete("/api/settings/remote")
    def disconnect_remote():
        config_path = get_config_path(recipes_dir)
        save_config(config_path, RemoteConfig(), SyncConfig())
        return {"disconnected": True}

    return router
```

**Modify `backend/app/main.py`** — register the settings router and initialize the sync engine:

Add these imports:
```python
from app.sync import SyncEngine
from app.routes.settings import create_settings_router
```

In `create_app`, after registering existing routers:
```python
    # Initialize sync engine
    sync_engine = SyncEngine(recipes_dir=recipes_path, index=index)
    app.include_router(create_settings_router(sync_engine, recipes_path))
```

### Step 4: Run tests to verify they pass

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_settings_routes.py -v 2>&1 | tail -20
```

### Step 5: Run full test suite

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/ -v 2>&1 | tail -30
```

### Step 6: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add backend/app/routes/settings.py backend/app/main.py backend/tests/test_settings_routes.py
git commit -m "feat: add settings and sync API routes"
```

---

## Task 7: Stream Timeline Endpoint

Create the `/api/recipes/{slug}/stream` endpoint that assembles a recipe's timeline from git history and fork metadata.

**Files:**
- Create: `backend/app/routes/stream.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_stream.py` (create)

### Step 1: Write failing tests

Create `backend/tests/test_stream.py`:

```python
"""Tests for recipe stream/timeline endpoint."""
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


BASE_RECIPE = textwrap.dedent("""\
    ---
    title: Pasta Carbonara
    tags: [italian]
    date_added: 2026-02-01
    ---

    # Pasta Carbonara

    ## Ingredients

    - 400g spaghetti
    - 200g guanciale
    - 4 egg yolks
    - 100g pecorino

    ## Instructions

    1. Cook pasta
    2. Fry guanciale
    3. Mix eggs and cheese
    4. Combine
""")


@pytest.fixture
def tmp_recipes(tmp_path):
    recipe = tmp_path / "pasta-carbonara.md"
    recipe.write_text(BASE_RECIPE)
    return tmp_path


@pytest.fixture
def client(tmp_recipes):
    app = create_app(recipes_dir=tmp_recipes)
    return TestClient(app)


class TestStreamEndpoint:
    def test_returns_stream_for_recipe(self, client):
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        assert resp.status_code == 200
        data = resp.json()
        assert "events" in data
        assert len(data["events"]) >= 1
        # First event should be creation
        assert data["events"][-1]["type"] == "created"

    def test_404_for_missing_recipe(self, client):
        resp = client.get("/api/recipes/nonexistent/stream")
        assert resp.status_code == 404

    @patch("app.routes.stream.git_log")
    def test_includes_edit_events(self, mock_log, client):
        mock_log.return_value = [
            {"hash": "abc123", "date": "2026-02-03T10:00:00", "message": "Update ingredients"},
            {"hash": "def456", "date": "2026-02-01T10:00:00", "message": "Create recipe: Pasta Carbonara"},
        ]
        resp = client.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        types = [e["type"] for e in events]
        assert "created" in types

    def test_includes_fork_events(self, client, tmp_recipes):
        """If a fork exists, stream should include a 'forked' event."""
        fork = tmp_recipes / "pasta-carbonara.fork.moms-version.md"
        fork.write_text(
            "---\nforked_from: pasta-carbonara\nfork_name: Mom's Version\n"
            "author: mom\ndate_added: 2026-02-05\nforked_at_commit: abc123\n---\n\n"
            "## Ingredients\n\n- 400g rigatoni\n"
        )
        # Rebuild index by re-creating client
        app = create_app(recipes_dir=tmp_recipes)
        c = TestClient(app)
        resp = c.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        fork_events = [e for e in events if e["type"] == "forked"]
        assert len(fork_events) == 1
        assert fork_events[0]["fork_name"] == "Mom's Version"

    def test_includes_merged_events(self, client, tmp_recipes):
        fork = tmp_recipes / "pasta-carbonara.fork.moms-version.md"
        fork.write_text(
            "---\nforked_from: pasta-carbonara\nfork_name: Mom's Version\n"
            "author: mom\ndate_added: 2026-02-05\nmerged_at: 2026-02-08\n---\n\n"
            "## Ingredients\n\n- 400g rigatoni\n"
        )
        app = create_app(recipes_dir=tmp_recipes)
        c = TestClient(app)
        resp = c.get("/api/recipes/pasta-carbonara/stream")
        events = resp.json()["events"]
        merged_events = [e for e in events if e["type"] == "merged"]
        assert len(merged_events) == 1
        assert merged_events[0]["fork_name"] == "Mom's Version"
```

### Step 2: Run to verify failure

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_stream.py -v -x 2>&1 | tail -10
```

### Step 3: Implement stream endpoint

Create `backend/app/routes/stream.py`:

```python
"""API route for recipe stream/timeline visualization."""

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.git import git_log
from app.index import RecipeIndex
from app.models import StreamEvent

logger = logging.getLogger(__name__)

# Commit messages that are noise (frontmatter-only changes)
_NOISE_PREFIXES = ("Log cook", "Add favorite", "Remove favorite", "Delete cook")


def create_stream_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/api/recipes/{slug}/stream")
    def get_stream(slug: str):
        recipe = index.get(slug)
        if not recipe:
            raise HTTPException(status_code=404, detail="Recipe not found")

        events: list[StreamEvent] = []

        # Get git log for the base recipe file
        base_path = recipes_dir / f"{slug}.md"
        if base_path.exists():
            log_entries = git_log(recipes_dir, base_path, max_entries=50)
            for entry in log_entries:
                msg = entry["message"]
                # Filter noise
                if any(msg.startswith(prefix) for prefix in _NOISE_PREFIXES):
                    continue
                # Classify event type
                if msg.startswith("Create recipe") or msg == "Initial commit":
                    event_type = "created"
                elif msg.startswith("Merge fork"):
                    event_type = "merged"
                    # Try to extract fork name from message like "Merge fork 'Name' into slug"
                    fork_name = None
                    if "'" in msg:
                        fork_name = msg.split("'")[1]
                    events.append(StreamEvent(
                        type=event_type,
                        date=entry["date"],
                        message=msg,
                        commit=entry["hash"],
                        fork_name=fork_name,
                    ))
                    continue
                else:
                    event_type = "edited"

                events.append(StreamEvent(
                    type=event_type,
                    date=entry["date"],
                    message=msg,
                    commit=entry["hash"],
                ))

        # Add fork events from fork metadata
        for fork_summary in recipe.forks:
            if fork_summary.date_added:
                events.append(StreamEvent(
                    type="forked",
                    date=fork_summary.date_added,
                    message=f"Forked: {fork_summary.fork_name}",
                    fork_name=fork_summary.fork_name,
                    fork_slug=fork_summary.name,
                ))

            if fork_summary.merged_at:
                # Check if we already have a merge event from git log
                has_merge = any(
                    e.type == "merged" and e.fork_name == fork_summary.fork_name
                    for e in events
                )
                if not has_merge:
                    events.append(StreamEvent(
                        type="merged",
                        date=fork_summary.merged_at,
                        message=f"Merged: {fork_summary.fork_name}",
                        fork_name=fork_summary.fork_name,
                        fork_slug=fork_summary.name,
                    ))

        # Sort by date (oldest first)
        events.sort(key=lambda e: e.date)

        return {"events": [e.model_dump() for e in events]}

    return router
```

**Modify `backend/app/main.py`** — register the stream router:

Add import:
```python
from app.routes.stream import create_stream_router
```

In `create_app`, add:
```python
    app.include_router(create_stream_router(index, recipes_path))
```

### Step 4: Run tests to verify they pass

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/test_stream.py -v 2>&1 | tail -20
```

### Step 5: Run full test suite

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/ -v 2>&1 | tail -30
```

### Step 6: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add backend/app/routes/stream.py backend/app/main.py backend/tests/test_stream.py
git commit -m "feat: add recipe stream/timeline endpoint"
```

---

## Task 8: Frontend Types & API Client

Update TypeScript types and API client to support new backend endpoints.

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/sync.ts`

### Step 1: Add new types

Add to `frontend/src/lib/types.ts`:

```typescript
export interface SyncStatus {
  connected: boolean;
  last_synced: string | null;
  ahead: number;
  behind: number;
  error: string | null;
}

export interface StreamEvent {
  type: 'created' | 'edited' | 'forked' | 'merged';
  date: string;
  message: string;
  commit: string | null;
  fork_name: string | null;
  fork_slug: string | null;
}

export interface StreamTimeline {
  events: StreamEvent[];
}

export interface RemoteConfig {
  provider: string | null;
  url: string | null;
  token: string | null;
}

export interface SyncConfig {
  enabled: boolean;
  interval_seconds: number;
}

export interface AppSettings {
  remote: RemoteConfig;
  sync: SyncConfig;
}
```

Update `ForkSummary` to include new fields:

```typescript
export interface ForkSummary {
  name: string;
  fork_name: string;
  author: string | null;
  date_added: string | null;
  merged_at: string | null;
  forked_at_commit: string | null;
}
```

### Step 2: Add new API functions

Add to `frontend/src/lib/api.ts`:

```typescript
import type { ..., SyncStatus, StreamTimeline, AppSettings } from './types';

export async function getSyncStatus(): Promise<SyncStatus> {
  const res = await fetch(`${BASE}/sync/status`);
  if (!res.ok) throw new Error('Failed to get sync status');
  return res.json();
}

export async function triggerSync(): Promise<{ pull_success: boolean; push_success: boolean; pull_changed: string[] }> {
  const res = await fetch(`${BASE}/sync/trigger`, { method: 'POST' });
  if (!res.ok) throw new Error('Sync failed');
  return res.json();
}

export async function getSettings(): Promise<AppSettings> {
  const res = await fetch(`${BASE}/settings`);
  if (!res.ok) throw new Error('Failed to get settings');
  return res.json();
}

export async function saveSettings(settings: AppSettings): Promise<void> {
  const res = await fetch(`${BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save settings');
}

export async function disconnectRemote(): Promise<void> {
  const res = await fetch(`${BASE}/settings/remote`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to disconnect');
}

export async function getRecipeStream(slug: string): Promise<StreamTimeline> {
  const res = await fetch(`${BASE}/recipes/${slug}/stream`);
  if (!res.ok) throw new Error('Failed to fetch recipe stream');
  return res.json();
}

export async function mergeFork(slug: string, forkName: string): Promise<{ merged: boolean }> {
  const res = await fetch(`${BASE}/recipes/${slug}/forks/${forkName}/merge`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Merge failed' }));
    throw new Error(err.detail || 'Merge failed');
  }
  return res.json();
}
```

### Step 3: Create sync status store

Create `frontend/src/lib/sync.ts`:

```typescript
import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { getSyncStatus } from './api';
import type { SyncStatus } from './types';

const defaultStatus: SyncStatus = {
  connected: false,
  last_synced: null,
  ahead: 0,
  behind: 0,
  error: null,
};

export const syncStatus = writable<SyncStatus>(defaultStatus);
export const isSyncing = writable(false);

let pollInterval: ReturnType<typeof setInterval> | null = null;

export function startSyncPolling(intervalMs = 90_000) {
  if (!browser) return;
  stopSyncPolling();

  async function poll() {
    try {
      const status = await getSyncStatus();
      syncStatus.set(status);
    } catch {
      // Silently fail — sync is optional
    }
  }

  poll(); // Immediate first check
  pollInterval = setInterval(poll, intervalMs);
}

export function stopSyncPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

export const isConnected = derived(syncStatus, $s => $s.connected);
```

### Step 4: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add frontend/src/lib/types.ts frontend/src/lib/api.ts frontend/src/lib/sync.ts
git commit -m "feat: add frontend types, API client, and sync store for Phase 7"
```

---

## Task 9: Settings Page

Create the `/settings` route with remote configuration UI.

**Files:**
- Create: `frontend/src/routes/settings/+page.svelte`
- Modify: `frontend/src/routes/+layout.svelte` (add gear icon)

### Step 1: Create settings page

Create `frontend/src/routes/settings/+page.svelte`:

```svelte
<script lang="ts">
  import { onMount } from 'svelte';
  import { getSettings, saveSettings, disconnectRemote, triggerSync } from '$lib/api';
  import { syncStatus, isSyncing } from '$lib/sync';
  import type { AppSettings } from '$lib/types';

  let settings: AppSettings | null = null;
  let loading = true;
  let saving = false;
  let message = '';

  // Form state
  let provider = '';
  let url = '';
  let token = '';
  let syncEnabled = false;
  let intervalSeconds = 90;

  onMount(async () => {
    try {
      settings = await getSettings();
      provider = settings.remote.provider || '';
      url = settings.remote.url || '';
      token = '';  // Never pre-fill token (it's redacted from API)
      syncEnabled = settings.sync.enabled;
      intervalSeconds = settings.sync.interval_seconds;
    } catch (e) {
      message = 'Failed to load settings';
    }
    loading = false;
  });

  async function handleSave() {
    saving = true;
    message = '';
    try {
      await saveSettings({
        remote: {
          provider: provider || null,
          url: url || null,
          token: token || null,
        },
        sync: {
          enabled: syncEnabled,
          interval_seconds: intervalSeconds,
        },
      });
      message = 'Settings saved';
    } catch (e) {
      message = 'Failed to save settings';
    }
    saving = false;
  }

  async function handleDisconnect() {
    if (!confirm('Disconnect from remote? Your local recipes will not be affected.')) return;
    try {
      await disconnectRemote();
      provider = '';
      url = '';
      token = '';
      syncEnabled = false;
      message = 'Disconnected';
    } catch (e) {
      message = 'Failed to disconnect';
    }
  }

  async function handleSync() {
    $isSyncing = true;
    message = '';
    try {
      const result = await triggerSync();
      const changed = result.pull_changed?.length || 0;
      message = changed > 0 ? `Synced — ${changed} file(s) updated` : 'Synced — up to date';
    } catch (e) {
      message = 'Sync failed';
    }
    $isSyncing = false;
  }
</script>

<svelte:head>
  <title>Settings - Forks</title>
</svelte:head>

<div class="settings">
  <a href="/" class="back-link">&larr; Back to recipes</a>
  <h1>Settings</h1>

  {#if loading}
    <p class="loading">Loading settings...</p>
  {:else}
    <section class="settings-section">
      <h2>Remote Sync</h2>
      <p class="description">Connect to a git remote to sync recipes across devices and share with others.</p>

      <div class="sync-status">
        <span class="status-dot" class:connected={$syncStatus.connected} class:error={$syncStatus.error}></span>
        {#if $syncStatus.connected}
          <span>Connected</span>
          {#if $syncStatus.last_synced}
            <span class="muted"> &middot; Last synced {new Date($syncStatus.last_synced).toLocaleString()}</span>
          {/if}
          {#if $syncStatus.ahead > 0 || $syncStatus.behind > 0}
            <span class="muted"> &middot; {$syncStatus.ahead} ahead, {$syncStatus.behind} behind</span>
          {/if}
        {:else}
          <span>Not connected</span>
        {/if}
        {#if $syncStatus.error}
          <span class="error-text">{$syncStatus.error}</span>
        {/if}
      </div>

      <form on:submit|preventDefault={handleSave}>
        <label class="field">
          <span>Provider</span>
          <select bind:value={provider}>
            <option value="">Select...</option>
            <option value="github">GitHub</option>
            <option value="gitlab">GitLab</option>
            <option value="generic">Other (generic git)</option>
          </select>
        </label>

        <label class="field">
          <span>Repository URL</span>
          <input type="url" bind:value={url} placeholder="https://github.com/user/recipes.git" />
        </label>

        <label class="field">
          <span>Personal Access Token</span>
          <input type="password" bind:value={token} placeholder="Leave blank to keep existing token" />
        </label>

        <label class="field checkbox">
          <input type="checkbox" bind:checked={syncEnabled} />
          <span>Enable automatic sync</span>
        </label>

        {#if syncEnabled}
          <label class="field">
            <span>Sync interval (seconds)</span>
            <input type="number" bind:value={intervalSeconds} min="30" max="600" />
          </label>
        {/if}

        <div class="actions">
          <button type="submit" class="save-btn" disabled={saving}>
            {saving ? 'Saving...' : 'Save Settings'}
          </button>
          {#if $syncStatus.connected}
            <button type="button" class="sync-btn" on:click={handleSync} disabled={$isSyncing}>
              {$isSyncing ? 'Syncing...' : 'Sync Now'}
            </button>
            <button type="button" class="disconnect-btn" on:click={handleDisconnect}>
              Disconnect
            </button>
          {/if}
        </div>
      </form>

      {#if message}
        <p class="message">{message}</p>
      {/if}
    </section>
  {/if}
</div>

<style>
  .settings {
    max-width: 600px;
  }

  .back-link {
    display: inline-block;
    font-size: 0.85rem;
    color: var(--color-text-muted);
    margin-bottom: 1.5rem;
  }

  h1 {
    font-size: 1.75rem;
    font-weight: 700;
    margin-bottom: 2rem;
  }

  h2 {
    font-size: 1.2rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
  }

  .description {
    color: var(--color-text-muted);
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
  }

  .sync-status {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.85rem;
    margin-bottom: 1.5rem;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-text-muted);
    flex-shrink: 0;
  }

  .status-dot.connected {
    background: #22c55e;
  }

  .status-dot.error {
    background: var(--color-danger);
  }

  .error-text {
    color: var(--color-danger);
  }

  .muted {
    color: var(--color-text-muted);
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    margin-bottom: 1rem;
  }

  .field span {
    font-size: 0.85rem;
    font-weight: 500;
  }

  .field input[type="url"],
  .field input[type="password"],
  .field input[type="number"],
  .field select {
    padding: 0.5rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    font-size: 0.9rem;
    font-family: var(--font-body);
    background: var(--color-bg);
    color: var(--color-text);
  }

  .field.checkbox {
    flex-direction: row;
    align-items: center;
  }

  .field.checkbox input {
    margin-right: 0.5rem;
  }

  .actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1.5rem;
  }

  .save-btn {
    padding: 0.5rem 1.25rem;
    background: var(--color-accent);
    color: white;
    border: none;
    border-radius: var(--radius);
    font-size: 0.85rem;
    font-weight: 600;
    cursor: pointer;
  }

  .save-btn:hover { opacity: 0.9; }
  .save-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  .sync-btn {
    padding: 0.5rem 1.25rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
    background: var(--color-surface);
    color: var(--color-text);
    font-size: 0.85rem;
    cursor: pointer;
  }

  .sync-btn:hover { border-color: var(--color-accent); color: var(--color-accent); }

  .disconnect-btn {
    padding: 0.5rem 1.25rem;
    border: 1px solid var(--color-danger-border);
    border-radius: var(--radius);
    background: var(--color-danger-light);
    color: var(--color-danger);
    font-size: 0.85rem;
    cursor: pointer;
  }

  .message {
    margin-top: 1rem;
    font-size: 0.85rem;
    color: var(--color-accent);
  }

  .loading {
    color: var(--color-text-muted);
  }
</style>
```

### Step 2: Add gear icon to topbar in +layout.svelte

In `frontend/src/routes/+layout.svelte`, add a settings link in the topbar nav area, after the theme toggle:

```svelte
<!-- Add import at top of script -->
import { startSyncPolling } from '$lib/sync';
import { syncStatus, isConnected } from '$lib/sync';

<!-- In onMount, start sync polling -->
onMount(async () => {
    // ... existing code ...
    startSyncPolling();
});
```

Add this in the `topbar-nav` section, before the theme toggle:

```svelte
      {#if $isConnected}
        <span class="sync-indicator" class:error={$syncStatus.error} title={$syncStatus.error || 'Synced'}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z"/>
          </svg>
        </span>
      {/if}
      <a href="/settings" class="settings-link" aria-label="Settings">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
        </svg>
      </a>
```

Add styles for the sync indicator and settings link.

### Step 3: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add frontend/src/routes/settings/+page.svelte frontend/src/routes/+layout.svelte
git commit -m "feat: add settings page and sync indicator in topbar"
```

---

## Task 10: Fork Merge UI

Add the "Merge into original" button on the fork view in the recipe detail page.

**Files:**
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte`

### Step 1: Add merge functionality

In the recipe detail page script, add:

```typescript
import { mergeFork } from '$lib/api';

let merging = false;
let mergeMessage = '';

async function handleMergeFork() {
    if (!recipe || !selectedFork) return;
    if (!confirm(`Merge "${forkDetail?.fork_name}" changes into the original recipe?`)) return;
    merging = true;
    mergeMessage = '';
    try {
        await mergeFork(recipe.slug, selectedFork);
        // Reload recipe to reflect merged state
        recipe = await getRecipe(slug);
        if (selectedFork) await selectFork(selectedFork);
        mergeMessage = 'Fork merged into original';
    } catch (e: any) {
        mergeMessage = e.message || 'Merge failed';
    }
    merging = false;
}
```

### Step 2: Add merge button in the recipe-actions section

In the template, inside the `{#if selectedFork}` block in `recipe-actions`, add:

```svelte
          <button class="merge-btn" on:click={handleMergeFork} disabled={merging}>
            {merging ? 'Merging...' : 'Merge into Original'}
          </button>
```

After the recipe-actions div, add merge message display:

```svelte
      {#if mergeMessage}
        <p class="merge-message">{mergeMessage}</p>
      {/if}
```

### Step 3: Add merged badge to fork pills

In the version selector, update fork pills to show merged state:

```svelte
          {#each recipe.forks as fork}
            <button
              class="version-pill"
              class:active={selectedFork === fork.name}
              class:merged={fork.merged_at != null}
              on:click={() => selectFork(fork.name)}
            >
              {fork.fork_name}
              {#if fork.merged_at}
                <span class="merged-badge">Merged</span>
              {/if}
            </button>
          {/each}
```

### Step 4: Add styles

```css
  .merge-btn {
    display: inline-block;
    padding: 0.4rem 1rem;
    border: 1px solid var(--color-accent);
    border-radius: var(--radius);
    font-size: 0.85rem;
    color: var(--color-accent);
    background: var(--color-surface);
    cursor: pointer;
    transition: all 0.15s;
  }

  .merge-btn:hover {
    background: var(--color-accent);
    color: white;
  }

  .merge-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .merge-message {
    font-size: 0.85rem;
    color: var(--color-accent);
    margin-top: 0.5rem;
  }

  .version-pill.merged {
    opacity: 0.7;
  }

  .merged-badge {
    font-size: 0.65rem;
    background: var(--color-tag);
    padding: 0.1rem 0.4rem;
    border-radius: 4px;
    margin-left: 0.25rem;
  }
```

### Step 5: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add frontend/src/routes/recipe/[slug]/+page.svelte
git commit -m "feat: add fork merge UI with merged badge on version pills"
```

---

## Task 11: Stream Visualization

Create the StreamGraph component and integrate it into the recipe detail page.

**Files:**
- Create: `frontend/src/lib/components/StreamGraph.svelte`
- Modify: `frontend/src/routes/recipe/[slug]/+page.svelte`

### Step 1: Create StreamGraph component

Create `frontend/src/lib/components/StreamGraph.svelte`:

```svelte
<script lang="ts">
  import type { StreamEvent } from '$lib/types';

  export let events: StreamEvent[] = [];
  export let onForkClick: ((slug: string) => void) | null = null;

  // Group events and identify active branches
  interface Branch {
    forkSlug: string;
    forkName: string;
    startIndex: number;
    endIndex: number | null;  // null = still active
    merged: boolean;
  }

  $: branches = (() => {
    const b: Branch[] = [];
    for (let i = 0; i < events.length; i++) {
      const e = events[i];
      if (e.type === 'forked' && e.fork_slug) {
        b.push({
          forkSlug: e.fork_slug,
          forkName: e.fork_name || e.fork_slug,
          startIndex: i,
          endIndex: null,
          merged: false,
        });
      }
      if (e.type === 'merged' && e.fork_slug) {
        const branch = b.find(br => br.forkSlug === e.fork_slug);
        if (branch) {
          branch.endIndex = i;
          branch.merged = true;
        }
      }
    }
    return b;
  })();

  function typeIcon(type: string): string {
    switch (type) {
      case 'created': return 'o';
      case 'edited': return 'o';
      case 'forked': return '+';
      case 'merged': return '<';
      default: return 'o';
    }
  }

  function formatDate(dateStr: string): string {
    try {
      return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return dateStr;
    }
  }

  function activeBranchesAt(index: number): Branch[] {
    return branches.filter(b => b.startIndex <= index && (b.endIndex === null || b.endIndex >= index));
  }
</script>

{#if events.length > 0}
  <div class="stream">
    {#each events as event, i}
      {@const active = activeBranchesAt(i)}
      <div class="stream-row">
        <div class="stream-line">
          <div class="main-line" class:first={i === 0} class:last={i === events.length - 1}>
            <span class="node" class:created={event.type === 'created'} class:forked={event.type === 'forked'} class:merged={event.type === 'merged'}>
              {typeIcon(event.type)}
            </span>
          </div>
          {#each active as branch}
            {#if branch.startIndex === i}
              <span class="branch-line branch-start"></span>
            {:else if branch.endIndex === i}
              <span class="branch-line branch-end"></span>
            {:else}
              <span class="branch-line branch-mid"></span>
            {/if}
          {/each}
        </div>
        <div class="stream-content">
          <span class="stream-message">
            {event.message}
            {#if event.type === 'forked' && event.fork_slug && onForkClick}
              <button class="fork-link" on:click={() => onForkClick && event.fork_slug && onForkClick(event.fork_slug)}>
                view &rarr;
              </button>
            {/if}
          </span>
          <span class="stream-date">{formatDate(event.date)}</span>
        </div>
      </div>
    {/each}
  </div>
{/if}

<style>
  .stream {
    display: flex;
    flex-direction: column;
  }

  .stream-row {
    display: flex;
    align-items: center;
    min-height: 2.5rem;
  }

  .stream-line {
    display: flex;
    align-items: center;
    width: 40px;
    flex-shrink: 0;
    position: relative;
  }

  .main-line {
    width: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }

  .main-line::before,
  .main-line::after {
    content: '';
    position: absolute;
    left: 50%;
    width: 2px;
    background: var(--color-border);
    transform: translateX(-50%);
  }

  .main-line::before {
    top: 0;
    height: 50%;
  }

  .main-line::after {
    bottom: 0;
    height: 50%;
  }

  .main-line.first::before { display: none; }
  .main-line.last::after { display: none; }

  .node {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    font-weight: 700;
    z-index: 1;
    background: var(--color-surface);
    border: 2px solid var(--color-border);
    color: var(--color-text-muted);
  }

  .node.created {
    border-color: var(--color-accent);
    color: var(--color-accent);
  }

  .node.forked {
    border-color: #3b82f6;
    color: #3b82f6;
  }

  .node.merged {
    border-color: #22c55e;
    color: #22c55e;
  }

  .branch-line {
    width: 2px;
    height: 2.5rem;
    background: #3b82f6;
    opacity: 0.4;
    margin-left: 4px;
  }

  .branch-start {
    height: 1.25rem;
    align-self: flex-end;
    border-radius: 2px 2px 0 0;
  }

  .branch-end {
    height: 1.25rem;
    align-self: flex-start;
    border-radius: 0 0 2px 2px;
  }

  .stream-content {
    flex: 1;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 0;
    gap: 1rem;
  }

  .stream-message {
    font-size: 0.85rem;
    color: var(--color-text);
  }

  .stream-date {
    font-size: 0.75rem;
    color: var(--color-text-muted);
    white-space: nowrap;
    flex-shrink: 0;
  }

  .fork-link {
    background: none;
    border: none;
    color: var(--color-accent);
    font-size: 0.8rem;
    cursor: pointer;
    padding: 0;
    margin-left: 0.5rem;
  }

  .fork-link:hover {
    text-decoration: underline;
  }
</style>
```

### Step 2: Integrate into recipe detail page

In `frontend/src/routes/recipe/[slug]/+page.svelte`, add:

```typescript
import StreamGraph from '$lib/components/StreamGraph.svelte';
import { getRecipeStream } from '$lib/api';
import type { StreamEvent } from '$lib/types';

let streamEvents: StreamEvent[] = [];
let streamOpen = false;
let streamLoading = false;

async function toggleStream() {
    if (streamOpen) {
        streamOpen = false;
        return;
    }
    if (!recipe) return;
    streamLoading = true;
    streamOpen = true;
    try {
        const data = await getRecipeStream(recipe.slug);
        streamEvents = data.events;
    } catch (e) {
        streamEvents = [];
    }
    streamLoading = false;
}

function handleStreamForkClick(forkSlug: string) {
    selectFork(forkSlug);
    streamOpen = false;
}
```

In the recipe-actions area, add a "Stream" button (shown when there's history):

```svelte
        <button class="history-btn" on:click={toggleStream}>
          {streamOpen ? 'Hide Stream' : 'Stream'}
        </button>
```

Below the recipe-actions, add the stream panel:

```svelte
      {#if streamOpen}
        <div class="stream-panel">
          <h3>Recipe Stream</h3>
          {#if streamLoading}
            <p class="stream-loading">Loading timeline...</p>
          {:else if streamEvents.length === 0}
            <p class="stream-empty">No history available</p>
          {:else}
            <StreamGraph events={streamEvents} onForkClick={handleStreamForkClick} />
          {/if}
        </div>
      {/if}
```

Add styles:

```css
  .stream-panel {
    margin-top: 1rem;
    padding: 1rem;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius);
  }

  .stream-panel h3 {
    font-size: 0.95rem;
    font-weight: 600;
    margin-bottom: 0.75rem;
  }

  .stream-loading, .stream-empty {
    font-size: 0.85rem;
    color: var(--color-text-muted);
  }
```

### Step 3: Commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add frontend/src/lib/components/StreamGraph.svelte frontend/src/routes/recipe/[slug]/+page.svelte
git commit -m "feat: add stream visualization component and recipe timeline"
```

---

## Task 12: Integration Testing & Polish

Run the full app, verify all features work end-to-end, fix any issues.

**Files:**
- Various (bug fixes as needed)

### Step 1: Run full backend test suite

```bash
cd /Users/cj.krueger/Documents/GitHub/forks && python -m pytest backend/tests/ -v 2>&1 | tail -40
```

All tests must pass.

### Step 2: Start the backend and frontend dev servers

```bash
cd /Users/cj.krueger/Documents/GitHub/forks/backend && python -m uvicorn app.main:app --reload &
cd /Users/cj.krueger/Documents/GitHub/forks/frontend && npm run dev &
```

### Step 3: Manual verification checklist

- [ ] Settings page loads at `/settings`
- [ ] Can save remote config (provider, URL, token)
- [ ] Sync status shows "Not connected" when no remote configured
- [ ] Gear icon visible in topbar, links to `/settings`
- [ ] Recipe detail page shows "Stream" button
- [ ] Stream panel shows timeline events from git history
- [ ] Fork pills show "Merged" badge for merged forks
- [ ] "Merge into Original" button appears when viewing a fork
- [ ] Merging a fork updates the base recipe content
- [ ] Fork gets marked with `merged_at` in frontmatter
- [ ] Stream visualization shows fork and merge events
- [ ] App works fully without any remote configured (local-only mode)

### Step 4: Fix any issues found during testing

Address bugs as discovered.

### Step 5: Final commit

```bash
cd /Users/cj.krueger/Documents/GitHub/forks
git add -A
git commit -m "fix: Phase 7 integration fixes and polish"
```
