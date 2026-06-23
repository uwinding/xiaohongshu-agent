"""XHS hot content collector package."""

from app.collector.config import CollectorConfig, load_keywords

__all__ = ["CollectorConfig", "load_keywords", "run_collect"]


def run_collect(*args, **kwargs):
    from app.collector.runner import run_collect as _run_collect

    return _run_collect(*args, **kwargs)
