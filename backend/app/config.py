from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    recipes_dir: Path = Path(__file__).resolve().parent.parent.parent / "recipes"
    host: str = "0.0.0.0"
    port: int = 8000
    # Comma-separated list of allowed CORS origins.
    # Defaults to an empty list (same-origin only).
    # Example: FORKS_CORS_ORIGINS="http://localhost:5173,https://myapp.example.com"
    cors_origins: List[str] = []

    model_config = {"env_prefix": "FORKS_"}


settings = Settings()
