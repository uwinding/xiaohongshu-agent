import requests
from bs4 import BeautifulSoup

XHS_SEARCH_URL = "https://www.xiaohongshu.com/search_result?keyword="


def fetch_xiaohongshu_trends(keyword: str, max_items: int = 20) -> list[str]:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        resp = requests.get(f"{XHS_SEARCH_URL}{keyword}", headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        cards = soup.select(".note-item, .feeds-page .note-item, section.note-item")
        titles = []
        for card in cards[:max_items]:
            title_el = card.select_one(".title, .note-title, a.title span")
            if title_el:
                titles.append(title_el.get_text(strip=True))
        return titles
    except Exception:
        return []


def fetch_trends_for_persona(style_tags: list[str]) -> list[str]:
    all_titles = []
    for tag in style_tags[:3]:
        titles = fetch_xiaohongshu_trends(keyword=tag)
        all_titles.extend(titles)
    return list(dict.fromkeys(all_titles))[:50]
