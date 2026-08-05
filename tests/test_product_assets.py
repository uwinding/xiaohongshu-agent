import json
from pathlib import Path

from app.product_assets import ProductAssetRegistry, product_asset_key, product_item_id


def test_product_item_id_from_tmall_url():
    assert product_item_id("https://detail.tmall.com/item.htm?id=12345&x=1") == "12345"


def test_product_asset_registry_prefers_local_subject_images(tmp_path):
    asset = tmp_path / "dress.webp"
    asset.write_bytes(b"RIFFxxxxWEBPfake")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps({
            "products": {
                "12345": {
                    "subject_images": [str(asset)],
                    "images": [{"path": str(tmp_path / "other.webp")}],
                }
            }
        }),
        encoding="utf-8",
    )
    registry = ProductAssetRegistry(manifest)

    refs = registry.references_for_product({
        "source_url": "https://detail.tmall.com/item.htm?id=12345",
        "images": ["https://img.alicdn.com/imgextra/i1/fallback.jpg"],
    })

    assert refs[0] == str(asset)
    assert refs[-1] == "https://img.alicdn.com/imgextra/i1/fallback.jpg"


def test_product_asset_key_falls_back_to_product_id():
    assert product_asset_key({"id": 9, "name": "鞋"}) == "product-9"
