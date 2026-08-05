from app.skills.base import BaseSkill, SkillResult


_BODY_TIPS = {
    "小个子": {
        "desc": "通过高腰、短上衣和利落下装抬高视觉重心，显高不压个子。",
        "neg": "oversized silhouette, floor length pants, bulky layers, tall supermodel body, exaggerated curves",
        "prompt": (
            "young adult petite slim Chinese woman, small frame, narrow shoulders, "
            "slender legs, realistic 155-160cm height impression, natural full-body proportions"
        ),
    },
}


class OutfitComposer(BaseSkill):
    name = "outfit_composer"

    def execute(self, product_set: list[dict] | None = None, persona: dict | None = None, scene: str = "", style: str = "", style_directions: list[dict] | None = None, **kwargs) -> SkillResult:
        product_set = product_set or kwargs.get("product_set", [])
        persona = persona or kwargs.get("persona", {})
        scene = scene or kwargs.get("scene", "")
        style = style or kwargs.get("style", "")
        style_directions = style_directions or kwargs.get("style_directions", [])

        if not product_set:
            return SkillResult(success=False, error="Empty product set")

        style_direction = self._choose_style(style, persona, style_directions)
        final_scene = scene or self._scene_from_style(style_direction)
        body_type = persona.get("body_type", "标准")
        body_tip = _BODY_TIPS.get(body_type, {
            "desc": "保持线条利落、配色统一，突出自然高级感。",
            "neg": "messy outfit, cheap fabric",
            "prompt": "Chinese fashion blogger, natural full-body proportions",
        })
        product_names = [p.get("name") or p.get("category") or "单品" for p in product_set]
        product_phrase = "、".join(product_names)

        outfit_desc = (
            f"这套以{style_direction}为主线，选择{product_phrase}组合。"
            f"{body_tip['desc']}配色保持干净统一，重点突出第一眼的穿搭完整度，"
            f"适合{final_scene}场景拍成小红书OOTD。"
        )

        prompt_items = ", ".join(self._prompt_item(p) for p in product_set)
        identity_prompt = persona.get("identity_prompt") or persona.get("avatar_desc", "")
        body_prompt = persona.get("body_prompt") or body_tip["prompt"]
        photo_prompt = persona.get("photo_prompt") or (
            "full body shot, natural soft light, clean composition, realistic fabric texture"
        )
        positive_parts = [
            "photorealistic unbranded fashion blogger OOTD",
            identity_prompt,
            body_prompt,
            f"wearing {prompt_items}",
            f"{style_direction} style",
            final_scene,
            photo_prompt,
            "consistent outfit details, matching pair of shoes, same shoes on both feet",
            "plain clean street background without signs or posters, no app interface elements",
        ]
        pos_prompt = ", ".join(part for part in positive_parts if part)

        negative_identity = persona.get("negative_identity_prompt", "")
        negative_parts = [
            negative_identity,
            body_tip["neg"],
            "deformed face, bad hands, extra fingers, distorted clothes, "
            "wrong product details, mismatched shoes, different shoes on each foot, barefoot, "
            "watermark, text overlay, low quality",
        ]
        neg_prompt = ", ".join(part for part in negative_parts if part)

        return SkillResult(success=True, data={
            "outfit_desc": outfit_desc,
            "pos_prompt": pos_prompt,
            "neg_prompt": neg_prompt,
            "scene": final_scene,
            "style_direction": style_direction,
        })

    def _choose_style(self, style: str, persona: dict, style_directions: list[dict]) -> str:
        if style:
            return style
        if style_directions:
            return style_directions[0].get("keyword", "") or "日常穿搭"
        style_tags = persona.get("style_tags") or []
        return style_tags[0] if style_tags else "日常穿搭"

    def _scene_from_style(self, style_direction: str) -> str:
        if "通勤" in style_direction or "职场" in style_direction:
            return "写字楼电梯厅或通勤街角"
        if "法式" in style_direction:
            return "法式咖啡馆外的自然街拍"
        if "海边" in style_direction or "度假" in style_direction:
            return "海边度假步道"
        if "约会" in style_direction:
            return "傍晚城市街区"
        return "干净街景或生活方式空间"

    def _prompt_item(self, product: dict) -> str:
        parts = [str(product.get("name") or product.get("category") or "fashion item")]
        attrs = product.get("attributes") or {}
        for key in ("color", "material", "fit", "pattern"):
            if attrs.get(key):
                parts.append(str(attrs[key]))
        if product.get("style"):
            parts.append(str(product["style"]))
        if product.get("category") == "鞋包配饰":
            parts.append(self._shoe_prompt_hint(product))
        return " ".join(parts)

    def _shoe_prompt_hint(self, product: dict) -> str:
        text = " ".join([
            str(product.get("name", "")),
            str(product.get("style", "")),
            " ".join(str(v) for v in (product.get("attributes") or {}).values()),
        ])
        hints = ["matching pair", "same shoes on both feet"]
        if "穆勒" in text or "拖" in text:
            hints.append("mule sandals")
        if "高跟" in text:
            hints.append("block high heel")
        if "夹脚" in text:
            hints.append("toe-post sandals")
        if "贴花" in text or "装饰" in text:
            hints.append("decorative floral applique")
        if "金" in text:
            hints.append("metallic gold")
        return " ".join(hints)
