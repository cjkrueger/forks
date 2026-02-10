from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    recipes_dir: Path = Path(__file__).resolve().parent.parent.parent / "recipes"
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_prefix": "FORKS_"}


settings = Settings()
