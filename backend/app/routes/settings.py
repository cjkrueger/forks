"""API routes for settings and sync management."""

import logging
from pathlib import Path

from fastapi import APIRouter

from app.enums import RemoteProvider
from app.models import RemoteConfig, SyncConfig, SyncStatus
from app.remote_config import get_config_path, load_config, save_config
from app.sync import SyncEngine

logger = logging.getLogger(__name__)


def create_settings_router(sync_engine: SyncEngine, recipes_dir: Path) -> APIRouter:
    router = APIRouter()

    @router.get("/api/sync/status", response_model=SyncStatus)
    def sync_status():
        return sync_engine.get_status()

    @router.post("/api/sync/trigger")
    def sync_trigger():
        pull_result = sync_engine.pull()
        push_ok = sync_engine.push()
        return {
            "pull_success": pull_result.success,
            "pull_changed": pull_result.changed_files,
            "push_success": push_ok,
        }

    @router.get("/api/settings")
    def get_settings():
        config_path = get_config_path(recipes_dir)
        remote, sync = load_config(config_path)
        redacted_remote = remote.model_copy(update={"token": "***" if remote.token else None})
        return {"remote": redacted_remote.model_dump(), "sync": sync.model_dump()}

    @router.put("/api/settings")
    def save_settings(body: dict):
        config_path = get_config_path(recipes_dir)
        remote = RemoteConfig(**body.get("remote", {}))
        sync = SyncConfig(**body.get("sync", {}))
        save_config(config_path, remote, sync)
        if remote.provider == RemoteProvider.LOCAL and remote.local_path:
            from app.git import git_init_bare, git_remote_add
            git_init_bare(Path(remote.local_path))
            git_remote_add(recipes_dir, remote.local_path)
        elif remote.url:
            from app.git import git_remote_add
            git_remote_add(recipes_dir, remote.url)
        return {"saved": True}

    @router.delete("/api/settings/remote")
    def disconnect_remote():
        config_path = get_config_path(recipes_dir)
        save_config(config_path, RemoteConfig(), SyncConfig())
        return {"disconnected": True}

    return router
