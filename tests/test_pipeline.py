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

    persona = BloggerPersona(name="小鹿", body_type="小个子", style_tags=["法式"])
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
                        data={"title": "测试标题", "content": "测试正文", "hashtags": ["小个子穿搭", "法式"], "product_tags": [{"name": "测试裙", "url": ""}]},
                    )

                    result = pipeline.run(persona_id=persona.id)

    assert result is not None
    assert "post" in result
    assert "outfit" in result
    assert "images" in result
    image_call = mock_img.call_args.kwargs
    assert image_call["persona_key"] == "xiaolu_summer"
    assert [item["role"] for item in image_call["reference_images"]] == [
        "face_identity",
        "face_identity",
        "body_proportion",
    ]


def test_pipeline_collect_reference_images_prioritizes_main_garments():
    pipeline = GenerationPipeline(llm_client=make_llm())

    refs = pipeline._collect_reference_images([
        {
            "category": "鞋包配饰",
            "images": [
                "https://img.alicdn.com/imgextra/i1/shoe-side.jpg",
                "https://img.alicdn.com/imgextra/i1/shoe-front.jpg",
                "https://img.alicdn.com/imgextra/i1/shoe-detail.jpg",
            ],
        },
        {
            "category": "裙装",
            "images": [
                "https://img.alicdn.com/imgextra/i1/dress-front.jpg",
                "https://img.alicdn.com/imgextra/i1/dress-side.jpg",
            ],
        },
    ])

    assert refs == [
        "https://img.alicdn.com/imgextra/i1/dress-front.jpg",
        "https://img.alicdn.com/imgextra/i1/dress-side.jpg",
        "https://img.alicdn.com/imgextra/i1/shoe-side.jpg",
        "https://img.alicdn.com/imgextra/i1/shoe-front.jpg",
    ]


def test_pipeline_allocates_typed_product_reference_slots():
    pipeline = GenerationPipeline(llm_client=make_llm())

    specs = pipeline._collect_product_reference_specs([
        {
            "id": 8,
            "name": "金色穆勒鞋",
            "category": "鞋包配饰",
            "images": [
                "https://img.alicdn.com/imgextra/i1/shoe-side.jpg",
                "https://img.alicdn.com/imgextra/i1/shoe-front.jpg",
            ],
        },
        {
            "id": 4,
            "name": "法式碎花裙",
            "category": "裙装",
            "images": [
                "https://img.alicdn.com/imgextra/i1/dress-front.jpg",
                "https://img.alicdn.com/imgextra/i1/dress-side.jpg",
                "https://img.alicdn.com/imgextra/i1/dress-detail.jpg",
            ],
        },
    ], limit=3)

    assert [item["role"] for item in specs] == [
        "primary_garment",
        "primary_garment",
        "accessory",
    ]
    assert [item["weight"] for item in specs] == [1.0, 0.92, 0.78]
    assert [item["product_id"] for item in specs] == [4, 4, 8]
