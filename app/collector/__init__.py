"""XHS hot content collector package."""

from app.collector.config import CollectorConfig, load_keywords
from app.collector.runner import run_collect

__all__ = ["CollectorConfig", "load_keywords", "run_collect"]
