import asyncio
import logging
import argparse
import os

from app.collector.config import CollectorConfig, load_keywords
from app.collector.runner import run_collect

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="XHS Hot Content Collector")
    parser.add_argument("--keyword", "-k", type=str, help="Single keyword to search")
    parser.add_argument("--keywords-file", type=str, default="data/keywords.yaml",
                        help="YAML file with keyword list")
    parser.add_argument("--max-notes", type=int, default=50,
                        help="Max notes per keyword")
    parser.add_argument("--headless", type=lambda x: x.lower() == "true", default=True,
                        help="Run browser in headless mode (true/false)")
    parser.add_argument("--page-hotwords", action="store_true",
                        help="Also extract hot words from page DOM (opens browser)")
    parser.add_argument("--recent-days", type=int, default=0,
                        help="Only keep notes published within N days when ranking top notes")
    parser.add_argument("--top-per-metric", type=int, default=0,
                        help="Keep top N notes for each metric: likes, comments, collects")
    parser.add_argument("--expand-page-hotwords", type=int, default=0,
                        help="Search the first N DOM hotword tabs next to 综合 and globally dedupe notes")
    parser.add_argument("--sorts", type=str, default="time_filtered",
                        help="Comma-separated XHS search sorts used to build a larger candidate pool")
    args = parser.parse_args()

    keywords = [args.keyword] if args.keyword else load_keywords(args.keywords_file)
    config = CollectorConfig(
        headless=args.headless,
        max_notes_per_keyword=args.max_notes,
        recent_days=args.recent_days,
        top_per_metric=args.top_per_metric,
        expand_page_hotwords_limit=args.expand_page_hotwords,
        search_sorts=args.sorts,
    )

    cookie_str = os.environ.get("XHS_COOKIE", "")

    print(f"Starting collector with keywords: {keywords}")
    if cookie_str:
        print(f"Using cookie from XHS_COOKIE env (length={len(cookie_str)})")
    else:
        print("No XHS_COOKIE set, will use browser QR login")

    results = asyncio.run(run_collect(
        keywords, config,
        cookie_str=cookie_str,
        fetch_page_hotwords=args.page_hotwords or args.expand_page_hotwords > 0,
    ))

    for r in results:
        if r.hotwords:
            print(f"  [{r.keyword}] hotwords: {[h.text for h in r.hotwords]}")
            print(f"  [{r.keyword}] notes: {len(r.cards)}")
        else:
            print(f"  [{r.keyword}] no data")

    print("Collection complete!")
    print(f"Output directory: {config.output_dir}")


if __name__ == "__main__":
    main()
