from dataclasses import dataclass
import time
from openai import OpenAI, APIError, APIConnectionError, RateLimitError
from app.config import get_settings


@dataclass
class LLMResponse:
    content: str
    model: str
    tokens_used: int = 0


class LLMClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = api_key or settings.llm_api_key
        self.base_url = base_url or settings.llm_base_url
        self.model = model or settings.llm_model
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def chat(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict | None = None,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> LLMResponse:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        last_error = None
        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                completion = self.client.chat.completions.create(**kwargs)
                content = completion.choices[0].message.content or ""
                tokens = completion.usage.total_tokens if completion.usage else 0
                return LLMResponse(content=content, model=self.model, tokens_used=tokens)
            except (APIError, APIConnectionError, RateLimitError) as e:
                last_error = e
                time.sleep(2 ** attempt)
                continue

        raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_error}")
