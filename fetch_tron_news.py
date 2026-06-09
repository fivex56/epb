#!/usr/bin/env python3
"""Fetch TRON energy news from Google News RSS and write tron_news.json"""
import json
import re
import feedparser
from datetime import datetime, timezone

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q=TRON+energy+TRX+blockchain&hl=en-US&gl=US&ceid=US:en"
OUT_FILE = "tron_news.json"
MAX_ITEMS = 30


def clean_google_link(raw: str) -> str:
    """Extract real URL from Google News redirect link."""
    m = re.search(r"/([a-zA-Z0-9_\-]{20,})", raw)
    if m:
        return f"https://news.google.com/articles/{m.group(1)}"
    return raw


def parse_date(published: str) -> str:
    """Try to parse and return ISO date string."""
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(published)
        return dt.isoformat()
    except Exception:
        return published


def main():
    print(f"Fetching: {GOOGLE_NEWS_RSS}")
    feed = feedparser.parse(GOOGLE_NEWS_RSS)

    items = []
    for entry in feed.entries[:MAX_ITEMS]:
        items.append({
            "title": entry.get("title", ""),
            "link": clean_google_link(entry.get("link", "")),
            "published": parse_date(entry.get("published", "")),
            "source": entry.get("source", {}).get("title", ""),
            "summary": (entry.get("summary") or "")[:300],
        })

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Google News RSS",
        "query": "TRON energy TRX blockchain",
        "count": len(items),
        "items": items,
    }

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(items)} items to {OUT_FILE}")


if __name__ == "__main__":
    main()
