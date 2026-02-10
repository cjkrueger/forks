"""Sync engine for pushing/pulling recipes to/from a git remote."""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.git import git_has_remote, git_push, git_pull, git_ahead_behind, PullResult
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
                theirs = subprocess.run(
                    ["git", "show", f"MERGE_HEAD:{filename}"],
                    cwd=str(self.recipes_dir), capture_output=True, text=True,
                )
                if theirs.returncode != 0:
                    continue
                subprocess.run(
                    ["git", "checkout", "--ours", filename],
                    cwd=str(self.recipes_dir), capture_output=True, text=True,
                )
                subprocess.run(
                    ["git", "add", filename],
                    cwd=str(self.recipes_dir), capture_output=True, text=True,
                )
                stem = Path(filename).stem
                if ".fork." in stem:
                    continue
                conflict_name = f"conflict-{date.today().isoformat()}"
                fork_filename = f"{stem}.fork.{conflict_name}.md"
                fork_path = self.recipes_dir / fork_filename
                fork_path.write_text(theirs.stdout)
                subprocess.run(
                    ["git", "add", fork_filename],
                    cwd=str(self.recipes_dir), capture_output=True, text=True,
                )
                logger.info("Created conflict fork: %s", fork_filename)
            except Exception:
                logger.exception("Failed to resolve conflict for %s", filename)

        try:
            subprocess.run(
                ["git", "commit", "--no-edit"],
                cwd=str(self.recipes_dir), capture_output=True, text=True,
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
