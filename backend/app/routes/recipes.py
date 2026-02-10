from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.index import RecipeIndex
from app.models import Recipe, RecipeSummary


def create_recipe_router(index: RecipeIndex) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.get("/recipes", response_model=List[RecipeSummary])
    def list_recipes(tags: Optional[str] = Query(None)):
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
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
