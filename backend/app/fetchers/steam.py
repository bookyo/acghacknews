"""Steam Store source fetcher using the featured categories and app details APIs."""

import asyncio
from typing import Any

import httpx
import logging

from app.fetchers.base import BaseFetcher, truncate_body

logger = logging.getLogger(__name__)

STEAM_FEATURED_URL = "https://store.steampowered.com/api/featuredcategories/"
STEAM_APP_DETAILS_URL = "https://store.steampowered.com/api/appdetails"


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

        # Enrich with short_description from app details API
        await self._enrich_with_details(client, items)

        return items

    async def _enrich_with_details(
        self, client: httpx.AsyncClient, items: list[dict[str, Any]]
    ) -> None:
        """Fetch app details for each item to get short_description."""
        # Process in small batches to avoid rate limiting
        batch_size = 5
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            tasks = [self._fetch_app_detail(client, item) for item in batch]
            await asyncio.gather(*tasks)
            # Small delay between batches to be respectful
            if i + batch_size < len(items):
                await asyncio.sleep(0.5)

    async def _fetch_app_detail(
        self, client: httpx.AsyncClient, item: dict[str, Any]
    ) -> None:
        """Fetch and attach short_description for a single app."""
        app_id = item.get("id")
        if not app_id:
            return
        try:
            response = await client.get(
                STEAM_APP_DETAILS_URL,
                params={"appids": app_id, "cc": "us"},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            detail = response.json()
            app_data = detail.get(str(app_id), {}).get("data")
            if app_data:
                item["short_description"] = app_data.get("short_description", "")
        except Exception as e:
            logger.warning(f"SteamFetcher: Failed to fetch details for app {app_id}: {e}")

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
