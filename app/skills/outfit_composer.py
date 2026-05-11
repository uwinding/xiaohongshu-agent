from app.skills.base import BaseSkill, SkillResult
import json

OUTFIT_COMPOSER_SYSTEM_PROMPT = """你是小红书穿搭搭配专家。根据商品组合、博主人设和当前趋势风格方向，
创作完整的穿搭方案，并生成用于AI图片生成的Prompt。

穿搭要求:
- 考虑体型特点，运用显瘦/显高技巧
- 考虑颜色搭配、材质搭配、风格统一
- 描述要具体可生成：包含款式、颜色、材质、搭配细节、场景、光线、构图
- 生图Prompt必须是英文，穿搭描述用中文
- 风格必须贴合趋势 style_directions 中的至少一个方向
- scene 从趋势风格方向中衍生（如"通勤穿搭"→"高层写字楼走廊"）

输出格式:
{
  "outfit_desc": "中文穿搭描述，100-200字",
  "pos_prompt": "英文生图Prompt，80-150词（须包含趋势风格关键词）",
  "neg_prompt": "英文反向Prompt",
  "scene": "场景描述",
  "style_direction": "本次采用的趋势风格方向"
}
"""


class OutfitComposer(BaseSkill):
    name = "outfit_composer"

    def execute(self, product_set: list[dict] | None = None, persona: dict | None = None, scene: str = "", style: str = "", style_directions: list[dict] | None = None, **kwargs) -> SkillResult:
        product_set = product_set or kwargs.get("product_set", [])
        persona = persona or kwargs.get("persona", {})
        scene = scene or kwargs.get("scene", "")
        style_directions = style_directions or kwargs.get("style_directions", [])

        if not product_set:
            return SkillResult(success=False, error="Empty product set")

        products_json = json.dumps(product_set, ensure_ascii=False, indent=2)
        persona_json = json.dumps(persona, ensure_ascii=False, indent=2)

        trend_section = ""
        if style_directions:
            dirs_text = "\n".join(
                f"  - {d['keyword']}（{d.get('lifecycle','')}，竞争度{d.get('competition','?')}%，增占比{d.get('inc_ratio','?')}%）"
                for d in style_directions[:8]
            )
            trend_section = f"\n当前趋势风格方向（优先使用增长期+低竞争度的方向）：\n{dirs_text}\n"

        user_prompt = f"""请根据以下信息创作穿搭方案:

博主人设:
{persona_json}

搭配商品:
{products_json}
{trend_section}
指定场景: {scene or '从趋势方向中选取'}
指定风格: {style or '从趋势方向中选取'}

穿搭规则:
1. 风格必须贴合趋势 style_directions 中的一个方向（优先增长期+低竞争度）
2. scene 从趋势风格方向中衍生
3. pos_prompt 必须包含趋势风格关键词
4. 考虑博主体型做显瘦/显高优化

请输出JSON格式的穿搭方案。"""

        result = self._llm_json(OUTFIT_COMPOSER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
