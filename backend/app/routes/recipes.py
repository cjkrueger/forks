from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.index import RecipeIndex
from app.models import Recipe, RecipeSummary


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
        recipe = index.get(slug)
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found")
        return recipe

    @router.get("/search", response_model=List[RecipeSummary])
    def search_recipes(q: str = Query("")):
        return index.search(q)

    return router
