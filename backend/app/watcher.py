import logging
import threading
from pathlib import Path
from typing import Dict

from watchdog.events import FileSystemEventHandler, FileSystemEvent
from watchdog.observers import Observer

from app.index import RecipeIndex

logger = logging.getLogger(__name__)


class RecipeEventHandler(FileSystemEventHandler):
    def __init__(self, index: RecipeIndex):
        self.index = index
        self._debounce_timers: Dict[str, threading.Timer] = {}

    def _debounced_update(self, path: Path) -> None:
        key = str(path)
        if key in self._debounce_timers:
            self._debounce_timers[key].cancel()

        timer = threading.Timer(0.5, self._handle_update, args=[path])
        self._debounce_timers[key] = timer
        timer.start()

    def _handle_update(self, path: Path) -> None:
        if path.exists():
            logger.info(f"Recipe updated: {path.name}")
            self.index.add_or_update(path)
        else:
            slug = path.stem
            logger.info(f"Recipe deleted: {slug}")
            self.index.remove(slug)

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix == ".md":
            self._debounced_update(path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix == ".md":
            self._debounced_update(path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix == ".md":
            self._debounced_update(path)


def start_watcher(index: RecipeIndex, recipes_dir: Path) -> Observer:
    """Start watching the recipes directory for changes."""
    handler = RecipeEventHandler(index)
    observer = Observer()
    observer.schedule(handler, str(recipes_dir), recursive=False)
    observer.daemon = True
    observer.start()
    logger.info(f"Watching for recipe changes in {recipes_dir}")
    return observer
