from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    recipes_dir: Path = Path(__file__).resolve().parent.parent.parent / "recipes"
    host: str = "0.0.0.0"
    port: int = 8000
    # Comma-separated list of allowed CORS origins.
    # Defaults to localhost only. Set FORKS_CORS_ORIGINS to override.
    # Example: FORKS_CORS_ORIGINS="https://myapp.example.com,https://other.example.com"
    cors_origins: List[str] = ["http://localhost", "http://localhost:5173", "http://localhost:3000"]

    model_config = {"env_prefix": "FORKS_"}


settings = Settings()
