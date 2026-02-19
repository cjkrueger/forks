"""Enum definitions for recurring string constants used across the app."""

from enum import StrEnum


class ChangelogAction(StrEnum):
    """Action types recorded in recipe and fork changelogs."""

    CREATED = "created"
    EDITED = "edited"
    MERGED = "merged"
    UNMERGED = "unmerged"
    FAILED = "failed"
    UNFAILED = "unfailed"


class EventType(StrEnum):
    """Event types emitted in the recipe stream/timeline.

    Extends ChangelogAction with the synthetic ``forked`` event, which is
    produced when a fork's ``created`` changelog entry is surfaced in the
    stream (so base-recipe ``created`` and fork-creation events are distinct).
    """

    CREATED = "created"
    EDITED = "edited"
    FORKED = "forked"
    MERGED = "merged"
    UNMERGED = "unmerged"
    FAILED = "failed"
    UNFAILED = "unfailed"


class RemoteProvider(StrEnum):
    """Supported remote git provider types."""

    GITHUB = "github"
    GITLAB = "gitlab"
    GENERIC = "generic"
    TANGLED = "tangled"
    LOCAL = "local"
