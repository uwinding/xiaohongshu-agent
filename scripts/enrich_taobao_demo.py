"""Demo: enrich a Taobao product from its link.

Usage:
    python scripts/enrich_taobao_demo.py "FULL_TAOBAO_URL"
"""
import asyncio
import re
import sys
import json
import base64
from pathlib import Path
from playwright.async_api import async_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://item.taobao.com/item.htm?id=1049456791542"


async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir="data/browser_data",
            headless=False,
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        )
        page = await ctx.new_page()
        try:
            print(f"Navigating to:\n{URL[:160]}...")
            await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(5000)
            url = page.url
            print("final_url:", url[:120])
            title = await page.title()
            print("tab_title:", title)
            html = await page.content()
            print("html_len:", len(html))

            # Extract og metadata
            for prop in ("og:title", "og:image", "og:description"):
                m = re.search(
                    r'<meta\s+[^>]*property=["\047]%s["\047][^>]*content=["\047](.*?)["\047]'
                    % prop,
                    html,
                )
                if m:
                    print(f"{prop}:", m.group(1)[:200])

            # Try extracting product images from page
            img_pattern = r"https?://[^\"\047> ]+\.(?:jpg|jpeg|png|webp)"
            imgs = re.findall(img_pattern, html)
            # Filter to likely product images (skip UI icons/logos)
            product_imgs = [i for i in imgs if "img.alicdn.com/imgextra" in i or "img.alicdn.com/bao" in i]
            if not product_imgs:
                # Fallback to all imgs containing "alicdn"
                product_imgs = [i for i in imgs if "alicdn" in i and "_tps-" not in i]
            print("img_count:", len(imgs))
            print("product_imgs_count:", len(product_imgs))
            for i in product_imgs[:8]:
                print("  prod_img:", i[:140])

            # Try to find product title in page via DOM
            try:
                page_title = await page.evaluate(
                    """() => {
                    const el = document.querySelector('[class*="title"] [class*="main"]')
                        || document.querySelector('h1')
                        || document.querySelector('[data-spm="1000971"]');
                    return el ? el.innerText.trim() : '';
                    }"""
                )
                print("page_title_from_dom:", page_title)
            except Exception as e:
                print("dom_title_failed:", e)

            # Try to find price
            try:
                price = await page.evaluate(
                    """() => {
                    const el = document.querySelector('[class*="price"]') 
                        || document.querySelector('. priceText');
                    return el ? el.innerText.trim() : '';
                    }"""
                )
                print("price_from_dom:", price)
            except Exception as e:
                print("dom_price_failed:", e)

            # Save screenshot for vision analysis if login page
            if "login" in url.lower():
                print("\\n=== LOGIN PAGE DETECTED ===")
                print("Taobao requires login. Try the script after manually scanning Taobao QR.")
            else:
                # Save screenshot
                ss_path = "/tmp/taobao_screenshot.png"
                await page.screenshot(path=ss_path, full_page=False)
                print(f"screenshot saved: {ss_path}")

        finally:
            await ctx.close()


asyncio.run(main())