"""集成测试：验证全链路生成流程（使用mock LLM）"""
from unittest.mock import patch, MagicMock
from app.llm_client import LLMClient, LLMResponse
from app.models import BloggerPersona, Product
from app.pipeline import GenerationPipeline


def seed_persona(db):
    p = BloggerPersona(
        name="小鹿",
        age_range="20-24",
        body_type="小个子",
        size_category="XS-S",
        height="158cm",
        style_tags=["甜美", "韩系", "轻法式"],
        tone_of_voice="亲切轻松，像朋友分享小个子穿搭经验",
        avatar_desc="小巧鹅蛋脸、黑色短波波头、轻薄空气刘海、自然浅暖肤色",
        avoid_tags=["宽大长上衣", "超长拖地"],
    )
    db.add(p)
    db.commit()
    return p


def seed_products(db):
    products = [
        Product(name="法式碎花A字连衣裙", category="裙装", price=199.0, brand="品牌A", attributes={"fit": "A字", "color": "碎花蓝"}),
        Product(name="高腰阔腿西裤", category="裤装", price=159.0, brand="品牌B", attributes={"fit": "阔腿", "color": "黑色"}),
        Product(name="米白短款针织开衫", category="上衣", price=129.0, brand="品牌C", attributes={"fit": "短款", "color": "米白"}),
    ]
    for p in products:
        db.add(p)
    db.commit()
    return products


@patch("app.pipeline.get_db")
def test_full_pipeline_integration(mock_get_db, setup_db):
    """全链路集成测试：从商品 -> 穿搭 -> 图片 -> 文案"""
    mock_get_db.return_value = iter([setup_db])

    persona = seed_persona(setup_db)
    products = seed_products(setup_db)

    llm = MagicMock(spec=LLMClient)
    llm.model = "gpt-4o"

    call_count = 0

    def mock_chat(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return LLMResponse(
                content=f'{{"product_set":[{{"id":{products[0].id},"name":"{products[0].name}","category":"{products[0].category}","reason":"高腰A字版型适合小个子","match_score":9}}],"overall_match_score":9.0,"style_match":"甜感韩系"}}',
                model="gpt-4o", tokens_used=200)
        elif call_count == 2:
            return LLMResponse(
                content='{"outfit_desc":"高腰A字裙搭配短款针织衫，抬高腰线并保持清爽甜感。","pos_prompt":"A petite young woman wearing a high-waist A-line skirt and cropped cardigan, full body shot","neg_prompt":"oversized silhouette, tall supermodel body","scene":"夏日街角"}',
                model="gpt-4o", tokens_used=300)
        return LLMResponse(content='{}', model="gpt-4o", tokens_used=100)

    llm.chat = mock_chat

    pipeline = GenerationPipeline(llm_client=llm)

    with patch.object(pipeline.image_generator, 'execute') as mock_img:
        mock_img.return_value = MagicMock(
            success=True,
            data={"image_paths": ["/tmp/img1.png", "/tmp/img2.png"], "num_generated": 2},
        )

        with patch.object(pipeline.content_writer, 'execute') as mock_write:
            mock_write.return_value = MagicMock(
                success=True,
                data={
                    "title": "小个子夏日穿搭，腰线一高比例就出来了",
                    "content": "小个子真的可以试试这套，清爽又显高。",
                    "hashtags": ["小个子穿搭", "显高穿搭", "韩系穿搭"],
                    "product_tags": [{"name": products[0].name, "url": products[0].source_url or ""}],
                },
            )

            result = pipeline.run(persona_id=persona.id)

    assert result is not None
    assert "post" in result
    assert result["post"]["title"] is not None
    assert len(result["images"]) == 2
    assert "outfit" in result
    assert result["outfit"]["description"] is not None
    assert "quality_report" in result
