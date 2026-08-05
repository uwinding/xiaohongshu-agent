import hashlib
import pytest
from unittest.mock import patch, MagicMock
from app.llm_client import LLMClient
from app.skills.image_generator import ImageGenerator


def make_llm() -> LLMClient:
    client = MagicMock(spec=LLMClient)
    client.model = "gpt-4o"
    return client


@patch("app.skills.image_generator.OpenAI")
def test_generate_images_success(mock_openai_class):
    llm = make_llm()
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_image = MagicMock()
    mock_image.url = "https://example.com/fake-image.png"
    mock_response = MagicMock()
    mock_response.data = [mock_image]
    mock_client.images.generate.return_value = mock_response

    with patch("app.skills.image_generator.requests.get") as mock_get:
        mock_img_resp = MagicMock()
        mock_img_resp.raise_for_status = MagicMock()
        mock_img_resp.content = b"fake-image-bytes"
        mock_get.return_value = mock_img_resp

        with patch("app.skills.image_generator.Path.mkdir"):
            with patch("builtins.open", MagicMock()):
                generator = ImageGenerator(llm, storage_dir="/tmp/test-images")
                result = generator.execute(
                    pos_prompt="Fashion blogger outfit photo",
                    neg_prompt="bad quality",
                    persona_avatar="圆脸、黑色短波波头",
                    num_images=2,
                )

    assert result.success
    assert len(result.data["image_paths"]) == 2
    assert result.data["num_generated"] == 2


def test_generate_missing_prompt():
    llm = make_llm()
    generator = ImageGenerator(llm)
    result = generator.execute(pos_prompt="")
    assert not result.success
    assert "Missing pos_prompt" in result.error


def test_seedream_default_size_meets_provider_min_pixels():
    llm = make_llm()
    generator = ImageGenerator(llm)

    assert generator._select_size("doubao-seedream-4-5-251128") == "1536x2560"


def test_build_prompt_adds_strong_no_text_constraints():
    llm = make_llm()
    generator = ImageGenerator(llm)

    prompt = generator._build_prompt("fashion photo", "bad hands", "round face")

    assert "no visible text" in prompt
    assert "Chinese characters" in prompt


def test_image_extension_uses_content_type():
    llm = make_llm()
    generator = ImageGenerator(llm)
    resp = MagicMock()
    resp.headers = {"content-type": "image/jpeg"}
    resp.content = b"\xff\xd8\xfffake"

    assert generator._image_extension(resp) == ".jpg"


def test_seedream_supports_multi_reference_images():
    llm = make_llm()
    generator = ImageGenerator(llm)

    assert generator._supports_multi_reference("doubao-seedream-4-5-251128")


def test_load_ref_image_skips_taobao_detail_page():
    llm = make_llm()
    generator = ImageGenerator(llm)

    assert generator._load_ref_image("https://detail.tmall.com/item.htm?id=123") is None


@patch("app.skills.image_generator.requests.get")
def test_load_ref_image_accepts_real_image_response(mock_get):
    llm = make_llm()
    generator = ImageGenerator(llm)
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.headers = {"content-type": "image/jpeg"}
    resp.content = b"\xff\xd8\xfffake-jpeg"
    mock_get.return_value = resp

    data_url = generator._load_ref_image("https://img.alicdn.com/imgextra/i1/test.jpg")

    assert data_url.startswith("data:image/jpg;base64,")


def test_persona_seed_is_stable_sha256_value():
    generator = ImageGenerator(make_llm())
    persona_key = "xiaolu_summer"
    expected = int.from_bytes(
        hashlib.sha256(persona_key.encode("utf-8")).digest()[:4],
        "big",
    ) & 0x7FFFFFFF

    assert generator._get_persona_seed(persona_key) == expected
    assert ImageGenerator(make_llm())._get_persona_seed(persona_key) == expected


def test_build_prompt_does_not_duplicate_existing_identity_prompt():
    generator = ImageGenerator(make_llm())
    identity = "same fixed face and short bob haircut"

    prompt = generator._build_prompt(
        f"photorealistic outfit photo, {identity}",
        "bad hands",
        identity,
    )

    assert prompt.count(identity) == 1


def test_typed_reference_specs_generate_role_specific_guide():
    generator = ImageGenerator(make_llm())
    references = [
        {
            "source": "https://example.com/face.jpg",
            "kind": "persona",
            "role": "face_identity",
            "weight": 1.0,
            "label": "face:front",
        },
        {
            "source": "https://example.com/dress.jpg",
            "kind": "product",
            "role": "primary_garment",
            "weight": 0.92,
            "label": "dress:front",
        },
    ]

    with patch.object(generator, "_load_ref_image", return_value="data:image/jpeg;base64,ZmFrZQ=="):
        specs = generator._normalize_reference_specs(references)
        prepared = generator._prepare_reference_images(specs)
    guide = generator._reference_guide(prepared)

    assert [item["index"] for item in prepared] == [1, 2]
    assert "Image 1 [persona/face_identity, weight=1.00" in guide
    assert "preserve the same face" in guide
    assert "Image 2 [product/primary_garment, weight=0.92" in guide
    assert "preserve garment category" in guide


def test_reference_weights_are_clamped_and_sources_are_deduplicated():
    generator = ImageGenerator(make_llm())
    source = "https://example.com/item.png"

    specs = generator._normalize_reference_specs([
        {"source": source, "weight": 3},
        {"source": source, "weight": 0.2},
    ])

    assert len(specs) == 1
    assert specs[0]["weight"] == 1.0
