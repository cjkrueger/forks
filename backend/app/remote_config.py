"""Instance-local configuration for remote sync settings.

Config is stored OUTSIDE the recipes directory so credentials
never get committed to the synced repo.
"""

import json
import logging
import os
from pathlib import Path
from typing import Tuple

from app.models import RemoteConfig, SyncConfig

logger = logging.getLogger(__name__)


def get_config_path(recipes_dir: Path) -> Path:
    """Return the config file path. Respects FORKS_CONFIG_PATH env var."""
    env = os.environ.get("FORKS_CONFIG_PATH")
    if env:
        return Path(env)
    return recipes_dir.parent / ".forks-config.json"


def load_config(config_path: Path) -> Tuple[RemoteConfig, SyncConfig]:
    """Load config from file. Returns defaults if file doesn't exist."""
    if not config_path.exists():
        return RemoteConfig(), SyncConfig()
    try:
        data = json.loads(config_path.read_text())
        remote = RemoteConfig(**data.get("remote", {}))
        sync = SyncConfig(**data.get("sync", {}))
        return remote, sync
    except Exception:
        logger.exception("Failed to load config from %s", config_path)
        return RemoteConfig(), SyncConfig()


def save_config(config_path: Path, remote: RemoteConfig, sync: SyncConfig) -> None:
    """Write config to file. Creates parent directories if needed."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "remote": remote.model_dump(exclude_none=False),
        "sync": sync.model_dump(),
    }
    config_path.write_text(json.dumps(data, indent=2))
