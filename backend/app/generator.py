import datetime
import re
from typing import List, Optional

from pydantic import BaseModel


class RecipeInput(BaseModel):
    title: str
    tags: List[str] = []
    servings: Optional[str] = None
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    image: Optional[str] = None
    likes: int = 0
    ingredients: List[str] = []
    instructions: List[str] = []
    notes: List[str] = []
    version: Optional[int] = None


def slugify(title: str) -> str:
    """Convert a title to a URL-friendly slug.

    - Lowercase
    - Replace spaces with hyphens
    - Strip special characters (keep only alphanumeric and hyphens)
    - Collapse multiple hyphens into one
    - Strip leading/trailing hyphens
    """
    slug = title.lower()
    slug = slug.replace(" ", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return slug


def generate_markdown(data: RecipeInput) -> str:
    """Take structured recipe data and return a complete markdown string
    with YAML frontmatter."""
    lines: List[str] = []

    # --- Frontmatter ---
    lines.append("---")
    lines.append(f"title: {data.title}")

    if data.source:
        lines.append(f"source: {data.source}")

    if data.author:
        lines.append(f"author: {data.author}")

    if data.tags:
        tag_list = ", ".join(data.tags)
        lines.append(f"tags: [{tag_list}]")

    if data.servings:
        lines.append(f"servings: {data.servings}")

    if data.prep_time:
        lines.append(f"prep_time: {data.prep_time}")

    if data.cook_time:
        lines.append(f"cook_time: {data.cook_time}")

    lines.append(f"date_added: {datetime.date.today().isoformat()}")

    if data.image:
        lines.append(f"image: {data.image}")

    if data.likes:
        lines.append(f"likes: {data.likes}")

    lines.append("---")

    # --- Body ---
    lines.append("")
    lines.append(f"# {data.title}")

    # Ingredients
    lines.append("")
    lines.append("## Ingredients")
    lines.append("")
    for item in data.ingredients:
        lines.append(f"- {item}")

    # Instructions
    lines.append("")
    lines.append("## Instructions")
    lines.append("")
    for i, step in enumerate(data.instructions, start=1):
        lines.append(f"{i}. {step}")

    # Notes (only if non-empty)
    if data.notes:
        lines.append("")
        lines.append("## Notes")
        lines.append("")
        for note in data.notes:
            lines.append(f"- {note}")

    # Trailing newline for clean file output
    lines.append("")

    return "\n".join(lines)
