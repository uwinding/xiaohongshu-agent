from app.skills.base import BaseSkill, SkillResult
from app.scraper import fetch_trends_for_persona

TREND_RADAR_SYSTEM_PROMPT = """你是一个小红书穿搭趋势分析专家。根据提供的热门笔记标题，
分析当前流行的穿搭趋势、热门关键词、热门单品，输出结构化JSON。

输出格式:
{
  "keywords": ["关键词1", "关键词2", ...],
  "style_trends": ["趋势风格1", ...],
  "hot_items": ["热门单品1", ...],
  "hot_scores": [9, 8, 7, ...],
  "trend_summary": "趋势综合描述(100字以内)"
}
"""

USER_PROMPT_TEMPLATE = """请分析以下小红书穿搭内容的趋势:

热门笔记标题:
{titles}

关注的风格标签: {style_tags}

请输出JSON格式的趋势分析结果。"""


class TrendRadar(BaseSkill):
    name = "trend_radar"

    def execute(self, style_tags: list[str] | None = None, **kwargs) -> SkillResult:
        tags = style_tags or kwargs.get("style_tags", ["穿搭", "女装"])
        titles = fetch_trends_for_persona(tags)

        if not titles:
            return SkillResult(
                success=True,
                data={
                    "keywords": [],
                    "style_trends": [],
                    "hot_items": [],
                    "hot_scores": [],
                    "trend_summary": "暂无趋势数据",
                },
            )

        titles_str = "\n".join(f"- {t}" for t in titles[:30])
        user_prompt = USER_PROMPT_TEMPLATE.format(titles=titles_str, style_tags=", ".join(tags))
        result = self._llm_json(TREND_RADAR_SYSTEM_PROMPT, user_prompt)

        return SkillResult(
            success=True,
            data=result,
            metadata={"scraped_count": len(titles)},
        )
