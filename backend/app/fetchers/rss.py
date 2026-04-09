"""RSS/Atom feed source fetcher for anime news sites."""

import re
from typing import Any

import httpx
import feedparser
import logging

from app.fetchers.base import BaseFetcher, truncate_body

logger = logging.getLogger(__name__)

DEFAULT_FEED_URLS = [
    "https://animeanime.jp/rss/index.rdf",
    "https://mantan-web.jp/rss/index.rdf",
]


def _strip_html(text: str) -> str:
    """Remove HTML tags from text."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", "", text)
    # Collapse whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


class RSSFetcher(BaseFetcher):
    """Fetches and parses RSS/Atom feeds from anime news sources."""

    def __init__(self, feed_urls: list[str] | None = None):
        self.feed_urls = feed_urls or DEFAULT_FEED_URLS

    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch and parse all configured RSS feeds."""
        all_items: list[dict[str, Any]] = []

        for feed_url in self.feed_urls:
            try:
                response = await client.get(feed_url, timeout=self.TIMEOUT)
                response.raise_for_status()
            except Exception:
                logger.warning(f"RSSFetcher: Failed to fetch {feed_url}")
                continue

            # feedparser can parse from raw bytes
            feed = feedparser.parse(response.content)

            for entry in feed.entries:
                entry["_feed_url"] = feed_url
                all_items.append(dict(entry))

        return all_items

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize an RSS entry into canonical format."""
        summary = raw.get("summary", "") or raw.get("description", "") or ""
        summary = _strip_html(summary)

        return {
            "source": "anime_news",
            "source_url": raw.get("link", ""),
            "original_title": raw.get("title", ""),
            "original_body": truncate_body(summary),
            "source_metadata": {
                "feed_url": raw.get("_feed_url", ""),
                "published": raw.get("published", ""),
                "author": raw.get("author", ""),
            },
            "engagement_metric": 0,
        }
