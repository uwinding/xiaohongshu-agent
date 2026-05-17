from collections import Counter

from app.skills.base import BaseSkill, SkillResult


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

        total_likes = sum(int(p.get("likes") or 0) for p in performances)
        total_comments = sum(int(p.get("comments") or 0) for p in performances)
        total_shares = sum(int(p.get("shares") or 0) for p in performances)
        avg_click = sum(float(p.get("click_rate") or 0) for p in performances) / len(performances)
        trend = self._trend(performances)
        best_style = self._best_style(posts_metadata)

        return SkillResult(success=True, data={
            "performance_summary": f"共{len(performances)}篇笔记，累计赞{total_likes}、评{total_comments}、藏/转{total_shares}，平均点击率{avg_click:.1%}。",
            "best_style": best_style,
            "best_time": "优先测试工作日晚8点-10点和周末上午10点",
            "optimization_suggestions": [
                "保留互动最高笔记的标题结构和首图构图",
                "下一轮优先复用表现好的风格标签",
                "低点击内容先优化封面关键词和前两行正文",
            ],
            "metrics_trend": trend,
        })

    def _trend(self, performances: list[dict]) -> str:
        if len(performances) < 2:
            return "stable"
        first = float(performances[0].get("click_rate") or 0)
        last = float(performances[-1].get("click_rate") or 0)
        if last > first * 1.1:
            return "up"
        if last < first * 0.9:
            return "down"
        return "stable"

    def _best_style(self, posts_metadata: list[dict]) -> str:
        counter = Counter()
        for meta in posts_metadata:
            for tag in meta.get("style_tags") or meta.get("hashtags") or []:
                counter[str(tag)] += 1
        if not counter:
            return "暂无足够风格数据"
        style, _ = counter.most_common(1)[0]
        return f"{style}相关内容出现频次最高，建议继续验证"
