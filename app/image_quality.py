"""Basic generated-image quality checks.

This module intentionally avoids heavy CV dependencies. It validates reference
coverage, generated file health, and prompt constraints, and produces a report
that can gate manual review. A vision-model scorer can replace/extend it later.
"""

from __future__ import annotations

import json
import base64
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings
from app.product_assets import ProductAssetRegistry
from app.product_refs import is_direct_image_reference, parse_reference_list


def _image_size(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()[:4096]
    if data.startswith(b"\x89PNG\r\n\x1a\n") and len(data) >= 24:
        return int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
    if data.startswith(b"\xff\xd8"):
        raw = path.read_bytes()
        i = 2
        while i + 9 < len(raw):
            if raw[i] != 0xFF:
                i += 1
                continue
            marker = raw[i + 1]
            if marker in {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}:
                return int.from_bytes(raw[i + 7:i + 9], "big"), int.from_bytes(raw[i + 5:i + 7], "big")
            length = int.from_bytes(raw[i + 2:i + 4], "big")
            i += 2 + max(length, 2)
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        # Minimal VP8X parser.
        if data[12:16] == b"VP8X" and len(data) >= 30:
            width = int.from_bytes(data[24:27] + b"\x00", "little") + 1
            height = int.from_bytes(data[27:30] + b"\x00", "little") + 1
            return width, height
    return None


class ImageQualityChecker:
    def __init__(self, reports_dir: str | Path | None = None, asset_registry: ProductAssetRegistry | None = None):
        settings = get_settings()
        self.reports_dir = Path(reports_dir or settings.image_quality_reports_dir)
        self.asset_registry = asset_registry or ProductAssetRegistry()

    def evaluate(
        self,
        image_paths: list[str],
        products: list[dict],
        reference_images: list[str],
        prompt: str,
        post_id: int | None = None,
    ) -> dict:
        settings = get_settings()
        file_reports = [self._check_file(path) for path in image_paths]
        product_reports = [self._check_product(product) for product in products]
        issues = []

        if not image_paths:
            issues.append("未生成图片")
        if any(not item["exists"] for item in file_reports):
            issues.append("生成图片文件缺失")
        if any(item.get("width", 0) < 1024 or item.get("height", 0) < 1024 for item in file_reports if item["exists"]):
            issues.append("生成图分辨率偏低")

        accessory_products = [p for p in products if p.get("category") == "鞋包配饰"]
        if accessory_products and "same shoes on both feet" not in prompt:
            issues.append("鞋款一致性 prompt 约束缺失")
        if accessory_products and len([r for r in reference_images if r]) < 2:
            issues.append("鞋包参考图数量不足")

        vision_report = self._vision_similarity_report(image_paths, products, reference_images, settings)
        if accessory_products and not vision_report.get("enabled"):
            issues.append("未启用视觉相似度质检，鞋款需要人工复核")
        if vision_report.get("enabled") and vision_report.get("score", 1.0) < 0.75:
            issues.append("视觉相似度低于阈值")

        products_with_refs = sum(1 for item in product_reports if item["reference_count"] > 0)
        products_with_assets = sum(1 for item in product_reports if item["asset_reference_count"] > 0)
        ref_coverage = products_with_refs / max(1, len(products))
        asset_coverage = products_with_assets / max(1, len(products))
        prompt_score = 1.0 if not accessory_products or "mismatched shoes" in prompt else 0.6
        file_score = 1.0 if file_reports and all(item["exists"] and item.get("width", 0) >= 1024 for item in file_reports) else 0.0
        base_score = 0.35 * file_score + 0.30 * ref_coverage + 0.20 * asset_coverage + 0.15 * prompt_score
        if vision_report.get("enabled"):
            score = round(0.55 * base_score + 0.45 * vision_report.get("score", 0), 2)
        else:
            score = round(min(base_score, 0.74) if accessory_products else base_score, 2)

        if score < 0.75:
            issues.append("质检分低于阈值")

        report = {
            "post_id": post_id,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "score": score,
            "needs_review": bool(issues),
            "issues": issues,
            "image_files": file_reports,
            "products": product_reports,
            "vision_similarity": vision_report,
            "reference_count": len(reference_images),
            "reference_images": reference_images,
            "limitations": "当前为无视觉模型基础质检，不能直接判断 SKU 像素级相似度",
        }
        if post_id is not None:
            self.write_report(report, post_id)
        return report

    def write_report(self, report: dict, post_id: int) -> Path:
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        path = self.reports_dir / f"post_{post_id}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _check_file(self, image_path: str) -> dict:
        path = Path(image_path)
        report = {"path": image_path, "exists": path.exists()}
        if not path.exists():
            return report
        report["bytes"] = path.stat().st_size
        size = _image_size(path)
        if size:
            report["width"], report["height"] = size
        return report

    def _check_product(self, product: dict) -> dict:
        direct_refs = [ref for ref in parse_reference_list(product.get("images")) if is_direct_image_reference(ref)]
        asset_refs = self.asset_registry.references_for_product(product)
        return {
            "id": product.get("id"),
            "name": product.get("name"),
            "category": product.get("category"),
            "reference_count": len(direct_refs),
            "asset_reference_count": len([ref for ref in asset_refs if Path(ref).exists()]),
        }

    def _vision_similarity_report(self, image_paths: list[str], products: list[dict], reference_images: list[str], settings) -> dict:
        if not settings.vision_quality_enabled:
            return {"enabled": False, "reason": "VISION_QUALITY_ENABLED is false"}
        if not settings.vision_api_key or not settings.vision_model:
            return {"enabled": False, "reason": "VISION_API_KEY or VISION_MODEL missing"}
        if not image_paths or not reference_images:
            return {"enabled": False, "reason": "missing generated image or reference image"}

        ref_path = next((Path(ref) for ref in reference_images if Path(ref).exists()), None)
        gen_path = Path(image_paths[0])
        if not ref_path or not gen_path.exists():
            return {"enabled": False, "reason": "local generated/reference image unavailable"}

        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.vision_api_key, base_url=settings.vision_base_url, timeout=60.0)
            product_names = "、".join(str(p.get("name", "")) for p in products)
            prompt = (
                "你是电商穿搭图质检员。请对比商品参考图和生成图，判断商品是否被正确还原。"
                "重点检查：品类、颜色、版型、图案、鞋型、双脚鞋是否一致、是否有水印文字。"
                "输出严格 JSON：score(0到1), issues(字符串数组), needs_review(boolean)。"
                f"商品：{product_names}"
            )
            resp = client.chat.completions.create(
                model=settings.vision_model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": self._data_url(ref_path)}},
                        {"type": "image_url", "image_url": {"url": self._data_url(gen_path)}},
                    ],
                }],
                temperature=0.0,
                max_tokens=300,
            )
            content = (resp.choices[0].message.content or "").strip()
            content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(content)
            return {
                "enabled": True,
                "score": float(parsed.get("score", 0)),
                "issues": parsed.get("issues", []),
                "needs_review": bool(parsed.get("needs_review", False)),
            }
        except Exception as exc:
            return {"enabled": False, "reason": f"vision check failed: {exc}"}

    def _data_url(self, path: Path) -> str:
        data = path.read_bytes()
        suffix = path.suffix.lower()
        mime = "image/webp" if suffix == ".webp" else "image/png" if suffix == ".png" else "image/jpeg"
        return f"data:{mime};base64,{base64.b64encode(data).decode('utf-8')}"
