"""Helpers for appending changelog entries to recipe/fork frontmatter."""

import datetime

from app.enums import ChangelogAction


def append_changelog_entry(post, action: ChangelogAction, summary: str) -> None:
    """Append a changelog entry to a frontmatter.Post object.

    Args:
        post: A python-frontmatter Post object.
        action: The action type (a :class:`~app.enums.ChangelogAction` value).
        summary: A human-readable summary of the change.
    """
    changelog = post.metadata.get("changelog", [])
    if not isinstance(changelog, list):
        changelog = []
    changelog.append({
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "action": action,
        "summary": summary,
    })
    post.metadata["changelog"] = changelog


def remove_changelog_entries_for_fork(post, fork_name: str) -> None:
    """Remove merged/unmerged changelog entries that reference a specific fork.

    Args:
        post: A python-frontmatter Post object.
        fork_name: The display name of the fork to match against.
    """
    changelog = post.metadata.get("changelog", [])
    if not isinstance(changelog, list):
        return
    post.metadata["changelog"] = [
        entry for entry in changelog
        if not (
            entry.get("action") in (ChangelogAction.MERGED, ChangelogAction.UNMERGED)
            and f"'{fork_name}'" in entry.get("summary", "")
        )
    ]
