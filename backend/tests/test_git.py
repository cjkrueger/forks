import subprocess
from pathlib import Path

import pytest

from app.git import (
    git_init_if_needed, git_commit, git_rm, git_log, git_show,
    git_head_hash, git_has_remote, git_remote_add, git_push, git_pull,
    git_ahead_behind, PullResult,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a temp dir and init git."""
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(tmp_path), capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(tmp_path), capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=str(tmp_path), capture_output=True,
    )
    return tmp_path


class TestGitInitIfNeeded:
    def test_inits_when_no_git_dir(self, tmp_path):
        git_init_if_needed(tmp_path)
        assert (tmp_path / ".git").exists()

    def test_skips_if_already_init(self, git_repo):
        git_init_if_needed(git_repo)  # should not error


class TestGitCommit:
    def test_commits_file(self, git_repo):
        f = git_repo / "test.md"
        f.write_text("hello")
        git_commit(git_repo, f, "Add test")
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=str(git_repo), capture_output=True, text=True,
        )
        assert "Add test" in result.stdout

    def test_does_not_raise_on_failure(self, git_repo):
        fake = git_repo / "nonexistent.md"
        git_commit(git_repo, fake, "Should not crash")


class TestGitRm:
    def test_removes_and_commits(self, git_repo):
        f = git_repo / "to-delete.md"
        f.write_text("bye")
        git_commit(git_repo, f, "Add file")
        git_rm(git_repo, f, "Remove file")
        assert not f.exists()
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=str(git_repo), capture_output=True, text=True,
        )
        assert "Remove file" in result.stdout


class TestGitLog:
    def test_returns_history(self, git_repo):
        f = git_repo / "recipe.md"
        f.write_text("v1")
        git_commit(git_repo, f, "Version 1")
        f.write_text("v2")
        git_commit(git_repo, f, "Version 2")
        entries = git_log(git_repo, f)
        assert len(entries) == 2
        assert entries[0]["message"] == "Version 2"
        assert entries[1]["message"] == "Version 1"
        assert "hash" in entries[0]
        assert "date" in entries[0]

    def test_empty_for_untracked(self, git_repo):
        f = git_repo / "untracked.md"
        entries = git_log(git_repo, f)
        assert entries == []


class TestGitShow:
    def test_shows_content_at_revision(self, git_repo):
        f = git_repo / "recipe.md"
        f.write_text("version 1 content")
        git_commit(git_repo, f, "v1")
        v1_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(git_repo), capture_output=True, text=True,
        ).stdout.strip()
        f.write_text("version 2 content")
        git_commit(git_repo, f, "v2")
        content = git_show(git_repo, v1_hash, f)
        assert "version 1 content" in content

    def test_returns_empty_on_bad_revision(self, git_repo):
        f = git_repo / "recipe.md"
        content = git_show(git_repo, "badrev", f)
        assert content == ""


# ---------------------------------------------------------------------------
# Fixture: bare remote + local clone for push/pull tests
# ---------------------------------------------------------------------------

@pytest.fixture
def remote_and_local(tmp_path):
    """Create a bare git repo (the 'remote') and a local clone connected to it."""
    bare_dir = tmp_path / "remote.git"
    bare_dir.mkdir()
    subprocess.run(["git", "init", "--bare"], cwd=str(bare_dir), capture_output=True, check=True)

    local_dir = tmp_path / "local"
    subprocess.run(
        ["git", "clone", str(bare_dir), str(local_dir)],
        capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(local_dir), capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(local_dir), capture_output=True,
    )
    # Create an initial commit so the branch exists
    readme = local_dir / "README.md"
    readme.write_text("init")
    subprocess.run(["git", "add", "-A"], cwd=str(local_dir), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=str(local_dir), capture_output=True,
    )
    subprocess.run(["git", "push", "-u", "origin", "main"], cwd=str(local_dir), capture_output=True)

    return bare_dir, local_dir


# ---------------------------------------------------------------------------
# Tests: git_head_hash
# ---------------------------------------------------------------------------

class TestGitHeadHash:
    def test_returns_40_char_hash(self, git_repo):
        h = git_head_hash(git_repo)
        assert len(h) == 40
        assert all(c in "0123456789abcdef" for c in h)

    def test_returns_empty_on_no_repo(self, tmp_path):
        h = git_head_hash(tmp_path)
        assert h == ""


# ---------------------------------------------------------------------------
# Tests: git_has_remote
# ---------------------------------------------------------------------------

class TestGitHasRemote:
    def test_false_when_no_remote(self, git_repo):
        assert git_has_remote(git_repo) is False

    def test_true_when_configured(self, remote_and_local):
        _bare, local = remote_and_local
        assert git_has_remote(local) is True


# ---------------------------------------------------------------------------
# Tests: git_remote_add
# ---------------------------------------------------------------------------

class TestGitRemoteAdd:
    def test_adds_remote(self, git_repo):
        git_remote_add(git_repo, "https://example.com/repo.git")
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(git_repo), capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "https://example.com/repo.git" in result.stdout

    def test_replaces_existing_remote(self, git_repo):
        git_remote_add(git_repo, "https://example.com/old.git")
        git_remote_add(git_repo, "https://example.com/new.git")
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(git_repo), capture_output=True, text=True,
        )
        assert "https://example.com/new.git" in result.stdout


# ---------------------------------------------------------------------------
# Tests: git_push / git_pull
# ---------------------------------------------------------------------------

class TestGitPushPull:
    def test_push_succeeds(self, remote_and_local):
        _bare, local = remote_and_local
        f = local / "recipe.md"
        f.write_text("# My Recipe")
        git_commit(local, f, "Add recipe")
        assert git_push(local) is True

    def test_push_fails_without_remote(self, git_repo):
        assert git_push(git_repo) is False

    def test_pull_gets_remote_changes(self, remote_and_local, tmp_path):
        bare, local = remote_and_local

        # Create a second clone, make a change, push it
        local2 = tmp_path / "local2"
        subprocess.run(
            ["git", "clone", str(bare), str(local2)],
            capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(local2), capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(local2), capture_output=True,
        )
        new_file = local2 / "new-recipe.md"
        new_file.write_text("# New Recipe")
        subprocess.run(["git", "add", "-A"], cwd=str(local2), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new recipe"],
            cwd=str(local2), capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=str(local2), capture_output=True)

        # Now pull from the first local clone
        result = git_pull(local)
        assert result.success is True
        assert "new-recipe.md" in result.changed_files
        assert result.conflict_files == []
        assert (local / "new-recipe.md").exists()

    def test_pull_returns_result_type(self, remote_and_local):
        _bare, local = remote_and_local
        result = git_pull(local)
        assert isinstance(result, PullResult)
        assert result.success is True

    def test_pull_fails_without_remote(self, git_repo):
        result = git_pull(git_repo)
        assert result.success is False


# ---------------------------------------------------------------------------
# Tests: git_ahead_behind
# ---------------------------------------------------------------------------

class TestGitAheadBehind:
    def test_zero_when_in_sync(self, remote_and_local):
        _bare, local = remote_and_local
        ahead, behind = git_ahead_behind(local)
        assert ahead == 0
        assert behind == 0

    def test_ahead_when_local_commits(self, remote_and_local):
        _bare, local = remote_and_local
        f = local / "extra.md"
        f.write_text("extra content")
        git_commit(local, f, "Local-only commit")
        ahead, behind = git_ahead_behind(local)
        assert ahead == 1
        assert behind == 0

    def test_zero_with_no_remote(self, git_repo):
        ahead, behind = git_ahead_behind(git_repo)
        assert ahead == 0
        assert behind == 0
