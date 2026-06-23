"""Normalize collector trend signals into a reviewable trend table.

TrendRadar reads only data/source_collector_trends.csv. Generate it with:
python3 scripts/collector_to_trends.py
"""

import csv

from app.trend_sources import DATA_DIR, load_trend_signals


OUTPUT_PATH = DATA_DIR / "trends_normalized.csv"
FIELDS = [
    "keyword",
    "category",
    "source",
    "heat_score",
    "growth_score",
    "confidence",
    "evidence_count",
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
                "heat_score": round(signal.heat_score, 2),
                "growth_score": round(signal.growth_score, 2),
                "confidence": signal.confidence,
                "evidence_count": signal.evidence_count,
            })

    print(f"wrote {OUTPUT_PATH} ({len(signals)} rows)")


if __name__ == "__main__":
    main()
