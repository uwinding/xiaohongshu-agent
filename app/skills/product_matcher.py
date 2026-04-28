from app.skills.base import BaseSkill, SkillResult
import json

PRODUCT_MATCHER_SYSTEM_PROMPT = """你是小红书穿搭商品匹配专家。根据博主人设（体型、风格偏好、避雷标签）
和待选商品，为博主挑选最合适的搭配商品组合。

穿搭约束规则:
- 大码体型: 优先A字/直筒/阔腿版型，V领/方领，深色/纯色，避免紧身/横条纹/低腰
- 小个子体型: 优先高腰线设计、短款/九分款、同色系搭配，避免过长/oversized
- 必须遵守博主的避雷标签，不能推荐避雷标签相关的商品

输出格式:
{
  "product_set": [
    {"name": "商品名", "category": "品类", "reason": "推荐理由", "match_score": 8}
  ],
  "overall_match_score": 8.5,
  "style_match": "风格匹配说明"
}
"""


class ProductMatcher(BaseSkill):
    name = "product_matcher"

    def execute(self, products: list[dict] | None = None, persona: dict | None = None, **kwargs) -> SkillResult:
        products = products or kwargs.get("products", [])
        persona = persona or kwargs.get("persona", {})

        if not products:
            return SkillResult(success=True, data={"product_set": [], "overall_match_score": 0.0, "style_match": ""})

        products_json = json.dumps(products, ensure_ascii=False, indent=2)
        persona_json = json.dumps(persona, ensure_ascii=False, indent=2)

        user_prompt = f"""请根据以下博主信息匹配最适合的商品:

博主人设:
{persona_json}

待选商品:
{products_json}

请输出JSON格式的匹配结果。"""

        result = self._llm_json(PRODUCT_MATCHER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
