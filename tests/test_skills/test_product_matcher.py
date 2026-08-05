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
        '"reason":"A字版型适合小个子","match_score":9}],'
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
            "body_type": "小个子",
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
    result = matcher.execute(products=[], persona={"body_type": "小个子", "style_tags": []})
    assert result.success
    assert result.data["product_set"] == []


def test_product_matcher_keeps_dress_outfit_coherent():
    matcher = ProductMatcher(make_llm())

    result = matcher.execute(
        products=[
            {"id": 1, "name": "法式碎花连衣裙", "category": "裙装", "style": "法式", "match_score": 9},
            {"id": 2, "name": "黄色吊带上衣", "category": "上衣", "style": "法式", "match_score": 8},
            {"id": 3, "name": "高腰牛仔短裤", "category": "裤装", "style": "休闲", "match_score": 7},
            {"id": 4, "name": "金色高跟凉鞋", "category": "鞋包配饰", "style": "法式", "match_score": 6},
            {"id": 5, "name": "棕色平底凉鞋", "category": "鞋包配饰", "style": "通勤", "match_score": 5},
        ],
        persona={"body_type": "小个子", "style_tags": ["法式"], "avoid_tags": []},
    )

    names = [p["name"] for p in result.data["product_set"]]
    assert "法式碎花连衣裙" in names
    assert "金色高跟凉鞋" in names
    assert "黄色吊带上衣" not in names
    assert "高腰牛仔短裤" not in names
    assert "棕色平底凉鞋" not in names
