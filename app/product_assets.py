"""Local product asset registry for reference-preserving generation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from app.config import get_settings
from app.product_refs import is_direct_image_reference, parse_reference_list


def product_item_id(source_url: str) -> str:
    parsed = urlparse(source_url or "")
    query = parse_qs(parsed.query)
    if query.get("id"):
        return query["id"][0]
    match = re.search(r"[?&]id=(\d+)", source_url or "")
    return match.group(1) if match else ""


def product_asset_key(product: dict) -> str:
    item_id = product_item_id(product.get("source_url", ""))
    if item_id:
        return item_id
    product_id = product.get("id")
    if product_id:
        return f"product-{product_id}"
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", str(product.get("name", "product"))).strip("-") or "product"


class ProductAssetRegistry:
    def __init__(self, manifest_path: str | Path | None = None):
        settings = get_settings()
        self.manifest_path = Path(manifest_path or settings.product_assets_manifest)
        self._manifest: dict | None = None

    def load(self) -> dict:
        if self._manifest is None:
            if self.manifest_path.exists():
                self._manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            else:
                self._manifest = {"products": {}}
        return self._manifest

    def references_for_product(self, product: dict) -> list[str]:
        manifest = self.load()
        entry = manifest.get("products", {}).get(product_asset_key(product), {})
        refs = []

        for path in entry.get("subject_images", []):
            if path and Path(path).exists() and path not in refs:
                refs.append(path)
        for asset in entry.get("images", []):
            path = asset.get("path", "") if isinstance(asset, dict) else str(asset)
            if path and Path(path).exists() and path not in refs:
                refs.append(path)

        for ref in parse_reference_list(product.get("images")):
            if is_direct_image_reference(ref) and ref not in refs:
                refs.append(ref)
        return refs

    def has_assets_for_product(self, product: dict) -> bool:
        return bool(self.references_for_product(product))
