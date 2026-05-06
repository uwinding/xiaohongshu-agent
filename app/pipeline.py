from app.llm_client import LLMClient
from app.skills.trend_radar import TrendRadar
from app.skills.product_matcher import ProductMatcher
from app.skills.outfit_composer import OutfitComposer
from app.skills.image_generator import ImageGenerator
from app.skills.content_writer import ContentWriter
from app.skills.performance_tracker import PerformanceTracker
from app.models import BloggerPersona, Product, Outfit, GeneratedPost
from app.database import get_db


class GenerationPipeline:
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient()
        self.trend_radar = TrendRadar(self.llm)
        self.product_matcher = ProductMatcher(self.llm)
        self.outfit_composer = OutfitComposer(self.llm)
        self.image_generator = ImageGenerator(self.llm)
        self.content_writer = ContentWriter(self.llm)
        self.performance_tracker = PerformanceTracker(self.llm)

    def run(self, persona_id: int = 1, product_ids: list[int] | None = None, style: str = "", scene: str = "", num_images: int = 1) -> dict:
        db = next(get_db())

        persona = db.query(BloggerPersona).filter(BloggerPersona.id == persona_id).first()
        if not persona:
            raise ValueError(f"Persona {persona_id} not found")
        print(f"[1/5] 博主: {persona.name} ({persona.body_type})")

        persona_dict = self._persona_to_dict(persona)

        if product_ids:
            products = db.query(Product).filter(Product.id.in_(product_ids)).all()
        else:
            products = db.query(Product).all()
        products_list = [self._product_to_dict(p) for p in products]
        print(f"[2/5] 商品匹配中 ({len(products_list)}件)...")

        match_result = self.product_matcher.execute(products=products_list, persona=persona_dict)
        if not match_result.success:
            raise RuntimeError(f"ProductMatcher failed: {match_result.error}")
        print(f"      匹配 {len(match_result.data.get('product_set', []))} 件商品")

        matched_products = match_result.data.get("product_set", [])

        print("[3/5] 穿搭方案生成中...")
        outfit_result = self.outfit_composer.execute(product_set=matched_products, persona=persona_dict, scene=scene, style=style)
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

        print(f"[4/5] AI生图中...")
        img_result = self.image_generator.execute(
            pos_prompt=outfit_result.data.get("pos_prompt", ""),
            neg_prompt=outfit_result.data.get("neg_prompt", ""),
            persona_avatar=persona.avatar_desc or "",
            num_images=num_images,
        )
        if not img_result.success:
            raise RuntimeError(f"ImageGenerator failed: {img_result.error}")
        image_paths = img_result.data.get("image_paths", [])
        print(f"      生成 {len(image_paths)} 张图片")

        print("[5/5] 文案生成中...")
        content_result = self.content_writer.execute(outfit_desc=outfit_result.data.get("outfit_desc", ""), products=matched_products, persona=persona_dict)
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

        return {"post": self._post_to_dict(post), "outfit": self._outfit_to_dict(outfit), "images": image_paths}

    def _persona_to_dict(self, persona: BloggerPersona) -> dict:
        return {"id": persona.id, "name": persona.name, "body_type": persona.body_type, "style_tags": persona.style_tags or [], "tone_of_voice": persona.tone_of_voice or "", "avatar_desc": persona.avatar_desc or "", "avoid_tags": persona.avoid_tags or [], "height": persona.height or ""}

    def _product_to_dict(self, product: Product) -> dict:
        return {"id": product.id, "name": product.name, "category": product.category or "", "price": product.price or 0, "brand": product.brand or "", "source_url": product.source_url or "", "attributes": product.attributes or {}}

    def _post_to_dict(self, post: GeneratedPost) -> dict:
        return {"id": post.id, "outfit_id": post.outfit_id, "images": post.images, "title": post.title, "content": post.content, "hashtags": post.hashtags, "product_tags": post.product_tags, "status": post.status, "created_at": post.created_at.isoformat() if post.created_at else None}

    def _outfit_to_dict(self, outfit: Outfit) -> dict:
        return {"id": outfit.id, "description": outfit.description, "pos_prompt": outfit.pos_prompt, "neg_prompt": outfit.neg_prompt, "style_tags": outfit.style_tags, "scene": outfit.scene}
