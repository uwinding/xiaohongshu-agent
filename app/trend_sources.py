import csv
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SOURCE_FILES = {
    "collector": "source_collector_trends.csv",
}


PRODUCT_CATEGORY_ALIASES = {
    "上装": ["短袖", "t恤", "衬衫", "吊带", "针织", "卫衣", "背心", "上衣"],
    "下装": ["裤", "牛仔裤", "阔腿裤", "半身裙", "短裙", "长裙"],
    "裙装": ["连衣裙", "裙子", "半身裙", "旗袍"],
    "外套": ["外套", "风衣", "西装", "开衫", "大衣", "防晒衣"],
    "鞋包配饰": ["鞋", "高跟鞋", "洞洞鞋", "包", "帽子", "首饰", "腰带"],
    "风格品类": ["jk", "汉服", "lolita", "新中式"],
}

TOPIC_CATEGORY_ALIASES = {
    "季节": ["夏季", "夏天", "夏日", "春季", "春夏", "早春", "秋冬"],
    "场景": ["通勤", "职场", "约会", "出游", "海边", "度假", "上班", "旅行"],
    "风格": ["法式", "韩系", "温柔", "高级感", "松弛", "慵懒", "日系", "国风", "新中式", "甜美", "辣妹", "休闲"],
    "人群": ["小个子", "微胖", "大码", "梨形", "显瘦", "显高"],
    "灵感": ["灵感", "技巧", "分享", "今天穿什么", "穿搭合集", "ootd"],
}


@dataclass(frozen=True)
class TrendSignal:
    keyword: str
    category: str
    source: str
    search_index_w: float = 0.0
    total_views_w: float = 0.0
    total_participants_w: float = 0.0
    inc_views_w: float = 0.0
    inc_participants_w: float = 0.0
    is_surging: bool = False
    confidence: float = 1.0
    evidence_count: int = 0

    @property
    def heat_score(self) -> float:
        return max(self.search_index_w, self.total_views_w / 100, self.inc_views_w)

    @property
    def growth_score(self) -> float:
        return self.inc_views_w + self.inc_participants_w * 10 + (200 if self.is_surging else 0)


def load_trend_signals(data_dir: Path | str = DATA_DIR) -> list[TrendSignal]:
    base = Path(data_dir)
    signals = _read_collector_trends(base / SOURCE_FILES["collector"])
    return sorted(signals, key=lambda s: (s.growth_score, s.heat_score), reverse=True)


def _read_collector_trends(path: Path) -> list[TrendSignal]:
    signals = []
    for row in _read_csv(path):
        keyword = _clean_keyword(row.get("keyword", ""))
        if not keyword:
            continue
        heat = _parse_number(row.get("heat_score"))
        growth = _parse_number(row.get("growth_score"))
        evidence_count = int(_parse_number(row.get("evidence_count")))
        if heat <= 0 and growth <= 0 and evidence_count <= 0:
            continue
        confidence = max(0.0, min(1.0, _parse_number(row.get("confidence"))))
        signals.append(
            TrendSignal(
                keyword=keyword,
                category=row.get("category") or classify_keyword(keyword),
                source=row.get("source") or "collector",
                search_index_w=heat,
                inc_views_w=growth,
                is_surging=growth > 0,
                confidence=confidence,
                evidence_count=evidence_count,
            )
        )
    return signals


def classify_keyword(keyword: str) -> str:
    for category, aliases in PRODUCT_CATEGORY_ALIASES.items():
        if any(alias.lower() in keyword.lower() for alias in aliases):
            return "品类"
    for category, aliases in TOPIC_CATEGORY_ALIASES.items():
        if any(alias.lower() in keyword.lower() for alias in aliases):
            return category
    return "话题"


def keyword_matches_any(keyword: str, terms: Iterable[str]) -> bool:
    keyword_lower = keyword.lower()
    return any(term and (term.lower() in keyword_lower or keyword_lower in term.lower()) for term in terms)


def _read_csv(path: Path) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _clean_keyword(value: object) -> str:
    return str(value or "").strip()


def _parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是"}


def _parse_number(value: object) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace(",", "")
    if not text:
        return 0.0
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else 0.0

