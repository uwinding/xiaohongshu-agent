import asyncio
import uuid
import random
import logging
from typing import List

from app.collector.browser import CollectorBrowser
from app.collector.client import XhsApiClient
from app.collector.config import CollectorConfig
from app.collector.search import search_keyword, SearchResult
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


async def run_collect(keywords: List[str], config: CollectorConfig = None) -> List[SearchResult]:
    config = config or CollectorConfig()
    browser = CollectorBrowser(config)

    try:
        await browser.start()
        await browser.ensure_logged_in()
        cookie_str = await browser.get_cookie_string()
        client = XhsApiClient(cookie_str, config)

        if not await client.check_login():
            logger.warning("Login check via API failed, proceeding anyway...")

        all_results = []
        for keyword in keywords:
            result = await _collect_keyword(client, keyword, config)
            all_results.append(result)
            await asyncio.sleep(random.uniform(3, 5))

        return all_results
    finally:
        await browser.close()


async def _collect_keyword(
    client: XhsApiClient, keyword: str, config: CollectorConfig
) -> SearchResult:
    task_id = uuid.uuid4().hex[:16]
    save_task(task_id, keyword, "running")

    try:
        result = await search_keyword(
            client, keyword, max_notes=config.max_notes_per_keyword
        )

        notes: List[NoteDetail] = []
        semaphore = asyncio.Semaphore(config.max_concurrency)

        async def fetch_one(card):
            async with semaphore:
                return await fetch_note_detail(client, card.note_id, card.xsec_token)

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
            await asyncio.sleep(random.uniform(1, 3))

        export_csv(result, notes)
        export_json(result, notes)

        update_task(task_id, "done", notes_found=len(result.cards), notes_saved=saved_count)
        logger.info("Keyword '%s' done: %d found, %d saved", keyword, len(result.cards), saved_count)
        return result

    except Exception as e:
        logger.error("Keyword '%s' failed: %s", keyword, e)
        update_task(task_id, "failed", error_msg=str(e))
        raise
