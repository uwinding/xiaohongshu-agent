from unittest.mock import MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.skills.outfit_composer import OutfitComposer


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


def test_outfit_composer_success():
    llm = make_llm()
    llm.chat.return_value = LLMResponse(
        content=(
            '{"outfit_desc":"法式碎花连衣裙搭配米白针织开衫，温柔优雅。'
            '高腰阔腿裤拉长腿部线条，整体显瘦显高。",'
            '"pos_prompt":"A plus-size woman wearing French floral A-line dress with cream knit cardigan, '
            'black high-waist wide-leg pants, French cafe background, soft natural light, '
            'full body shot, Xiaohongshu OOTD style, photorealistic",'
            '"neg_prompt":"tight clothing, horizontal stripes, low waist, deformed face, '
            'bad fingers, product distortion",'
            '"scene":"法式咖啡馆"}'
        ),
        model="gpt-4o",
        tokens_used=300,
    )

    composer = OutfitComposer(llm)
    result = composer.execute(
        product_set=[
            {"name": "法式碎花裙", "category": "裙装"},
            {"name": "米白针织开衫", "category": "上衣"},
            {"name": "高腰阔腿裤", "category": "裤装"},
        ],
        persona={
            "body_type": "大码",
            "height": "165cm",
            "style_tags": ["法式", "通勤"],
            "avatar_desc": "圆脸、温柔杏眼、长发微卷",
        },
        scene="法式咖啡馆",
    )

    assert result.success
    assert len(result.data["outfit_desc"]) > 10
    assert len(result.data["pos_prompt"]) > 20
    assert len(result.data["neg_prompt"]) > 5


def test_outfit_composer_empty_products():
    llm = make_llm()
    composer = OutfitComposer(llm)
    result = composer.execute(product_set=[], persona={})
    assert not result.success
    assert "Empty product set" in result.error
