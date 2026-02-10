"""Tests for the sections utility module."""

from app.sections import (
    parse_sections,
    sections_from_recipe_data,
    diff_sections,
    generate_fork_markdown,
    merge_content,
    merge_fork_into_base,
)


class TestParseSections:
    def test_splits_on_h2_headers(self):
        content = "# Title\n\n## Ingredients\n\n- flour\n- sugar\n\n## Instructions\n\n1. Mix"
        sections = parse_sections(content)
        assert "Ingredients" in sections
        assert "Instructions" in sections
        assert "- flour" in sections["Ingredients"]

    def test_preamble_captured(self):
        content = "# My Recipe\n\nSome intro text\n\n## Ingredients\n\n- flour"
        sections = parse_sections(content)
        assert "_preamble" in sections
        assert "My Recipe" in sections["_preamble"]

    def test_empty_content(self):
        sections = parse_sections("")
        assert sections == {}

    def test_no_sections(self):
        sections = parse_sections("# Just a title")
        assert "_preamble" in sections


class TestSectionsFromRecipeData:
    def test_ingredients_formatted(self):
        result = sections_from_recipe_data(["flour", "sugar"], [], [])
        assert result["Ingredients"] == "- flour\n- sugar"

    def test_instructions_numbered(self):
        result = sections_from_recipe_data([], ["Mix", "Bake"], [])
        assert result["Instructions"] == "1. Mix\n2. Bake"

    def test_notes_formatted(self):
        result = sections_from_recipe_data([], [], ["Great recipe"])
        assert result["Notes"] == "- Great recipe"

    def test_empty_lists_excluded(self):
        result = sections_from_recipe_data([], [], [])
        assert result == {}


class TestDiffSections:
    def test_detects_changed_ingredients(self):
        base = "# Title\n\n## Ingredients\n\n- flour\n- 2 eggs\n\n## Instructions\n\n1. Mix"
        changed = diff_sections(base, ["flour", "2 flax eggs"], ["Mix"], [])
        assert "Ingredients" in changed
        assert "Instructions" not in changed

    def test_no_changes_returns_empty(self):
        base = "# Title\n\n## Ingredients\n\n- flour\n\n## Instructions\n\n1. Mix"
        changed = diff_sections(base, ["flour"], ["Mix"], [])
        assert changed == {}

    def test_added_notes_detected(self):
        base = "# Title\n\n## Ingredients\n\n- flour"
        changed = diff_sections(base, ["flour"], [], ["New note"])
        assert "Notes" in changed


class TestGenerateForkMarkdown:
    def test_produces_valid_frontmatter(self):
        result = generate_fork_markdown(
            "chocolate-chip-cookies", "Vegan Version",
            {"Ingredients": "- coconut oil"},
            author="CJ",
        )
        assert "forked_from: chocolate-chip-cookies" in result
        assert "fork_name: Vegan Version" in result
        assert "author: CJ" in result

    def test_includes_changed_sections(self):
        result = generate_fork_markdown(
            "test", "Fork",
            {"Ingredients": "- flour\n- sugar", "Notes": "- Tasty"},
        )
        assert "## Ingredients" in result
        assert "## Notes" in result
        assert "- flour" in result

    def test_no_author_omitted(self):
        result = generate_fork_markdown("test", "Fork", {"Ingredients": "- flour"})
        assert "author:" not in result


class TestMergeContent:
    def test_fork_section_replaces_base(self):
        base = "# Title\n\n## Ingredients\n\n- flour\n- 2 eggs\n\n## Instructions\n\n1. Mix"
        fork = "## Ingredients\n\n- flour\n- 2 flax eggs"
        merged = merge_content(base, fork)
        assert "2 flax eggs" in merged
        assert "2 eggs" not in merged
        assert "1. Mix" in merged

    def test_base_sections_preserved_when_no_fork(self):
        base = "# Title\n\n## Ingredients\n\n- flour\n\n## Instructions\n\n1. Mix\n\n## Notes\n\n- Good"
        fork = "## Notes\n\n- Even better"
        merged = merge_content(base, fork)
        assert "- flour" in merged
        assert "1. Mix" in merged
        assert "Even better" in merged
        assert "- Good" not in merged

    def test_preamble_from_base(self):
        base = "# My Recipe\n\n## Ingredients\n\n- flour"
        fork = "## Ingredients\n\n- whole wheat flour"
        merged = merge_content(base, fork)
        assert "# My Recipe" in merged


class TestMergeForkIntoBase:
    def test_merges_changed_ingredients(self):
        base = "# Cookies\n\n## Ingredients\n\n- 1 cup butter\n- 2 cups flour\n\n## Instructions\n\n1. Mix\n2. Bake\n"
        fork = "## Ingredients\n\n- 1 cup coconut oil\n- 2 cups flour\n"
        result = merge_fork_into_base(base, fork)
        assert "coconut oil" in result
        assert "butter" not in result
        assert "## Instructions" in result
        assert "Mix" in result

    def test_preserves_preamble(self):
        base = "# Cookies\n\n## Ingredients\n\n- butter\n\n## Notes\n\n- old note\n"
        fork = "## Notes\n\n- new note\n"
        result = merge_fork_into_base(base, fork)
        assert "new note" in result
        assert "old note" not in result
        assert "# Cookies" in result

    def test_no_fork_sections_returns_base(self):
        base = "# Title\n\n## Ingredients\n\n- flour\n"
        result = merge_fork_into_base(base, "")
        assert "flour" in result


class TestGenerateForkMarkdownForkedAtCommit:
    def test_includes_forked_at_commit(self):
        result = generate_fork_markdown(
            "test-recipe", "My Fork",
            {"Ingredients": "- flour"},
            forked_at_commit="abc123def456",
        )
        assert "forked_at_commit: abc123def456" in result

    def test_omits_forked_at_commit_when_none(self):
        result = generate_fork_markdown(
            "test-recipe", "My Fork",
            {"Ingredients": "- flour"},
        )
        assert "forked_at_commit" not in result
