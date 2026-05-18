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
    args = parser.parse_args()

    keywords = [args.keyword] if args.keyword else load_keywords(args.keywords_file)
    config = CollectorConfig(
        headless=args.headless,
        max_notes_per_keyword=args.max_notes,
    )

    cookie_str = os.environ.get("XHS_COOKIE", "")

    print(f"Starting collector with keywords: {keywords}")
    if cookie_str:
        print(f"Using cookie from XHS_COOKIE env (length={len(cookie_str)})")
    else:
        print("No XHS_COOKIE set, will use browser QR login")

    results = asyncio.run(run_collect(keywords, config, cookie_str=cookie_str))

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
