"""Prepare local product assets for reference-preserving image generation.

This first version is dependency-light: it downloads product images from
products.csv and writes a manifest. If Pillow/segmentation is added later,
the same manifest shape can point to true transparent cutouts/masks.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import mimetypes
import re
from datetime import datetime, timezone
from pathlib import Path

import requests

from app.config import get_settings
from app.product_assets import product_asset_key, product_item_id
from app.product_refs import is_direct_image_reference, parse_reference_list


CSV_HEADERS = [
    "name", "category", "price", "brand", "size_available",
    "source_url", "attributes", "style", "images",
]


def _open_csv_with_fallback(path: Path):
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            f = path.open(newline="", encoding=encoding)
            f.read(2048)
            f.seek(0)
            return f
        except UnicodeDecodeError:
            f.close()
    return path.open(newline="", encoding="utf-8", errors="replace")


def _read_products(path: Path) -> list[dict]:
    with _open_csv_with_fallback(path) as f:
        return list(csv.DictReader(f))


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value or "product").strip("-")[:80] or "product"


def _extension_from_response(resp, url: str) -> str:
    content_type = (resp.headers.get("content-type") or "").split(";", 1)[0].lower()
    ext = mimetypes.guess_extension(content_type) if content_type else ""
    if ext in {".jpe", ".jpeg"}:
        return ".jpg"
    if ext:
        return ext
    suffix = Path(url.split("?", 1)[0]).suffix.lower()
    return suffix if suffix in {".jpg", ".jpeg", ".png", ".webp"} else ".jpg"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _download_image(url: str, dest_dir: Path, index: int, timeout: int = 30) -> dict | None:
    if not is_direct_image_reference(url):
        return None
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    resp.raise_for_status()
    content_type = (resp.headers.get("content-type") or "").lower()
    if content_type and not content_type.startswith("image/"):
        return None
    data = resp.content
    digest = _sha256(data)
    ext = _extension_from_response(resp, url)
    path = dest_dir / f"ref_{index:02d}_{digest[:10]}{ext}"
    path.write_bytes(data)
    return {
        "url": url,
        "path": str(path),
        "sha256": digest,
        "bytes": len(data),
        "content_type": content_type,
    }


def _visual_signature(row: dict, image_count: int) -> dict:
    attrs = {}
    try:
        attrs = json.loads(row.get("attributes") or "{}")
    except json.JSONDecodeError:
        attrs = {}
    text = " ".join([
        row.get("name", ""),
        row.get("category", ""),
        row.get("style", ""),
        " ".join(str(v) for v in attrs.values()),
    ])
    signature = {
        "category": row.get("category", ""),
        "color": attrs.get("color", ""),
        "fit": attrs.get("fit", ""),
        "material": attrs.get("material") or attrs.get("fabric", ""),
        "style": row.get("style", ""),
        "image_count": image_count,
    }
    if row.get("category") == "鞋包配饰":
        signature["shoe_type"] = "mule" if "穆勒" in text else "toe-post" if "夹脚" in text else ""
        signature["heel"] = "high heel" if "高跟" in text else "flat" if "平底" in text else ""
        signature["decor"] = "floral applique" if "贴花" in text else "metal decor" if "金属" in text else ""
    return signature


def _prepare_subject_images(downloaded: list[dict], limit: int = 3) -> list[str]:
    """Create cutout-like subject images when Pillow is available.

    Without Pillow/segmentation, this safely falls back to raw product refs.
    """
    try:
        from PIL import Image
    except Exception:
        return [asset["path"] for asset in downloaded[:limit]]

    subjects = []
    for asset in downloaded[:limit]:
        src = Path(asset["path"])
        try:
            img = Image.open(src).convert("RGBA")
            bbox = _foreground_bbox_from_white_bg(img)
            if bbox:
                img = img.crop(bbox)
            img = _remove_near_white_background(img)
            dest = src.with_name(src.stem.replace("ref_", "subject_") + ".png")
            img.save(dest)
            subjects.append(str(dest))
        except Exception:
            subjects.append(str(src))
    return subjects


def _foreground_bbox_from_white_bg(img) -> tuple[int, int, int, int] | None:
    pixels = img.load()
    width, height = img.size
    xs = []
    ys = []
    for y in range(0, height, max(1, height // 300)):
        for x in range(0, width, max(1, width // 300)):
            r, g, b, a = pixels[x, y]
            if a > 0 and not (r > 245 and g > 245 and b > 245):
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return None
    pad = 24
    return max(0, min(xs) - pad), max(0, min(ys) - pad), min(width, max(xs) + pad), min(height, max(ys) + pad)


def _remove_near_white_background(img):
    pixels = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]
            if r > 248 and g > 248 and b > 248:
                pixels[x, y] = (r, g, b, 0)
    return img


def extract_assets(products_csv: Path, assets_dir: Path, manifest_path: Path, max_images: int = 6) -> dict:
    rows = _read_products(products_csv)
    assets_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "products_csv": str(products_csv),
        "products": {},
    }

    for row in rows:
        product = {
            "id": row.get("id", ""),
            "name": row.get("name", ""),
            "source_url": row.get("source_url", ""),
        }
        key = product_asset_key(product)
        item_id = product_item_id(row.get("source_url", ""))
        product_dir = assets_dir / _safe_name(key)
        product_dir.mkdir(parents=True, exist_ok=True)

        image_urls = [u for u in parse_reference_list(row.get("images")) if is_direct_image_reference(u)]
        downloaded = []
        seen_hashes = set()
        for url in image_urls[:max_images]:
            try:
                asset = _download_image(url, product_dir, len(downloaded) + 1)
            except Exception as exc:
                print(f"WARN: download failed for {row.get('name')}: {exc}")
                continue
            if not asset or asset["sha256"] in seen_hashes:
                continue
            seen_hashes.add(asset["sha256"])
            downloaded.append(asset)

        subject_images = _prepare_subject_images(downloaded[:3])
        manifest["products"][key] = {
            "key": key,
            "item_id": item_id,
            "name": row.get("name", ""),
            "category": row.get("category", ""),
            "source_url": row.get("source_url", ""),
            "asset_dir": str(product_dir),
            "images": downloaded,
            "subject_images": subject_images,
            "mask_images": [],
            "visual_signature": _visual_signature(row, len(downloaded)),
            "quality_score": round(min(1.0, len(downloaded) / max(1, max_images)), 2),
            "notes": "subject_images are transparent cutouts when Pillow is available; otherwise raw product refs",
        }
        print(f"{row.get('name')}: downloaded {len(downloaded)} images")

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"manifest written: {manifest_path}")
    return manifest


def main() -> None:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Download and prepare local product assets")
    parser.add_argument("--products-csv", default="data/products.csv")
    parser.add_argument("--assets-dir", default=settings.product_assets_dir)
    parser.add_argument("--manifest", default=settings.product_assets_manifest)
    parser.add_argument("--max-images", type=int, default=6)
    args = parser.parse_args()

    extract_assets(
        products_csv=Path(args.products_csv),
        assets_dir=Path(args.assets_dir),
        manifest_path=Path(args.manifest),
        max_images=args.max_images,
    )


if __name__ == "__main__":
    main()
