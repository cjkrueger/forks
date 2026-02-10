import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


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


def git_commit(recipes_dir: Path, path: Path, message: str) -> None:
    """Stage a file and commit. Fire-and-forget: failures logged, never raised."""
    try:
        subprocess.run(
            ["git", "add", str(path.relative_to(recipes_dir))],
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
