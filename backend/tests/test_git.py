import subprocess
from pathlib import Path

import pytest

from app.git import git_init_if_needed, git_commit, git_rm, git_log, git_show


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
