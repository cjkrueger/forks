"""Tests for fork indexing."""
import textwrap
from pathlib import Path

from app.index import RecipeIndex


def _write_recipe(path: Path, title: str, ingredients: str = "- flour"):
    path.write_text(textwrap.dedent(f"""\
        ---
        title: {title}
        tags: [test]
        ---

        # {title}

        ## Ingredients

        {ingredients}

        ## Instructions

        1. Mix everything
    """))


def _write_fork(path: Path, forked_from: str, fork_name: str, ingredients: str):
    path.write_text(textwrap.dedent(f"""\
        ---
        forked_from: {forked_from}
        fork_name: {fork_name}
        author: Test
        ---

        ## Ingredients

        {ingredients}
    """))


class TestForkIndexing:
    def test_fork_files_not_listed_as_recipes(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        _write_fork(tmp_path / "cookies.fork.vegan.md", "cookies", "Vegan Cookies", "- coconut oil")
        index = RecipeIndex(tmp_path)
        index.build()
        recipes = index.list_all()
        assert len(recipes) == 1
        assert recipes[0].slug == "cookies"

    def test_forks_attached_to_base_recipe(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        _write_fork(tmp_path / "cookies.fork.vegan.md", "cookies", "Vegan Cookies", "- coconut oil")
        _write_fork(tmp_path / "cookies.fork.gf.md", "cookies", "Gluten Free Cookies", "- gf flour")
        index = RecipeIndex(tmp_path)
        index.build()
        recipe = index.list_all()[0]
        assert len(recipe.forks) == 2
        fork_names = [f.name for f in recipe.forks]
        assert "vegan" in fork_names
        assert "gf" in fork_names

    def test_fork_summary_fields(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        _write_fork(tmp_path / "cookies.fork.vegan.md", "cookies", "Vegan Cookies", "- coconut oil")
        index = RecipeIndex(tmp_path)
        index.build()
        fork = index.list_all()[0].forks[0]
        assert fork.name == "vegan"
        assert fork.fork_name == "Vegan Cookies"
        assert fork.author == "Test"

    def test_add_fork_updates_index(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        index = RecipeIndex(tmp_path)
        index.build()
        assert len(index.list_all()[0].forks) == 0
        fork_path = tmp_path / "cookies.fork.vegan.md"
        _write_fork(fork_path, "cookies", "Vegan Cookies", "- coconut oil")
        index.add_or_update(fork_path)
        assert len(index.list_all()[0].forks) == 1

    def test_remove_fork_updates_index(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        _write_fork(tmp_path / "cookies.fork.vegan.md", "cookies", "Vegan Cookies", "- coconut oil")
        index = RecipeIndex(tmp_path)
        index.build()
        assert len(index.list_all()[0].forks) == 1
        index.remove("cookies.fork.vegan")
        assert len(index.list_all()[0].forks) == 0

    def test_recipe_without_forks_has_empty_list(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        index = RecipeIndex(tmp_path)
        index.build()
        assert index.list_all()[0].forks == []

    def test_get_recipe_includes_forks(self, tmp_path):
        _write_recipe(tmp_path / "cookies.md", "Cookies")
        _write_fork(tmp_path / "cookies.fork.vegan.md", "cookies", "Vegan Cookies", "- coconut oil")
        index = RecipeIndex(tmp_path)
        index.build()
        recipe = index.get("cookies")
        assert recipe is not None
        assert len(recipe.forks) == 1
