from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import Dict, Optional

from app.collector.client import XhsApiClient
from app.collector.extractor import extract_tags, clean_content, compute_content_hash

import logging

logger = logging.getLogger(__name__)


@dataclass
class NoteDetail:
    note_id: str
    title: str = ""
    content_raw: str = ""
    content_clean: str = ""
    content_hash: str = ""
    author_id: str = ""
    author_name: str = ""
    publish_time: str = ""
    like_count: int = 0
    collect_count: int = 0
    comment_count: int = 0
    note_type: str = "normal"
    tags: list = field(default_factory=list)
    source_url: str = ""


def _ts_to_iso(ts_ms: int) -> str:
    if ts_ms and ts_ms > 0:
        return datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).isoformat()
    return ""


def _parse_count(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if not value:
        return 0
    s = str(value).strip().rstrip("+")
    if not s:
        return 0
    if "万" in s:
        return int(float(s.replace("万", "")) * 10000)
    if "千" in s:
        return int(float(s.replace("千", "")) * 1000)
    try:
        return int(float(s))
    except ValueError:
        return 0


async def fetch_note_detail(
    client: XhsApiClient,
    note_id: str,
    xsec_token: str,
    xsec_source: str = "pc_search",
) -> Optional[NoteDetail]:
    try:
        data = await client.get_note_detail(note_id, xsec_token, xsec_source)
    except Exception as e:
        logger.warning("Failed to fetch note detail for %s: %s", note_id, e)
        return None

    if not data:
        return None

    title = data.get("display_title", "") or data.get("title", "")
    desc = data.get("desc", "")
    content_raw = f"{title}\n{desc}".strip()

    interact = data.get("interact_info", {})
    user_info = data.get("user", {})

    tags = []
    raw_tags = data.get("tag_list", [])
    for t in raw_tags:
        tag_name = t.get("name", "")
        if tag_name:
            tags.append(f"#{tag_name}")
    content_tags = extract_tags(desc)
    for t in content_tags:
        if t not in tags:
            tags.append(t)

    content_clean = clean_content(content_raw)
    content_hash = compute_content_hash(content_clean)

    note_type_val = data.get("type", "normal")
    if note_type_val == "video":
        note_type_val = "video"
    else:
        note_type_val = "normal"

    source_url = f"https://www.xiaohongshu.com/explore/{note_id}"

    return NoteDetail(
        note_id=note_id,
        title=title,
        content_raw=content_raw,
        content_clean=content_clean,
        content_hash=content_hash,
        author_id=user_info.get("user_id", "") or user_info.get("id", ""),
        author_name=user_info.get("nickname", "") or user_info.get("name", ""),
        publish_time=_ts_to_iso(data.get("time", 0)),
        like_count=_parse_count(interact.get("liked_count", 0)),
        collect_count=_parse_count(interact.get("collected_count", 0)),
        comment_count=_parse_count(interact.get("comment_count", 0)),
        note_type=note_type_val,
        tags=tags,
        source_url=source_url,
    )
