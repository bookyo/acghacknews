"""Tests for the database layer: init_db, FeedRepository, and body truncation."""

import json
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.db import get_connection, init_db
from app.models import FeedItem, SourceEnum
from app.repository import FeedRepository, truncate_body


def _make_item(
    *,
    item_id: str = "id-1",
    source: SourceEnum = SourceEnum.reddit,
    source_url: str = "https://example.com/1",
    original_title: str = "Original Title",
    translated_title: str = "Translated Title",
    original_body: str = "Original body text",
    translated_body: str = "Translated body text",
    heat_score: float = 0.0,
    fetched_at: datetime | None = None,
    translated_at: datetime | None = None,
    source_metadata: dict | None = None,
    language: str = "zh-CN",
) -> FeedItem:
    """Helper to create a FeedItem with sensible defaults."""
    return FeedItem(
        id=item_id,
        source=source,
        source_url=source_url,
        original_title=original_title,
        translated_title=translated_title,
        original_body=original_body,
        translated_body=translated_body,
        heat_score=heat_score,
        fetched_at=fetched_at or datetime.now(timezone.utc),
        translated_at=translated_at,
        source_metadata=source_metadata or {},
        language=language,
    )


# ---------------------------------------------------------------------------
# Fixtures — each test gets its own temporary file-based SQLite database
#           (behaves identically to :memory: for testing purposes).
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Return a unique temporary database file path for testing."""
    return str(tmp_path / f"test_{uuid.uuid4().hex}.db")


@pytest.fixture
async def initialized_db(db_path):
    """Provide an initialized database via init_db."""
    await init_db(db_path)
    return db_path


@pytest.fixture
def repo(initialized_db):
    """Provide a FeedRepository pointed at the initialized test database."""
    return FeedRepository(initialized_db)


# ---------------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------------

class TestInitDb:
    """Tests for init_db creating correct tables and indexes."""

    @pytest.mark.asyncio
    async def test_creates_feed_items_table(self, initialized_db):
        async with get_connection(initialized_db) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='feed_items'"
            )
            row = await cursor.fetchone()
            assert row is not None

    @pytest.mark.asyncio
    async def test_creates_system_metadata_table(self, initialized_db):
        async with get_connection(initialized_db) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='system_metadata'"
            )
            row = await cursor.fetchone()
            assert row is not None

    @pytest.mark.asyncio
    async def test_creates_indexes(self, initialized_db):
        async with get_connection(initialized_db) as db:
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_feed_items_%'"
            )
            rows = await cursor.fetchall()
            index_names = {row["name"] for row in rows}
            assert "idx_feed_items_heat_score" in index_names
            assert "idx_feed_items_fetched_at" in index_names
            assert "idx_feed_items_source" in index_names
            assert "idx_feed_items_source_url" in index_names


# ---------------------------------------------------------------------------
# Insert and retrieve
# ---------------------------------------------------------------------------

class TestInsertAndRetrieve:
    """Tests for inserting items and retrieving them via get_feed."""

    @pytest.mark.asyncio
    async def test_insert_and_get_feed(self, repo):
        item = _make_item()
        inserted = await repo.insert_items([item])
        assert inserted == 1

        result = await repo.get_feed()
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].id == "id-1"
        assert result.items[0].source == SourceEnum.reddit

    @pytest.mark.asyncio
    async def test_get_item_by_id(self, repo):
        item = _make_item(item_id="abc-123")
        await repo.insert_items([item])

        found = await repo.get_item("abc-123")
        assert found is not None
        assert found.source_url == item.source_url

        missing = await repo.get_item("nonexistent")
        assert missing is None


# ---------------------------------------------------------------------------
# Dedup
# ---------------------------------------------------------------------------

class TestDedup:
    """Dedup: inserting the same source_url twice only keeps one."""

    @pytest.mark.asyncio
    async def test_duplicate_source_url_ignored(self, repo):
        item1 = _make_item(item_id="id-1", source_url="https://example.com/dup")
        item2 = _make_item(item_id="id-2", source_url="https://example.com/dup")

        inserted1 = await repo.insert_items([item1])
        assert inserted1 == 1

        inserted2 = await repo.insert_items([item2])
        assert inserted2 == 0

        total = await repo.count_items()
        assert total == 1

        # The original item should still be there
        found = await repo.get_item("id-1")
        assert found is not None


# ---------------------------------------------------------------------------
# Body truncation
# ---------------------------------------------------------------------------

class TestTruncateBody:
    """Tests for the truncate_body helper function."""

    def test_long_body_truncated_to_500(self):
        long_text = "A" * 1500
        result = truncate_body(long_text)
        assert len(result) == 500
        assert result == "A" * 500

    def test_short_body_unchanged(self):
        short_text = "Hello world"
        result = truncate_body(short_text)
        assert result == short_text
        assert len(result) == 11

    def test_exact_500_chars_unchanged(self):
        exact_text = "B" * 500
        result = truncate_body(exact_text)
        assert len(result) == 500
        assert result == exact_text

    def test_custom_max_length(self):
        text = "C" * 300
        result = truncate_body(text, max_length=200)
        assert len(result) == 200


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

class TestCleanup:
    """Tests for cleanup_old_items."""

    @pytest.mark.asyncio
    async def test_old_items_deleted_recent_kept(self, repo):
        now = datetime.now(timezone.utc)
        old_item = _make_item(
            item_id="old-1",
            source_url="https://example.com/old",
            fetched_at=now - timedelta(days=10),
        )
        recent_item = _make_item(
            item_id="recent-1",
            source_url="https://example.com/recent",
            fetched_at=now - timedelta(days=1),
        )
        await repo.insert_items([old_item, recent_item])

        deleted = await repo.cleanup_old_items(7)
        assert deleted == 1

        remaining = await repo.count_items()
        assert remaining == 1

        found = await repo.get_item("recent-1")
        assert found is not None

    @pytest.mark.asyncio
    async def test_cleanup_returns_correct_count(self, repo):
        now = datetime.now(timezone.utc)
        items = [
            _make_item(
                item_id=f"old-{i}",
                source_url=f"https://example.com/old-{i}",
                fetched_at=now - timedelta(days=10 + i),
            )
            for i in range(3)
        ]
        await repo.insert_items(items)

        deleted = await repo.cleanup_old_items(7)
        assert deleted == 3

    @pytest.mark.asyncio
    async def test_cleanup_handles_database_error_gracefully(self, repo):
        """When the underlying DB raises an exception, cleanup returns 0."""
        with patch(
            "app.repository.get_connection",
            side_effect=Exception("simulated DB failure"),
        ):
            deleted = await repo.cleanup_old_items(7)
            assert deleted == 0


# ---------------------------------------------------------------------------
# get_feed: filtering, sorting, pagination
# ---------------------------------------------------------------------------

class TestGetFeed:
    """Tests for get_feed: source filtering, sorting, and pagination."""

    @pytest.fixture
    async def populated_repo(self, repo):
        """Repository with items from multiple sources and varying scores."""
        now = datetime.now(timezone.utc)
        items = [
            _make_item(
                item_id="r1",
                source=SourceEnum.reddit,
                source_url="https://reddit.com/1",
                heat_score=50.0,
                fetched_at=now - timedelta(hours=3),
            ),
            _make_item(
                item_id="r2",
                source=SourceEnum.reddit,
                source_url="https://reddit.com/2",
                heat_score=30.0,
                fetched_at=now - timedelta(hours=1),
            ),
            _make_item(
                item_id="a1",
                source=SourceEnum.anilist,
                source_url="https://anilist.co/1",
                heat_score=90.0,
                fetched_at=now - timedelta(hours=2),
            ),
            _make_item(
                item_id="s1",
                source=SourceEnum.steam,
                source_url="https://store.steampowered.com/1",
                heat_score=10.0,
                fetched_at=now - timedelta(hours=5),
            ),
        ]
        await repo.insert_items(items)
        return repo

    @pytest.mark.asyncio
    async def test_source_filtering(self, populated_repo):
        result = await populated_repo.get_feed(sources=["reddit"])
        assert result.total == 2
        assert all(item.source == SourceEnum.reddit for item in result.items)

    @pytest.mark.asyncio
    async def test_source_filtering_multiple(self, populated_repo):
        result = await populated_repo.get_feed(sources=["reddit", "steam"])
        assert result.total == 3
        sources = {item.source for item in result.items}
        assert sources == {SourceEnum.reddit, SourceEnum.steam}

    @pytest.mark.asyncio
    async def test_sort_by_hot(self, populated_repo):
        result = await populated_repo.get_feed(sort="hot")
        scores = [item.heat_score for item in result.items]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_sort_by_new(self, populated_repo):
        result = await populated_repo.get_feed(sort="new")
        times = [item.fetched_at for item in result.items]
        assert times == sorted(times, reverse=True)

    @pytest.mark.asyncio
    async def test_pagination_page_and_per_page(self, populated_repo):
        result = await populated_repo.get_feed(page=1, per_page=2)
        assert len(result.items) == 2
        assert result.page == 1
        assert result.per_page == 2
        assert result.has_next is True
        assert result.total == 4

    @pytest.mark.asyncio
    async def test_pagination_last_page(self, populated_repo):
        result = await populated_repo.get_feed(page=2, per_page=2)
        assert len(result.items) == 2
        assert result.has_next is False

    @pytest.mark.asyncio
    async def test_pagination_beyond_last_page(self, populated_repo):
        result = await populated_repo.get_feed(page=3, per_page=2)
        assert len(result.items) == 0
        assert result.has_next is False

    @pytest.mark.asyncio
    async def test_no_filters_returns_all(self, populated_repo):
        result = await populated_repo.get_feed()
        assert result.total == 4


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

class TestMetadata:
    """Tests for get_metadata / set_metadata roundtrip."""

    @pytest.mark.asyncio
    async def test_metadata_roundtrip(self, repo):
        await repo.set_metadata("last_fetch", "2025-01-01T00:00:00Z")
        value = await repo.get_metadata("last_fetch")
        assert value == "2025-01-01T00:00:00Z"

    @pytest.mark.asyncio
    async def test_metadata_missing_key_returns_none(self, repo):
        value = await repo.get_metadata("nonexistent")
        assert value is None

    @pytest.mark.asyncio
    async def test_metadata_upsert(self, repo):
        await repo.set_metadata("key1", "value1")
        await repo.set_metadata("key1", "value2")
        value = await repo.get_metadata("key1")
        assert value == "value2"


# ---------------------------------------------------------------------------
# get_existing_urls
# ---------------------------------------------------------------------------

class TestGetExistingUrls:
    @pytest.mark.asyncio
    async def test_returns_existing_subset(self, repo):
        item = _make_item(source_url="https://example.com/existing")
        await repo.insert_items([item])

        urls = [
            "https://example.com/existing",
            "https://example.com/missing",
        ]
        existing = await repo.get_existing_urls(urls)
        assert existing == {"https://example.com/existing"}

    @pytest.mark.asyncio
    async def test_empty_input(self, repo):
        existing = await repo.get_existing_urls([])
        assert existing == set()


# ---------------------------------------------------------------------------
# count_items
# ---------------------------------------------------------------------------

class TestCountItems:
    @pytest.mark.asyncio
    async def test_count_empty(self, repo):
        assert await repo.count_items() == 0

    @pytest.mark.asyncio
    async def test_count_after_inserts(self, repo):
        items = [
            _make_item(item_id=f"id-{i}", source_url=f"https://example.com/{i}")
            for i in range(5)
        ]
        await repo.insert_items(items)
        assert await repo.count_items() == 5
