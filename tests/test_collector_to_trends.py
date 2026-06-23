from datetime import datetime, timezone

from scripts.collector_to_trends import build_collector_trends


def test_build_collector_trends_from_observations():
    now = datetime(2026, 6, 23, tzinfo=timezone.utc)
    rows = build_collector_trends(
        hotword_rows=[
            {
                "seed_keyword": "穿搭",
                "hotword": "通勤穿搭",
                "rank": 1,
                "source": "api_hot_query",
                "observed_at": now.isoformat(),
            },
            {
                "seed_keyword": "夏季穿搭",
                "hotword": "通勤穿搭",
                "rank": 3,
                "source": "dom_tab",
                "observed_at": now.isoformat(),
            },
            {
                "seed_keyword": "穿搭",
                "hotword": "宝宝穿搭",
                "rank": 2,
                "source": "api_hot_query",
                "observed_at": now.isoformat(),
            },
        ],
        note_rows=[
            {
                "seed_keyword": "穿搭",
                "note_id": "note1",
                "like_count": 100,
                "collect_count": 20,
                "comment_count": 5,
                "tags_json": '["#通勤穿搭[话题]", "#夏季穿搭", "#宝宝穿搭", "#做个会穿搭的女孩子"]',
                "observed_at": now.isoformat(),
            }
        ],
        now=now,
    )

    by_keyword = {row["keyword"]: row for row in rows}
    assert "通勤穿搭" in by_keyword
    assert "通勤穿搭[话题]" not in by_keyword
    assert "宝宝穿搭" not in by_keyword
    assert "做个会穿搭的女孩子" in by_keyword
    assert by_keyword["通勤穿搭"]["confidence"] > 0
    assert by_keyword["通勤穿搭"]["evidence_count"] >= 3
    assert by_keyword["通勤穿搭"]["heat_score"] > 0
