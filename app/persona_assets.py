"""Persona prompts and reference-image assets used by image generation."""

from __future__ import annotations

from pathlib import Path

import yaml

from app.config import get_settings
from app.product_refs import is_direct_image_reference


class PersonaAssetRegistry:
    def __init__(self, profile_path: str | Path | None = None):
        settings = get_settings()
        self.profile_path = Path(profile_path or settings.persona_profile_path)
        self._profile: dict | None = None

    def load(self) -> dict:
        if self._profile is None:
            if not self.profile_path.exists():
                self._profile = {}
            else:
                data = yaml.safe_load(self.profile_path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError(f"Persona profile must be a mapping: {self.profile_path}")
                self._profile = data
        return self._profile

    def matches_persona(self, persona_name: str) -> bool:
        profile = self.load()
        names = [profile.get("name", ""), *(profile.get("legacy_names") or [])]
        return bool(persona_name and persona_name in names)

    def context_for_persona(self, persona_name: str) -> dict:
        if not self.matches_persona(persona_name):
            return {}
        profile = self.load()
        image_generation = profile.get("image_generation") or {}
        return {
            "persona_key": profile.get("id") or profile.get("name") or persona_name,
            "identity_prompt": self._compact(
                image_generation.get("character_lock_prompt_en")
                or image_generation.get("character_lock_prompt_cn", "")
            ),
            "body_prompt": self._compact(image_generation.get("body_lock_prompt_en", "")),
            "photo_prompt": self._compact(image_generation.get("photo_fixed_prompt_en", "")),
            "negative_identity_prompt": self._compact(
                image_generation.get("negative_prompt_en")
                or image_generation.get("negative_prompt_cn", "")
            ),
        }

    def reference_specs_for_persona(
        self,
        persona_name: str,
        face_limit: int = 2,
        body_limit: int = 1,
    ) -> list[dict]:
        if not self.matches_persona(persona_name):
            return []
        references = self.load().get("references") or {}
        specs = []
        specs.extend(
            self._reference_group(
                references.get("face") or [],
                kind="persona",
                role="face_identity",
                default_weight=1.0,
                limit=face_limit,
            )
        )
        specs.extend(
            self._reference_group(
                references.get("body") or [],
                kind="persona",
                role="body_proportion",
                default_weight=0.85,
                limit=body_limit,
            )
        )
        return specs

    def _reference_group(
        self,
        items: list,
        kind: str,
        role: str,
        default_weight: float,
        limit: int,
    ) -> list[dict]:
        normalized = []
        sorted_items = sorted(
            (item for item in items if isinstance(item, dict)),
            key=lambda item: int(item.get("priority", 99)),
        )
        for index, item in enumerate(sorted_items[:limit]):
            raw_path = str(item.get("path") or "").strip()
            source = self.profile_path.parent / raw_path
            if not raw_path or not source.is_file() or not is_direct_image_reference(str(source)):
                continue
            normalized.append({
                "source": str(source),
                "kind": kind,
                "role": role,
                "weight": float(item.get("weight", max(0.5, default_weight - index * 0.05))),
                "label": f"{role}:{item.get('view', index + 1)}",
            })
        return normalized

    def _compact(self, value: str) -> str:
        return " ".join((value or "").split())
