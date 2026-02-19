from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    recipes_dir: Path = Path(__file__).resolve().parent.parent.parent / "recipes"
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS origins — comma-separated list of allowed origins.
    # Defaults to ["*"] which is fine for a self-hosted home server.
    # To restrict access, set FORKS_CORS_ORIGINS="http://192.168.1.10:3000,http://forks.local"
    cors_origins: List[str] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = {"env_prefix": "FORKS_"}


settings = Settings()
