from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from app.llm_client import LLMClient


@dataclass
class SkillResult:
    success: bool
    data: Any = None
    error: str = ""
    metadata: dict = field(default_factory=dict)


class BaseSkill(ABC):
    name: str = "base"

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    @abstractmethod
    def execute(self, **kwargs) -> SkillResult:
        raise NotImplementedError

    def _llm_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> dict:
        import json
        resp = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format={"type": "json_object"},
            temperature=temperature,
        )
        try:
            return json.loads(resp.content)
        except json.JSONDecodeError:
            return {"raw": resp.content}
