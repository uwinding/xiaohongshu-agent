"""Normalize trend source CSVs into a reviewable trend table.

Crawler/export adapters should write these files under data/:
- source_hot_search.csv: keyword,search_index_w,is_surging
- source_topic_total.csv: keyword,views,participants
- source_topic_inc.csv: keyword,views,participants
"""

import csv

from app.trend_sources import DATA_DIR, load_trend_signals


OUTPUT_PATH = DATA_DIR / "trends_normalized.csv"
FIELDS = [
    "keyword",
    "category",
    "source",
    "search_index_w",
    "total_views_w",
    "total_participants_w",
    "inc_views_w",
    "inc_participants_w",
    "is_surging",
    "heat_score",
    "growth_score",
]


def main() -> None:
    signals = load_trend_signals(DATA_DIR)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        for signal in signals:
            writer.writerow({
                "keyword": signal.keyword,
                "category": signal.category,
                "source": signal.source,
                "search_index_w": signal.search_index_w or "",
                "total_views_w": signal.total_views_w or "",
                "total_participants_w": signal.total_participants_w or "",
                "inc_views_w": signal.inc_views_w or "",
                "inc_participants_w": signal.inc_participants_w or "",
                "is_surging": "1" if signal.is_surging else "",
                "heat_score": round(signal.heat_score, 2),
                "growth_score": round(signal.growth_score, 2),
            })

    print(f"wrote {OUTPUT_PATH} ({len(signals)} rows)")


if __name__ == "__main__":
    main()
