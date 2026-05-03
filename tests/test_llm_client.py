import pytest
from unittest.mock import patch, MagicMock
from openai import APIConnectionError
from app.llm_client import LLMClient, LLMResponse


@pytest.fixture(autouse=True)
def mock_settings():
    with patch("app.llm_client.get_settings") as mock:
        settings = MagicMock()
        settings.llm_api_key = "test-key"
        settings.llm_base_url = "https://api.openai.com/v1"
        settings.llm_model = "gpt-4o"
        settings.image_model = "dall-e-3"
        mock.return_value = settings
        yield mock


def test_llm_client_initialization():
    client = LLMClient()
    assert client.model == "gpt-4o"


def test_llm_response_model():
    resp = LLMResponse(content="test content", model="gpt-4o", tokens_used=100)
    assert resp.content == "test content"
    assert resp.model == "gpt-4o"
    assert resp.tokens_used == 100


@patch("app.llm_client.OpenAI")
def test_chat_completion(mock_openai_class):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = '{"key": "value"}'
    mock_completion.usage.total_tokens = 150
    mock_client.chat.completions.create.return_value = mock_completion

    client = LLMClient()
    resp = client.chat(
        system_prompt="You are helpful",
        user_prompt="Hello",
        response_format={"type": "json_object"},
    )

    assert resp.content == '{"key": "value"}'
    assert resp.tokens_used == 150
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "gpt-4o"
    assert call_kwargs["temperature"] == 0.7
    assert call_kwargs["response_format"] == {"type": "json_object"}


@patch("app.llm_client.OpenAI")
def test_chat_with_error_retry(mock_openai_class):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_client.chat.completions.create.side_effect = [
        APIConnectionError(message="API Error", request=MagicMock()),
        APIConnectionError(message="API Error again", request=MagicMock()),
    ]

    client = LLMClient()
    with pytest.raises(RuntimeError, match="LLM call failed after"):
        client.chat(system_prompt="test", user_prompt="test", max_retries=2)


@patch("app.llm_client.OpenAI")
def test_chat_retry_then_succeed(mock_openai_class):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_completion = MagicMock()
    mock_completion.choices = [MagicMock()]
    mock_completion.choices[0].message.content = "retry success"
    mock_completion.usage.total_tokens = 50

    mock_client.chat.completions.create.side_effect = [
        APIConnectionError(message="transient error", request=MagicMock()),
        mock_completion,
    ]

    client = LLMClient()
    resp = client.chat(system_prompt="test", user_prompt="test")

    assert resp.content == "retry success"
    assert mock_client.chat.completions.create.call_count == 2
