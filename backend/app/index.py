import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

import frontmatter

from app.models import RecipeSummary, Recipe
from app.parser import parse_frontmatter, parse_recipe

logger = logging.getLogger(__name__)


class RecipeIndex:
    def __init__(self, recipes_dir: Path):
        self.recipes_dir = recipes_dir
        self._index: Dict[str, RecipeSummary] = {}
        self._ingredients: Dict[str, List[str]] = {}

    def build(self) -> None:
        self._index.clear()
        self._ingredients.clear()
        if not self.recipes_dir.exists():
            logger.warning(f"Recipes directory not found: {self.recipes_dir}")
            return
        for path in self.recipes_dir.glob("*.md"):
            self._index_file(path)
        logger.info(f"Indexed {len(self._index)} recipes from {self.recipes_dir}")

    def _index_file(self, path: Path) -> None:
        summary = parse_frontmatter(path)
        self._index[summary.slug] = summary
        self._ingredients[summary.slug] = self._extract_ingredients(path)

    def _extract_ingredients(self, path: Path) -> List[str]:
        try:
            post = frontmatter.load(path)
            content = post.content
        except Exception:
            content = path.read_text()

        lines = []
        in_ingredients = False
        for line in content.split("\n"):
            if re.match(r"^##\s+Ingredients", line, re.IGNORECASE):
                in_ingredients = True
                continue
            if in_ingredients and re.match(r"^##\s+", line):
                break
            if in_ingredients and line.strip().startswith("- "):
                lines.append(line.strip().lstrip("- ").lower())
        return lines

    def list_slugs(self) -> List[str]:
        return list(self._index.keys())

    def list_all(self) -> List[RecipeSummary]:
        return sorted(self._index.values(), key=lambda r: r.title.lower())

    def filter_by_tags(self, tags: List[str]) -> List[RecipeSummary]:
        results = [
            r for r in self._index.values()
            if all(tag in r.tags for tag in tags)
        ]
        return sorted(results, key=lambda r: r.title.lower())

    def get(self, slug: str) -> Optional[Recipe]:
        if slug not in self._index:
            return None
        path = self.recipes_dir / f"{slug}.md"
        if not path.exists():
            return None
        return parse_recipe(path)

    def search(self, query: str) -> List[RecipeSummary]:
        if not query.strip():
            return self.list_all()

        q = query.lower()
        results = []
        for slug, summary in self._index.items():
            if q in summary.title.lower():
                results.append(summary)
                continue
            if any(q in tag.lower() for tag in summary.tags):
                results.append(summary)
                continue
            if any(q in ing for ing in self._ingredients.get(slug, [])):
                results.append(summary)
                continue
        return sorted(results, key=lambda r: r.title.lower())

    def add_or_update(self, path: Path) -> None:
        self._index_file(path)

    def remove(self, slug: str) -> None:
        self._index.pop(slug, None)
        self._ingredients.pop(slug, None)
