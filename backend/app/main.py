import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.index import RecipeIndex
from app.routes.editor import create_editor_router
from app.routes.recipes import create_recipe_router
from app.watcher import start_watcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(recipes_dir: Optional[Path] = None) -> FastAPI:
    app = FastAPI(title="Forks", version="0.1.0")

    recipes_path = recipes_dir or settings.recipes_dir

    # Build recipe index
    index = RecipeIndex(recipes_path)
    index.build()

    # Register API routes
    app.include_router(create_recipe_router(index))
    app.include_router(create_editor_router(index, recipes_path))

    # Serve recipe images
    images_dir = recipes_path / "images"
    if images_dir.exists():
        app.mount("/api/images", StaticFiles(directory=str(images_dir)), name="images")

    # Start file watcher
    @app.on_event("startup")
    def startup():
        start_watcher(index, recipes_path)

    # Serve frontend static files (in production)
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")

    return app


app = create_app()
