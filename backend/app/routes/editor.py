import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.generator import RecipeInput, slugify, generate_markdown
from app.index import RecipeIndex
from app.scraper import scrape_recipe, download_image
from app.tagger import auto_tag

logger = logging.getLogger(__name__)


class ScrapeRequest(BaseModel):
    url: str


class ScrapeResponse(BaseModel):
    title: Optional[str] = None
    tags: list = []
    ingredients: list = []
    instructions: list = []
    prep_time: Optional[str] = None
    cook_time: Optional[str] = None
    total_time: Optional[str] = None
    servings: Optional[str] = None
    image_url: Optional[str] = None
    source: str = ""
    notes: Optional[str] = None


def create_editor_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/scrape", response_model=ScrapeResponse)
    def scrape(req: ScrapeRequest):
        data = scrape_recipe(req.url)
        if not data.get("title"):
            raise HTTPException(status_code=422, detail="Could not extract recipe from URL")
        data["tags"] = auto_tag(
            title=data.get("title", ""),
            ingredients=data.get("ingredients", []),
            prep_time=data.get("prep_time"),
            cook_time=data.get("cook_time"),
            total_time=data.get("total_time"),
        )
        return data

    @router.post("/recipes", status_code=201)
    def create_recipe(data: RecipeInput):
        slug = slugify(data.title)
        if not slug:
            raise HTTPException(status_code=400, detail="Invalid recipe title")

        filepath = recipes_dir / f"{slug}.md"
        if filepath.exists():
            raise HTTPException(status_code=409, detail=f"Recipe '{slug}' already exists")

        # Download image if provided
        image_field = None
        if data.image and data.image.startswith("http"):
            # This is a URL to download
            ext = _get_image_ext(data.image)
            image_path = recipes_dir / "images" / f"{slug}{ext}"
            if download_image(data.image, image_path):
                image_field = f"images/{slug}{ext}"
        elif data.image:
            image_field = data.image

        # Generate markdown with the local image path
        recipe_data = data.model_copy(update={"image": image_field})
        markdown = generate_markdown(recipe_data)
        filepath.write_text(markdown)

        # Update index
        index.add_or_update(filepath)

        return index.get(slug)

    @router.put("/recipes/{slug}")
    def update_recipe(slug: str, data: RecipeInput):
        filepath = recipes_dir / f"{slug}.md"
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Handle image
        image_field = None
        if data.image and data.image.startswith("http"):
            ext = _get_image_ext(data.image)
            image_path = recipes_dir / "images" / f"{slug}{ext}"
            if download_image(data.image, image_path):
                image_field = f"images/{slug}{ext}"
        elif data.image:
            image_field = data.image

        recipe_data = data.model_copy(update={"image": image_field})
        markdown = generate_markdown(recipe_data)
        filepath.write_text(markdown)

        index.add_or_update(filepath)
        return index.get(slug)

    @router.delete("/recipes/{slug}", status_code=204)
    def delete_recipe(slug: str):
        filepath = recipes_dir / f"{slug}.md"
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Recipe not found")

        filepath.unlink()

        # Also delete image if it exists
        images_dir = recipes_dir / "images"
        if images_dir.exists():
            for img in images_dir.glob(f"{slug}.*"):
                img.unlink()

        index.remove(slug)

    return router


def _get_image_ext(url: str) -> str:
    """Extract file extension from image URL, default to .jpg"""
    path = urlparse(url).path
    if "." in path:
        ext = "." + path.rsplit(".", 1)[-1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            return ext
    return ".jpg"
