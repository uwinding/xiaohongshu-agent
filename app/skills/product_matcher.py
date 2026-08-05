from app.skills.base import BaseSkill, SkillResult
from app.trend_sources import keyword_matches_any
from app.product_refs import is_direct_image_reference, parse_reference_list


_BODY_POSITIVE = {
    "小个子": ["高腰", "短款", "九分", "收腰", "同色", "显高", "短裙"],
}

_BODY_NEGATIVE = {
    "小个子": ["拖地", "超长", "oversized", "宽大"],
}


class ProductMatcher(BaseSkill):
    name = "product_matcher"

    def execute(self, products: list[dict] | None = None, persona: dict | None = None, product_hints: list[dict] | None = None, style_directions: list[dict] | None = None, **kwargs) -> SkillResult:
        products = products or kwargs.get("products", [])
        persona = persona or kwargs.get("persona", {})
        product_hints = product_hints or kwargs.get("product_hints", [])
        style_directions = style_directions or kwargs.get("style_directions", [])

        if not products:
            return SkillResult(success=True, data={
                "product_set": [],
                "overall_match_score": 0.0,
                "style_match": "",
                "trend_alignment": "无可匹配商品",
            })

        scored = []
        for product in products:
            score, reasons = self._score_product(product, persona, product_hints, style_directions)
            if score > 0:
                item = dict(product)
                item["match_score"] = min(10, round(score, 1))
                item["reason"] = "；".join(reasons[:3]) or "基础风格匹配"
                scored.append(item)

        scored.sort(key=lambda p: p["match_score"], reverse=True)
        selected = self._pick_balanced_set(scored)
        avg_score = round(sum(p["match_score"] for p in selected) / len(selected), 1) if selected else 0.0

        hit_trends = self._hit_keywords(selected, product_hints)
        hit_styles = self._hit_keywords(selected, style_directions, include_style=True)

        return SkillResult(success=True, data={
            "product_set": selected,
            "overall_match_score": avg_score,
            "style_match": "、".join(hit_styles) if hit_styles else "按博主人设风格进行基础匹配",
            "trend_alignment": f"选品命中{len(hit_trends)}/{len(product_hints[:10])}趋势品类，风格方向对齐{('、'.join(hit_styles) or '基础风格')}",
        })

    def _score_product(self, product: dict, persona: dict, product_hints: list[dict], style_directions: list[dict]) -> tuple[float, list[str]]:
        body_type = persona.get("body_type", "")
        avoid_tags = persona.get("avoid_tags") or []
        style_tags = persona.get("style_tags") or []
        haystack = self._product_text(product)

        if keyword_matches_any(haystack, avoid_tags + _BODY_NEGATIVE.get(body_type, [])):
            return 0, ["命中避雷或体型硬约束"]

        score = 4.0
        reasons = []

        product_keywords = [h.get("keyword", "") for h in product_hints]
        if keyword_matches_any(haystack, product_keywords):
            score += 3.0
            reasons.append("命中趋势品类")

        style_keywords = [d.get("keyword", "") for d in style_directions] + style_tags
        if keyword_matches_any(haystack, style_keywords):
            score += 2.0
            reasons.append("风格与趋势方向兼容")

        body_positive = _BODY_POSITIVE.get(body_type, [])
        if keyword_matches_any(haystack, body_positive):
            score += 1.5
            reasons.append(f"适合{body_type}体型")

        if self._has_reference_image(product):
            score += 0.5
            reasons.append("有商品参考图，利于图生图一致性")

        return score, reasons

    def _has_reference_image(self, product: dict) -> bool:
        return any(is_direct_image_reference(ref) for ref in parse_reference_list(product.get("images")))

    def _product_text(self, product: dict) -> str:
        attrs = product.get("attributes") or {}
        return " ".join([
            str(product.get("name", "")),
            str(product.get("category", "")),
            str(product.get("brand", "")),
            str(product.get("style", "")),
            " ".join(f"{k}:{v}" for k, v in attrs.items()),
        ]).lower()

    def _pick_balanced_set(self, products: list[dict]) -> list[dict]:
        coherent = self._pick_coherent_outfit(products)
        if coherent:
            return coherent

        selected = []
        seen_categories = set()
        for product in products:
            category = product.get("category") or "其他"
            if category not in seen_categories or len(selected) < 2:
                selected.append(product)
                seen_categories.add(category)
            if len(selected) >= 4:
                break
        return selected or products[:3]

    def _pick_coherent_outfit(self, products: list[dict]) -> list[dict]:
        dresses = []
        tops = []
        bottoms = []
        outerwear = []
        shoes_bags = []

        for product in products:
            text = self._product_text(product)
            category = product.get("category") or ""
            if "连衣裙" in text or "one-piece dress" in text:
                dresses.append(product)
            elif category == "上衣":
                tops.append(product)
            elif category in {"裤装", "裙装"}:
                bottoms.append(product)
            elif category == "外套":
                outerwear.append(product)
            elif category == "鞋包配饰":
                shoes_bags.append(product)

        if dresses:
            selected = [dresses[0]]
            selected.extend(outerwear[:1])
            selected.extend(shoes_bags[:1])
            return selected[:4]

        if tops and bottoms:
            selected = [tops[0], bottoms[0]]
            selected.extend(outerwear[:1])
            selected.extend(shoes_bags[:1])
            return selected[:4]

        return []

    def _hit_keywords(self, products: list[dict], trends: list[dict], include_style: bool = False) -> list[str]:
        hits = []
        product_text = " ".join(self._product_text(p) for p in products)
        if include_style:
            product_text += " " + " ".join(str(p.get("style", "")) for p in products)
        for trend in trends[:10]:
            keyword = trend.get("keyword", "")
            if keyword and keyword_matches_any(product_text, [keyword]):
                hits.append(keyword)
        return hits
