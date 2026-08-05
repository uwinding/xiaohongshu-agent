"""初始化数据库种子数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import csv
import json
from app.database import init_db, SessionLocal
from app.models import BloggerPersona, Product
from app.product_refs import split_product_references


PERSONA_PROFILE_PATH = Path("data/personas/xiaolu/profile.yaml")
PERSONA_FIELDS = (
    "name",
    "age_range",
    "body_type",
    "size_category",
    "height",
    "style_tags",
    "tone_of_voice",
    "avatar_desc",
    "content_focus",
    "avoid_tags",
)


def _compact_text(value: str) -> str:
    return " ".join((value or "").split())


def _open_text_with_fallback(path: str):
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            f = open(path, "r", newline="", encoding=encoding)
            f.read(2048)
            f.seek(0)
            return f
        except UnicodeDecodeError:
            f.close()
    return open(path, "r", newline="", encoding="utf-8", errors="replace")


def _json_or_empty(value: str, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def load_persona_seed_data(profile_path: Path = PERSONA_PROFILE_PATH) -> tuple[dict, list[str]]:
    profile = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError(f"Persona profile must be a mapping: {profile_path}")

    basic = profile.get("basic_profile") or {}
    body = profile.get("body_features") or {}
    outfit = profile.get("outfit_definition") or {}
    voice = profile.get("content_voice") or {}
    image_generation = profile.get("image_generation") or {}

    height_cm = body.get("height_cm")
    tone_parts = [voice.get("tone", ""), voice.get("persona_voice", "")]
    data = {
        "name": profile.get("name", ""),
        "age_range": str(basic.get("age_range", "")),
        "body_type": body.get("body_type", ""),
        "size_category": body.get("size_category", ""),
        "height": f"{height_cm}cm" if height_cm else "",
        "style_tags": outfit.get("style_tags") or [],
        "tone_of_voice": "；".join(part for part in tone_parts if part),
        "avatar_desc": _compact_text(image_generation.get("character_lock_prompt_cn", "")),
        "content_focus": basic.get("content_keywords") or [],
        "avoid_tags": outfit.get("avoid_styles") or [],
    }
    missing = [field for field in ("name", "age_range", "body_type", "height") if not data[field]]
    if missing:
        raise ValueError(f"Persona profile missing required fields: {', '.join(missing)}")
    return data, profile.get("legacy_names") or []


def seed_persona():
    db = SessionLocal()
    try:
        data, legacy_names = load_persona_seed_data()
        lookup_names = [data["name"], *legacy_names]
        payload = {field: data[field] for field in PERSONA_FIELDS}
        existing = (
            db.query(BloggerPersona)
            .filter(BloggerPersona.name.in_(lookup_names))
            .order_by(BloggerPersona.id)
            .first()
        )
        if existing:
            for field, value in payload.items():
                setattr(existing, field, value)
            db.commit()
            print(f"博主 [{data['name']}] 更新成功")
            return
        persona = BloggerPersona(**payload)
        db.add(persona)
        db.commit()
        print(f"博主 [{data['name']}] 导入成功")
    finally:
        db.close()


def seed_products():
    db = SessionLocal()
    created = 0
    updated = 0
    try:
        with _open_text_with_fallback("data/products.csv") as f:
            reader = csv.DictReader(f)
            for row in reader:
                source_url, images = split_product_references(row)
                existing = db.query(Product).filter(Product.name == row["name"]).first()
                if existing:
                    existing.category = row.get("category", "")
                    existing.price = float(row.get("price") or 0)
                    existing.brand = row.get("brand", "")
                    existing.size_available = row.get("size_available", "")
                    existing.source_url = source_url
                    existing.attributes = _json_or_empty(row.get("attributes", "{}"), {})
                    existing.images = images
                    existing.style = row.get("style", "")
                    updated += 1
                    continue
                product = Product(
                    name=row["name"],
                    category=row.get("category", ""),
                    price=float(row.get("price") or 0),
                    brand=row.get("brand", ""),
                    size_available=row.get("size_available", ""),
                    source_url=source_url,
                    attributes=_json_or_empty(row.get("attributes", "{}"), {}),
                    images=images,
                    style=row.get("style", ""),
                )
                db.add(product)
                created += 1
            db.commit()
            print(f"商品库导入成功：新增 {created}，更新 {updated}")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_persona()
    seed_products()
    print("种子数据初始化完成")
