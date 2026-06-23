import time
import random
import asyncio
from typing import Dict, Optional, Any

import httpx

from app.collector.config import CollectorConfig
from app.collector.exceptions import DataFetchError, NoteNotFound, RateLimitError

import logging

logger = logging.getLogger(__name__)


class XhsApiClient:

    def __init__(self, cookie_str: str, config: Optional[CollectorConfig] = None):
        self.config = config or CollectorConfig()
        self._host = self.config.xhs_api_host
        self._domain = self.config.xhs_domain
        self._cookie_str = cookie_str
        self._cookie_dict = self._parse_cookies(cookie_str)
        self._timeout = 30

    @staticmethod
    def _parse_cookies(cookie_str: str) -> dict:
        result = {}
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                result[k.strip()] = v.strip()
        return result

    def _sign(self, uri: str, data: Optional[Dict] = None, method: str = "POST") -> Dict[str, str]:
        from xhshow import Xhshow

        xhshow_client = Xhshow()
        is_post = method.upper() == "POST"

        if is_post:
            headers = xhshow_client.sign_headers_post(
                uri=uri,
                cookies=self._cookie_str,
                payload=data if isinstance(data, dict) else {},
            )
        else:
            headers = xhshow_client.sign_headers_get(
                uri=uri,
                cookies=self._cookie_str,
                params=data if isinstance(data, dict) else None,
            )

        return {
            "x-s": headers.get("x-s", ""),
            "x-t": headers.get("x-t", ""),
            "x-s-common": headers.get("x-s-common", ""),
            "x-b3-traceid": headers.get("x-b3-traceid", self._gen_trace_id()),
        }

    @staticmethod
    def _gen_trace_id() -> str:
        return "".join(random.choice("abcdef0123456789") for _ in range(16))

    @staticmethod
    def _gen_search_id() -> str:
        e = int(time.time() * 1000) << 64
        t = int(random.uniform(0, 2147483646))
        num = e + t
        alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        if num == 0:
            return "0"
        base36 = ""
        while num != 0:
            num, i = divmod(num, len(alphabet))
            base36 = alphabet[i] + base36
        return base36

    def _base_headers(self) -> Dict[str, str]:
        return {
            "accept": "application/json, text/plain, */*",
            "accept-language": "zh-CN,zh;q=0.9",
            "content-type": "application/json;charset=UTF-8",
            "origin": self._domain,
            "referer": f"{self._domain}/",
            "user-agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "Cookie": self._cookie_str,
        }

    async def _request(self, method: str, url: str, headers: Optional[Dict] = None,
                       json_data: Optional[Dict] = None, params: Optional[Dict] = None) -> Any:
        max_retries = self.config.retry_times

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.request(
                        method, url, headers=headers, json=json_data, params=params
                    )
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                if attempt < max_retries - 1:
                    delay = 2 ** attempt + random.uniform(0, 1)
                    logger.warning("%s %s network error (attempt %d/%d): %s — retrying in %.1fs",
                                   method, url, attempt + 1, max_retries, e, delay)
                    await asyncio.sleep(delay)
                    continue
                raise DataFetchError(f"Request network failed after {max_retries} retries: {e}") from e

            if resp.status_code in (461, 471):
                raise RateLimitError(f"CAPTCHA required, status={resp.status_code}")

            if resp.status_code >= 500:
                if attempt < max_retries - 1:
                    delay = 2 ** attempt + random.uniform(0, 1)
                    logger.warning("%s %s server error %d (attempt %d/%d) — retrying in %.1fs",
                                   method, url, resp.status_code, attempt + 1, max_retries, delay)
                    await asyncio.sleep(delay)
                    continue
                raise DataFetchError(f"Server error {resp.status_code} persisted after {max_retries} retries")

            data = resp.json()
            if data.get("success"):
                return data.get("data", data.get("success", {}))
            elif data.get("code") in (-510000, -510001):
                raise NoteNotFound(f"Note not found, code={data.get('code')}")
            else:
                raise DataFetchError(data.get("msg", resp.text[:200]))

        raise DataFetchError(f"Unexpected: retry loop exhausted for {url}")

    async def search_notes(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        note_type: int = 2,
        sort: str = "time_filtered",
    ) -> Dict:
        uri = "/api/sns/web/v1/search/notes"
        payload = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": self._gen_search_id(),
            "sort": sort,
            "note_type": note_type,
        }
        sign_headers = self._sign(uri, payload, method="POST")
        headers = {**self._base_headers(), **sign_headers}
        return await self._request(
            "POST", f"{self._host}{uri}", headers=headers, json_data=payload
        )

    async def get_note_detail(
        self, note_id: str, xsec_token: str, xsec_source: str = "pc_search"
    ) -> Dict:
        uri = "/api/sns/web/v1/feed"
        payload = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
            "xsec_source": xsec_source,
            "xsec_token": xsec_token,
        }
        sign_headers = self._sign(uri, payload, method="POST")
        headers = {**self._base_headers(), **sign_headers}
        res = await self._request(
            "POST", f"{self._host}{uri}", headers=headers, json_data=payload
        )
        if res and res.get("items"):
            return res["items"][0].get("note_card", {})
        return {}

    async def check_login(self) -> bool:
        uri = "/api/sns/web/v1/user/selfinfo"
        sign_headers = self._sign(uri, data={}, method="GET")
        headers = {**self._base_headers(), **sign_headers}
        try:
            resp = await self._request("GET", f"{self._host}{uri}", headers=headers, params={})
            return bool(resp)
        except DataFetchError:
            return False
