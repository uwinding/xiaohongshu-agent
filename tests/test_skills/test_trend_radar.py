from unittest.mock import patch, MagicMock, mock_open
from app.llm_client import LLMClient
from app.skills.trend_radar import TrendRadar


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


_FAKE_CSV = """keyword,category,lifecycle,search_index_w,is_surging,inc_views_w,inc_participants_w,total_views_yi,total_participants_w,inc_engagement_pct,total_engagement_pct,inc_ratio_pct,competition_pct,priority,recommend_for,action_note
夏季穿搭,季节,增长期,846.2,1,33323.0,22.5,389.6,1490.8,0.07,0.04,0.86,60.8,高,综合,综合推荐：夏季穿搭
韩系穿搭,风格,增长期,234.0,0,24000.0,10.4,252.0,1030.0,0.04,0.04,0.95,10.6,中,风格,穿搭方向：韩系穿搭
通勤穿搭,场景,增长期,,0,14000.0,8.5,134.7,558.6,0.06,0.04,1.04,43.6,中,风格,穿搭方向：通勤穿搭
微胖穿搭,人群,增长期,,0,11000.0,4.6,204.8,370.6,0.04,0.02,0.54,15.0,中,风格,穿搭方向：微胖穿搭
短袖,品类参考,萌芽期,273.4,1,5760.7,3.5,,,0.06,,,,中,选品,优先备货：短袖
裙子,品类参考,需求期,285.1,1,,,,,,,,,中,选品,优先备货：裙子
穿搭灵感,灵感,萌芽期,,0,6289.1,1.6,,,0.03,,,,低,标签,话题标签：穿搭灵感
"""


def test_trend_radar_reads_csv_and_matches_persona():
    llm = make_llm()
    radar = TrendRadar(llm)

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=_FAKE_CSV)):
        result = radar.execute(persona_style_tags=["通勤", "韩系"], persona_body_type="大码")

    assert result.success
    data = result.data
    # 韩系穿搭/通勤穿搭 match style tags, 微胖穿搭 matches body_type 大码
    # product_hints: 0 (no trending product keyword in CSV matches this persona)
    assert len(data["style_directions"]) >= 3  # 韩系穿搭, 通勤穿搭, 微胖穿搭
    assert len(data["topic_tags"]) >= 3
    assert len(data["trend_summary"]) > 0
    assert data["matched_count"] >= 3


def test_trend_radar_no_csv():
    llm = make_llm()
    radar = TrendRadar(llm)

    with patch("os.path.exists", return_value=False):
        result = radar.execute(persona_style_tags=["法式"], persona_body_type="大码")

    assert result.success
    assert result.data["product_hints"] == []
    assert result.data["style_directions"] == []
    assert result.data["topic_tags"] == []
    assert "暂无" in result.data["trend_summary"]


def test_trend_radar_matches_by_body_type():
    """Test that body_type matching works: 大码 → 微胖, 显瘦 etc."""
    llm = make_llm()
    radar = TrendRadar(llm)

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=_FAKE_CSV)):
        result = radar.execute(persona_style_tags=[], persona_body_type="大码")

    assert result.success
    # 微胖穿搭 should match body_type 大码
    keywords = [d["keyword"] for d in result.data["style_directions"]]
    assert "微胖穿搭" in keywords


def test_trend_radar_no_match_for_unrelated_persona():
    """Persona with unrelated tags should get empty results."""
    llm = make_llm()
    radar = TrendRadar(llm)

    with patch("os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=_FAKE_CSV)):
        result = radar.execute(persona_style_tags=["运动", "户外"], persona_body_type="标准")

    assert result.success
    assert result.data["product_hints"] == []
    assert result.data["style_directions"] == []
    assert result.data["matched_count"] == 0
