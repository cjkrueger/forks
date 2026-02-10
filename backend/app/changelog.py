"""Helpers for appending changelog entries to recipe/fork frontmatter."""

import datetime


def append_changelog_entry(post, action: str, summary: str) -> None:
    """Append a changelog entry to a frontmatter.Post object.

    Args:
        post: A python-frontmatter Post object.
        action: The action type (e.g. "created", "edited", "merged").
        summary: A human-readable summary of the change.
    """
    changelog = post.metadata.get("changelog", [])
    if not isinstance(changelog, list):
        changelog = []
    changelog.append({
        "date": datetime.date.today().isoformat(),
        "action": action,
        "summary": summary,
    })
    post.metadata["changelog"] = changelog
