import logging
from datetime import date
from pathlib import Path
from typing import Optional

import frontmatter
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.git import git_commit
from app.index import RecipeIndex

logger = logging.getLogger(__name__)


class CookHistoryInput(BaseModel):
    fork: Optional[str] = None


def create_cook_router(index: RecipeIndex, recipes_dir: Path) -> APIRouter:
    router = APIRouter(prefix="/api/recipes/{slug}")

    def _load_post(slug: str):
        path = recipes_dir / f"{slug}.md"
        if not path.exists():
            raise HTTPException(status_code=404, detail="Recipe not found")
        return path, frontmatter.load(path)

    def _save(path: Path, post) -> None:
        path.write_text(frontmatter.dumps(post))
        index.add_or_update(path)

    @router.post("/cook-history", status_code=201)
    def add_cook_history(slug: str, data: CookHistoryInput):
        path, post = _load_post(slug)
        today = str(date.today())

        history = post.metadata.get("cook_history", [])
        if not isinstance(history, list):
            history = []

        # Deduplicate: same date + fork
        for entry in history:
            if isinstance(entry, dict):
                if entry.get("date") == today and entry.get("fork") == data.fork:
                    return {"cook_history": history}
            elif isinstance(entry, str) and entry == today and data.fork is None:
                return {"cook_history": history}

        new_entry = {"date": today}
        if data.fork:
            new_entry["fork"] = data.fork
        history.insert(0, new_entry)

        post.metadata["cook_history"] = history
        _save(path, post)
        git_commit(recipes_dir, path, f"Log cook: {slug}")
        return {"cook_history": history}

    @router.delete("/cook-history/{entry_index}")
    def delete_cook_history(slug: str, entry_index: int):
        path, post = _load_post(slug)
        history = post.metadata.get("cook_history", [])
        if not isinstance(history, list):
            history = []

        if entry_index < 0 or entry_index >= len(history):
            raise HTTPException(status_code=404, detail="Cook history entry not found")

        history.pop(entry_index)
        post.metadata["cook_history"] = history
        _save(path, post)
        git_commit(recipes_dir, path, f"Delete cook entry: {slug}")
        return {"cook_history": history}

    @router.post("/favorite", status_code=200)
    def add_favorite(slug: str):
        path, post = _load_post(slug)
        tags = post.metadata.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        if "favorite" not in tags:
            tags.append("favorite")
            post.metadata["tags"] = tags
            _save(path, post)
            git_commit(recipes_dir, path, f"Favorite: {slug}")

        return {"favorited": True}

    @router.delete("/favorite")
    def remove_favorite(slug: str):
        path, post = _load_post(slug)
        tags = post.metadata.get("tags", [])
        if not isinstance(tags, list):
            tags = []

        if "favorite" in tags:
            tags = [t for t in tags if t != "favorite"]
            post.metadata["tags"] = tags
            _save(path, post)
            git_commit(recipes_dir, path, f"Unfavorite: {slug}")

        return {"favorited": False}

    @router.post("/like", status_code=200)
    def like_recipe(slug: str):
        path, post = _load_post(slug)
        current = int(post.metadata.get("likes", 0))
        current += 1
        post.metadata["likes"] = current
        _save(path, post)
        git_commit(recipes_dir, path, f"Like: {slug}")
        return {"likes": current}

    return router
