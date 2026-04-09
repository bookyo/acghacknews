"""Fetch orchestrator that coordinates all source fetchers, translation, scoring, and storage."""

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx

from app.config import Settings
from app.db import init_db
from app.fetchers.anilist import AniListFetcher
from app.fetchers.base import BaseFetcher
from app.fetchers.reddit import RedditFetcher
from app.fetchers.rss import RSSFetcher
from app.fetchers.steam import SteamFetcher
from app.models import FeedItem
from app.repository import FeedRepository
from app.scoring import calculate_heat_score
from app.translation import TranslationService

logger = logging.getLogger(__name__)


class FetchOrchestrator:
    """Coordinates the fetch-translate-score-store pipeline."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.repo = FeedRepository(settings.database_path)
        self.translation = TranslationService(settings.deepseek_api_key)
        self.fetchers: list[BaseFetcher] = [
            RedditFetcher(
                settings.reddit_client_id,
                settings.reddit_client_secret,
                settings.reddit_user_agent,
            ),
            AniListFetcher(),
            SteamFetcher(),
            RSSFetcher(),
        ]

    async def ensure_db(self):
        """Initialize database if needed."""
        await init_db(self.settings.database_path)

    async def run_fetch_cycle(self) -> dict[str, Any]:
        """Main orchestration method. Returns summary dict."""
        logger.info("Starting fetch cycle")
        start_time = datetime.now(timezone.utc)

        # 1. Fetch all sources in parallel
        all_items: list[dict[str, Any]] = []
        source_results: dict[str, dict[str, Any]] = {}
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            tasks = [fetcher.safe_fetch(client) for fetcher in self.fetchers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for fetcher, result in zip(self.fetchers, results):
                name = fetcher.__class__.__name__
                if isinstance(result, Exception):
                    logger.error(f"{name} raised exception: {result}")
                    source_results[name] = {"status": "error", "count": 0}
                elif isinstance(result, list):
                    all_items.extend(result)
                    source_results[name] = {"status": "ok", "count": len(result)}
                else:
                    source_results[name] = {"status": "unknown", "count": 0}

        logger.info(f"Fetched {len(all_items)} total raw items: {source_results}")

        if not all_items:
            logger.error("All sources failed in this cycle")
            await self.repo.set_metadata("last_fetch_status", "all_sources_failed")
            await self.repo.set_metadata("last_fetch_at", start_time.isoformat())
            return {
                "status": "all_sources_failed",
                "items_fetched": 0,
                "source_results": source_results,
            }

        # 2. Dedup
        urls = [item["source_url"] for item in all_items]
        existing = await self.repo.get_existing_urls(urls)
        new_items = [
            item for item in all_items if item["source_url"] not in existing
        ]
        logger.info(
            f"After dedup: {len(new_items)} new items "
            f"(skipped {len(all_items) - len(new_items)} duplicates)"
        )

        if not new_items:
            await self.repo.set_metadata("last_fetch_status", "no_new_items")
            await self.repo.set_metadata("last_fetch_at", start_time.isoformat())
            return {"status": "no_new_items", "items_fetched": 0}

        # 3. Translate
        try:
            new_items = await self.translation.translate_items(new_items)
        except Exception as e:
            logger.error(f"Translation pipeline error: {e}")
            for item in new_items:
                item["translated_title"] = (
                    f"[TRANSLATION_PENDING] {item['original_title']}"
                )
                item["translated_body"] = item.get("original_body", "")
                item["translated_at"] = None

        # 4. Score
        now = datetime.now(timezone.utc)
        for item in new_items:
            item["heat_score"] = calculate_heat_score(
                engagement=item.get("engagement_metric", 0),
                fetched_at=now,
                source=item["source"],
                now=now,
            )

        # 5. Store
        feed_items: list[FeedItem] = []
        for item in new_items:
            translated_at_val = item.get("translated_at")
            if isinstance(translated_at_val, str):
                translated_at_val = datetime.fromisoformat(translated_at_val)
            feed_items.append(
                FeedItem(
                    id=str(uuid.uuid4()),
                    source=item["source"],
                    source_url=item["source_url"],
                    original_title=item["original_title"],
                    translated_title=item["translated_title"],
                    original_body=item["original_body"],
                    translated_body=item["translated_body"],
                    heat_score=item["heat_score"],
                    source_metadata=item.get("source_metadata", {}),
                    fetched_at=now,
                    translated_at=translated_at_val,
                    language="zh-CN",
                )
            )

        inserted = await self.repo.insert_items(feed_items)

        # 6. Update metadata
        await self.repo.set_metadata("last_fetch_at", start_time.isoformat())
        await self.repo.set_metadata("last_fetch_status", "success")

        logger.info(f"Fetch cycle complete: {inserted} items inserted")
        return {
            "status": "success",
            "items_fetched": inserted,
            "source_results": source_results,
        }

    async def run_cleanup(self) -> int:
        """Run data retention cleanup."""
        try:
            count = await self.repo.cleanup_old_items(self.settings.retention_days)
            logger.info(f"Cleaned up {count} expired items")
            await self.repo.set_metadata(
                "last_cleanup_at", datetime.now(timezone.utc).isoformat()
            )
            return count
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0

    async def should_fetch_on_startup(self) -> bool:
        """Check if a fetch should run immediately on startup."""
        last_fetch = await self.repo.get_metadata("last_fetch_at")
        if not last_fetch:
            return True
        try:
            last_dt = datetime.fromisoformat(last_fetch)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            age_minutes = (
                datetime.now(timezone.utc) - last_dt
            ).total_seconds() / 60
            return age_minutes > self.settings.fetch_interval_minutes
        except (ValueError, TypeError):
            return True
