from pathlib import Path

import yaml

from scripts.seed import load_persona_seed_data


PROFILE_PATH = Path("data/personas/xiaolu/profile.yaml")


def test_xiaolu_profile_maps_to_main_persona_fields():
    data, legacy_names = load_persona_seed_data(PROFILE_PATH)

    assert data["name"] == "小鹿"
    assert data["age_range"] == "20-24"
    assert data["body_type"] == "小个子"
    assert data["size_category"] == "XS-S"
    assert data["height"] == "158cm"
    assert "韩系" in data["style_tags"]
    assert "短波波头" in data["avatar_desc"]
    assert "小鹿学姐" in legacy_names


def test_xiaolu_profile_reference_files_exist():
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    refs = profile["references"]["face"] + profile["references"]["body"]

    assert len(refs) == 4
    assert all((PROFILE_PATH.parent / item["path"]).is_file() for item in refs)
