import csv
import os
from app.skills.base import BaseSkill, SkillResult

_STRATEGY_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "strategy_full.csv")

# 博主人设 → 关键词映射表
_BODY_TYPE_MAP = {
    "大码": ["微胖", "显瘦", "梨形", "大码", "胖", "丰满"],
    "小个子": ["小个子", "显高", "矮个子", "娇小"],
    "标准": [],
}

_STYLE_ALIAS = {
    "法式": ["法式", "法式优雅", "高级感"],
    "通勤": ["通勤", "职场", "上班", "OL"],
    "温柔": ["温柔", "知性", "优雅", "女性化"],
    "韩系": ["韩系", "韩剧", "韩国"],
    "甜美": ["甜美", "甜妹", "可爱"],
    "休闲": ["休闲", "日常", "街头", "运动"],
    "国潮": ["国风", "新中式", "中国风", "东方美学"],
    "平价": ["平价", "学生", "便宜", "性价比"],
    "辣妹": ["辣妹", "性感", "欧美"],
}


def _match_persona(keyword: str, persona_style_tags: list[str], persona_body_type: str) -> int:
    """Compute relevance score between a keyword and persona. Higher = more relevant."""
    score = 0
    kw_lower = keyword.lower()

    # Body type match
    body_matches = _BODY_TYPE_MAP.get(persona_body_type, [])
    for term in body_matches:
        if term in kw_lower or term in keyword:
            score += 3
            break

    # Style tag match
    for tag in persona_style_tags:
        tag_lower = tag.lower()
        aliases = _STYLE_ALIAS.get(tag, [tag])
        for alias in aliases:
            if alias in kw_lower or alias in keyword or tag_lower in kw_lower:
                score += 2
                break

    return score


class TrendRadar(BaseSkill):
    name = "trend_radar"

    def execute(self, persona_style_tags: list[str] | None = None, persona_body_type: str = "", **kwargs) -> SkillResult:
        style_tags = persona_style_tags or kwargs.get("style_tags", [])
        body_type = persona_body_type or kwargs.get("body_type", "")

        rows = self._load_strategy_csv()
        if not rows:
            return SkillResult(success=True, data={
                "product_hints": [], "style_directions": [], "topic_tags": [],
                "trend_summary": "暂无趋势数据（strategy_full.csv 不存在或为空）"
            })

        # Filter and score
        matched = []
        for r in rows:
            kw = r.get("keyword", "")
            score = _match_persona(kw, style_tags, body_type)
            if score > 0:
                r["_match_score"] = score
                matched.append(r)

        # Sort by _match_score desc, then priority
        pri_order = {"高": 0, "中": 1, "低": 2}
        matched.sort(key=lambda r: (-r["_match_score"], pri_order.get(r.get("priority", "低"), 3)))

        # Split by recommend_for
        product_hints = []
        style_directions = []
        topic_tags = []

        for r in matched:
            rf = r.get("recommend_for", "标签")
            entry = {
                "keyword": r["keyword"],
                "priority": r["priority"],
                "category": r["category"],
                "lifecycle": r["lifecycle"],
                "competition": r.get("competition_pct", ""),
                "inc_ratio": r.get("inc_ratio_pct", ""),
                "search_index_w": r.get("search_index_w", ""),
                "is_surging": r.get("is_surging", "") == "1",
            }
            if rf == "选品" or rf == "综合":
                if r["priority"] in ("高", "中"):
                    product_hints.append(entry)
            if rf == "风格" or rf == "综合":
                if r["priority"] in ("高", "中"):
                    style_directions.append(entry)
            # topic_tags: all matched keywords, limited to top 15
            if len(topic_tags) < 15:
                topic_tags.append(entry)

        # Generate trend summary
        top_product = product_hints[0]["keyword"] if product_hints else "N/A"
        top_style = style_directions[0]["keyword"] if style_directions else "N/A"
        summary = f"趋势分析：选品优先{top_product}等{len(product_hints)}个品类，风格方向推荐{top_style}等{len(style_directions)}个方向，可带{len(topic_tags)}个话题标签"

        return SkillResult(success=True, data={
            "product_hints": product_hints,
            "style_directions": style_directions,
            "topic_tags": topic_tags,
            "trend_summary": summary,
            "matched_count": len(matched),
        })

    def _load_strategy_csv(self) -> list[dict]:
        if not os.path.exists(_STRATEGY_PATH):
            return []
        rows = []
        with open(_STRATEGY_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows
