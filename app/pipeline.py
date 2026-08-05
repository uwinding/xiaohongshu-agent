from app.skills.trend_radar import TrendRadar
from app.skills.product_matcher import ProductMatcher
from app.skills.outfit_composer import OutfitComposer
from app.skills.image_generator import ImageGenerator
from app.skills.content_writer import ContentWriter
from app.skills.performance_tracker import PerformanceTracker
from app.models import BloggerPersona, Product, Outfit, GeneratedPost
from app.database import SessionLocal, get_db
from app.product_refs import is_direct_image_reference, parse_reference_list
from app.product_assets import ProductAssetRegistry
from app.image_quality import ImageQualityChecker
from app.persona_assets import PersonaAssetRegistry


class GenerationPipeline:
    def __init__(self, llm_client=None):
        self.llm = llm_client
        self.trend_radar = TrendRadar()
        self.product_matcher = ProductMatcher()
        self.outfit_composer = OutfitComposer()
        self.image_generator = ImageGenerator(llm_client)
        self.content_writer = ContentWriter()
        self.performance_tracker = PerformanceTracker()
        self.product_assets = ProductAssetRegistry()
        self.persona_assets = PersonaAssetRegistry()
        self.image_quality = ImageQualityChecker(asset_registry=self.product_assets)

    def run(self, persona_id: int = 1, product_ids: list[int] | None = None, style: str = "", scene: str = "", num_images: int = 1) -> dict:
        db_provider = get_db()
        db = next(db_provider) if hasattr(db_provider, "__next__") else SessionLocal()
        try:
            return self._run_with_db(db, persona_id, product_ids, style, scene, num_images)
        finally:
            if hasattr(db_provider, "__next__"):
                close = getattr(db_provider, "close", None)
                if close:
                    close()
            else:
                db.close()

    def _run_with_db(self, db, persona_id: int, product_ids: list[int] | None, style: str, scene: str, num_images: int) -> dict:

        persona = db.query(BloggerPersona).filter(BloggerPersona.id == persona_id).first()
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")
        print(f"[1/6] 博主: {persona.name} ({persona.body_type})")

        persona_dict = self._persona_to_dict(persona)
        persona_context = self.persona_assets.context_for_persona(persona.name)
        persona_dict.update(persona_context)

        # [1.5/6] TrendRadar — 趋势分析
        print(f"[2/6] 趋势分析中...")
        trend_result = self.trend_radar.execute(
            persona_style_tags=persona.style_tags or [],
            persona_body_type=persona.body_type or "",
        )
        product_hints = trend_result.data.get("product_hints", []) if trend_result.success else []
        style_directions = trend_result.data.get("style_directions", []) if trend_result.success else []
        topic_tags = trend_result.data.get("topic_tags", []) if trend_result.success else []
        print(f"      趋势品类 {len(product_hints)} 个，风格方向 {len(style_directions)} 个")

        if product_ids:
            products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        else:
            products = db.query(Product).all()
        products_list = [self._product_to_dict(p) for p in products]
        print(f"[3/6] 商品匹配中 ({len(products_list)}件)...")

        match_result = self.product_matcher.execute(
            products=products_list,
            persona=persona_dict,
            product_hints=product_hints,
            style_directions=style_directions,
        )
        if not match_result.success:
            raise RuntimeError(f"ProductMatcher failed: {match_result.error}")
        matched_products = match_result.data.get("product_set", [])
        print(f"      匹配 {len(matched_products)} 件商品（方向: {match_result.data.get('trend_alignment', '')}）")

        print("[4/6] 穿搭方案生成中...")
        outfit_result = self.outfit_composer.execute(
            product_set=matched_products,
            persona=persona_dict,
            scene=scene,
            style=style,
            style_directions=style_directions,
        )
        if not outfit_result.success:
            raise RuntimeError(f"OutfitComposer failed: {outfit_result.error}")
        print(f"      穿搭: {outfit_result.data.get('outfit_desc', '')[:60]}...")

        outfit = Outfit(
            product_ids=[p.get("id", 0) for p in matched_products],
            description=outfit_result.data.get("outfit_desc", ""),
            pos_prompt=outfit_result.data.get("pos_prompt", ""),
            neg_prompt=outfit_result.data.get("neg_prompt", ""),
            style_tags=persona.style_tags,
            scene=outfit_result.data.get("scene", scene),
            body_type_suitability=persona.body_type,
        )
        db.add(outfit)
        db.commit()
        db.refresh(outfit)

        # Prioritize main garments over accessories for SKU-level img2img fidelity.
        product_ref_images = self._collect_reference_images(matched_products)

        persona_ref_specs = self.persona_assets.reference_specs_for_persona(persona.name)
        product_ref_specs = self._collect_product_reference_specs(
            matched_products,
            limit=max(0, 6 - len(persona_ref_specs)),
        )
        generation_ref_specs = (persona_ref_specs + product_ref_specs)[:6]

        print(
            f"[5/6] AI生图中（人物参考{len(persona_ref_specs)}张，"
            f"商品参考{len(product_ref_specs)}张）..."
        )
        img_result = self.image_generator.execute(
            pos_prompt=outfit_result.data.get("pos_prompt", ""),
            neg_prompt=outfit_result.data.get("neg_prompt", ""),
            num_images=num_images,
            reference_images=generation_ref_specs,
            persona_name=persona.name,
            persona_key=persona_context.get("persona_key", persona.name),
        )
        if not img_result.success:
            raise RuntimeError(f"ImageGenerator failed: {img_result.error}")
        image_paths = img_result.data.get("image_paths", [])
        print(f"      生成 {len(image_paths)} 张图片 (seed={img_result.data.get('seed')})")

        print("[6/6] 文案生成中...")
        content_result = self.content_writer.execute(
            outfit_desc=outfit_result.data.get("outfit_desc", ""),
            products=matched_products,
            persona=persona_dict,
            topic_tags=topic_tags,
        )
        if not content_result.success:
            raise RuntimeError(f"ContentWriter failed: {content_result.error}")
        print(f"      标题: {content_result.data.get('title', '')}")
        print(f"====== 生成完成 ======")

        post = GeneratedPost(
            outfit_id=outfit.id,
            images=image_paths,
            title=content_result.data.get("title", ""),
            content=content_result.data.get("content", ""),
            hashtags=content_result.data.get("hashtags", []),
            product_tags=content_result.data.get("product_tags", []),
            status="draft",
        )
        db.add(post)
        db.commit()
        db.refresh(post)

        quality_report = self.image_quality.evaluate(
            image_paths=image_paths,
            products=matched_products,
            reference_images=product_ref_images,
            prompt=img_result.data.get("prompt_used", outfit_result.data.get("pos_prompt", "")),
            post_id=post.id,
        )

        return {"post": self._post_to_dict(post), "outfit": self._outfit_to_dict(outfit), "images": image_paths, "quality_report": quality_report, "trend": {"product_hints": product_hints, "style_directions": style_directions, "topic_tags": topic_tags}}

    def _persona_to_dict(self, persona: BloggerPersona) -> dict:
        return {
            "id": persona.id,
            "name": persona.name,
            "age_range": persona.age_range or "",
            "body_type": persona.body_type,
            "size_category": persona.size_category or "",
            "height": persona.height or "",
            "style_tags": persona.style_tags or [],
            "tone_of_voice": persona.tone_of_voice or "",
            "avatar_desc": persona.avatar_desc or "",
            "content_focus": persona.content_focus or [],
            "avoid_tags": persona.avoid_tags or [],
        }

    def _product_to_dict(self, product: Product) -> dict:
        return {"id": product.id, "name": product.name, "category": product.category or "", "price": product.price or 0, "brand": product.brand or "", "source_url": product.source_url or "", "attributes": product.attributes or {}, "style": product.style or "", "images": product.images or []}

    def _collect_reference_images(self, products: list[dict], limit: int = 6) -> list[str]:
        priority = {
            "裙装": 0,
            "上衣": 1,
            "裤装": 2,
            "外套": 3,
            "鞋包配饰": 4,
        }
        refs = []
        sorted_products = sorted(products, key=lambda p: priority.get(p.get("category") or "", 9))
        for product in sorted_products:
            per_product_limit = 3 if product.get("category") != "鞋包配饰" else 2
            added_for_product = 0
            product_refs = self.product_assets.references_for_product(product)
            for img in product_refs:
                if is_direct_image_reference(img) and img not in refs:
                    refs.append(img)
                    added_for_product += 1
                if added_for_product >= per_product_limit:
                    break
            if len(refs) >= limit:
                break
        return refs[:limit]

    def _collect_product_reference_specs(self, products: list[dict], limit: int = 3) -> list[dict]:
        if limit <= 0:
            return []
        priority = {
            "裙装": 0,
            "上衣": 1,
            "裤装": 2,
            "外套": 3,
            "鞋包配饰": 4,
        }
        garment_candidates = []
        accessory_candidates = []
        sorted_products = sorted(products, key=lambda p: priority.get(p.get("category") or "", 9))
        for product in sorted_products:
            category = product.get("category") or ""
            refs = self.product_assets.references_for_product(product)
            per_product_limit = 1 if category == "鞋包配饰" else 2
            for ref_index, source in enumerate(refs[:per_product_limit]):
                if not is_direct_image_reference(source):
                    continue
                is_accessory = category == "鞋包配饰"
                spec = {
                    "source": source,
                    "kind": "product",
                    "role": "accessory" if is_accessory else "primary_garment",
                    "weight": 0.78 if is_accessory else max(0.85, 1.0 - ref_index * 0.08),
                    "label": f"{product.get('name') or category}:reference_{ref_index + 1}",
                    "product_id": product.get("id"),
                }
                (accessory_candidates if is_accessory else garment_candidates).append(spec)

        selected = garment_candidates[: min(2, limit)]
        if accessory_candidates and len(selected) < limit:
            selected.append(accessory_candidates[0])
        remaining = [
            spec
            for spec in garment_candidates[2:] + accessory_candidates[1:]
            if spec not in selected
        ]
        selected.extend(remaining[: max(0, limit - len(selected))])
        return selected[:limit]

    def _post_to_dict(self, post: GeneratedPost) -> dict:
        return {"id": post.id, "outfit_id": post.outfit_id, "images": post.images, "title": post.title, "content": post.content, "hashtags": post.hashtags, "product_tags": post.product_tags, "status": post.status, "created_at": post.created_at.isoformat() if post.created_at else None}

    def _outfit_to_dict(self, outfit: Outfit) -> dict:
        return {"id": outfit.id, "description": outfit.description, "pos_prompt": outfit.pos_prompt, "neg_prompt": outfit.neg_prompt, "style_tags": outfit.style_tags, "scene": outfit.scene}
