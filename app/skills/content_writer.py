import json
from app.skills.base import BaseSkill, SkillResult

CONTENT_WRITER_SYSTEM_PROMPT = """你是小红书穿搭爆款文案写手。根据穿搭描述、商品信息和当前趋势标签，
生成一篇吸引人的小红书穿搭笔记。

文案要求:
- 标题: 15-25字，包含emoji，制造好奇心或实用价值感
- 正文: 150-300字，口语化、像真人分享而非营销号，像闺蜜推荐
- 分段清晰，每段2-3句，适度使用emoji点缀
- 大码博主强调"显瘦""自信""微胖友好"
- 小个子博主强调"显高""拉长比例""小个子福音"
- 话题标签: 5-8个，优先从 topic_tags 中选取高优先级的热门标签，
  覆盖风格标签（如 #高级感穿搭）+ 人群标签（如 #微胖穿搭）+ 品类标签（如 #连衣裙），
  不局限于单一类别

输出格式:
{
  "title": "标题",
  "content": "正文",
  "hashtags": ["标签1", "标签2", ...],
  "product_tags": [{"name": "商品名", "url": "商品链接"}]
}
"""


class ContentWriter(BaseSkill):
    name = "content_writer"

    def execute(self, outfit_desc: str = "", products: list[dict] | None = None, persona: dict | None = None, topic_tags: list[dict] | None = None, **kwargs) -> SkillResult:
        outfit_desc = outfit_desc or kwargs.get("outfit_desc", "")
        products = products or kwargs.get("products", [])
        persona = persona or kwargs.get("persona", {})
        topic_tags = topic_tags or kwargs.get("topic_tags", [])

        if not outfit_desc:
            return SkillResult(success=False, error="Empty outfit description")

        tags_section = ""
        if topic_tags:
            tags_text = "\n".join(
                f"  - #{d['keyword']}#（{d.get('category','')}类，热度{d.get('priority','中')}）"
                for d in topic_tags[:15]
            )
            tags_section = f"\n当前热门话题标签（从以下选取5-8个，覆盖风格+人群+品类多类）：\n{tags_text}\n"

        user_prompt = f"""请根据以下信息生成一篇小红书穿搭笔记:

博主口吻: {persona.get('tone_of_voice', '亲切自然')}
博主体型: {persona.get('body_type', '标准')}

穿搭描述:
{outfit_desc}

关联商品:
{json.dumps(products, ensure_ascii=False, indent=2)}
{tags_section}
话题标签选取规则:
1. 优先使用 topic_tags 中"高"热度标签
2. 必须覆盖风格类+人群类+品类类标签（不限于单一类别）
3. 如果 topic_tags 为空，根据正文自行生成标签

请输出JSON格式的小红书笔记内容。"""

        result = self._llm_json(CONTENT_WRITER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
