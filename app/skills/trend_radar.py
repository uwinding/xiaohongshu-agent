from app.skills.base import BaseSkill, SkillResult
from app.trend_sources import TrendSignal, keyword_matches_any, load_trend_signals


_BODY_TYPE_MAP = {
    "大码": ["微胖", "显瘦", "梨形", "大码", "丰满"],
    "小个子": ["小个子", "显高", "矮个子", "娇小"],
    "标准": [],
}

_STYLE_ALIAS = {
    "法式": ["法式", "法式优雅", "高级感"],
    "通勤": ["通勤", "职场", "上班", "OL"],
    "温柔": ["温柔", "知性", "优雅"],
    "韩系": ["韩系", "韩剧", "韩国"],
    "甜美": ["甜美", "甜妹", "可爱"],
    "休闲": ["休闲", "日常", "街头", "运动"],
    "国潮": ["国风", "新中式", "中国风", "东方美学"],
    "平价": ["平价", "学生", "性价比"],
    "辣妹": ["辣妹", "性感", "欧美"],
}


class TrendRadar(BaseSkill):
    name = "trend_radar"

    def execute(self, persona_style_tags: list[str] | None = None, persona_body_type: str = "", **kwargs) -> SkillResult:
        style_tags = persona_style_tags or kwargs.get("style_tags", [])
        body_type = persona_body_type or kwargs.get("body_type", "")
        signals = load_trend_signals()

        if not signals:
            return SkillResult(success=True, data={
                "product_hints": [],
                "style_directions": [],
                "topic_tags": [],
                "trend_summary": "暂无趋势源数据，请写入 data/source_hot_search.csv、data/source_topic_total.csv、data/source_topic_inc.csv",
                "matched_count": 0,
            })

        ranked = sorted(
            ((self._persona_score(signal, style_tags, body_type), signal) for signal in signals),
            key=lambda item: (item[0], item[1].growth_score, item[1].heat_score),
            reverse=True,
        )
        matched = [signal for score, signal in ranked if score > 0]
        candidate_pool = matched

        product_hints = [self._to_entry(s) for s in candidate_pool if s.category == "品类"][:10]
        style_directions = [self._to_entry(s) for s in candidate_pool if s.category in {"风格", "场景", "季节", "人群"}][:10]
        topic_tags = [self._to_entry(s) for s in candidate_pool if s.category != "品类"][:15]

        top_product = product_hints[0]["keyword"] if product_hints else "暂无明确品类"
        top_style = style_directions[0]["keyword"] if style_directions else "暂无明确风格"
        summary = (
            f"趋势分析：基于热词榜/话题总量榜/话题增量榜，"
            f"选品优先{top_product}，内容方向优先{top_style}，"
            f"可用话题{len(topic_tags)}个。"
        )

        return SkillResult(success=True, data={
            "product_hints": product_hints,
            "style_directions": style_directions,
            "topic_tags": topic_tags,
            "trend_summary": summary,
            "matched_count": len(matched),
        })

    def _persona_score(self, signal: TrendSignal, style_tags: list[str], body_type: str) -> int:
        terms = []
        for tag in style_tags:
            terms.extend(_STYLE_ALIAS.get(tag, [tag]))
        terms.extend(_BODY_TYPE_MAP.get(body_type, []))
        score = 0
        if keyword_matches_any(signal.keyword, terms):
            score += 5
        if score > 0 and (signal.is_surging or signal.inc_views_w > 0):
            score += 2
        if score > 0 and signal.search_index_w > 0:
            score += 1
        return score

    def _to_entry(self, signal: TrendSignal) -> dict:
        priority = "高" if signal.growth_score >= 500 or signal.heat_score >= 200 else "中"
        lifecycle = "增长期" if signal.growth_score > 0 or signal.is_surging else "稳定期"
        return {
            "keyword": signal.keyword,
            "priority": priority,
            "category": signal.category,
            "lifecycle": lifecycle,
            "competition": "",
            "inc_ratio": "",
            "search_index_w": signal.search_index_w or "",
            "total_views_w": signal.total_views_w or "",
            "inc_views_w": signal.inc_views_w or "",
            "is_surging": signal.is_surging,
            "source": signal.source,
        }
