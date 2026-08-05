import requests
import uuid
import base64
from pathlib import Path
import hashlib
from datetime import datetime, timezone
from openai import OpenAI
from app.skills.base import BaseSkill, SkillResult
from app.config import get_settings
from app.llm_client import LLMClient
from app.product_refs import is_direct_image_reference, normalize_reference


class ImageGenerator(BaseSkill):
    name = "image_generator"

    def __init__(self, llm_client: LLMClient, storage_dir: str | None = None):
        super().__init__(llm_client)
        self.storage_dir = Path(storage_dir or get_settings().storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._persona_seeds: dict[str, int] = {}

    def execute(
        self,
        pos_prompt: str = "",
        neg_prompt: str = "",
        persona_avatar: str = "",
        num_images: int = 3,
        reference_images: list[str | dict] | None = None,
        persona_name: str = "",
        persona_key: str = "",
        **kwargs,
    ) -> SkillResult:
        pos_prompt = pos_prompt or kwargs.get("pos_prompt", "")
        neg_prompt = neg_prompt or kwargs.get("neg_prompt", "")
        persona_avatar = persona_avatar or kwargs.get("persona_avatar", "")
        num_images = min(num_images, int(kwargs.get("num_images", 3)))
        reference_images = reference_images if reference_images is not None else kwargs.get("reference_images", [])
        persona_name = persona_name or kwargs.get("persona_name", "")
        persona_key = persona_key or kwargs.get("persona_key", "") or persona_name

        if not pos_prompt:
            return SkillResult(success=False, error="Missing pos_prompt")

        seed = self._get_persona_seed(persona_key)

        try:
            reference_specs = self._normalize_reference_specs(reference_images)
            prepared_references = self._prepare_reference_images(reference_specs)
            full_prompt = self._build_prompt(pos_prompt, neg_prompt, persona_avatar)
            full_prompt += self._reference_guide(prepared_references)
            image_paths = self._generate_images(full_prompt, num_images, prepared_references, seed)
            reference_manifest = [
                {key: value for key, value in item.items() if key != "data_url"}
                for item in prepared_references
            ]
            return SkillResult(success=True, data={
                "image_paths": image_paths,
                "num_generated": len(image_paths),
                "prompt_used": full_prompt,
                "seed": seed,
                "reference_manifest": reference_manifest,
            })
        except Exception as e:
            return SkillResult(success=False, error=str(e))

    def _get_persona_seed(self, persona_key: str) -> int | None:
        if not persona_key:
            return None
        if persona_key not in self._persona_seeds:
            digest = hashlib.sha256(persona_key.encode("utf-8")).digest()
            self._persona_seeds[persona_key] = int.from_bytes(digest[:4], "big") & 0x7FFFFFFF
        return self._persona_seeds[persona_key]

    def _build_prompt(self, pos: str, neg: str, avatar: str) -> str:
        prompt = (
            f"{pos}. Editorial quality, no visible text, no watermark, no logo, "
            "no caption, no poster typography, no storefront signage, no background lettering"
        )
        if avatar and avatar not in pos:
            prompt = f"Subject: {avatar}. " + prompt
        if neg:
            prompt += f". Avoid: {neg}, watermark, text, logo, Chinese characters, subtitles, signage"
        return prompt

    def _normalize_reference_specs(self, references: list[str | dict] | None) -> list[dict]:
        specs = []
        seen_sources = set()
        for index, item in enumerate(references or []):
            if isinstance(item, str):
                source = normalize_reference(item)
                raw_spec = {
                    "source": source,
                    "kind": "product",
                    "role": "product_reference",
                    "weight": 0.5,
                    "label": f"legacy_reference_{index + 1}",
                }
            elif isinstance(item, dict):
                source = normalize_reference(
                    str(item.get("source") or item.get("src") or item.get("path") or "")
                )
                raw_spec = {
                    "source": source,
                    "kind": str(item.get("kind") or "product"),
                    "role": str(item.get("role") or "product_reference"),
                    "weight": float(item.get("weight", 0.5)),
                    "label": str(item.get("label") or f"reference_{index + 1}"),
                }
                if item.get("product_id") is not None:
                    raw_spec["product_id"] = item["product_id"]
            else:
                continue
            if not source or source in seen_sources or not is_direct_image_reference(source):
                continue
            raw_spec["weight"] = round(max(0.0, min(1.0, raw_spec["weight"])), 2)
            seen_sources.add(source)
            specs.append(raw_spec)
        return specs[:6]

    def _prepare_reference_images(self, specs: list[dict]) -> list[dict]:
        prepared = []
        for spec in specs[:6]:
            data_url = self._load_ref_image(spec["source"])
            if not data_url:
                continue
            item = dict(spec)
            item["index"] = len(prepared) + 1
            item["data_url"] = data_url
            prepared.append(item)
        return prepared

    def _reference_guide(self, prepared_references: list[dict]) -> str:
        if not prepared_references:
            return ""
        parts = [
            ". Reference image control: each image has a distinct role; "
            "higher weight means stricter preservation."
        ]
        for item in prepared_references:
            kind = item["kind"]
            role = item["role"]
            if kind == "persona" and role == "face_identity":
                instruction = "preserve the same face, facial proportions, hairstyle, and age; ignore clothing/background"
            elif kind == "persona" and role == "body_proportion":
                instruction = "preserve body frame and proportions; ignore clothing/background"
            elif role == "primary_garment":
                instruction = "preserve garment category, silhouette, color, pattern, and material"
            elif role == "accessory":
                instruction = "preserve accessory shape, color, decoration, and left-right consistency"
            else:
                instruction = "use only for the labeled product appearance"
            parts.append(
                f"Image {item['index']} [{kind}/{role}, weight={item['weight']:.2f}, "
                f"label={item['label']}]: {instruction}."
            )
        return " " + " ".join(parts)

    def _load_ref_image(self, src: str) -> str | None:
        """Load reference image as base64 data URL for img2img."""
        if not src:
            return None
        src = normalize_reference(src)
        if not is_direct_image_reference(src):
            return None
        try:
            if src.startswith("http://") or src.startswith("https://"):
                resp = requests.get(src, timeout=30)
                resp.raise_for_status()
                raw_content_type = getattr(resp, "headers", {}).get("content-type", "")
                content_type = raw_content_type.split(";", 1)[0].lower() if isinstance(raw_content_type, str) else ""
                if content_type and not content_type.startswith("image/"):
                    return None
                img_data = resp.content
            elif Path(src).exists():
                img_data = Path(src).read_bytes()
            else:
                return None
            if not self._looks_like_image_bytes(img_data):
                return None
            b64 = base64.b64encode(img_data).decode("utf-8")
            ext = src.rsplit(".", 1)[-1].lower().split("?")[0] if "." in src else "png"
            mime = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "webp") else "image/png"
            return f"data:{mime};base64,{b64}"
        except Exception:
            return None

    def _looks_like_image_bytes(self, data: bytes) -> bool:
        return (
            data.startswith(b"\xff\xd8\xff")
            or data.startswith(b"\x89PNG\r\n\x1a\n")
            or data.startswith(b"RIFF") and data[8:12] == b"WEBP"
            or data.startswith(b"GIF87a")
            or data.startswith(b"GIF89a")
        )

    def _generate_images(
        self,
        prompt: str,
        num: int,
        prepared_references: list[dict] | None = None,
        seed: int | None = None,
    ) -> list[str]:
        settings = get_settings()
        client = OpenAI(api_key=settings.image_api_key, base_url=settings.image_base_url)
        model = settings.image_model
        size = self._select_size(model, settings.image_size)

        date_dir = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        dir_path = self.storage_dir / date_dir
        dir_path.mkdir(parents=True, exist_ok=True)

        ref_images_b64 = [item["data_url"] for item in (prepared_references or [])]

        paths = []
        for i in range(min(num, 4)):
            print(f"      生图 {i+1}/{min(num,4)}...")
            extra = {"watermark": False}
            if ref_images_b64:
                extra["image"] = ref_images_b64 if self._supports_multi_reference(model) else ref_images_b64[0]
            if seed is not None:
                extra["seed"] = seed

            response = client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
                size=size,
                response_format="url",
                extra_body=extra,
            )
            for img in response.data:
                if img.url:
                    img_data = requests.get(img.url, timeout=30)
                    img_data.raise_for_status()
                    filename = f"{uuid.uuid4().hex[:12]}{self._image_extension(img_data)}"
                    filepath = dir_path / filename
                    with open(filepath, 'wb') as f:
                        f.write(img_data.content)
                    paths.append(str(filepath))

        return paths

    def _supports_multi_reference(self, model: str) -> bool:
        model_lower = (model or "").lower()
        return "seedream" in model_lower or "doubao" in model_lower

    def _select_size(self, model: str, configured_size: str = "") -> str:
        if configured_size:
            return configured_size
        model_lower = (model or "").lower()
        if "seedream" in model_lower or "doubao" in model_lower:
            return "1536x2560"
        if "dall-e" in model_lower:
            return "1024x1792"
        return "1024x1536"

    def _image_extension(self, response) -> str:
        raw_content_type = getattr(response, "headers", {}).get("content-type", "")
        content_type = raw_content_type.split(";", 1)[0].lower() if isinstance(raw_content_type, str) else ""
        if content_type == "image/png":
            return ".png"
        if content_type in {"image/jpeg", "image/jpg"}:
            return ".jpg"
        if content_type == "image/webp":
            return ".webp"

        data = getattr(response, "content", b"")
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return ".png"
        if data.startswith(b"\xff\xd8\xff"):
            return ".jpg"
        if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
            return ".webp"
        return ".png"
