"""Extract hot words from XHS search page DOM using Playwright.

These are the filter-tab buttons (搜索筛选词) rendered on the search page,
not the "大家都在搜" hot_query items from the API.
"""

import asyncio
from typing import List, Optional

from app.collector.browser import CollectorBrowser
from app.collector.config import CollectorConfig
from app.collector.search import Hotword

import logging

logger = logging.getLogger(__name__)

_HOT_TAB_SELECTOR = "div.content-container button.tab"


async def extract_dom_hotwords(
    keyword: str,
    config: Optional[CollectorConfig] = None,
    cookie_str: str = "",
    browser: Optional[CollectorBrowser] = None,
) -> List[Hotword]:
    """Open XHS search page and extract hot word tabs from DOM.

    Args:
        keyword: Search keyword
        config: Collector config
        cookie_str: Cookie string (if already logged in)
        browser: Reuse existing browser if provided (avoids profile lock)

    Returns:
        List of Hotword objects
    """
    config = config or CollectorConfig()
    own_browser = browser is None
    if own_browser:
        browser = CollectorBrowser(config)

    try:
        if own_browser:
            await browser.start()
        page = browser.page

        if cookie_str:
            cookies_list = []
            for item in cookie_str.split("; "):
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookies_list.append({
                        "name": k,
                        "value": v,
                        "domain": ".xiaohongshu.com",
                        "path": "/",
                    })
            await browser.browser_context.add_cookies(cookies_list)

        from urllib.parse import quote
        encoded_kw = quote(keyword)
        url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_kw}&type=2&sort=time_filtered"
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(3)

        tabs = await page.query_selector_all(_HOT_TAB_SELECTOR)
        hotwords = []
        seen = set()
        rank = 0
        for tab in tabs:
            text = (await tab.inner_text()).strip()
            if text and text != "综合" and text not in seen:
                seen.add(text)
                rank += 1
                hotwords.append(Hotword(rank=rank, text=text))

        logger.info("DOM hotwords extracted: %d words for keyword='%s'", len(hotwords), keyword)
        return hotwords
    finally:
        if own_browser:
            await browser.close()
