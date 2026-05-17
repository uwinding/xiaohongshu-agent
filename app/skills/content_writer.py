from app.skills.base import BaseSkill, SkillResult


class ContentWriter(BaseSkill):
    name = "content_writer"

    def execute(self, outfit_desc: str = "", products: list[dict] | None = None, persona: dict | None = None, topic_tags: list[dict] | None = None, **kwargs) -> SkillResult:
        outfit_desc = outfit_desc or kwargs.get("outfit_desc", "")
        products = products or kwargs.get("products", [])
        persona = persona or kwargs.get("persona", {})
        topic_tags = topic_tags or kwargs.get("topic_tags", [])

        if not outfit_desc:
            return SkillResult(success=False, error="Empty outfit description")

        body_type = persona.get("body_type", "标准")
        style_tags = persona.get("style_tags") or []
        tone = persona.get("tone_of_voice") or "亲切自然"
        main_style = style_tags[0] if style_tags else self._first_topic(topic_tags, "风格") or "日常"
        main_product = self._main_product(products)
        title = self._title(body_type, main_style, main_product)
        hashtags = self._hashtags(body_type, style_tags, products, topic_tags)
        product_tags = [{"name": p.get("name", ""), "url": p.get("source_url", "")} for p in products if p.get("name")]

        content = (
            f"姐妹们，今天这套{main_style}穿搭我会直接存进近期模板里。\n\n"
            f"{outfit_desc}\n\n"
            f"我最喜欢的是它没有用力过猛，{self._body_sentence(body_type)}。"
            f"如果你平时喜欢{tone}的分享方式，这套会很适合做成图文首发。"
        )

        return SkillResult(success=True, data={
            "title": title,
            "content": content,
            "hashtags": hashtags,
            "product_tags": product_tags,
        })

    def _title(self, body_type: str, style: str, product: str) -> str:
        if body_type == "大码":
            return f"大码姐妹试试这套{style}{product}，显瘦很自然"
        if body_type == "小个子":
            return f"小个子这套{style}{product}，比例直接拉高"
        return f"这套{style}{product}，日常也能很出片"

    def _body_sentence(self, body_type: str) -> str:
        if body_type == "大码":
            return "对微胖身材的腰腹和胯部都比较友好，拍照也不容易显局促"
        if body_type == "小个子":
            return "高腰线和利落轮廓能把比例向上带，显高效果很直观"
        return "线条干净、层次明确，日常照着穿不容易出错"

    def _hashtags(self, body_type: str, style_tags: list[str], products: list[dict], topic_tags: list[dict]) -> list[str]:
        tags = []
        for item in topic_tags:
            keyword = item.get("keyword", "").strip("# ")
            if keyword and keyword not in tags:
                tags.append(keyword)
            if len(tags) >= 4:
                break
        for tag in style_tags:
            value = f"{tag}穿搭" if "穿搭" not in tag else tag
            if value not in tags:
                tags.append(value)
        if body_type == "大码":
            tags.extend(["大码穿搭", "显瘦穿搭", "微胖穿搭"])
        elif body_type == "小个子":
            tags.extend(["小个子穿搭", "显高穿搭"])
        for product in products[:3]:
            category = product.get("category") or ""
            if category and category not in tags:
                tags.append(category)
        normalized = []
        for tag in tags:
            tag = tag.strip("# ")
            if tag and tag not in normalized:
                normalized.append(tag)
        return normalized[:8]

    def _main_product(self, products: list[dict]) -> str:
        if not products:
            return ""
        product = products[0]
        return product.get("category") or product.get("name", "")

    def _first_topic(self, topic_tags: list[dict], category: str) -> str:
        for item in topic_tags:
            if item.get("category") == category:
                return item.get("keyword", "")
        return ""
