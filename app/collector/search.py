import asyncio
import random
from dataclasses import dataclass, field
from typing import List
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
    dom_hotwords: List[Hotword] = field(default_factory=list)
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
        logger.info("Searching keyword=%s page=%s (collected=%s)", keyword, page, len(result.cards))
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
        has_more = data.get("has_more", False)
        logger.debug("Page %s: items=%s has_more=%s model_types=%s",
                     page, len(items), has_more,
                     list(set(i.get("model_type","?") for i in items[:5])))

        if not items:
            break

        for item in items:
            model_type = item.get("model_type", "")
            if model_type == "hot_query":
                hq = item.get("hot_query", {})
                queries = hq.get("queries", [])
                for q in queries:
                    q_text = q.get("search_word", "")
                    if q_text and q_text not in hotwords_seen:
                        hotwords_seen.add(q_text)
                        result.hotwords.append(
                            Hotword(rank=len(result.hotwords) + 1, text=q_text)
                        )
            elif model_type not in ("rec_query",):
                if len(result.cards) >= max_notes:
                    continue
                note_id = item.get("id", "")
                xsec_token = item.get("xsec_token", "")
                note_card = item.get("note_card", item)
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

        if not has_more:
            break
        page += 1
        await asyncio.sleep(random.uniform(2, 4))

    logger.info(
        "Search done: keyword=%s hotwords=%s notes=%s",
        keyword, len(result.hotwords), len(result.cards),
    )
    return result
