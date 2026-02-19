import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import frontmatter
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.changelog import append_changelog_entry
from app.enums import ChangelogAction
from app.generator import RecipeInput, slugify, generate_markdown
from app.git import git_commit, git_rm
from app.index import RecipeIndex
from app.normalizer import normalize_ingredients
from app.scraper import scrape_recipe, download_image
from app.sections import detect_changed_sections
from app.tagger import auto_tag

logger = logging.getLogger(__name__)


class ScrapeRequest(BaseModel):
    url: str


class ScrapeResponse(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
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
        data["ingredients"] = normalize_ingredients(data.get("ingredients", []))
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
        failed_image_url = None
        if data.image and data.image.startswith("http"):
            ext = _get_image_ext(data.image)
            image_path = recipes_dir / "images" / f"{slug}{ext}"
            if download_image(data.image, image_path):
                image_field = f"images/{slug}{ext}"
            else:
                failed_image_url = data.image
        elif data.image:
            image_field = data.image

        # Normalize ingredients and generate markdown with the local image path
        recipe_data = data.model_copy(update={
            "image": image_field,
            "ingredients": normalize_ingredients(data.ingredients),
        })
        markdown = generate_markdown(recipe_data)
        filepath.write_text(markdown)

        # Append changelog entry and set initial version
        post = frontmatter.load(filepath)
        append_changelog_entry(post, ChangelogAction.CREATED, "Created")
        post.metadata["version"] = 1
        filepath.write_text(frontmatter.dumps(post))

        commit_paths = [filepath]
        if image_field and not image_field.startswith("http"):
            commit_paths.append(recipes_dir / image_field)
        git_commit(recipes_dir, commit_paths, f"Create recipe: {data.title}")

        # Update index
        index.add_or_update(filepath)

        recipe = index.get(slug)
        if failed_image_url:
            data = recipe.model_dump()
            data["_image_failed"] = failed_image_url
            return data
        return recipe

    @router.put("/recipes/{slug}")
    def update_recipe(slug: str, data: RecipeInput):
        filepath = recipes_dir / f"{slug}.md"
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Read old content before overwriting
        old_post = frontmatter.load(filepath)
        old_content = old_post.content

        # Optimistic locking: reject stale writes
        old_version = int(old_post.metadata.get("version", 0))
        if data.version is not None and data.version != old_version:
            raise HTTPException(
                status_code=409,
                detail="Recipe was modified by another user. Please reload and try again.",
            )

        # Handle image
        image_field = None
        failed_image_url = None
        if data.image and data.image.startswith("http"):
            ext = _get_image_ext(data.image)
            image_path = recipes_dir / "images" / f"{slug}{ext}"
            if download_image(data.image, image_path):
                image_field = f"images/{slug}{ext}"
            else:
                failed_image_url = data.image
        elif data.image:
            image_field = data.image

        recipe_data = data.model_copy(update={
            "image": image_field,
            "ingredients": normalize_ingredients(data.ingredients),
        })
        markdown = generate_markdown(recipe_data)
        filepath.write_text(markdown)

        # Detect changed sections and append changelog entry
        new_post = frontmatter.load(filepath)
        new_content = new_post.content
        changed = detect_changed_sections(old_content, new_content)
        if changed:
            summary = "Edited " + ", ".join(changed)
        else:
            summary = "Edited metadata"
        # Carry forward existing changelog from the old post
        new_post.metadata["changelog"] = old_post.metadata.get("changelog", [])
        append_changelog_entry(new_post, ChangelogAction.EDITED, summary)
        new_post.metadata["version"] = old_version + 1
        filepath.write_text(frontmatter.dumps(new_post))

        commit_paths = [filepath]
        if image_field and not image_field.startswith("http"):
            commit_paths.append(recipes_dir / image_field)
        git_commit(recipes_dir, commit_paths, f"Update recipe: {data.title}")

        index.add_or_update(filepath)
        recipe = index.get(slug)
        if failed_image_url:
            data = recipe.model_dump()
            data["_image_failed"] = failed_image_url
            return data
        return recipe

    @router.delete("/recipes/{slug}", status_code=204)
    def delete_recipe(slug: str):
        filepath = recipes_dir / f"{slug}.md"
        if not filepath.exists():
            raise HTTPException(status_code=404, detail="Recipe not found")

        # Collect image paths before deleting
        commit_paths = [filepath]
        images_dir = recipes_dir / "images"
        if images_dir.exists():
            for img in images_dir.glob(f"{slug}.*"):
                commit_paths.append(img)
                img.unlink()

        filepath.unlink()
        git_commit(recipes_dir, commit_paths, f"Delete recipe: {slug}")

        index.remove(slug)

    @router.post("/images/upload")
    async def upload_image(file: UploadFile = File(...)):
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image")

        ext_map = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/gif": ".gif",
        }
        ext = ext_map.get(file.content_type, ".jpg")

        # Use the original filename stem, sanitized
        stem = Path(file.filename or "upload").stem
        safe_stem = slugify(stem) or "upload"
        filename = f"{safe_stem}{ext}"

        images_dir = recipes_dir / "images"
        images_dir.mkdir(exist_ok=True)
        dest = images_dir / filename

        # Avoid overwriting
        counter = 1
        while dest.exists():
            dest = images_dir / f"{safe_stem}-{counter}{ext}"
            counter += 1

        content = await file.read()
        dest.write_bytes(content)
        git_commit(recipes_dir, dest, f"Add image: {dest.name}")

        return {"path": f"images/{dest.name}"}

    return router


def _get_image_ext(url: str) -> str:
    """Extract file extension from image URL, default to .jpg"""
    path = urlparse(url).path
    if "." in path:
        ext = "." + path.rsplit(".", 1)[-1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            return ext
    return ".jpg"
