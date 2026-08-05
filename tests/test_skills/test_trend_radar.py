from unittest.mock import patch, MagicMock, mock_open
from app.llm_client import LLMClient
from app.skills.trend_radar import TrendRadar
from app.trend_sources import TrendSignal


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


_FAKE_CSV = """keyword,category,heat_score,growth_score,confidence,evidence_count,source,observed_date
夏季穿搭,季节,846.2,333.23,0.82,30,collector,2026-06-23
韩系穿搭,风格,234.0,240.0,0.72,24,collector,2026-06-23
通勤穿搭,场景,300.0,140.0,0.7,28,collector,2026-06-23
小个子穿搭,人群,180.0,110.0,0.62,16,collector,2026-06-23
短袖,品类,273.4,57.6,0.55,18,collector,2026-06-23
裙子,品类,285.1,20.0,0.5,12,collector,2026-06-23
穿搭灵感,灵感,120.0,62.8,0.38,9,collector,2026-06-23
"""


def test_trend_radar_reads_collector_csv_and_matches_persona():
    llm = make_llm()
    radar = TrendRadar(llm)

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=_FAKE_CSV)):
        result = radar.execute(persona_style_tags=["通勤", "韩系"], persona_body_type="小个子")

    assert result.success
    data = result.data
    # 韩系穿搭/通勤穿搭 match style tags, 小个子穿搭 matches body_type 小个子.
    # High-heat product keywords are retained as product hints even without persona terms.
    assert len(data["product_hints"]) >= 1
    assert len(data["style_directions"]) >= 3  # 韩系穿搭, 通勤穿搭, 小个子穿搭
    assert len(data["topic_tags"]) >= 3
    assert len(data["trend_summary"]) > 0
    assert data["matched_count"] >= 3


def test_trend_radar_no_csv():
    llm = make_llm()
    radar = TrendRadar(llm)

    with patch("os.path.exists", return_value=False):
        result = radar.execute(persona_style_tags=["法式"], persona_body_type="小个子")

    assert result.success
    assert result.data["product_hints"] == []
    assert result.data["style_directions"] == []
    assert result.data["topic_tags"] == []
    assert "暂无" in result.data["trend_summary"]


def test_trend_radar_matches_by_body_type():
    """Test that body_type matching works: 小个子 → 小个子, 显瘦 etc."""
    llm = make_llm()
    radar = TrendRadar(llm)

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=_FAKE_CSV)):
        result = radar.execute(persona_style_tags=[], persona_body_type="小个子")

    assert result.success
    # 小个子穿搭 should match body_type 小个子
    keywords = [d["keyword"] for d in result.data["style_directions"]]
    assert "小个子穿搭" in keywords


def test_trend_radar_no_match_for_unrelated_persona():
    """Unrelated personas should not get style directions, but hot products stay usable."""
    llm = make_llm()
    radar = TrendRadar(llm)

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=_FAKE_CSV)):
        result = radar.execute(persona_style_tags=["运动", "户外"], persona_body_type="标准")

    assert result.success
    assert result.data["product_hints"] != []
    assert result.data["style_directions"] == []
    assert result.data["matched_count"] == 0


def test_trend_radar_ranks_collector_confidence():
    radar = TrendRadar(make_llm())
    signals = [
        TrendSignal(
            keyword="低证据穿搭",
            category="风格",
            source="collector",
            search_index_w=500,
            inc_views_w=200,
            confidence=0.05,
            evidence_count=1,
        ),
        TrendSignal(
            keyword="通勤穿搭",
            category="场景",
            source="collector",
            search_index_w=300,
            inc_views_w=180,
            confidence=0.7,
            evidence_count=30,
        ),
    ]

    with patch("app.skills.trend_radar.load_trend_signals", return_value=signals):
        result = radar.execute(persona_style_tags=["通勤"], persona_body_type="标准")

    assert result.success
    assert result.data["style_directions"][0]["keyword"] == "通勤穿搭"
    assert result.data["style_directions"][0]["confidence"] == 0.7
    assert result.data["style_directions"][0]["evidence_count"] == 30
