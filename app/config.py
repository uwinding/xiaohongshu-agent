from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    image_api_key: str = ""
    image_base_url: str = "https://api.openai.com/v1"
    image_model: str = "dall-e-3"
    database_url: str = "sqlite:///./data/agent.db"
    storage_dir: str = "./storage/images"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
