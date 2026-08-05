import asyncio
import uuid
import random
import logging
from typing import List, Optional

from app.collector.browser import CollectorBrowser
from app.collector.client import XhsApiClient
from app.collector.config import CollectorConfig
from app.collector.exceptions import LoginExpired
from app.collector.hotword_dom import extract_dom_hotwords
from app.collector.search import search_keyword, SearchResult, Hotword
from app.collector.note_detail import fetch_note_detail, NoteDetail
from app.collector.ranking import select_top_recent_notes
from app.collector.candidates import parse_search_sorts, merge_search_result
from app.collector.store import (
    save_task,
    update_task,
    save_note,
    save_snapshot,
    save_hotword_observations,
    save_note_observation,
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
            raise LoginExpired("Cookie login check failed — cookie may be expired or invalid")
        return await _collect_keywords(client, keywords, config, cookie_str, fetch_page_hotwords)

    browser = CollectorBrowser(config)
    try:
        await browser.start()
        await browser.ensure_logged_in()
        cookie_str = await browser.get_cookie_string()
        client = XhsApiClient(cookie_str, config)

        if not await client.check_login():
            raise LoginExpired("API login check failed after browser login — cookie extraction may be incomplete")

        return await _collect_keywords(client, keywords, config, cookie_str, fetch_page_hotwords, browser)
    finally:
        await browser.close()


async def _collect_keywords(
    client: XhsApiClient, keywords: List[str], config: CollectorConfig,
    cookie_str: str = "", fetch_page_hotwords: bool = False,
    browser: Optional[CollectorBrowser] = None,
) -> List[SearchResult]:
    results = []
    seen_note_ids: set[str] = set()
    expanded_keywords: set[str] = set(keywords)
    for keyword in keywords:
        try:
            result = await _collect_keyword(
                client, keyword, config, cookie_str, fetch_page_hotwords, browser, seen_note_ids
            )
            results.append(result)
            if config.expand_page_hotwords_limit > 0:
                for hotword in result.dom_hotwords[:config.expand_page_hotwords_limit]:
                    expanded = hotword.text.strip()
                    if not expanded or expanded in expanded_keywords:
                        continue
                    expanded_keywords.add(expanded)
                    try:
                        expanded_result = await _collect_keyword(
                            client, expanded, config, cookie_str, False, browser, seen_note_ids
                        )
                        results.append(expanded_result)
                    except Exception as e:
                        logger.error("Expanded keyword '%s' failed: %s", expanded, e)
                        results.append(SearchResult(keyword=expanded))
                    await asyncio.sleep(random.uniform(3, 5))
        except Exception as e:
            logger.error("Keyword '%s' failed: %s", keyword, e)
            results.append(SearchResult(keyword=keyword))
        await asyncio.sleep(random.uniform(3, 5))
    return results


async def _collect_keyword(
    client: XhsApiClient, keyword: str, config: CollectorConfig,
    cookie_str: str = "", fetch_page_hotwords: bool = False,
    browser: Optional[CollectorBrowser] = None,
    seen_note_ids: Optional[set[str]] = None,
) -> SearchResult:
    task_id = uuid.uuid4().hex[:16]
    save_task(task_id, keyword, "running")

    try:
        result = await search_candidate_pool(client, keyword, config)
        save_hotword_observations(task_id, keyword, result.hotwords, source="api_hot_query")

        dom_hotwords: List[Hotword] = []
        if fetch_page_hotwords:
            try:
                dom_hotwords = await extract_dom_hotwords(keyword, config, cookie_str, browser=browser)
                result.dom_hotwords = dom_hotwords
                logger.info("DOM hotwords: %s", [h.text for h in dom_hotwords])
                save_hotword_observations(task_id, keyword, dom_hotwords, source="dom_tab")
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
        selected_details = select_top_recent_notes(
            [detail for detail in detail_results if detail is not None],
            recent_days=config.recent_days,
            top_per_metric=config.top_per_metric,
        )
        if seen_note_ids is not None:
            deduped_details = []
            for detail in selected_details:
                if detail.note_id in seen_note_ids:
                    continue
                seen_note_ids.add(detail.note_id)
                deduped_details.append(detail)
            selected_details = deduped_details

        saved_count = 0
        for detail in selected_details:
            save_note_observation(task_id, keyword, detail)
            is_new = save_note(detail)
            if is_new:
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


async def search_candidate_pool(
    client: XhsApiClient,
    keyword: str,
    config: CollectorConfig,
) -> SearchResult:
    sorts = parse_search_sorts(config.search_sorts)
    if not sorts:
        sorts = ["time_filtered"]

    merged = SearchResult(keyword=keyword)
    seen_hotwords: set[str] = set()
    seen_cards: set[str] = set()
    for sort in sorts:
        result = await search_keyword(
            client,
            keyword,
            max_notes=config.max_notes_per_keyword,
            sort=sort,
        )
        merge_search_result(merged, result, seen_hotwords, seen_cards)
        await asyncio.sleep(random.uniform(1, 2))
    return merged

