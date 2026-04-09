"""Steam Store source fetcher using the featured categories API."""

from typing import Any

import httpx
import logging

from app.fetchers.base import BaseFetcher, truncate_body

logger = logging.getLogger(__name__)

STEAM_FEATURED_URL = "https://store.steampowered.com/api/featuredcategories/"


class SteamFetcher(BaseFetcher):
    """Fetches top sellers and coming soon items from the Steam Store API."""

    async def fetch(self, client: httpx.AsyncClient) -> list[dict[str, Any]]:
        """Fetch featured categories from Steam Store."""
        response = await client.get(STEAM_FEATURED_URL, timeout=self.TIMEOUT)
        response.raise_for_status()
        data = response.json()

        items: list[dict[str, Any]] = []

        # Extract top sellers
        top_sellers = data.get("top_sellers", {}).get("items", [])
        for item in top_sellers:
            item["_category"] = "top_sellers"
            items.append(item)

        # Extract coming soon
        coming_soon = data.get("coming_soon", {}).get("items", [])
        for item in coming_soon:
            item["_category"] = "coming_soon"
            items.append(item)

        return items

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize a Steam store item into canonical format."""
        app_id = raw.get("id", "")
        return {
            "source": "steam",
            "source_url": f"https://store.steampowered.com/app/{app_id}",
            "original_title": raw.get("name", ""),
            "original_body": truncate_body(raw.get("short_description", "") or ""),
            "source_metadata": {
                "steam_app_id": app_id,
                "category": raw.get("_category", ""),
                "currency": raw.get("currency", ""),
            },
            "engagement_metric": 0,
        }
