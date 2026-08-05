"""Enrich product data from a Taobao link.

Pipeline:
1. Open Taobao in persistent browser (login QR if first time)
2. Navigate to product page, scrape title + main image URL
3. (Optional) If vision LLM configured, identify attributes:
   category / color / fabric / fit / scene / style / brand
4. Append to data/products.csv

Usage:
    python scripts/enrich_products.py "TAOBAO_URL"
    python scripts/enrich_products.py "URL1" "URL2" --no-llm
    python scripts/enrich_products.py --from-csv data/products_raw.csv

Env (optional, for LLM identification):
    VISION_API_KEY=...
    VISION_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
    VISION_MODEL=<your-doubao-vision-endpoint-id or gpt-4o>
"""
import argparse
import asyncio
import base64
import csv
import json
import os
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright
from app.product_refs import is_product_page_url, parse_reference_list, split_product_references

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_CSV = PROJECT_ROOT / "data" / "products.csv"
RAW_CSV = PROJECT_ROOT / "data" / "products_raw.csv"
BROWSER_DATA = PROJECT_ROOT / "data" / "browser_data"

CSV_HEADERS = [
    "name", "category", "price", "brand", "size_available",
    "source_url", "attributes", "style", "images",
]


def _load_env():
    env = PROJECT_ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


_load_env()


def _strip_taobao_id(url: str) -> str:
    m = re.search(r"[?&]id=(\d+)", url)
    return m.group(1) if m else ""


def _open_csv_with_fallback(path: Path):
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            f = path.open(newline="", encoding=encoding)
            f.read(2048)
            f.seek(0)
            return f
        except UnicodeDecodeError:
            f.close()
    return path.open(newline="", encoding="utf-8", errors="replace")


def _read_rows(path: Path) -> list[dict]:
    with _open_csv_with_fallback(path) as f:
        return list(csv.DictReader(f))


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        w.writeheader()
        for row in rows:
            w.writerow({h: row.get(h, "") for h in CSV_HEADERS})


def _row_source_url(row: dict) -> str:
    source_url, _ = split_product_references(row)
    if source_url:
        return source_url
    for ref in parse_reference_list(row.get("images")):
        if is_product_page_url(ref):
            return ref
    return ""


def _merge_scraped_into_existing(row: dict, enriched: dict) -> dict:
    merged = dict(row)
    scraped_images = parse_reference_list(enriched.get("images"))
    source_url = enriched.get("source_url") or _row_source_url(row)
    if source_url:
        merged["source_url"] = source_url
    if scraped_images:
        merged["images"] = json.dumps(scraped_images, ensure_ascii=False)
    else:
        _, existing_images = split_product_references(merged)
        merged["images"] = json.dumps(existing_images, ensure_ascii=False)
    return merged


def _normalize_image_url(src: str) -> str:
    src = (src or "").strip()
    if not src:
        return ""
    if src.startswith("//"):
        src = "https:" + src
    src = src.split("?")[0]
    src = src.replace("\\u002F", "/")
    return src


def _is_likely_product_image(src: str) -> bool:
    src = _normalize_image_url(src)
    if not src.startswith(("http://", "https://")):
        return False
    if "alicdn.com" not in src:
        return False
    lowered = src.lower()
    if any(token in lowered for token in ("_tps-", "logo", "avatar", "icon", "sprite")):
        return False
    return any(token in lowered for token in ("/bao/uploaded/", "/imgextra/", "/uploaded/i"))


def _add_image(images: list[str], src: str, limit: int) -> None:
    src = _normalize_image_url(src)
    if not _is_likely_product_image(src):
        return
    if src not in images:
        images.append(src)
    if len(images) > limit:
        del images[limit:]


async def _ensure_login(page, ctx) -> None:
    """Detect login page and wait for user QR scan."""
    cur = page.url
    if "login" not in cur.lower():
        return
    print("[login] Taobao requires login. Please scan the QR code in the browser window...")
    for _ in range(90):  # 90s timeout
        await asyncio.sleep(1)
        cur = page.url
        if "login" not in cur.lower():
            print("[login] Login detected, continuing.")
            return
    raise RuntimeError("Taobao login timed out after 90s")


async def scrape_taobao(url: str, ctx, max_images: int = 6) -> dict:
    """Scrape one Taobao product: returns dict with title/price/images."""
    page = await ctx.new_page()
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(4000)
        await _ensure_login(page, ctx)
        # If redirected to login, after login go back to product
        if "login" in page.url.lower():
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(4000)

        # Title — try several common selectors
        title = ""
        for sel in [
            '[class*="ItemHeader--mainText"]',
            '[data-spm="1000971"]',
            'h1[class*="title"]',
            'h1',
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    title = (await el.inner_text()).strip()
                    if title:
                        break
            except Exception:
                pass
        if not title:
            title = await page.title()
            title = re.sub(r"\s*[-–—|].*$", "", title).strip()

        # Price — try common selectors
        price = ""
        for sel in [
            '[class*="Price--priceText"]',
            '[class*="priceText"]',
            '[class*="Price--current"]',
            '[class*="price"]',
        ]:
            try:
                el = await page.query_selector(sel)
                if el:
                    price = (await el.inner_text()).strip()
                    if re.search(r"\d", price):
                        break
                    price = ""
            except Exception:
                pass

        # Product gallery images. Prefer visible gallery/thumb images, then fall back to page-wide candidates.
        images = []
        for sel in [
            '[class*="PicGallery--mainWrapper"] img',
            '[class*="PicGallery"] [class*="thumbnail"] img',
            '[class*="PicGallery"] [class*="thumb"] img',
            '[class*="mainPic"] img',
            '[class*="PicGallery"] img',
            '#J_ImgBooth',
        ]:
            try:
                els = await page.query_selector_all(sel)
                for el in els:
                    for attr in ("src", "data-src", "data-ks-lazyload", "data-lazy-src"):
                        _add_image(images, await el.get_attribute(attr) or "", max_images)
            except Exception:
                pass

        # Hover/click thumbnails to force lazy main images into DOM.
        try:
            thumbs = await page.query_selector_all('[class*="PicGallery"] img, [class*="thumb"] img')
            for thumb in thumbs[:max_images]:
                try:
                    await thumb.hover(timeout=1000)
                    await page.wait_for_timeout(250)
                    await thumb.click(timeout=1000)
                    await page.wait_for_timeout(250)
                    for el in await page.query_selector_all('[class*="PicGallery"] img, [class*="mainPic"] img'):
                        for attr in ("src", "data-src", "data-ks-lazyload", "data-lazy-src"):
                            _add_image(images, await el.get_attribute(attr) or "", max_images)
                    if len(images) >= max_images:
                        break
                except Exception:
                    pass
        except Exception:
            pass

        if len(images) < max_images:
            try:
                candidates = await page.evaluate(
                    """() => {
                    const urls = new Set();
                    const add = (v) => {
                        if (!v) return;
                        String(v).split(',').forEach(part => {
                            const token = part.trim().split(/\\s+/)[0];
                            if (token) urls.add(token);
                        });
                    };
                    document.querySelectorAll('img').forEach(img => {
                        ['src', 'data-src', 'data-ks-lazyload', 'data-lazy-src', 'srcset'].forEach(a => add(img.getAttribute(a)));
                    });
                    document.querySelectorAll('*').forEach(el => {
                        const bg = getComputedStyle(el).backgroundImage || '';
                        const m = bg.match(/url\\(["']?(.*?)["']?\\)/);
                        if (m) add(m[1]);
                    });
                    return Array.from(urls);
                    }"""
                )
                for candidate in candidates:
                    _add_image(images, candidate, max_images)
            except Exception:
                pass

        # Fallback: collect og:image meta
        if not images:
            try:
                og = await page.evaluate(
                    """() => {
                    const m = document.querySelector('meta[property="og:image"]');
                    return m ? m.content : '';
                    }"""
                )
                if og:
                    _add_image(images, og, max_images)
            except Exception:
                pass

        result = {
            "title": title,
            "price": price,
            "images": images[:max_images],
            "source_url": url,
            "item_id": _strip_taobao_id(url),
        }
        print(f"  scraped: title='{title[:50]}' price='{price}' imgs={len(images)}")
        return result
    finally:
        await page.close()


def _vision_identify(image_url: str, scraped_title: str = "") -> dict:
    """Call vision LLM to identify product attributes."""
    api_key = os.environ.get("VISION_API_KEY", "")
    base_url = os.environ.get("VISION_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    model = os.environ.get("VISION_MODEL", "")
    if not api_key or not model:
        return {}

    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=60.0)

    import httpx
    try:
        r = httpx.get(image_url, timeout=20)
        r.raise_for_status()
        img_b64 = base64.b64encode(r.content).decode("utf-8")
        ext = image_url.rsplit(".", 1)[-1].lower().split("?")[0]
        mime = f"image/{ext}" if ext in ("png", "jpg", "jpeg", "webp") else "image/jpeg"
        data_url = f"data:{mime};base64,{img_b64}"
    except Exception as e:
        print(f"  vision: image fetch failed: {e}")
        return {}

    prompt = (
        "你是一名服装商品属性识别专家。请观察这张商品图，结合商品标题，"
        "判断下列属性（中文回答，未知写『未知』），以 JSON 输出:\n"
        "- name: 商品名称（不超 20 字，含品类和关键词）\n"
        "- category: 品类（取值：上衣/裙装/裤装/外套/鞋包配饰）\n"
        "- brand: 品牌（如无则填『无』）\n"
        "- color: 主色调\n"
        "- fabric: 面料/材质\n"
        "- fit: 版型关键词（如 高腰/A字/宽松/修身/短款）\n"
        "- scene: 适用场景（如 通勤/约会/海边/日常）\n"
        "- style: 风格标签数组（如 [法式, 显瘦, 韩系]）\n"
        "- size_available: 尺码区间（如 S-2XL）\n\n"
        f"商品标题（参考）：{scraped_title}\n"
        "只输出严格 JSON，不要 markdown 包裹。"
    )

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }],
            temperature=0.2,
            max_tokens=400,
        )
        content = resp.choices[0].message.content.strip()
        # strip markdown code fence if any
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.M).strip()
        return json.loads(content)
    except Exception as e:
        print(f"  vision: LLM call failed: {e}")
        return {}


def _build_row(scraped: dict, vision: dict) -> dict:
    """Merge scraped + vision data into a products.csv row dict."""
    name = vision.get("name") or scraped.get("title") or "未命名商品"
    category = vision.get("category") or "上衣"
    price_str = scraped.get("price") or ""
    m = re.search(r"(\d+(?:\.\d+)?)", price_str)
    price = m.group(1) if m else ""
    brand = vision.get("brand", "无") or "无"
    size = vision.get("size_available", "")
    source = scraped.get("source_url", "")
    attrs = {
        "color": vision.get("color", ""),
        "fabric": vision.get("fabric", ""),
        "fit": vision.get("fit", ""),
        "scene": vision.get("scene", ""),
    }
    style_list = vision.get("style", [])
    if isinstance(style_list, str):
        style_list = [s.strip() for s in style_list.split("/")]
    style = "/".join(style_list) if style_list else ""
    images = scraped.get("images") or []
    return {
        "name": name,
        "category": category,
        "price": price,
        "brand": brand,
        "size_available": size,
        "source_url": source,
        "attributes": json.dumps(attrs, ensure_ascii=False),
        "style": style,
        "images": json.dumps(images, ensure_ascii=False),
    }


def _append_csv(row: dict, path: Path = OUTPUT_CSV) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"  appended to {path}")


async def enrich_one(url: str, ctx, use_llm: bool = True) -> dict:
    print(f"\n[enrich] {url[:100]}")
    scraped = await scrape_taobao(url, ctx)
    if not scraped.get("images"):
        print("  WARN: no images scraped; skipping vision step")
        return _build_row(scraped, {})
    vision = _vision_identify(scraped["images"][0], scraped["title"]) if use_llm else {}
    if vision:
        print(f"  vision: {vision}")
    return _build_row(scraped, vision)


async def run(urls: list[str], use_llm: bool = True, output: Path = OUTPUT_CSV) -> None:
    async with async_playwright() as p:
        BROWSER_DATA.mkdir(parents=True, exist_ok=True)
        executable_path = os.environ.get("COLLECTOR_BROWSER_EXECUTABLE_PATH") or None
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA),
            headless=False,
            executable_path=executable_path,
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        )
        try:
            for url in urls:
                try:
                    row = await enrich_one(url, ctx, use_llm=use_llm)
                    _append_csv(row, output)
                except Exception as e:
                    print(f"  ERROR: {e}")
        finally:
            await ctx.close()


async def update_csv_in_place(path: Path, use_llm: bool = False) -> None:
    rows = _read_rows(path)
    source_urls = [_row_source_url(row) for row in rows]
    urls = [url for url in source_urls if url]
    if not urls:
        raise RuntimeError(f"No Taobao/Tmall source URLs found in {path}")

    enriched_by_item_id: dict[str, dict] = {}
    async with async_playwright() as p:
        BROWSER_DATA.mkdir(parents=True, exist_ok=True)
        executable_path = os.environ.get("COLLECTOR_BROWSER_EXECUTABLE_PATH") or None
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA),
            headless=False,
            executable_path=executable_path,
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        )
        try:
            for url in urls:
                try:
                    row = await enrich_one(url, ctx, use_llm=use_llm)
                    item_id = _strip_taobao_id(url)
                    if item_id:
                        enriched_by_item_id[item_id] = row
                except Exception as e:
                    print(f"  ERROR: {e}")
        finally:
            await ctx.close()

    updated = 0
    for row in rows:
        source_url = _row_source_url(row)
        item_id = _strip_taobao_id(source_url)
        enriched = enriched_by_item_id.get(item_id)
        if not enriched:
            continue
        merged = _merge_scraped_into_existing(row, enriched)
        row.clear()
        row.update(merged)
        updated += 1

    _write_rows(path, rows)
    print(f"updated {updated}/{len(rows)} rows in {path}")


def main():
    parser = argparse.ArgumentParser(description="Enrich products.csv from Taobao links")
    parser.add_argument("urls", nargs="*", help="Taobao item URLs")
    parser.add_argument("--from-csv", help="Read URLs from a CSV with source_url column")
    parser.add_argument("--no-llm", action="store_true", help="Skip vision LLM identification")
    parser.add_argument("--output", default=str(OUTPUT_CSV), help="Output CSV path")
    parser.add_argument("--in-place", action="store_true", help="Update --from-csv rows instead of appending rows")
    args = parser.parse_args()

    if args.in_place:
        if not args.from_csv:
            parser.error("--in-place requires --from-csv")
        asyncio.run(update_csv_in_place(Path(args.from_csv), use_llm=not args.no_llm))
        return

    urls = list(args.urls)
    if args.from_csv:
        for r in _read_rows(Path(args.from_csv)):
            u = _row_source_url(r)
            if u:
                urls.append(u)
    if not urls:
        parser.error("Provide at least one URL or --from-csv")

    asyncio.run(run(urls, use_llm=not args.no_llm, output=Path(args.output)))


if __name__ == "__main__":
    main()
