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
    mock_image2 = MagicMock()
    mock_image2.url = "https://example.com/fake-image2.png"
    mock_response = MagicMock()
    mock_response.data = [mock_image, mock_image2]
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
                    persona_avatar="圆脸、长发微卷",
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
