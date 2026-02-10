"""Tests for cook history model and parsing."""
import textwrap
from pathlib import Path

from app.parser import parse_frontmatter, parse_recipe


def _write(path, content):
    path.write_text(textwrap.dedent(content))


class TestCookHistoryParsing:
    def test_parse_cook_history_from_frontmatter(self, tmp_path):
        _write(tmp_path / "soup.md", """\
            ---
            title: Soup
            tags: [soup]
            cook_history:
              - date: 2026-02-09
                fork: vegan
              - date: 2026-01-25
            ---

            # Soup

            ## Ingredients

            - water
        """)
        summary = parse_frontmatter(tmp_path / "soup.md")
        assert len(summary.cook_history) == 2
        assert summary.cook_history[0].date == "2026-02-09"
        assert summary.cook_history[0].fork == "vegan"
        assert summary.cook_history[1].date == "2026-01-25"
        assert summary.cook_history[1].fork is None

    def test_parse_empty_cook_history(self, tmp_path):
        _write(tmp_path / "soup.md", """\
            ---
            title: Soup
            tags: [soup]
            ---

            # Soup
        """)
        summary = parse_frontmatter(tmp_path / "soup.md")
        assert summary.cook_history == []

    def test_parse_recipe_includes_cook_history(self, tmp_path):
        _write(tmp_path / "soup.md", """\
            ---
            title: Soup
            tags: [soup]
            cook_history:
              - date: 2026-02-09
            ---

            # Soup

            ## Ingredients

            - water
        """)
        recipe = parse_recipe(tmp_path / "soup.md")
        assert len(recipe.cook_history) == 1
        assert recipe.cook_history[0].date == "2026-02-09"
