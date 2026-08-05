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
            '"pos_prompt":"A petite woman wearing French floral A-line dress with cream knit cardigan, '
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
            {"name": "亮光贴花穆勒鞋款式高跟凉鞋", "category": "鞋包配饰", "attributes": {"color": "金色", "fit": "高跟"}},
        ],
        persona={
            "body_type": "小个子",
            "height": "158cm",
            "style_tags": ["法式", "通勤"],
            "avatar_desc": "圆脸、温柔杏眼、黑色短波波头",
        },
        scene="法式咖啡馆",
    )

    assert result.success
    assert len(result.data["outfit_desc"]) > 10
    assert len(result.data["pos_prompt"]) > 20
    assert len(result.data["neg_prompt"]) > 5
    assert "plain clean street background" in result.data["pos_prompt"]
    assert "young adult petite slim Chinese woman" in result.data["pos_prompt"]
    assert "same shoes on both feet" in result.data["pos_prompt"]
    assert "mule sandals" in result.data["pos_prompt"]
    assert "mismatched shoes" in result.data["neg_prompt"]


def test_outfit_composer_empty_products():
    llm = make_llm()
    composer = OutfitComposer(llm)
    result = composer.execute(product_set=[], persona={})
    assert not result.success
    assert "Empty product set" in result.error


def test_outfit_composer_uses_petiteness_constraints():
    composer = OutfitComposer(make_llm())
    result = composer.execute(
        product_set=[{"name": "高腰A字短裙", "category": "裙装"}],
        persona={
            "body_type": "小个子",
            "height": "158cm",
            "style_tags": ["甜美", "韩系"],
            "avatar_desc": "年轻成年亚洲女性，黑色短波波头，轻薄空气刘海",
        },
    )

    assert result.success
    assert "petite slim Chinese woman" in result.data["pos_prompt"]
    assert "155-160cm height impression" in result.data["pos_prompt"]
    assert "tall supermodel body" in result.data["neg_prompt"]


def test_outfit_composer_assembles_persona_prompts_once():
    composer = OutfitComposer(make_llm())
    identity = "fixed face anchor with short bob haircut"
    body = "fixed petite body proportions"
    photo = "fixed full body camera setup"
    negative = "avoid changing face identity"

    result = composer.execute(
        product_set=[{"name": "白色短袖", "category": "上衣"}],
        persona={
            "body_type": "小个子",
            "style_tags": ["韩系"],
            "avatar_desc": "legacy avatar description",
            "identity_prompt": identity,
            "body_prompt": body,
            "photo_prompt": photo,
            "negative_identity_prompt": negative,
        },
    )

    assert result.success
    assert result.data["pos_prompt"].count(identity) == 1
    assert result.data["pos_prompt"].count(body) == 1
    assert result.data["pos_prompt"].count(photo) == 1
    assert "legacy avatar description" not in result.data["pos_prompt"]
    assert negative in result.data["neg_prompt"]
