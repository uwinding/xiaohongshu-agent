from app.skills.base import BaseSkill, SkillResult
import json

OUTFIT_COMPOSER_SYSTEM_PROMPT = """你是小红书穿搭搭配专家。根据提供的商品组合和博主人设，
创作完整的穿搭方案，并生成用于AI图片生成的Prompt。

穿搭要求:
- 考虑体型特点，运用显瘦/显高技巧
- 考虑颜色搭配、材质搭配、风格统一
- 描述要具体可生成：包含款式、颜色、材质、搭配细节、场景、光线、构图
- 生图Prompt必须是英文（DALL-E最佳输入语言），穿搭描述用中文

输出格式:
{
  "outfit_desc": "中文穿搭描述，100-200字",
  "pos_prompt": "DALL-E正向生图Prompt，英文，80-150词",
  "neg_prompt": "DALL-E反向Prompt，英文",
  "scene": "场景描述"
}
"""


class OutfitComposer(BaseSkill):
    name = "outfit_composer"

    def execute(self, product_set: list[dict] | None = None, persona: dict | None = None, scene: str = "", style: str = "", **kwargs) -> SkillResult:
        product_set = product_set or kwargs.get("product_set", [])
        persona = persona or kwargs.get("persona", {})
        scene = scene or kwargs.get("scene", "")

        if not product_set:
            return SkillResult(success=False, error="Empty product set")

        products_json = json.dumps(product_set, ensure_ascii=False, indent=2)
        persona_json = json.dumps(persona, ensure_ascii=False, indent=2)

        user_prompt = f"""请根据以下信息创作穿搭方案:

博主人设:
{persona_json}

搭配商品:
{products_json}

指定场景: {scene or '日常街拍/咖啡馆'}
指定风格: {style or persona_json}

请输出JSON格式的穿搭方案。"""

        result = self._llm_json(OUTFIT_COMPOSER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
