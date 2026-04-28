from unittest.mock import MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.skills.product_matcher import ProductMatcher


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


def test_product_matcher_success():
    llm = make_llm()
    llm.chat.return_value = LLMResponse(
        content='{"product_set":[{"name":"法式碎花裙","category":"裙装","brand":"品牌A",'
        '"reason":"A字版型适合大码","match_score":9}],'
        '"overall_match_score":8.5,"style_match":"法式优雅"}',
        model="gpt-4o",
        tokens_used=200,
    )

    matcher = ProductMatcher(llm)
    result = matcher.execute(
        products=[
            {"id": 1, "name": "法式碎花裙", "category": "裙装", "price": 199, "attributes": {"fit": "A字"}},
            {"id": 2, "name": "紧身包臀裙", "category": "裙装", "price": 159, "attributes": {"fit": "包臀"}},
        ],
        persona={
            "body_type": "大码",
            "style_tags": ["法式", "通勤"],
            "avoid_tags": ["紧身包臀"],
        },
    )

    assert result.success
    assert len(result.data["product_set"]) == 1
    assert "法式碎花裙" in str(result.data)


def test_product_matcher_empty_products():
    llm = make_llm()
    matcher = ProductMatcher(llm)
    result = matcher.execute(products=[], persona={"body_type": "大码", "style_tags": []})
    assert result.success
    assert result.data["product_set"] == []
