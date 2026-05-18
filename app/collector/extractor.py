import re
import hashlib
from typing import List


def extract_tags(content: str) -> List[str]:
    tags = re.findall(r"#([^\s#]+)", content)
    seen: set = set()
    result = []
    for tag in tags:
        tag_clean = tag.strip()
        if tag_clean and tag_clean not in seen:
            seen.add(tag_clean)
            result.append(f"#{tag_clean}")
    return result


def clean_content(raw: str) -> str:
    text = raw.strip()
    text = re.sub(r"(\xa0|\u3000)+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def compute_content_hash(content: str) -> str:
    normalized = re.sub(r"\s+", "", content).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
