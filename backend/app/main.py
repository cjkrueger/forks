import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.git import git_init_if_needed
from app.index import RecipeIndex
from app.remote_config import get_config_path
from app.routes.cook import create_cook_router
from app.routes.editor import create_editor_router
from app.routes.forks import create_fork_router
from app.routes.planner import create_planner_router
from app.routes.recipes import create_recipe_router
from app.routes.settings import create_settings_router
from app.routes.stream import create_stream_router
from app.sync import SyncEngine
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
    app.include_router(create_fork_router(index, recipes_path))
    app.include_router(create_cook_router(index, recipes_path))
    config_path = get_config_path(recipes_path)
    app.include_router(create_planner_router(recipes_path, config_path))

    app.include_router(create_stream_router(index, recipes_path))

    sync_engine = SyncEngine(recipes_dir=recipes_path, index=index)
    app.include_router(create_settings_router(sync_engine, recipes_path))

    # Serve recipe images
    images_dir = recipes_path / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/api/images", StaticFiles(directory=str(images_dir)), name="images")

    # Start file watcher
    @app.on_event("startup")
    def startup():
        git_init_if_needed(recipes_path)
        start_watcher(index, recipes_path)

    # Serve frontend static files (in production)
    static_dir = Path(__file__).resolve().parent / "static"
    if static_dir.exists():
        app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")

    return app


app = create_app()
