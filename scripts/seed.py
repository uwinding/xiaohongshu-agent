"""初始化数据库种子数据"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yaml
import csv
import json
from app.database import init_db, SessionLocal
from app.models import BloggerPersona, Product


def seed_persona():
    db = SessionLocal()
    try:
        with open("data/persona.yaml", "r") as f:
            data = yaml.safe_load(f)
        existing = db.query(BloggerPersona).filter(BloggerPersona.name == data["name"]).first()
        if existing:
            print(f"博主 [{data['name']}] 已存在，跳过")
            return
        persona = BloggerPersona(**data)
        db.add(persona)
        db.commit()
        print(f"博主 [{data['name']}] 导入成功")
    finally:
        db.close()


def seed_products():
    db = SessionLocal()
    try:
        with open("data/products.csv", "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing = db.query(Product).filter(Product.name == row["name"]).first()
                if existing:
                    continue
                product = Product(
                    name=row["name"],
                    category=row.get("category", ""),
                    price=float(row.get("price", 0)),
                    brand=row.get("brand", ""),
                    size_available=row.get("size_available", ""),
                    source_url=row.get("source_url", ""),
                    attributes=json.loads(row.get("attributes", "{}")),
                    images=json.loads(row.get("images", "[]")),
                )
                db.add(product)
            db.commit()
            print("商品库导入成功")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_persona()
    seed_products()
    print("种子数据初始化完成")
