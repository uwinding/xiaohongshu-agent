import asyncio
import os
from typing import Optional
from playwright.async_api import (
    async_playwright,
    BrowserContext,
    BrowserType,
    Page,
    Playwright,
)
from app.collector.config import CollectorConfig
from app.collector.exceptions import LoginExpired

import logging

logger = logging.getLogger(__name__)


class CollectorBrowser:
    def __init__(self, config: Optional[CollectorConfig] = None):
        self.config = config or CollectorConfig()
        self.playwright: Optional[Playwright] = None
        self.browser_context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def start(self) -> Page:
        self.playwright = await async_playwright().start()
        chromium = self.playwright.chromium
        self.browser_context = await self._launch_persistent(chromium)
        self.page = await self.browser_context.new_page()
        return self.page

    async def _launch_persistent(self, chromium: BrowserType) -> BrowserContext:
        user_data_dir = os.path.join(os.getcwd(), "data", "browser_data")
        os.makedirs(user_data_dir, exist_ok=True)

        logger.info("Launching persistent browser context (headless=%s)", self.config.headless)
        return await chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=self.config.headless,
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        )

    async def ensure_logged_in(self) -> None:
        page = self.page
        await page.goto(self.config.xhs_domain, wait_until="domcontentloaded")
        await asyncio.sleep(2)

        if await self._check_login_status():
            logger.info("Already logged in")
            return

        logger.info("Waiting for QR code login...")
        await self._trigger_qrcode_login()
        await self._wait_for_qrcode_login()
        await self.save_storage_state()

    async def _check_login_status(self) -> bool:
        try:
            await self.page.wait_for_selector(
                "xpath=//a[contains(@href, '/user/profile/')]//span[text()='我']",
                timeout=5000,
            )
            return True
        except Exception:
            return False

    async def _trigger_qrcode_login(self) -> None:
        try:
            login_btn = self.page.locator(
                "xpath=//*[@id='app']/div[1]/div[2]/div[1]/ul/div[1]/button"
            )
            await login_btn.click(timeout=5000)
        except Exception:
            pass

    async def _wait_for_qrcode_login(self, timeout: int = 120) -> None:
        page = self.page
        start = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start) < timeout:
            if await self._check_login_status():
                logger.info("Login successful via QR code")
                return
            await asyncio.sleep(2)

        raise LoginExpired("QR code login timed out after %s seconds" % timeout)

    async def save_storage_state(self) -> None:
        await self.browser_context.storage_state(path=self.config.storage_state_path)
        logger.info("Storage state saved to %s", self.config.storage_state_path)

    async def get_cookie_string(self, urls: Optional[list[str]] = None) -> str:
        if urls is None:
            urls = [self.config.xhs_domain]
        cookies = await self.browser_context.cookies(urls)
        return "; ".join(f"{c['name']}={c['value']}" for c in cookies)

    async def close(self) -> None:
        if self.browser_context:
            await self.browser_context.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")
