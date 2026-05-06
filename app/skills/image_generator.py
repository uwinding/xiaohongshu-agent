import requests
import uuid
from pathlib import Path
from datetime import datetime, timezone
from openai import OpenAI
from app.skills.base import BaseSkill, SkillResult
from app.config import get_settings
from app.llm_client import LLMClient


class ImageGenerator(BaseSkill):
    name = "image_generator"

    def __init__(self, llm_client: LLMClient, storage_dir: str | None = None):
        super().__init__(llm_client)
        self.storage_dir = Path(storage_dir or get_settings().storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def execute(self, pos_prompt: str = "", neg_prompt: str = "", persona_avatar: str = "", num_images: int = 3, **kwargs) -> SkillResult:
        pos_prompt = pos_prompt or kwargs.get("pos_prompt", "")
        neg_prompt = neg_prompt or kwargs.get("neg_prompt", "")
        persona_avatar = persona_avatar or kwargs.get("persona_avatar", "")
        num_images = min(num_images, int(kwargs.get("num_images", 3)))

        if not pos_prompt:
            return SkillResult(success=False, error="Missing pos_prompt")

        full_prompt = self._build_prompt(pos_prompt, neg_prompt, persona_avatar)

        try:
            image_paths = self._generate_images(full_prompt, num_images)
            return SkillResult(success=True, data={"image_paths": image_paths, "num_generated": len(image_paths), "prompt_used": full_prompt})
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _build_prompt(self, pos: str, neg: str, avatar: str) -> str:
        prompt = pos
        if avatar:
            prompt = f"Subject: {avatar}. " + prompt
        if neg:
            prompt += f" --no {neg}"
        return prompt

    def _generate_images(self, prompt: str, num: int) -> list[str]:
        settings = get_settings()
        client = OpenAI(api_key=settings.image_api_key, base_url=settings.image_base_url)
        model = settings.image_model

        date_dir = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        dir_path = self.storage_dir / date_dir
        dir_path.mkdir(parents=True, exist_ok=True)

        paths = []
        for i in range(min(num, 3)):
            print(f"      生图 {i+1}/{min(num,3)}...")
            response = client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
                size="2K",
                extra_body={"watermark": False},
            )
            for img in response.data:
                if img.url:
                    img_data = requests.get(img.url, timeout=30)
                    img_data.raise_for_status()
                    filename = f"{uuid.uuid4().hex[:12]}.png"
                    filepath = dir_path / filename
                    with open(filepath, 'wb') as f:
                        f.write(img_data.content)
                    paths.append(str(filepath))

        return paths
