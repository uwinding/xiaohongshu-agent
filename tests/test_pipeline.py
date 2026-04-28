from unittest.mock import MagicMock, patch
from app.llm_client import LLMClient
from app.skills.base import SkillResult
from app.pipeline import GenerationPipeline
from app.models import BloggerPersona, Product, Outfit, GeneratedPost


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


@patch("app.pipeline.get_db")
def test_pipeline_full_flow_success(mock_get_db, setup_db):
    mock_get_db.return_value = iter([setup_db])

    persona = BloggerPersona(name="测试博主", body_type="大码", style_tags=["法式"])
    setup_db.add(persona)

    product = Product(name="测试连衣裙", category="裙装", price=199.0)
    setup_db.add(product)
    setup_db.commit()

    llm = make_llm()
    pipeline = GenerationPipeline(llm_client=llm)

    with patch.object(pipeline.product_matcher, "execute") as mock_match:
        mock_match.return_value = SkillResult(
            success=True,
            data={"product_set": [{"name": "测试裙", "match_score": 9}], "overall_match_score": 9.0, "style_match": "法式"},
        )

        with patch.object(pipeline.outfit_composer, "execute") as mock_outfit:
            mock_outfit.return_value = SkillResult(
                success=True,
                data={"outfit_desc": "测试穿搭描述", "pos_prompt": "test prompt", "neg_prompt": "bad stuff", "scene": "街拍"},
            )

            with patch.object(pipeline.image_generator, "execute") as mock_img:
                mock_img.return_value = SkillResult(
                    success=True,
                    data={"image_paths": ["/tmp/img1.png", "/tmp/img2.png"], "num_generated": 2},
                )

                with patch.object(pipeline.content_writer, "execute") as mock_write:
                    mock_write.return_value = SkillResult(
                        success=True,
                        data={"title": "测试标题", "content": "测试正文", "hashtags": ["大码穿搭", "法式"], "product_tags": [{"name": "测试裙", "url": ""}]},
                    )

                    result = pipeline.run(persona_id=persona.id)

    assert result is not None
    assert "post" in result
    assert "outfit" in result
    assert "images" in result
