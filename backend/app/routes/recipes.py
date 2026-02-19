from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.git import git_log, git_show
from app.index import RecipeIndex
from app.models import Recipe, RecipeSummary
from app.sections import extract_structured_data
from app.validation import validate_slug


def create_recipe_router(index: RecipeIndex) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/recipes/random", response_model=RecipeSummary)
    def random_recipe():
        recipe = index.random()
        if recipe is None:
            raise HTTPException(status_code=404, detail="No recipes available")
        return recipe

    @router.get("/recipes", response_model=List[RecipeSummary])
    def list_recipes(
        tags: Optional[str] = Query(None),
        sort: Optional[str] = Query(None),
    ):
        tag_list = (
            [t.strip() for t in tags.split(",") if t.strip()]
            if tags
            else None
        )

        if sort == "never-cooked":
            return index.filter_never_cooked(tag_list)
        elif sort == "least-recent":
            return index.filter_least_recent(tag_list)
        elif sort == "quick":
            return index.filter_quick(tag_list)

        # Default: no sort filter
        if tag_list:
            return index.filter_by_tags(tag_list)
        return index.list_all()

    @router.get("/recipes/{slug}", response_model=Recipe)
    def get_recipe(slug: str):
        validate_slug(slug)
        recipe = index.get(slug)
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
        structured = extract_structured_data(recipe.content)
        return {**recipe.model_dump(), **structured}

    @router.get("/recipes/{slug}/export")
    def export_recipe(slug: str):
        validate_slug(slug)
        path = index.recipes_dir / f"{slug}.md"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Recipe not found")
        return PlainTextResponse(
            content=path.read_text(),
            headers={"Content-Disposition": f'attachment; filename="{slug}.md"'},
        )

    @router.get("/recipes/{slug}/history")
    def recipe_history(slug: str):
        """Return git history for the base recipe with content at each version."""
        validate_slug(slug)
        path = index.recipes_dir / f"{slug}.md"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Recipe not found")

        entries = git_log(index.recipes_dir, path)
        for entry in entries:
            entry["content"] = git_show(index.recipes_dir, entry["hash"], path)
        return {"history": entries}

    @router.get("/search", response_model=List[RecipeSummary])
    def search_recipes(q: str = Query("")):
        return index.search(q)

    @router.get("/tags")
    def list_tags():
        tags: dict[str, int] = {}
        for recipe in index.list_all():
            for tag in recipe.tags:
                tags[tag] = tags.get(tag, 0) + 1
        return [{"tag": t, "count": c} for t, c in sorted(tags.items())]

    return router
