"""AniList source fetcher using GraphQL API."""

from typing import Any

import httpx
import logging

from app.fetchers.base import BaseFetcher, truncate_body

logger = logging.getLogger(__name__)

ANILIST_GRAPHQL_URL = "https://graphql.anilist.co"

TRENDING_QUERY = """
query {
  TrendingAnime: Page(page: 1, perPage: 25) {
    media(sort: TRENDING_DESC, type: ANIME, isAdult: false) {
      id
      title { romaji english }
      description(asHtml: false)
      trending
      popularity
      siteUrl
    }
  }
  TrendingManga: Page(page: 1, perPage: 15) {
    media(sort: TRENDING_DESC, type: MANGA, isAdult: false) {
      id
      title { romaji english }
      description(asHtml: false)
      trending
      popularity
      siteUrl
    }
  }
}
"""


class AniListFetcher(BaseFetcher):
    """Fetches trending anime and manga from AniList GraphQL API."""

    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch trending anime + manga from AniList."""
        response = await client.post(
            ANILIST_GRAPHQL_URL,
            json={"query": TRENDING_QUERY},
            timeout=self.TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        items: list[dict[str, Any]] = []

        anime_results = (
            data.get("data", {})
            .get("TrendingAnime", {})
            .get("media", [])
        )
        for media in anime_results:
            media["_media_type"] = "anime"
            items.append(media)

        manga_results = (
            data.get("data", {})
            .get("TrendingManga", {})
            .get("media", [])
        )
        for media in manga_results:
            media["_media_type"] = "manga"
            items.append(media)

        return items

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize an AniList media item into canonical format."""
        titles = raw.get("title", {})
        title = titles.get("romaji") or titles.get("english") or ""

        return {
            "source": "anilist",
            "source_url": raw.get("siteUrl", ""),
            "original_title": title,
            "original_body": truncate_body(raw.get("description", "") or ""),
            "source_metadata": {
                "anilist_id": raw.get("id"),
                "media_type": raw.get("_media_type", ""),
                "trending": raw.get("trending"),
                "popularity": raw.get("popularity", 0),
            },
            "engagement_metric": raw.get("trending") or raw.get("popularity", 0),
        }
