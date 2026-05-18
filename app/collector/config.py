from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import List
import yaml


class CollectorConfig(BaseSettings):
    headless: bool = True
    max_concurrency: int = 3
    retry_times: int = 3
    page_timeout: int = 30000
    max_notes_per_keyword: int = 50
    storage_state_path: str = "data/storage_state.json"
    output_dir: str = "data/output"
    raw_dir: str = "data/raw"
    xhs_domain: str = "https://www.xiaohongshu.com"
    xhs_api_host: str = "https://edith.xiaohongshu.com"

    model_config = {"env_file": ".env", "env_prefix": "COLLECTOR_", "extra": "ignore"}


def load_keywords(path: str = "data/keywords.yaml") -> List[str]:
    p = Path(path)
    if not p.exists():
        return ["穿搭"]
    with open(p, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("keywords", ["穿搭"]) if data else ["穿搭"]
