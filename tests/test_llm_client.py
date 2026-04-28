import pytest
from unittest.mock import patch, MagicMock
from app.llm_client import LLMClient, LLMResponse


def test_llm_client_initialization():
    client = LLMClient(api_key="test-key", model="gpt-4o")
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

    client = LLMClient(api_key="test-key")
    resp = client.chat(
        system_prompt="You are helpful",
        user_prompt="Hello",
        response_format={"type": "json_object"},
    )

    assert resp.content == '{"key": "value"}'
    assert resp.tokens_used == 150


@patch("app.llm_client.OpenAI")
def test_chat_with_error_retry(mock_openai_class):
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client

    mock_client.chat.completions.create.side_effect = [
        Exception("API Error"),
        Exception("API Error again"),
    ]

    client = LLMClient(api_key="test-key")
    with pytest.raises(RuntimeError, match="LLM call failed after"):
        client.chat(system_prompt="test", user_prompt="test", max_retries=2)
