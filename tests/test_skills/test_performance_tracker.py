from unittest.mock import MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.skills.performance_tracker import PerformanceTracker


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


def test_analyze_performance_success():
    llm = make_llm()
    llm.chat.return_value = LLMResponse(
        content='{"performance_summary":"本周3篇笔记，平均互动率3.2%",'
        '"best_style":"法式通勤风互动率最高(4.5%)",'
        '"best_time":"周五晚8点互动峰值",'
        '"optimization_suggestions":["增加通勤主题","尝试晚上8点发布","减少碎花元素比重"],'
        '"metrics_trend":"up"}',
        model="gpt-4o",
        tokens_used=250,
    )

    tracker = PerformanceTracker(llm)
    result = tracker.execute(
        performances=[
            {"likes": 120, "comments": 15, "shares": 8, "click_rate": 0.032},
            {"likes": 85, "comments": 10, "shares": 5, "click_rate": 0.025},
        ],
        posts_metadata=[
            {"title": "法式通勤", "style_tags": ["法式", "通勤"]},
            {"title": "碎花穿搭", "style_tags": ["碎花", "田园"]},
        ],
    )

    assert result.success
    assert "performance_summary" in result.data
    assert len(result.data["optimization_suggestions"]) > 0


def test_analyze_empty_performance():
    llm = make_llm()
    tracker = PerformanceTracker(llm)
    result = tracker.execute(performances=[], posts_metadata=[])
    assert result.success
    assert "暂无数据" in result.data["performance_summary"]
