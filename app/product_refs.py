"""Helpers for normalizing product source and image references."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse


_IMAGE_EXT_RE = re.compile(r"\.(?:jpg|jpeg|png|webp|gif)(?:$|[?_])", re.I)
_URL_SPLIT_RE = re.compile(r"[\n\r|;]+")
_IMAGE_HOST_HINTS = (
    "img.alicdn.com",
    "gw.alicdn.com",
    "g-search.alicdn.com",
    "tbcdn.cn",
)
_PRODUCT_PAGE_HOSTS = (
    "detail.tmall.com",
    "item.taobao.com",
    "world.taobao.com",
    "detail.1688.com",
)


def normalize_reference(src: str) -> str:
    src = (src or "").strip()
    if src.startswith("//"):
        return "https:" + src
    return src


def parse_reference_list(value) -> list[str]:
    """Parse JSON arrays, plain URLs, or pipe/newline separated references."""
    if not value:
        return []
    if isinstance(value, list):
        refs = []
        for item in value:
            refs.extend(parse_reference_list(item))
        return refs
    if not isinstance(value, str):
        return []

    text = value.strip()
    if not text:
        return []

    try:
        loaded = json.loads(text)
    except json.JSONDecodeError:
        loaded = None
    if loaded is not None:
        return parse_reference_list(loaded)

    refs = []
    for part in _URL_SPLIT_RE.split(text):
        ref = normalize_reference(part)
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def is_product_page_url(src: str) -> bool:
    src = normalize_reference(src)
    if not src.startswith(("http://", "https://")):
        return False
    parsed = urlparse(src)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    return any(h in host for h in _PRODUCT_PAGE_HOSTS) or path.endswith("/item.htm")


def is_direct_image_reference(src: str) -> bool:
    src = normalize_reference(src)
    if not src:
        return False
    if src.startswith(("http://", "https://")):
        if is_product_page_url(src):
            return False
        host = urlparse(src).netloc.lower()
        return bool(_IMAGE_EXT_RE.search(src)) or any(h in host for h in _IMAGE_HOST_HINTS)
    return Path(src).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def split_product_references(row: dict) -> tuple[str, list[str]]:
    """Return (source_url, direct_image_refs) from a products.csv row."""
    source_url = (row.get("source_url") or "").strip()
    refs = parse_reference_list(row.get("images"))
    images = [ref for ref in refs if is_direct_image_reference(ref)]

    if not source_url:
        for ref in refs:
            if is_product_page_url(ref):
                source_url = ref
                break

    return source_url, images
