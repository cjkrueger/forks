import logging
from pathlib import Path

import frontmatter

from typing import List

from app.models import Recipe, RecipeSummary, ForkSummary, CookHistoryEntry, ChangelogEntry

logger = logging.getLogger(__name__)


def _parse_changelog(meta: dict) -> List[ChangelogEntry]:
    raw = meta.get("changelog", [])
    entries = []
    for item in raw:
        if isinstance(item, dict):
            entries.append(ChangelogEntry(
                date=str(item.get("date", "")),
                action=str(item.get("action", "")),
                summary=str(item.get("summary", "")),
            ))
    return entries


def _parse_cook_history(meta: dict) -> List[CookHistoryEntry]:
    raw = meta.get("cook_history", [])
    entries = []
    for item in raw:
        if isinstance(item, dict):
            entries.append(CookHistoryEntry(
                date=str(item.get("date", "")),
                fork=item.get("fork"),
            ))
        elif isinstance(item, str):
            entries.append(CookHistoryEntry(date=item))
    return entries


def parse_frontmatter(path: Path) -> RecipeSummary:
    """Parse only the frontmatter metadata from a recipe file."""
    slug = path.stem
    try:
        post = frontmatter.load(path)
        meta = post.metadata
    except Exception:
        logger.warning(f"Failed to parse frontmatter: {path}")
        return RecipeSummary(slug=slug, title=slug)

    servings = meta.get("servings")

    return RecipeSummary(
        slug=slug,
        title=meta.get("title", slug),
        tags=meta.get("tags", []),
        servings=str(servings) if servings is not None else None,
        prep_time=meta.get("prep_time"),
        cook_time=meta.get("cook_time"),
        date_added=str(meta.get("date_added")) if meta.get("date_added") else None,
        source=meta.get("source"),
        author=meta.get("author"),
        image=meta.get("image"),
        cook_history=_parse_cook_history(meta),
        likes=int(meta.get("likes", 0)),
        changelog=_parse_changelog(meta),
    )


def parse_recipe(path: Path) -> Recipe:
    """Parse full recipe including frontmatter and markdown body."""
    slug = path.stem
    try:
        post = frontmatter.load(path)
        meta = post.metadata
        content = post.content
    except Exception:
        logger.warning(f"Failed to parse recipe: {path}")
        content = path.read_text()
        return Recipe(slug=slug, title=slug, content=content)

    servings = meta.get("servings")

    return Recipe(
        slug=slug,
        title=meta.get("title", slug),
        tags=meta.get("tags", []),
        servings=str(servings) if servings is not None else None,
        prep_time=meta.get("prep_time"),
        cook_time=meta.get("cook_time"),
        date_added=str(meta.get("date_added")) if meta.get("date_added") else None,
        source=meta.get("source"),
        author=meta.get("author"),
        image=meta.get("image"),
        cook_history=_parse_cook_history(meta),
        likes=int(meta.get("likes", 0)),
        changelog=_parse_changelog(meta),
        content=content,
    )


def parse_fork_frontmatter(path: Path) -> ForkSummary:
    """Parse fork file frontmatter into a ForkSummary."""
    stem = path.stem
    parts = stem.split(".fork.")
    name = parts[-1] if len(parts) > 1 else stem

    try:
        post = frontmatter.load(path)
        meta = post.metadata
    except Exception:
        logger.warning(f"Failed to parse fork frontmatter: {path}")
        return ForkSummary(name=name, fork_name=name)

    return ForkSummary(
        name=name,
        fork_name=meta.get("fork_name", name),
        author=meta.get("author"),
        date_added=str(meta.get("date_added")) if meta.get("date_added") else None,
        merged_at=str(meta.get("merged_at")) if meta.get("merged_at") else None,
        forked_at_commit=meta.get("forked_at_commit"),
        changelog=_parse_changelog(meta),
    )
