import logging
from pathlib import Path

import frontmatter

from app.models import Recipe, RecipeSummary

logger = logging.getLogger(__name__)


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
        image=meta.get("image"),
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
        image=meta.get("image"),
        content=content,
    )
