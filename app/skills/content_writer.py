import json
from app.skills.base import BaseSkill, SkillResult

CONTENT_WRITER_SYSTEM_PROMPT = """你是小红书穿搭爆款文案写手。根据穿搭描述和商品信息，
生成一篇吸引人的小红书穿搭笔记。

文案要求:
- 标题: 15-25字，包含emoji，制造好奇心或实用价值感
- 正文: 150-300字，口语化、亲切感，像闺蜜推荐
- 分段清晰，每段2-3句，多用emoji点缀
- 高频词: 姐妹们/绝绝子/冲/闭眼入/氛围感/谁穿谁好看
- 大码博主强调"显瘦""自信""微胖友好"
- 小个子博主强调"显高""拉长比例""小个子福音"
- 话题标签: 5-8个，包含体型标签+风格标签+泛流量标签

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

    def execute(self, outfit_desc: str = "", products: list[dict] | None = None, persona: dict | None = None, **kwargs) -> SkillResult:
        outfit_desc = outfit_desc or kwargs.get("outfit_desc", "")
        products = products or kwargs.get("products", [])
        persona = persona or kwargs.get("persona", {})

        if not outfit_desc:
            return SkillResult(success=False, error="Empty outfit description")

        user_prompt = f"""请根据以下信息生成一篇小红书穿搭笔记:

博主口吻: {persona.get('tone_of_voice', '亲切自然')}
博主体型: {persona.get('body_type', '标准')}

穿搭描述:
{outfit_desc}

关联商品:
{json.dumps(products, ensure_ascii=False, indent=2)}

请输出JSON格式的小红书笔记内容。"""

        result = self._llm_json(CONTENT_WRITER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
