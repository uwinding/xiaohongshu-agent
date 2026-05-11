import requests
import uuid
import base64
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
        self._persona_seeds: dict[str, int] = {}

    def execute(self, pos_prompt: str = "", neg_prompt: str = "", persona_avatar: str = "", num_images: int = 3, reference_images: list[str] | None = None, persona_name: str = "", **kwargs) -> SkillResult:
        pos_prompt = pos_prompt or kwargs.get("pos_prompt", "")
        neg_prompt = neg_prompt or kwargs.get("neg_prompt", "")
        persona_avatar = persona_avatar or kwargs.get("persona_avatar", "")
        num_images = min(num_images, int(kwargs.get("num_images", 3)))
        reference_images = reference_images or kwargs.get("reference_images", [])
        persona_name = persona_name or kwargs.get("persona_name", "")

        if not pos_prompt:
            return SkillResult(success=False, error="Missing pos_prompt")

        full_prompt = self._build_prompt(pos_prompt, neg_prompt, persona_avatar)

        seed = self._get_persona_seed(persona_name)

        try:
            image_paths = self._generate_images(full_prompt, num_images, reference_images, seed)
            return SkillResult(success=True, data={"image_paths": image_paths, "num_generated": len(image_paths), "prompt_used": full_prompt, "seed": seed})
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _get_persona_seed(self, persona_name: str) -> int | None:
        if not persona_name:
            return None
        if persona_name not in self._persona_seeds:
            self._persona_seeds[persona_name] = abs(hash(persona_name)) % (2**31)
        return self._persona_seeds[persona_name]

    def _build_prompt(self, pos: str, neg: str, avatar: str) -> str:
        prompt = pos
        if avatar:
            prompt = f"Subject: {avatar}. " + prompt
        if neg:
            prompt += f". Avoid: {neg}"
        return prompt

    def _load_ref_image(self, src: str) -> str | None:
        """Load reference image as base64 data URL for img2img."""
        if not src:
            return None
        try:
            if src.startswith("http://") or src.startswith("https://"):
                resp = requests.get(src, timeout=30)
                resp.raise_for_status()
                img_data = resp.content
            elif Path(src).exists():
                img_data = Path(src).read_bytes()
            else:
                return None
            b64 = base64.b64encode(img_data).decode("utf-8")
            ext = src.rsplit(".", 1)[-1].lower().split("?")[0] if "." in src else "png"
            mime = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "webp") else "image/png"
            return f"data:{mime};base64,{b64}"
        except Exception:
            return None

    def _generate_images(self, prompt: str, num: int, reference_images: list[str] | None = None, seed: int | None = None) -> list[str]:
        settings = get_settings()
        client = OpenAI(api_key=settings.image_api_key, base_url=settings.image_base_url)
        model = settings.image_model

        date_dir = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        dir_path = self.storage_dir / date_dir
        dir_path.mkdir(parents=True, exist_ok=True)

        # Load reference image for img2img (use first available product image)
        ref_image_b64 = None
        if reference_images:
            for src in reference_images:
                ref_image_b64 = self._load_ref_image(src)
                if ref_image_b64:
                    break

        paths = []
        for i in range(min(num, 4)):
            print(f"      生图 {i+1}/{min(num,4)}...")
            extra = {"watermark": False}
            if ref_image_b64:
                extra["image"] = ref_image_b64
            if seed is not None:
                extra["seed"] = seed

            response = client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
                size="1024x1536",
                response_format="url",
                extra_body=extra,
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
