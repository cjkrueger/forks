"""Tests for Pydantic models."""

from app.models import (
    ForkSummary,
    RemoteConfig,
    StreamEvent,
    SyncConfig,
    SyncStatus,
)


# --- ForkSummary new fields ---


class TestForkSummaryNewFields:
    def test_merged_at_defaults_to_none(self):
        fs = ForkSummary(name="base", fork_name="spicy")
        assert fs.merged_at is None

    def test_forked_at_commit_defaults_to_none(self):
        fs = ForkSummary(name="base", fork_name="spicy")
        assert fs.forked_at_commit is None

    def test_merged_at_can_be_set(self):
        fs = ForkSummary(
            name="base", fork_name="spicy", merged_at="2026-02-01"
        )
        assert fs.merged_at == "2026-02-01"

    def test_forked_at_commit_can_be_set(self):
        fs = ForkSummary(
            name="base", fork_name="spicy", forked_at_commit="abc1234"
        )
        assert fs.forked_at_commit == "abc1234"

    def test_both_new_fields_set(self):
        fs = ForkSummary(
            name="base",
            fork_name="spicy",
            merged_at="2026-02-01",
            forked_at_commit="abc1234",
        )
        assert fs.merged_at == "2026-02-01"
        assert fs.forked_at_commit == "abc1234"


# --- SyncStatus ---


class TestSyncStatus:
    def test_defaults(self):
        ss = SyncStatus()
        assert ss.connected is False
        assert ss.last_synced is None
        assert ss.ahead == 0
        assert ss.behind == 0
        assert ss.error is None

    def test_custom_values(self):
        ss = SyncStatus(
            connected=True,
            last_synced="2026-02-10T12:00:00Z",
            ahead=3,
            behind=1,
            error=None,
        )
        assert ss.connected is True
        assert ss.last_synced == "2026-02-10T12:00:00Z"
        assert ss.ahead == 3
        assert ss.behind == 1
        assert ss.error is None

    def test_with_error(self):
        ss = SyncStatus(error="Authentication failed")
        assert ss.error == "Authentication failed"
        assert ss.connected is False


# --- StreamEvent ---


class TestStreamEvent:
    def test_basic_event(self):
        event = StreamEvent(
            type="created",
            date="2026-02-10",
            message="Recipe created",
        )
        assert event.type == "created"
        assert event.date == "2026-02-10"
        assert event.message == "Recipe created"
        assert event.commit is None
        assert event.fork_name is None
        assert event.fork_slug is None

    def test_fork_event(self):
        event = StreamEvent(
            type="forked",
            date="2026-02-10",
            message="Fork created: spicy-version",
            commit="abc1234",
            fork_name="spicy-version",
            fork_slug="chocolate-cookies/spicy-version",
        )
        assert event.type == "forked"
        assert event.commit == "abc1234"
        assert event.fork_name == "spicy-version"
        assert event.fork_slug == "chocolate-cookies/spicy-version"

    def test_merged_event(self):
        event = StreamEvent(
            type="merged",
            date="2026-02-10",
            message="Fork merged: spicy-version",
            commit="def5678",
            fork_name="spicy-version",
        )
        assert event.type == "merged"
        assert event.commit == "def5678"
        assert event.fork_name == "spicy-version"
        assert event.fork_slug is None


# --- RemoteConfig ---


class TestRemoteConfig:
    def test_defaults(self):
        rc = RemoteConfig()
        assert rc.provider is None
        assert rc.url is None
        assert rc.token is None

    def test_github_config(self):
        rc = RemoteConfig(
            provider="github",
            url="https://github.com/user/recipes.git",
            token="ghp_xxxx",
        )
        assert rc.provider == "github"
        assert rc.url == "https://github.com/user/recipes.git"
        assert rc.token == "ghp_xxxx"

    def test_gitlab_config(self):
        rc = RemoteConfig(
            provider="gitlab",
            url="https://gitlab.com/user/recipes.git",
        )
        assert rc.provider == "gitlab"
        assert rc.url == "https://gitlab.com/user/recipes.git"
        assert rc.token is None


# --- SyncConfig ---


class TestSyncConfig:
    def test_defaults(self):
        sc = SyncConfig()
        assert sc.enabled is False
        assert sc.interval_seconds == 5400

    def test_custom_values(self):
        sc = SyncConfig(enabled=True, interval_seconds=300)
        assert sc.enabled is True
        assert sc.interval_seconds == 300
