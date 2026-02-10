"""Tests for the sync engine."""
import subprocess
from pathlib import Path

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
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=str(local), capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=str(local), capture_output=True,
    )

    f = local / "init.md"
    f.write_text("init")
    subprocess.run(["git", "add", "."], cwd=str(local), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(local), capture_output=True)
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare)],
        cwd=str(local), capture_output=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "HEAD"],
        cwd=str(local), capture_output=True,
    )

    engine = SyncEngine(recipes_dir=local, index=None)
    return bare, local, engine


@pytest.fixture
def second_clone(sync_env, tmp_path):
    """Create a second clone of the bare remote for simulating remote changes."""
    bare, local, engine = sync_env
    clone2 = tmp_path / "clone2"
    subprocess.run(["git", "clone", str(bare), str(clone2)], capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "other@test.com"],
        cwd=str(clone2), capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Other"],
        cwd=str(clone2), capture_output=True,
    )
    return clone2


class TestSyncEnginePush:
    def test_push_after_commit_succeeds(self, sync_env):
        bare, local, engine = sync_env
        f = local / "recipe.md"
        f.write_text("# My Recipe\n\nDelicious food.")
        git_commit(local, f, "Add recipe")
        assert engine.push() is True
        assert engine._last_synced is not None
        assert engine._last_error is None

    def test_push_with_no_remote_returns_false(self, tmp_path):
        """Push should return False when there is no remote configured."""
        repo = tmp_path / "norepo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=str(repo), capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(repo), capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(repo), capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "init"],
            cwd=str(repo), capture_output=True,
        )
        engine = SyncEngine(recipes_dir=repo, index=None)
        assert engine.push() is False


class TestSyncEnginePull:
    def test_pull_gets_new_files(self, sync_env, second_clone):
        bare, local, engine = sync_env
        clone2 = second_clone

        # Push a new file from the second clone
        new_file = clone2 / "new-recipe.md"
        new_file.write_text("# New Recipe\n\nFrom another machine.")
        subprocess.run(["git", "add", "."], cwd=str(clone2), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add new recipe"],
            cwd=str(clone2), capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=str(clone2), capture_output=True)

        # Pull from the engine's local repo
        result = engine.pull()
        assert result.success is True
        assert (local / "new-recipe.md").exists()
        assert engine._last_synced is not None
        assert engine._last_error is None

    def test_pull_returns_changed_files(self, sync_env, second_clone):
        bare, local, engine = sync_env
        clone2 = second_clone

        # Modify an existing file and add a new one from clone2
        (clone2 / "init.md").write_text("modified init")
        new_file = clone2 / "another.md"
        new_file.write_text("# Another Recipe")
        subprocess.run(["git", "add", "."], cwd=str(clone2), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Update and add files"],
            cwd=str(clone2), capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=str(clone2), capture_output=True)

        result = engine.pull()
        assert result.success is True
        assert "init.md" in result.changed_files
        assert "another.md" in result.changed_files

    def test_pull_reindexes_changed_md_files(self, sync_env, second_clone):
        bare, local, engine = sync_env
        clone2 = second_clone

        # Set up a mock index to verify re-indexing
        class MockIndex:
            def __init__(self):
                self.added = []
                self.removed = []

            def add_or_update(self, path):
                self.added.append(path)

            def remove(self, slug):
                self.removed.append(slug)

        mock_index = MockIndex()
        engine.index = mock_index

        # Push a new .md file from clone2
        new_file = clone2 / "indexed-recipe.md"
        new_file.write_text("# Indexed Recipe")
        subprocess.run(["git", "add", "."], cwd=str(clone2), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add indexed recipe"],
            cwd=str(clone2), capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=str(clone2), capture_output=True)

        result = engine.pull()
        assert result.success is True
        assert any("indexed-recipe.md" in str(p) for p in mock_index.added)

    def test_pull_removes_deleted_files_from_index(self, sync_env, second_clone):
        bare, local, engine = sync_env
        clone2 = second_clone

        # First push a file from clone2
        recipe = clone2 / "to-delete.md"
        recipe.write_text("# To Delete")
        subprocess.run(["git", "add", "."], cwd=str(clone2), capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Add to-delete"],
            cwd=str(clone2), capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=str(clone2), capture_output=True)

        # Pull it locally first
        engine.pull()

        # Now delete the file from clone2 and push
        subprocess.run(
            ["git", "rm", "to-delete.md"],
            cwd=str(clone2), capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Delete to-delete"],
            cwd=str(clone2), capture_output=True,
        )
        subprocess.run(["git", "push"], cwd=str(clone2), capture_output=True)

        # Set up mock index for removal tracking
        class MockIndex:
            def __init__(self):
                self.added = []
                self.removed = []

            def add_or_update(self, path):
                self.added.append(path)

            def remove(self, slug):
                self.removed.append(slug)

        mock_index = MockIndex()
        engine.index = mock_index

        result = engine.pull()
        assert result.success is True
        assert "to-delete" in mock_index.removed


class TestSyncEngineStatus:
    def test_status_when_connected(self, sync_env):
        bare, local, engine = sync_env
        status = engine.get_status()
        assert status.connected is True
        assert status.ahead == 0
        assert status.behind == 0
        assert status.error is None

    def test_status_when_no_remote(self, tmp_path):
        """Status should report disconnected when there is no remote."""
        repo = tmp_path / "norepo"
        repo.mkdir()
        subprocess.run(["git", "init"], cwd=str(repo), capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=str(repo), capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(repo), capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", "init"],
            cwd=str(repo), capture_output=True,
        )
        engine = SyncEngine(recipes_dir=repo, index=None)
        status = engine.get_status()
        assert status.connected is False
        assert status.ahead == 0
        assert status.behind == 0

    def test_status_shows_ahead_count(self, sync_env):
        bare, local, engine = sync_env
        # Create a local commit that hasn't been pushed
        f = local / "local-only.md"
        f.write_text("# Local Only")
        git_commit(local, f, "Local commit")
        status = engine.get_status()
        assert status.connected is True
        assert status.ahead == 1

    def test_status_tracks_last_synced_after_push(self, sync_env):
        bare, local, engine = sync_env
        assert engine._last_synced is None
        f = local / "recipe.md"
        f.write_text("# Recipe")
        git_commit(local, f, "Add recipe")
        engine.push()
        status = engine.get_status()
        assert status.last_synced is not None

    def test_status_tracks_last_synced_after_pull(self, sync_env):
        bare, local, engine = sync_env
        assert engine._last_synced is None
        engine.pull()
        status = engine.get_status()
        assert status.last_synced is not None
