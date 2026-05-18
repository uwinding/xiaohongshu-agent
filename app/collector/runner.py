import asyncio
import uuid
import random
import logging
from typing import List, Optional

from app.collector.browser import CollectorBrowser
from app.collector.client import XhsApiClient
from app.collector.config import CollectorConfig
from app.collector.hotword_dom import extract_dom_hotwords
from app.collector.search import search_keyword, SearchResult, Hotword
from app.collector.note_detail import fetch_note_detail, NoteDetail
from app.collector.store import (
    save_task,
    update_task,
    save_note,
    save_snapshot,
    export_csv,
    export_json,
)

logger = logging.getLogger(__name__)


async def run_collect(
    keywords: List[str],
    config: Optional[CollectorConfig] = None,
    cookie_str: str = "",
    fetch_page_hotwords: bool = False,
) -> List[SearchResult]:
    config = config or CollectorConfig()

    if cookie_str:
        client = XhsApiClient(cookie_str, config)
        if not await client.check_login():
            logger.warning("Cookie login check failed, proceeding anyway...")
        return await _collect_keywords(client, keywords, config, cookie_str, fetch_page_hotwords)

    browser = CollectorBrowser(config)
    try:
        await browser.start()
        await browser.ensure_logged_in()
        cookie_str = await browser.get_cookie_string()
        client = XhsApiClient(cookie_str, config)

        if not await client.check_login():
            logger.warning("Login check via API failed, proceeding anyway...")

        return await _collect_keywords(client, keywords, config, cookie_str, fetch_page_hotwords)
    finally:
        await browser.close()


async def _collect_keywords(
    client: XhsApiClient, keywords: List[str], config: CollectorConfig,
    cookie_str: str = "", fetch_page_hotwords: bool = False,
) -> List[SearchResult]:
    results = []
    for keyword in keywords:
        try:
            result = await _collect_keyword(client, keyword, config, cookie_str, fetch_page_hotwords)
            results.append(result)
        except Exception as e:
            logger.error("Keyword '%s' failed: %s", keyword, e)
            results.append(SearchResult(keyword=keyword))
        await asyncio.sleep(random.uniform(3, 5))
    return results


async def _collect_keyword(
    client: XhsApiClient, keyword: str, config: CollectorConfig,
    cookie_str: str = "", fetch_page_hotwords: bool = False,
) -> SearchResult:
    task_id = uuid.uuid4().hex[:16]
    save_task(task_id, keyword, "running")

    try:
        result = await search_keyword(
            client, keyword, max_notes=config.max_notes_per_keyword
        )

        dom_hotwords: List[Hotword] = []
        if fetch_page_hotwords:
            try:
                dom_hotwords = await extract_dom_hotwords(keyword, config, cookie_str)
                logger.info("DOM hotwords: %s", [h.text for h in dom_hotwords])
                dom_texts = {h.text for h in dom_hotwords}
                api_texts = {h.text for h in result.hotwords}
                for h in dom_hotwords:
                    if h.text not in api_texts:
                        result.hotwords.append(Hotword(rank=len(result.hotwords) + 1, text=h.text))
            except Exception as e:
                logger.warning("DOM hotword extraction failed: %s", e)

        notes: List[NoteDetail] = []
        semaphore = asyncio.Semaphore(config.max_concurrency)

        async def fetch_one(card):
            async with semaphore:
                try:
                    return await fetch_note_detail(client, card.note_id, card.xsec_token)
                except Exception as e:
                    logger.warning("Note detail fetch failed for %s: %s", card.note_id, e)
                    return None

        tasks = [fetch_one(card) for card in result.cards]
        detail_results = await asyncio.gather(*tasks)

        saved_count = 0
        for detail in detail_results:
            if detail is None:
                continue
            if save_note(detail):
                saved_count += 1
            save_snapshot(task_id, detail, keyword, result.hotwords)
            notes.append(detail)
            await asyncio.sleep(random.uniform(1.5, 3))

        export_csv(result, notes)
        export_json(result, notes)

        update_task(task_id, "done", notes_found=len(result.cards), notes_saved=saved_count)
        logger.info("Keyword '%s' done: %d found, %d saved", keyword, len(result.cards), saved_count)
        return result

    except Exception as e:
        logger.error("Keyword '%s' failed: %s", keyword, e)
        update_task(task_id, "failed", error_msg=str(e))
        raise
