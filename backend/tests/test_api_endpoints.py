"""Tests for API endpoints: feed, health, sources, and admin."""

import asyncio
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import init_db
from app.main import create_app
from app.models import FeedItem, SourceEnum
from app.repository import FeedRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_item(
    index: int,
    source: str = "reddit",
    heat_score: float = 50.0,
    fetched_at: datetime | None = None,
) -> FeedItem:
    """Create a FeedItem suitable for testing."""
    now = fetched_at or datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    return FeedItem(
        id=f"item-{source}-{index}",
        source=source,
        source_url=f"https://example.com/{source}/{index}",
        original_title=f"Original Title {index}",
        translated_title=f"Translated Title {index}",
        original_body=f"Body text for item {index}",
        translated_body=f"Translated body for item {index}",
        heat_score=heat_score,
        source_metadata={"foo": "bar"},
        language="zh-CN",
        fetched_at=now,
        translated_at=now,
    )


async def _seed_items(repo: FeedRepository, count: int = 25) -> list[FeedItem]:
    """Insert *count* test items spread across sources and return them."""
    sources = ["reddit", "anilist", "steam", "anime_news"]
    items: list[FeedItem] = []
    for i in range(count):
        src = sources[i % len(sources)]
        score = float(count - i) * 10  # decreasing heat
        fetched = datetime(2026, 1, 1, i % 24, i % 60, 0, tzinfo=timezone.utc)
        items.append(_make_item(i, source=src, heat_score=score, fetched_at=fetched))
    await repo.insert_items(items)
    return items


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_db(tmp_path):
    """Provide a temporary database path for testing."""
    db_dir = tmp_path / "data"
    db_dir.mkdir()
    return str(db_dir / "test_acgfeed.db")


@pytest.fixture
def test_settings(temp_db):
    """Return Settings configured for testing."""
    return Settings(
        deepseek_api_key="test-key",
        reddit_client_id="test-reddit-id",
        reddit_client_secret="test-reddit-secret",
        reddit_user_agent="acgfeed-test/1.0",
        database_path=temp_db,
        admin_api_key="test-admin-key",
        frontend_url="http://localhost:3000",
        log_level="WARNING",
        retention_days=1,
        fetch_interval_minutes=5,
    )


@pytest.fixture
def app(test_settings):
    """Create a FastAPI app wired with test settings."""
    return create_app(settings=test_settings)


@pytest.fixture
def client(app):
    """Provide a TestClient for the configured app."""
    return TestClient(app)


@pytest.fixture
def repo(app):
    """Return the FeedRepository attached to the test app."""
    return app.state.repo


def _init_and_seed(repo, count=25):
    """Synchronous helper: init DB and seed items."""
    async def _run():
        await init_db(repo.db_path)
        return await _seed_items(repo, count)
    return asyncio.get_event_loop().run_until_complete(_run())


def _init_db(repo):
    """Synchronous helper: just init DB."""
    asyncio.get_event_loop().run_until_complete(init_db(repo.db_path))


def _set_metadata(repo, key, value):
    """Synchronous helper: set metadata."""
    asyncio.get_event_loop().run_until_complete(repo.set_metadata(key, value))


# ---------------------------------------------------------------------------
# Feed endpoint tests
# ---------------------------------------------------------------------------

class TestFeedEndpoint:
    """Tests for GET /api/feed."""

    def test_feed_endpoint_default(self, client, repo):
        """GET /api/feed returns paginated results with default params."""
        _init_and_seed(repo, 25)
        resp = client.get("/api/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) == 20  # default per_page
        assert data["total"] == 25
        assert data["page"] == 1
        assert data["per_page"] == 20
        assert data["has_next"] is True

    def test_feed_endpoint_source_filter(self, client, repo):
        """GET /api/feed?sources=reddit,anilist filters to those sources."""
        _init_and_seed(repo, 25)
        resp = client.get("/api/feed", params={"sources": "reddit,anilist"})
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["source"] in ("reddit", "anilist")
        # 25 items, 4 sources round-robin -> reddit gets indices 0,4,8,12,16,20,24 = 7
        # anilist gets 1,5,9,13,17,21 = 6, total = 13
        assert data["total"] == 13

    def test_feed_endpoint_sort_new(self, client, repo):
        """GET /api/feed?sort=new returns items ordered by fetched_at DESC."""
        _init_and_seed(repo, 25)
        resp = client.get("/api/feed", params={"sort": "new"})
        assert resp.status_code == 200
        data = resp.json()
        items = data["items"]
        assert len(items) > 0
        # Items are sorted by fetched_at DESC; later timestamps come first.
        for i in range(len(items) - 1):
            cur = datetime.fromisoformat(items[i]["fetched_at"])
            nxt = datetime.fromisoformat(items[i + 1]["fetched_at"])
            assert cur >= nxt

    def test_feed_endpoint_pagination(self, client, repo):
        """Pagination: page 1 has has_next, page 2 returns remaining items."""
        _init_and_seed(repo, 25)
        # Page 1
        resp1 = client.get("/api/feed", params={"page": 1, "per_page": 10})
        data1 = resp1.json()
        assert len(data1["items"]) == 10
        assert data1["has_next"] is True
        assert data1["page"] == 1

        # Page 2
        resp2 = client.get("/api/feed", params={"page": 2, "per_page": 10})
        data2 = resp2.json()
        assert len(data2["items"]) == 10
        assert data2["has_next"] is True
        assert data2["page"] == 2

        # Page 3 (last)
        resp3 = client.get("/api/feed", params={"page": 3, "per_page": 10})
        data3 = resp3.json()
        assert len(data3["items"]) == 5
        assert data3["has_next"] is False
        assert data3["page"] == 3

        # All item IDs are unique across pages
        all_ids = (
            [i["id"] for i in data1["items"]]
            + [i["id"] for i in data2["items"]]
            + [i["id"] for i in data3["items"]]
        )
        assert len(all_ids) == 25
        assert len(set(all_ids)) == 25


class TestFeedItemEndpoint:
    """Tests for GET /api/feed/{item_id}."""

    def test_feed_item_endpoint(self, client, repo):
        """GET /api/feed/{id} returns a single feed item."""
        items = _init_and_seed(repo, 5)
        target_id = items[0].id
        resp = client.get(f"/api/feed/{target_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == target_id
        assert "translated_title" in data
        assert "heat_score" in data

    def test_feed_item_404(self, client, repo):
        """GET /api/feed/nonexistent returns 404."""
        _init_db(repo)
        resp = client.get("/api/feed/nonexistent-id")
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Feed item not found"


# ---------------------------------------------------------------------------
# Health endpoint tests
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """Tests for GET /api/health."""

    def test_health_healthy(self, client, repo):
        """Health endpoint returns healthy status on fresh start."""
        _init_db(repo)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["total_items"] == 0
        assert data["db_size_mb"] >= 0.0
        assert data["last_fetch_at"] is None
        assert data["last_fetch_status"] is None

    def test_health_degraded(self, client, repo):
        """Health endpoint returns degraded when last_fetch_status is all_sources_failed."""
        _init_db(repo)
        _set_metadata(repo, "last_fetch_status", "all_sources_failed")
        _set_metadata(repo, "last_fetch_at", datetime.now(timezone.utc).isoformat())
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["last_fetch_status"] == "all_sources_failed"

    def test_health_degraded_old_fetch(self, client, repo):
        """Health endpoint returns degraded when last fetch was more than 2 hours ago."""
        _init_db(repo)
        old_time = datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        _set_metadata(repo, "last_fetch_at", old_time.isoformat())
        _set_metadata(repo, "last_fetch_status", "success")
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"

    def test_health_healthy_recent_fetch(self, client, repo):
        """Health endpoint returns healthy when fetch was recent and successful."""
        _init_db(repo)
        _set_metadata(repo, "last_fetch_at", datetime.now(timezone.utc).isoformat())
        _set_metadata(repo, "last_fetch_status", "success")
        _init_and_seed(repo, 10)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["total_items"] == 10


# ---------------------------------------------------------------------------
# Sources endpoint tests
# ---------------------------------------------------------------------------

class TestSourcesEndpoint:
    """Tests for GET /api/sources."""

    def test_sources_endpoint(self, client, repo):
        """Sources endpoint returns the configured list of sources."""
        _init_db(repo)
        resp = client.get("/api/sources")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4
        names = {s["name"] for s in data}
        assert names == {"reddit", "anilist", "steam", "anime_news"}
        # All enabled by default
        assert all(s["enabled"] for s in data)
        # Each has a label
        assert all(s["label"] for s in data)


# ---------------------------------------------------------------------------
# Admin endpoint tests
# ---------------------------------------------------------------------------

class TestAdminEndpoint:
    """Tests for POST /api/admin/trigger-fetch."""

    def test_admin_trigger_success(self, client, repo):
        """Valid admin key returns 200 with fetch_triggered status."""
        _init_db(repo)
        resp = client.post(
            "/api/admin/trigger-fetch",
            headers={"X-Admin-Key": "test-admin-key"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "fetch_triggered"

    def test_admin_trigger_invalid_key(self, client, repo):
        """Invalid admin key returns 401 Unauthorized."""
        _init_db(repo)
        resp = client.post(
            "/api/admin/trigger-fetch",
            headers={"X-Admin-Key": "wrong-key"},
        )
        assert resp.status_code == 401

    def test_admin_trigger_missing_key(self, client, repo):
        """Missing admin key returns 401 Unauthorized."""
        _init_db(repo)
        resp = client.post("/api/admin/trigger-fetch")
        assert resp.status_code == 401
