"""Tests for FetchOrchestrator: full cycle, dedup, failure handling, cleanup, metadata."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import Settings
from app.db import init_db
from app.models import FeedItem
from app.orchestrator import FetchOrchestrator
from app.repository import FeedRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Return a path to a temporary SQLite database file."""
    d = tmp_path / "data"
    d.mkdir()
    return str(d / "test_orchestrator.db")


@pytest.fixture
def settings(db_path):
    """Return test Settings pointing at the temporary database."""
    return Settings(
        deepseek_api_key="test-key",
        reddit_client_id="test-id",
        reddit_client_secret="test-secret",
        reddit_user_agent="test-agent",
        database_path=db_path,
        admin_api_key="test-admin",
        frontend_url="http://localhost:3000",
        log_level="WARNING",
        retention_days=1,
        fetch_interval_minutes=30,
    )


@pytest.fixture
async def orchestrator(settings, db_path):
    """Return a FetchOrchestrator with an initialized database."""
    await init_db(db_path)
    orch = FetchOrchestrator(settings)
    return orch


def _make_item(
    source="reddit",
    source_url=None,
    title="Test Title",
    body="Test body",
    engagement=10,
):
    """Helper to build a normalized item dict as fetchers would produce."""
    return {
        "source": source,
        "source_url": source_url or f"https://example.com/{uuid.uuid4()}",
        "original_title": title,
        "original_body": body,
        "source_metadata": {"test": True},
        "engagement_metric": engagement,
    }


async def _fake_translate(items):
    """Populate translation fields on items (used as mock for translate_items)."""
    for item in items:
        item["translated_title"] = f"ZH: {item['original_title']}"
        item["translated_body"] = f"ZH: {item.get('original_body', '')}"
        item["translated_at"] = datetime.now(timezone.utc).isoformat()
    return items


async def _insert_raw_item(repo: FeedRepository, source_url: str, source="reddit"):
    """Insert a FeedItem directly into the DB for dedup / cleanup tests."""
    now = datetime.now(timezone.utc)
    item = FeedItem(
        id=str(uuid.uuid4()),
        source=source,
        source_url=source_url,
        original_title="Existing",
        translated_title="Existing ZH",
        original_body="body",
        translated_body="body ZH",
        heat_score=1.0,
        source_metadata={},
        fetched_at=now,
        translated_at=now,
        language="zh-CN",
    )
    await repo.insert_items([item])
    return item


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_fetch_cycle_happy_path(orchestrator):
    """All fetchers return items, translation mocked; items end up in DB."""
    reddit_items = [_make_item(source="reddit", engagement=100)]
    anilist_items = [_make_item(source="anilist", engagement=50)]
    steam_items = [_make_item(source="steam", engagement=0)]
    rss_items = [_make_item(source="anime_news", engagement=0)]

    # Mock each fetcher's safe_fetch to return known items
    mock_fetches = [
        AsyncMock(return_value=reddit_items),
        AsyncMock(return_value=anilist_items),
        AsyncMock(return_value=steam_items),
        AsyncMock(return_value=rss_items),
    ]

    # Mock translation to just echo
    async def fake_translate(items):
        for item in items:
            item["translated_title"] = f"ZH: {item['original_title']}"
            item["translated_body"] = f"ZH: {item['original_body']}"
            item["translated_at"] = datetime.now(timezone.utc).isoformat()
        return items

    with patch.object(
        orchestrator.fetchers[0], "safe_fetch", mock_fetches[0]
    ), patch.object(
        orchestrator.fetchers[1], "safe_fetch", mock_fetches[1]
    ), patch.object(
        orchestrator.fetchers[2], "safe_fetch", mock_fetches[2]
    ), patch.object(
        orchestrator.fetchers[3], "safe_fetch", mock_fetches[3]
    ), patch.object(
        orchestrator.translation, "translate_items", side_effect=fake_translate
    ):
        result = await orchestrator.run_fetch_cycle()

    assert result["status"] == "success"
    assert result["items_fetched"] == 4
    assert result["source_results"]["RedditFetcher"]["status"] == "ok"
    assert result["source_results"]["RedditFetcher"]["count"] == 1
    assert result["source_results"]["AniListFetcher"]["status"] == "ok"
    assert result["source_results"]["SteamFetcher"]["status"] == "ok"
    assert result["source_results"]["RSSFetcher"]["status"] == "ok"

    # Verify items actually landed in the DB
    total = await orchestrator.repo.count_items()
    assert total == 4


@pytest.mark.asyncio
async def test_dedup_in_orchestrator(orchestrator):
    """Pre-insert an item, then run a cycle containing the same URL; no duplicate."""
    dup_url = "https://reddit.com/r/anime/duplicate_post"
    await _insert_raw_item(orchestrator.repo, dup_url)

    new_items = [
        _make_item(source_url=dup_url, title="Duplicate"),
        _make_item(source_url="https://example.com/new-one", title="New"),
    ]

    with patch.object(
        orchestrator.fetchers[0], "safe_fetch", AsyncMock(return_value=new_items)
    ), patch.object(
        orchestrator.fetchers[1], "safe_fetch", AsyncMock(return_value=[])
    ), patch.object(
        orchestrator.fetchers[2], "safe_fetch", AsyncMock(return_value=[])
    ), patch.object(
        orchestrator.fetchers[3], "safe_fetch", AsyncMock(return_value=[])
    ), patch.object(
        orchestrator.translation,
        "translate_items",
        side_effect=_fake_translate,
    ):
        result = await orchestrator.run_fetch_cycle()

    assert result["status"] == "success"
    # Only the new item should have been inserted (the duplicate was skipped)
    assert result["items_fetched"] == 1

    total = await orchestrator.repo.count_items()
    assert total == 2  # 1 pre-existing + 1 new


@pytest.mark.asyncio
async def test_all_sources_fail(orchestrator):
    """All fetchers return empty lists; orchestrator does not crash, metadata updated."""
    with patch.object(
        orchestrator.fetchers[0], "safe_fetch", AsyncMock(return_value=[])
    ), patch.object(
        orchestrator.fetchers[1], "safe_fetch", AsyncMock(return_value=[])
    ), patch.object(
        orchestrator.fetchers[2], "safe_fetch", AsyncMock(return_value=[])
    ), patch.object(
        orchestrator.fetchers[3], "safe_fetch", AsyncMock(return_value=[])
    ):
        result = await orchestrator.run_fetch_cycle()

    assert result["status"] == "all_sources_failed"
    assert result["items_fetched"] == 0

    status = await orchestrator.repo.get_metadata("last_fetch_status")
    assert status == "all_sources_failed"

    last_fetch = await orchestrator.repo.get_metadata("last_fetch_at")
    assert last_fetch is not None


@pytest.mark.asyncio
async def test_partial_sources_fail(orchestrator):
    """Reddit fails (exception), others succeed; only working sources contribute items."""
    reddit_error = Exception("Reddit API down")
    anilist_items = [_make_item(source="anilist")]
    steam_items = [_make_item(source="steam")]
    rss_items = [_make_item(source="anime_news")]

    # safe_fetch catches exceptions internally and returns [], but if
    # asyncio.gather receives return_exceptions=True it surfaces as exception.
    # Simulate the exception bubbling through gather (the orchestrator uses
    # return_exceptions=True).
    with patch.object(
        orchestrator.fetchers[0],
        "safe_fetch",
        AsyncMock(side_effect=reddit_error),
    ), patch.object(
        orchestrator.fetchers[1], "safe_fetch", AsyncMock(return_value=anilist_items)
    ), patch.object(
        orchestrator.fetchers[2], "safe_fetch", AsyncMock(return_value=steam_items)
    ), patch.object(
        orchestrator.fetchers[3], "safe_fetch", AsyncMock(return_value=rss_items)
    ), patch.object(
        orchestrator.translation,
        "translate_items",
        side_effect=_fake_translate,
    ):
        result = await orchestrator.run_fetch_cycle()

    assert result["status"] == "success"
    assert result["items_fetched"] == 3
    assert result["source_results"]["RedditFetcher"]["status"] == "error"
    assert result["source_results"]["AniListFetcher"]["status"] == "ok"
    assert result["source_results"]["SteamFetcher"]["status"] == "ok"
    assert result["source_results"]["RSSFetcher"]["status"] == "ok"


@pytest.mark.asyncio
async def test_startup_catch_up_missed(orchestrator):
    """last_fetch_at is 45 minutes ago; should_fetch_on_startup returns True."""
    old_time = (datetime.now(timezone.utc) - timedelta(minutes=45)).isoformat()
    await orchestrator.repo.set_metadata("last_fetch_at", old_time)

    result = await orchestrator.should_fetch_on_startup()
    assert result is True


@pytest.mark.asyncio
async def test_startup_catch_up_recent(orchestrator):
    """last_fetch_at is 10 minutes ago; should_fetch_on_startup returns False."""
    recent_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    await orchestrator.repo.set_metadata("last_fetch_at", recent_time)

    result = await orchestrator.should_fetch_on_startup()
    assert result is False


@pytest.mark.asyncio
async def test_cleanup_scheduled(orchestrator):
    """run_cleanup removes items older than retention_days."""
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=3)

    # Insert an old item
    old_item = FeedItem(
        id=str(uuid.uuid4()),
        source="reddit",
        source_url="https://example.com/old-item",
        original_title="Old",
        translated_title="Old ZH",
        original_body="old body",
        translated_body="old body ZH",
        heat_score=1.0,
        source_metadata={},
        fetched_at=old_time,
        translated_at=old_time,
        language="zh-CN",
    )

    # Insert a recent item
    recent_item = FeedItem(
        id=str(uuid.uuid4()),
        source="reddit",
        source_url="https://example.com/recent-item",
        original_title="Recent",
        translated_title="Recent ZH",
        original_body="recent body",
        translated_body="recent body ZH",
        heat_score=2.0,
        source_metadata={},
        fetched_at=now,
        translated_at=now,
        language="zh-CN",
    )

    await orchestrator.repo.insert_items([old_item, recent_item])
    assert await orchestrator.repo.count_items() == 2

    # retention_days=1, so the 3-day-old item should be removed
    deleted = await orchestrator.run_cleanup()
    assert deleted == 1

    remaining = await orchestrator.repo.count_items()
    assert remaining == 1

    # Verify the remaining item is the recent one
    item = await orchestrator.repo.get_item(recent_item.id)
    assert item is not None
    assert item.source_url == "https://example.com/recent-item"


@pytest.mark.asyncio
async def test_metadata_updated_after_fetch(orchestrator):
    """After a successful fetch, last_fetch_at and last_fetch_status are set."""
    items = [_make_item()]

    with patch.object(
        orchestrator.fetchers[0], "safe_fetch", AsyncMock(return_value=items)
    ), patch.object(
        orchestrator.fetchers[1], "safe_fetch", AsyncMock(return_value=[])
    ), patch.object(
        orchestrator.fetchers[2], "safe_fetch", AsyncMock(return_value=[])
    ), patch.object(
        orchestrator.fetchers[3], "safe_fetch", AsyncMock(return_value=[])
    ), patch.object(
        orchestrator.translation,
        "translate_items",
        side_effect=_fake_translate,
    ):
        await orchestrator.run_fetch_cycle()

    last_fetch = await orchestrator.repo.get_metadata("last_fetch_at")
    assert last_fetch is not None
    # Verify it parses as an ISO datetime
    parsed = datetime.fromisoformat(last_fetch)
    assert parsed.tzinfo is not None or parsed.year >= 2020

    last_status = await orchestrator.repo.get_metadata("last_fetch_status")
    assert last_status == "success"
