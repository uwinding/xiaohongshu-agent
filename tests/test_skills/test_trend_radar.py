from unittest.mock import patch, MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.skills.trend_radar import TrendRadar


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


def test_trend_radar_execute_success():
    llm = make_llm()
    llm.chat.return_value = LLMResponse(
        content='{"keywords":["法式碎花","通勤显瘦"],"style_trends":["法式田园风"],'
        '"hot_items":["碎花连衣裙","阔腿裤"],"trend_summary":"今夏法式通勤风热","hot_scores":[9,8]}',
        model="gpt-4o",
        tokens_used=200,
    )

    with patch("app.skills.trend_radar.fetch_trends_for_persona") as mock_fetch:
        mock_fetch.return_value = ["法式连衣裙 绝绝子", "通勤穿搭 显瘦", "碎花裙 法式"]
        radar = TrendRadar(llm)
        result = radar.execute(style_tags=["法式", "通勤"])

    assert result.success
    data = result.data
    assert len(data["keywords"]) >= 2
    assert "trend_summary" in data


def test_trend_radar_empty_trends():
    llm = make_llm()
    with patch("app.skills.trend_radar.fetch_trends_for_persona") as mock_fetch:
        mock_fetch.return_value = []
        radar = TrendRadar(llm)
        result = radar.execute(style_tags=["稀有标签"])

    assert result.success
    assert result.data["keywords"] == []
