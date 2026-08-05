from pathlib import Path

from app.persona_assets import PersonaAssetRegistry


PROFILE_PATH = Path("data/personas/xiaolu/profile.yaml")


def test_persona_registry_loads_prompts_and_priority_references():
    registry = PersonaAssetRegistry(PROFILE_PATH)

    context = registry.context_for_persona("小鹿")
    references = registry.reference_specs_for_persona("小鹿")

    assert context["persona_key"] == "xiaolu_summer"
    assert "short bob haircut" in context["identity_prompt"]
    assert "petite and slim figure" in context["body_prompt"]
    assert "full body outfit photo" in context["photo_prompt"]
    assert "tall supermodel body" in context["negative_identity_prompt"]

    assert [item["role"] for item in references] == [
        "face_identity",
        "face_identity",
        "body_proportion",
    ]
    assert [item["weight"] for item in references] == [1.0, 0.95, 0.85]
    assert all(Path(item["source"]).is_file() for item in references)


def test_persona_registry_supports_legacy_name_but_not_other_personas():
    registry = PersonaAssetRegistry(PROFILE_PATH)

    assert registry.context_for_persona("小鹿学姐")["persona_key"] == "xiaolu_summer"
    assert registry.context_for_persona("测试博主") == {}
    assert registry.reference_specs_for_persona("测试博主") == []
