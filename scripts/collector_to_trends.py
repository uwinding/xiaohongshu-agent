"""Build TrendRadar input from collector observations.

The collector only sees sampled search results, not platform-wide indexes.
This script therefore writes a sampled trend table with confidence metadata:
data/source_collector_trends.csv
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app.database import SessionLocal, init_db
from app.trend_sources import DATA_DIR, classify_keyword
from app.collector.models import (
    CollectorHotwordObservation,
    CollectorNoteObservation,
    CollectorSnapshot,
    CollectorNote,
)


OUTPUT_PATH = DATA_DIR / "source_collector_trends.csv"
FIELDS = [
    "keyword",
    "category",
    "heat_score",
    "growth_score",
    "confidence",
    "evidence_count",
    "source",
    "observed_date",
]

OFF_TOPIC_KEYWORDS = [
    "宝宝",
    "宝妈",
    "宝爸",
    "女宝",
    "男宝",
    "萌娃",
    "母婴",
    "亲子",
    "儿童",
    "童装",
    "婴儿",
    "幼儿",
    "小朋友",
    "小孩",
    "孩子穿搭",
    "孕妇",
    "孕妈",
    "孕期",
    "产后",
    "哺乳",
    "奶粉",
    "纸尿裤",
]


@dataclass
class TrendAggregate:
    keyword: str
    sources: set[str] = field(default_factory=set)
    seed_keywords: set[str] = field(default_factory=set)
    note_ids: set[str] = field(default_factory=set)
    authors_or_participants: int = 0
    rank_points: float = 0.0
    engagement: float = 0.0
    recent_engagement: float = 0.0
    observations: int = 0

    @property
    def evidence_count(self) -> int:
        return self.observations + len(self.note_ids)

    @property
    def heat_score(self) -> float:
        return self.rank_points + self.engagement / 100

    @property
    def growth_score(self) -> float:
        return self.recent_engagement / 100 + max(0, self.observations - len(self.seed_keywords))

    @property
    def confidence(self) -> float:
        sample_score = min(0.45, self.evidence_count / 80 * 0.45)
        seed_score = min(0.25, len(self.seed_keywords) / 5 * 0.25)
        source_score = min(0.20, len(self.sources) / 3 * 0.20)
        continuity_score = 0.10 if self.observations >= 3 else 0.0
        return round(sample_score + seed_score + source_score + continuity_score, 3)


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _clean_keyword(value: str) -> str:
    return value.strip().strip("#").replace("[话题]", "").strip()


def _is_relevant_keyword(keyword: str) -> bool:
    if not keyword:
        return False
    keyword_lower = keyword.lower()
    return not any(term.lower() in keyword_lower for term in OFF_TOPIC_KEYWORDS)


def _engagement(like_count: int, collect_count: int, comment_count: int) -> float:
    return float((like_count or 0) + (collect_count or 0) * 2 + (comment_count or 0) * 3)


def build_collector_trends(
    hotword_rows: list[dict],
    note_rows: list[dict],
    now: datetime | None = None,
) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=3)
    aggregates: dict[str, TrendAggregate] = {}

    def get(keyword: str) -> TrendAggregate:
        if keyword not in aggregates:
            aggregates[keyword] = TrendAggregate(keyword=keyword)
        return aggregates[keyword]

    for row in hotword_rows:
        keyword = _clean_keyword(str(row.get("hotword") or ""))
        if not _is_relevant_keyword(keyword):
            continue
        agg = get(keyword)
        rank = int(row.get("rank") or 20)
        agg.rank_points += max(1, 21 - min(rank, 20)) * 5
        agg.observations += 1
        agg.sources.add(str(row.get("source") or "api_hot_query"))
        if row.get("seed_keyword"):
            agg.seed_keywords.add(str(row["seed_keyword"]))

    for row in note_rows:
        keywords = [_clean_keyword(str(row.get("seed_keyword") or ""))]
        try:
            tags = json.loads(row.get("tags_json") or "[]")
        except json.JSONDecodeError:
            tags = []
        keywords.extend(_clean_keyword(str(tag)) for tag in tags)
        engagement = _engagement(
            int(row.get("like_count") or 0),
            int(row.get("collect_count") or 0),
            int(row.get("comment_count") or 0),
        )
        observed_at = _parse_dt(str(row.get("observed_at") or ""))
        is_recent = bool(observed_at and observed_at >= recent_cutoff)

        for keyword in {kw for kw in keywords if _is_relevant_keyword(kw)}:
            agg = get(keyword)
            agg.sources.add("note_observation")
            agg.engagement += engagement
            if is_recent:
                agg.recent_engagement += engagement
            if row.get("note_id"):
                agg.note_ids.add(str(row["note_id"]))
            if row.get("seed_keyword"):
                agg.seed_keywords.add(str(row["seed_keyword"]))

    rows = []
    for agg in aggregates.values():
        if agg.evidence_count == 0:
            continue
        rows.append({
            "keyword": agg.keyword,
            "category": classify_keyword(agg.keyword),
            "heat_score": round(agg.heat_score, 2),
            "growth_score": round(agg.growth_score, 2),
            "confidence": agg.confidence,
            "evidence_count": agg.evidence_count,
            "source": "/".join(sorted(agg.sources)),
            "observed_date": now.date().isoformat(),
        })

    return sorted(
        rows,
        key=lambda item: (
            float(item["confidence"]),
            float(item["growth_score"]),
            float(item["heat_score"]),
        ),
        reverse=True,
    )


def load_observation_rows() -> tuple[list[dict], list[dict]]:
    db = SessionLocal()
    try:
        hotwords = [
            {
                "seed_keyword": row.seed_keyword,
                "hotword": row.hotword,
                "rank": row.rank,
                "source": row.source,
                "observed_at": row.observed_at,
            }
            for row in db.query(CollectorHotwordObservation).all()
        ]
        notes = [
            {
                "seed_keyword": row.seed_keyword,
                "note_id": row.note_id,
                "like_count": row.like_count,
                "collect_count": row.collect_count,
                "comment_count": row.comment_count,
                "publish_time": row.publish_time,
                "tags_json": row.tags_json,
                "observed_at": row.observed_at,
            }
            for row in db.query(CollectorNoteObservation).all()
        ]
        if not hotwords and not notes:
            return _load_legacy_snapshot_rows(db)
        return hotwords, notes
    finally:
        db.close()


def _load_legacy_snapshot_rows(db) -> tuple[list[dict], list[dict]]:
    hotwords = []
    notes = []
    note_cache = {note.note_id: note for note in db.query(CollectorNote).all()}
    for snapshot in db.query(CollectorSnapshot).all():
        try:
            snapshot_hotwords = json.loads(snapshot.hotwords_json or "[]")
        except json.JSONDecodeError:
            snapshot_hotwords = []
        for item in snapshot_hotwords:
            hotwords.append({
                "seed_keyword": snapshot.keyword,
                "hotword": item.get("text", ""),
                "rank": item.get("rank"),
                "source": "legacy_snapshot",
                "observed_at": snapshot.crawled_at,
            })

        note = note_cache.get(snapshot.note_id or "")
        try:
            tags = json.loads(snapshot.tags_json or "[]")
        except json.JSONDecodeError:
            tags = []
        notes.append({
            "seed_keyword": snapshot.keyword,
            "note_id": snapshot.note_id,
            "like_count": note.like_count if note else 0,
            "collect_count": note.collect_count if note else 0,
            "comment_count": note.comment_count if note else 0,
            "publish_time": note.publish_time if note else "",
            "tags_json": json.dumps(tags, ensure_ascii=False),
            "observed_at": snapshot.crawled_at,
        })
    return hotwords, notes


def write_trends(rows: list[dict], output_path: Path = OUTPUT_PATH) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def main() -> None:
    init_db()
    hotwords, notes = load_observation_rows()
    rows = build_collector_trends(hotwords, notes)
    path = write_trends(rows)
    print(f"wrote {path} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
