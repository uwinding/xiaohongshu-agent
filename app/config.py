from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    image_api_key: str = ""
    image_base_url: str = "https://api.openai.com/v1"
    image_model: str = "dall-e-3"
    image_size: str = ""
    database_url: str = "sqlite:///./data/agent.db"
    storage_dir: str = "./storage/images"
    product_assets_dir: str = "./data/product_assets"
    product_assets_manifest: str = "./data/product_assets/manifest.json"
    persona_profile_path: str = "./data/personas/xiaolu/profile.yaml"
    image_quality_reports_dir: str = "./data/quality_reports"
    vision_quality_enabled: bool = False
    vision_api_key: str = ""
    vision_base_url: str = "https://api.openai.com/v1"
    vision_model: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
