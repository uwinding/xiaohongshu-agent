from app.skills.base import BaseSkill, SkillResult
import json

PRODUCT_MATCHER_SYSTEM_PROMPT = """你是小红书穿搭商品匹配专家。根据博主人设、趋势信号和待选商品，
为博主挑选最合适的搭配商品组合。

穿搭约束规则:
- 大码体型: 优先A字/直筒/阔腿版型，V领/方领，深色/纯色，避免紧身/横条纹/低腰
- 小个子体型: 优先高腰线设计、短款/九分款、同色系搭配，避免过长/oversized
- 必须遵守博主的避雷标签，不能推荐避雷标签相关的商品

选品优先级:
- 品类趋势热度（product_hints 中的品类优先匹配，搜索指数越高权重越大）
- 风格兼容性（商品 style 标签需与 style_directions 至少一个方向兼容，冲突的排除）
- 人设匹配度（版型/尺码/避雷硬约束必须满足）

输出格式:
{
  "product_set": [
    {"name": "商品名", "category": "品类", "reason": "推荐理由（须说明贴合的趋势方向+风格兼容性）", "match_score": 8}
  ],
  "overall_match_score": 8.5,
  "style_match": "风格匹配说明",
  "trend_alignment": "选品命中X/Y趋势品类，风格方向对齐XX/YY"
}
"""


class ProductMatcher(BaseSkill):
    name = "product_matcher"

    def execute(self, products: list[dict] | None = None, persona: dict | None = None, product_hints: list[dict] | None = None, style_directions: list[dict] | None = None, **kwargs) -> SkillResult:
        products = products or kwargs.get("products", [])
        persona = persona or kwargs.get("persona", {})
        product_hints = product_hints or kwargs.get("product_hints", [])
        style_directions = style_directions or kwargs.get("style_directions", [])

        if not products:
            return SkillResult(success=True, data={"product_set": [], "overall_match_score": 0.0, "style_match": ""})

        products_json = json.dumps(products, ensure_ascii=False, indent=2)
        persona_json = json.dumps(persona, ensure_ascii=False, indent=2)

        trend_section = ""
        if product_hints:
            hints_text = "\n".join(f"  - {h['keyword']}（搜索指数{h.get('search_index_w','?')}w，{'飙升' if h.get('is_surging') else '稳定'}，优先级{h.get('priority','中')}）" for h in product_hints[:10])
            trend_section += f"\n当前趋势品类（优先匹配）：\n{hints_text}\n"

        if style_directions:
            dirs_text = "\n".join(f"  - {d['keyword']}（{d.get('lifecycle','')}，竞争度{d.get('competition','?')}%，增占比{d.get('inc_ratio','?')}%）" for d in style_directions[:10])
            trend_section += f"\n当前趋势风格方向（商品 style 标签需与至少一个方向兼容，冲突的排除）：\n{dirs_text}\n"

        user_prompt = f"""请根据以下信息匹配最适合的商品:

博主人设:
{persona_json}
{trend_section}
待选商品:
{products_json}

选品规则:
1. 优先匹配趋势品类中的商品（品类命中 trend_hints → 加分）
2. 商品的 style 标签必须与趋势风格方向兼容，冲突的排除
3. 每套搭配覆盖 2-3 个趋势品类
4. 必须遵守博主的体型约束和避雷标签（硬约束）

请输出JSON格式的匹配结果。"""

        result = self._llm_json(PRODUCT_MATCHER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
