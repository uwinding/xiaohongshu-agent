import json
from app.skills.base import BaseSkill, SkillResult

PERFORMANCE_TRACKER_SYSTEM_PROMPT = """你是小红书内容数据分析师。根据给出的笔记效果数据，
分析内容表现，并给出优化建议。

输出格式:
{
  "performance_summary": "总体表现总结(100字以内)",
  "best_style": "表现最好的风格/话题",
  "best_time": "建议最佳发布时间",
  "optimization_suggestions": ["建议1", "建议2", ...],
  "metrics_trend": "up|stable|down"
}
"""


class PerformanceTracker(BaseSkill):
    name = "performance_tracker"

    def execute(self, performances: list[dict] | None = None, posts_metadata: list[dict] | None = None, **kwargs) -> SkillResult:
        performances = performances or kwargs.get("performances", [])
        posts_metadata = posts_metadata or kwargs.get("posts_metadata", [])

        if not performances:
            return SkillResult(success=True, data={
                "performance_summary": "暂无数据",
                "best_style": "",
                "best_time": "",
                "optimization_suggestions": ["积累更多发布数据后再分析"],
                "metrics_trend": "stable",
            })

        perf_json = json.dumps(performances, ensure_ascii=False, indent=2)
        meta_json = json.dumps(posts_metadata, ensure_ascii=False, indent=2)

        user_prompt = f"""请分析以下穿搭笔记的效果数据:

笔记效果数据:
{perf_json}

笔记元信息:
{meta_json}

请输出JSON格式的分析结果。"""

        result = self._llm_json(PERFORMANCE_TRACKER_SYSTEM_PROMPT, user_prompt)
        return SkillResult(success=True, data=result)
