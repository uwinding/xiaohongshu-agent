from dataclasses import dataclass, field
from typing import Dict, List
from app.collector.client import XhsApiClient

import logging

logger = logging.getLogger(__name__)


@dataclass
class Hotword:
    rank: int
    text: str


@dataclass
class NoteCard:
    note_id: str
    title: str
    xsec_token: str
    note_type: str = "normal"
    cover_url: str = ""


@dataclass
class SearchResult:
    keyword: str
    hotwords: List[Hotword] = field(default_factory=list)
    cards: List[NoteCard] = field(default_factory=list)
    has_more: bool = False


async def search_keyword(
    client: XhsApiClient,
    keyword: str,
    max_notes: int = 50,
    note_type: int = 2,
    sort: str = "time_filtered",
) -> SearchResult:
    result = SearchResult(keyword=keyword)
    hotwords_seen: set = set()
    page = 1
    xhs_limit = 20

    while len(result.cards) < max_notes:
        logger.info("Searching keyword=%s page=%s", keyword, page)
        try:
            data = await client.search_notes(
                keyword=keyword,
                page=page,
                page_size=xhs_limit,
                note_type=note_type,
                sort=sort,
            )
        except Exception as e:
            logger.error("Search failed for keyword=%s page=%s: %s", keyword, page, e)
            break

        items = data.get("items", [])
        if not items:
            break

        for item in items:
            model_type = item.get("model_type", "")
            if model_type == "hot_query":
                hotword_text = item.get("search_word", "")
                if hotword_text and hotword_text not in hotwords_seen:
                    hotwords_seen.add(hotword_text)
                    result.hotwords.append(
                        Hotword(rank=len(result.hotwords) + 1, text=hotword_text)
                    )
            elif model_type in ("note", "") or "note_card" in item:
                note_card = item.get("note_card", item)
                note_id = note_card.get("note_id", "") or note_card.get("id", "")
                xsec_token = item.get("xsec_token", "")
                title = note_card.get("display_title", "") or note_card.get("title", "")
                ntype = note_card.get("type", "normal")
                cover = note_card.get("cover", {})
                if isinstance(cover, dict):
                    cover = cover.get("url_default", "")

                if note_id:
                    result.cards.append(NoteCard(
                        note_id=note_id,
                        title=title,
                        xsec_token=xsec_token,
                        note_type=ntype,
                        cover_url=str(cover),
                    ))

        result.has_more = data.get("has_more", False)
        if not result.has_more:
            break
        page += 1

    logger.info(
        "Search done: keyword=%s hotwords=%s notes=%s",
        keyword, len(result.hotwords), len(result.cards),
    )
    return result
