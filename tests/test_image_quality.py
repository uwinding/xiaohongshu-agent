import json

from app.image_quality import ImageQualityChecker
from app.product_assets import ProductAssetRegistry


def _minimal_jpeg(width: int = 1536, height: int = 2560) -> bytes:
    return (
        b"\xff\xd8"
        b"\xff\xc0"
        + (17).to_bytes(2, "big")
        + b"\x08"
        + height.to_bytes(2, "big")
        + width.to_bytes(2, "big")
        + b"\x03\x01\x11\x00\x02\x11\x00\x03\x11\x00"
        + b"\xff\xd9"
    )


def test_image_quality_checker_writes_report(tmp_path):
    image = tmp_path / "generated.jpg"
    image.write_bytes(_minimal_jpeg())
    manifest = tmp_path / "manifest.json"
    asset = tmp_path / "shoe.webp"
    asset.write_bytes(b"RIFFxxxxWEBPfake")
    manifest.write_text(
        json.dumps({"products": {"123": {"subject_images": [str(asset)], "images": []}}}),
        encoding="utf-8",
    )
    checker = ImageQualityChecker(
        reports_dir=tmp_path / "reports",
        asset_registry=ProductAssetRegistry(manifest),
    )

    report = checker.evaluate(
        image_paths=[str(image)],
        products=[{
            "id": 1,
            "name": "金色穆勒鞋",
            "category": "鞋包配饰",
            "source_url": "https://detail.tmall.com/item.htm?id=123",
            "images": ["https://img.alicdn.com/imgextra/i1/shoe.jpg"],
        }],
        reference_images=[str(asset), "https://img.alicdn.com/imgextra/i1/shoe.jpg"],
        prompt="same shoes on both feet, mismatched shoes",
        post_id=7,
    )

    assert report["score"] == 0.74
    assert report["needs_review"]
    assert "未启用视觉相似度质检，鞋款需要人工复核" in report["issues"]
    assert report["image_files"][0]["width"] == 1536
    assert (tmp_path / "reports" / "post_7.json").exists()
