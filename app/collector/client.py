import json
import hashlib
import time
import random
from typing import Dict, Optional, Any
from urllib.parse import quote

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
            content_string = self._build_content_string(uri, data, method)
            a1_value = self._cookie_dict.get("a1", "")
            ts = time.time()
            d_value = hashlib.md5(content_string.encode("utf-8")).hexdigest()
            payload_array = xhshow_client.crypto_processor.build_payload_array(
                d_value, a1_value, "xhs-pc-web", content_string, ts
            )
            xor_result = xhshow_client.crypto_processor.bit_ops.xor_transform_array(
                payload_array
            )
            cfg = xhshow_client.config
            x3_b64 = xhshow_client.crypto_processor.b64encoder.encode_x3(
                xor_result[: cfg.PAYLOAD_LENGTH]
            )
            sig_data = cfg.SIGNATURE_DATA_TEMPLATE.copy()
            sig_data["x3"] = cfg.X3_PREFIX + x3_b64
            x_s = cfg.XYS_PREFIX + xhshow_client.crypto_processor.b64encoder.encode(
                json.dumps(sig_data, separators=(",", ":"), ensure_ascii=False)
            )
            headers = {
                "x-s": x_s,
                "x-s-common": xhshow_client.sign_xs_common(self._cookie_dict),
                "x-t": str(xhshow_client.get_x_t(ts)),
                "x-b3-traceid": xhshow_client.get_b3_trace_id(),
            }

        return {
            "x-s": headers.get("x-s", ""),
            "x-t": headers.get("x-t", ""),
            "x-s-common": headers.get("x-s-common", ""),
            "x-b3-traceid": headers.get("x-b3-traceid", self._gen_trace_id()),
        }

    @staticmethod
    def _build_content_string(uri: str, data: Optional[Dict], method: str) -> str:
        if method.upper() == "POST":
            c = uri
            if data:
                c += json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            return c
        if not data:
            return uri
        params = []
        for key, value in data.items():
            if isinstance(value, list):
                value_str = ",".join(str(v) for v in value)
            elif value is not None:
                value_str = str(value)
            else:
                value_str = ""
            value_str = quote(value_str, safe=",")
            params.append(f"{key}={value_str}")
        return f"{uri}?{'&'.join(params)}"

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
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.request(
                method, url, headers=headers, json=json_data, params=params
            )
            if resp.status_code in (461, 471):
                raise RateLimitError(f"CAPTCHA required, status={resp.status_code}")

            data = resp.json()
            if data.get("success"):
                return data.get("data", data.get("success", {}))
            elif data.get("code") in (-510000, -510001):
                raise NoteNotFound(f"Note not found, code={data.get('code')}")
            else:
                raise DataFetchError(data.get("msg", resp.text[:200]))

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
