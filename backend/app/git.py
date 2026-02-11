import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PullResult:
    """Result of a git pull operation."""
    success: bool = False
    changed_files: list = field(default_factory=list)
    conflict_files: list = field(default_factory=list)


def git_init_if_needed(recipes_dir: Path) -> None:
    """Initialize a git repo in recipes_dir if one doesn't exist."""
    git_dir = recipes_dir / ".git"
    if git_dir.exists():
        return
    try:
        subprocess.run(
            ["git", "init"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit", "--allow-empty"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
        )
        logger.info("Initialized git repo in %s", recipes_dir)
    except Exception:
        logger.exception("Failed to initialize git repo")


def git_commit(recipes_dir: Path, path, message: str) -> None:
    """Stage file(s) and commit. Fire-and-forget: failures logged, never raised.

    path can be a single Path or a list of Paths.
    """
    try:
        paths = path if isinstance(path, list) else [path]
        for p in paths:
            subprocess.run(
                ["git", "add", str(p.relative_to(recipes_dir))],
                cwd=str(recipes_dir),
                capture_output=True,
                text=True,
                check=True,
            )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        logger.exception("Git commit failed: %s", message)


def git_rm(recipes_dir: Path, path: Path, message: str) -> None:
    """Remove a file from git and commit. Fire-and-forget."""
    try:
        subprocess.run(
            ["git", "rm", str(path.relative_to(recipes_dir))],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        logger.exception("Git rm failed: %s", message)


def git_log(recipes_dir: Path, path: Path, max_entries: int = 20):
    """Return list of {hash, date, message} for a file's git history."""
    try:
        result = subprocess.run(
            [
                "git", "log",
                "--format=%H|%aI|%s",
                "-n", str(max_entries),
                "--", str(path.relative_to(recipes_dir)),
            ],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        entries = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("|", 2)
            if len(parts) == 3:
                entries.append({
                    "hash": parts[0],
                    "date": parts[1],
                    "message": parts[2],
                })
        return entries
    except Exception:
        logger.exception("Git log failed for %s", path)
        return []


def git_find_commit(recipes_dir: Path, path: Path, message_substring: str) -> Optional[str]:
    """Find the most recent commit whose message contains *message_substring* for *path*.

    Returns the full commit hash, or ``None`` if no matching commit is found.
    """
    try:
        rel = str(path.relative_to(recipes_dir))
        result = subprocess.run(
            [
                "git", "log",
                "--format=%H",
                "-n", "1",
                f"--grep={message_substring}",
                "--", rel,
            ],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        sha = result.stdout.strip()
        return sha if sha else None
    except Exception:
        logger.exception("git_find_commit failed for %s", path)
        return None


def git_show(recipes_dir: Path, revision: str, path: Path) -> str:
    """Return file content at a specific git revision."""
    try:
        rel = str(path.relative_to(recipes_dir))
        result = subprocess.run(
            ["git", "show", f"{revision}:{rel}"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except Exception:
        logger.exception("Git show failed for %s at %s", path, revision)
        return ""


# ---------------------------------------------------------------------------
# Remote operations – return success/failure for UI feedback
# ---------------------------------------------------------------------------


def git_head_hash(recipes_dir: Path) -> str:
    """Return the current HEAD commit hash, or empty string if unavailable."""
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
        logger.debug("git_head_hash failed for %s", recipes_dir)
        return ""


def git_has_remote(recipes_dir: Path) -> bool:
    """Return True if the repo has an 'origin' remote configured."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except Exception:
        return False


def git_remote_add(recipes_dir: Path, url: str) -> None:
    """Add or update the 'origin' remote URL."""
    try:
        if git_has_remote(recipes_dir):
            subprocess.run(
                ["git", "remote", "set-url", "origin", url],
                cwd=str(recipes_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Updated origin remote to %s", url)
        else:
            subprocess.run(
                ["git", "remote", "add", "origin", url],
                cwd=str(recipes_dir),
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info("Added origin remote %s", url)
    except Exception:
        logger.exception("Failed to add/update origin remote")


def git_push(recipes_dir: Path) -> bool:
    """Push current branch to origin. Returns True on success, False on failure."""
    try:
        # Determine the current branch name
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        branch = branch_result.stdout.strip()

        result = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.warning("git push failed: %s", result.stderr.strip())
            return False
        return True
    except Exception:
        logger.exception("git push failed")
        return False


def git_pull(recipes_dir: Path) -> PullResult:
    """Pull from origin. Returns a PullResult with changed/conflict info."""
    try:
        # Record HEAD before pull to diff afterwards
        head_before = git_head_hash(recipes_dir)

        result = subprocess.run(
            ["git", "pull", "origin"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            # Check for merge conflicts
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(recipes_dir),
                capture_output=True,
                text=True,
            )
            conflict_files = []
            for line in status.stdout.strip().split("\n"):
                if line.startswith("UU ") or line.startswith("AA "):
                    conflict_files.append(line[3:].strip())
            if conflict_files:
                return PullResult(
                    success=False,
                    changed_files=[],
                    conflict_files=conflict_files,
                )
            logger.warning("git pull failed: %s", result.stderr.strip())
            return PullResult(success=False)

        # Determine which files changed
        head_after = git_head_hash(recipes_dir)
        changed_files = []
        if head_before and head_after and head_before != head_after:
            diff_result = subprocess.run(
                ["git", "diff", "--name-only", head_before, head_after],
                cwd=str(recipes_dir),
                capture_output=True,
                text=True,
            )
            changed_files = [
                f for f in diff_result.stdout.strip().split("\n") if f
            ]

        return PullResult(
            success=True,
            changed_files=changed_files,
            conflict_files=[],
        )
    except Exception:
        logger.exception("git pull failed")
        return PullResult(success=False)


def git_ahead_behind(recipes_dir: Path) -> tuple:
    """Return (ahead, behind) counts relative to origin tracking branch.

    Returns (0, 0) if there is no remote or tracking info is unavailable.
    """
    try:
        if not git_has_remote(recipes_dir):
            return (0, 0)

        # Fetch to make sure remote refs are up-to-date
        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
        )

        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
            cwd=str(recipes_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return (0, 0)

        parts = result.stdout.strip().split()
        if len(parts) == 2:
            return (int(parts[0]), int(parts[1]))
        return (0, 0)
    except Exception:
        logger.debug("git_ahead_behind failed for %s", recipes_dir)
        return (0, 0)
