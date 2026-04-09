"""Tests for source fetchers: Reddit, AniList, Steam, RSS."""

import json
import re
from typing import Any

import httpx
import pytest
import respx

from app.fetchers.base import BaseFetcher, truncate_body
from app.fetchers.reddit import RedditFetcher, SUPPORTED_SUBREDDITS
from app.fetchers.anilist import AniListFetcher
from app.fetchers.steam import SteamFetcher
from app.fetchers.rss import RSSFetcher


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def http_client():
    """Provide an httpx.AsyncClient with trust_env=False to skip proxy."""
    return httpx.AsyncClient(trust_env=False)


@pytest.fixture
def reddit_fetcher():
    return RedditFetcher(
        client_id="test-id",
        client_secret="test-secret",
        user_agent="test-agent/1.0",
    )


# ---------------------------------------------------------------------------
# Helper: build realistic mock data
# ---------------------------------------------------------------------------

def _make_reddit_post(
    subreddit: str = "anime",
    title: str = "Test Anime Post",
    selftext: str = "Discussion about anime",
    ups: int = 42,
    num_comments: int = 7,
    permalink: str = "/r/anime/comments/abc123/test_anime_post/",
    author: str = "testuser",
) -> dict[str, Any]:
    return {
        "kind": "t3",
        "data": {
            "title": title,
            "selftext": selftext,
            "ups": ups,
            "num_comments": num_comments,
            "permalink": permalink,
            "subreddit": subreddit,
            "author": author,
        },
    }


def _make_reddit_listing(posts: list[dict]) -> dict[str, Any]:
    return {"data": {"children": posts}}


def _make_anilist_media(
    media_id: int = 1,
    romaji: str = "Test Anime",
    english: str = "Test Anime EN",
    description: str = "A test anime description",
    trending: int = 100,
    popularity: int = 5000,
    site_url: str = "https://anilist.co/anime/1",
) -> dict[str, Any]:
    return {
        "id": media_id,
        "title": {"romaji": romaji, "english": english},
        "description": description,
        "trending": trending,
        "popularity": popularity,
        "siteUrl": site_url,
    }


def _make_steam_item(
    app_id: int = 12345,
    name: str = "Test Game",
    short_description: str = "An exciting test game",
) -> dict[str, Any]:
    return {
        "id": str(app_id),
        "name": name,
        "short_description": short_description,
        "currency": "USD",
    }


def _make_anime_news_rss_xml() -> bytes:
    return b"""<?xml version="1.0" encoding="UTF-8"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns="http://purl.org/rss/1.0/"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
  </channel>
  <item>
    <title>Test News Article</title>
    <link>https://example.com/article/1</link>
    <description>Some &lt;b&gt;HTML&lt;/b&gt; summary text here.</description>
  </item>
  <item>
    <title>Another Article</title>
    <link>https://example.com/article/2</link>
    <description>Plain description.</description>
  </item>
</rdf:RDF>"""


# ===========================================================================
# truncate_body tests
# ===========================================================================

class TestTruncateBody:
    def test_body_truncation_long(self):
        long_text = "A" * 600
        result = truncate_body(long_text, max_length=500)
        assert len(result) == 500
        assert result == "A" * 500

    def test_body_truncation_short(self):
        short_text = "Hello world"
        result = truncate_body(short_text, max_length=500)
        assert result == short_text
        assert len(result) == len(short_text)

    def test_body_truncation_empty(self):
        assert truncate_body("") == ""

    def test_body_truncation_exact(self):
        text = "B" * 500
        result = truncate_body(text, max_length=500)
        assert result == text
        assert len(result) == 500


# ===========================================================================
# RedditFetcher tests
# ===========================================================================

class TestRedditFetcher:

    @pytest.mark.asyncio
    async def test_reddit_fetcher_happy_path(self, reddit_fetcher):
        """Mock OAuth + hot posts for all subreddits, verify normalized items."""
        token_response = {"access_token": "fake-token-123", "token_type": "bearer", "expires_in": 3600}

        # Build one listing per subreddit
        anime_listing = _make_reddit_listing([_make_reddit_post("anime", "Best Anime 2025")])
        manga_listing = _make_reddit_listing([_make_reddit_post("manga", "Best Manga")])
        games_listing = _make_reddit_listing([_make_reddit_post("Games", "Best Game")])

        with respx.mock(assert_all_called=False) as mock:
            # Mock the OAuth token endpoint
            mock.post("https://www.reddit.com/api/v1/access_token").mock(
                return_value=httpx.Response(200, json=token_response)
            )

            # Register each subreddit endpoint explicitly
            mock.get("https://oauth.reddit.com/r/anime/hot").mock(
                return_value=httpx.Response(200, json=anime_listing)
            )
            mock.get("https://oauth.reddit.com/r/manga/hot").mock(
                return_value=httpx.Response(200, json=manga_listing)
            )
            mock.get("https://oauth.reddit.com/r/Games/hot").mock(
                return_value=httpx.Response(200, json=games_listing)
            )

            async with httpx.AsyncClient(trust_env=False) as client:
                results = await reddit_fetcher.safe_fetch(client)

        assert len(results) == 3

        # Verify canonical format fields
        for item in results:
            assert "source" in item
            assert item["source"] == "reddit"
            assert "source_url" in item
            assert "original_title" in item
            assert "original_body" in item
            assert "source_metadata" in item
            assert "engagement_metric" in item

        # Check first item specifically
        anime_item = results[0]
        assert anime_item["original_title"] == "Best Anime 2025"
        assert anime_item["source_url"].startswith("https://www.reddit.com")
        assert anime_item["engagement_metric"] == 42

    @pytest.mark.asyncio
    async def test_reddit_fetcher_timeout(self, reddit_fetcher):
        """Mock timeout, verify empty list."""
        with respx.mock(assert_all_called=False) as mock:
            mock.post("https://www.reddit.com/api/v1/access_token").mock(
                side_effect=httpx.TimeoutException("Connection timed out")
            )

            async with httpx.AsyncClient(trust_env=False) as client:
                results = await reddit_fetcher.safe_fetch(client)

        assert results == []

    @pytest.mark.asyncio
    async def test_reddit_fetcher_500(self, reddit_fetcher):
        """Mock 500 response on the hot posts endpoint, verify empty list."""
        token_response = {"access_token": "fake-token-123", "token_type": "bearer", "expires_in": 3600}

        with respx.mock(assert_all_called=False) as mock:
            mock.post("https://www.reddit.com/api/v1/access_token").mock(
                return_value=httpx.Response(200, json=token_response)
            )

            # Return 500 for the first subreddit request
            mock.get("https://oauth.reddit.com/r/anime/hot").mock(
                return_value=httpx.Response(500, json={"error": "internal server error"})
            )

            async with httpx.AsyncClient(trust_env=False) as client:
                results = await reddit_fetcher.safe_fetch(client)

        assert results == []


# ===========================================================================
# AniListFetcher tests
# ===========================================================================

class TestAniListFetcher:

    @pytest.mark.asyncio
    async def test_anilist_fetcher_happy_path(self):
        """Mock GraphQL response, verify normalized items."""
        fetcher = AniListFetcher()

        anime_media = _make_anilist_media(
            media_id=101, romaji="Shingeki no Kyojin", trending=200, popularity=10000,
            site_url="https://anilist.co/anime/101",
        )
        manga_media = _make_anilist_media(
            media_id=202, romaji=None, english="One Punch Man",
            trending=50, popularity=8000,
            site_url="https://anilist.co/manga/202",
        )
        manga_media["title"]["romaji"] = None

        graphql_response = {
            "data": {
                "TrendingAnime": {"media": [anime_media]},
                "TrendingManga": {"media": [manga_media]},
            }
        }

        with respx.mock(assert_all_called=False) as mock:
            mock.post("https://graphql.anilist.co").mock(
                return_value=httpx.Response(200, json=graphql_response)
            )

            async with httpx.AsyncClient(trust_env=False) as client:
                results = await fetcher.safe_fetch(client)

        assert len(results) == 2

        # Verify anime item
        anime_item = results[0]
        assert anime_item["source"] == "anilist"
        assert anime_item["original_title"] == "Shingeki no Kyojin"
        assert anime_item["engagement_metric"] == 200
        assert anime_item["source_url"] == "https://anilist.co/anime/101"

        # Verify manga item (english fallback)
        manga_item = results[1]
        assert manga_item["original_title"] == "One Punch Man"
        assert manga_item["source_metadata"]["media_type"] == "manga"
        assert manga_item["engagement_metric"] == 50

    @pytest.mark.asyncio
    async def test_anilist_fetcher_error(self):
        """Mock error response, verify empty list."""
        fetcher = AniListFetcher()

        with respx.mock(assert_all_called=False) as mock:
            mock.post("https://graphql.anilist.co").mock(
                return_value=httpx.Response(500, json={"errors": [{"message": "Internal error"}]})
            )

            async with httpx.AsyncClient(trust_env=False) as client:
                results = await fetcher.safe_fetch(client)

        assert results == []


# ===========================================================================
# SteamFetcher tests
# ===========================================================================

class TestSteamFetcher:

    @pytest.mark.asyncio
    async def test_steam_fetcher_happy_path(self):
        """Mock Store API response, verify normalized items."""
        fetcher = SteamFetcher()

        top_item = _make_steam_item(app_id=100, name="Top Seller Game")
        coming_item = _make_steam_item(app_id=200, name="Coming Soon Game")

        store_response = {
            "top_sellers": {"items": [top_item]},
            "coming_soon": {"items": [coming_item]},
        }

        with respx.mock(assert_all_called=False) as mock:
            mock.get("https://store.steampowered.com/api/featuredcategories/").mock(
                return_value=httpx.Response(200, json=store_response)
            )

            async with httpx.AsyncClient(trust_env=False) as client:
                results = await fetcher.safe_fetch(client)

        assert len(results) == 2

        # Verify top seller
        top_result = results[0]
        assert top_result["source"] == "steam"
        assert top_result["original_title"] == "Top Seller Game"
        assert top_result["source_url"] == "https://store.steampowered.com/app/100"
        assert top_result["engagement_metric"] == 0
        assert top_result["source_metadata"]["category"] == "top_sellers"

        # Verify coming soon
        coming_result = results[1]
        assert coming_result["original_title"] == "Coming Soon Game"
        assert coming_result["source_url"] == "https://store.steampowered.com/app/200"
        assert coming_result["source_metadata"]["category"] == "coming_soon"


# ===========================================================================
# RSSFetcher tests
# ===========================================================================

class TestRSSFetcher:

    @pytest.mark.asyncio
    async def test_rss_fetcher_happy_path(self):
        """Mock RSS XML, verify normalized items."""
        fetcher = RSSFetcher(feed_urls=["https://example.com/rss"])

        rss_xml = _make_anime_news_rss_xml()

        with respx.mock(assert_all_called=False) as mock:
            mock.get("https://example.com/rss").mock(
                return_value=httpx.Response(200, content=rss_xml)
            )

            async with httpx.AsyncClient(trust_env=False) as client:
                results = await fetcher.safe_fetch(client)

        assert len(results) == 2

        first = results[0]
        assert first["source"] == "anime_news"
        assert first["original_title"] == "Test News Article"
        assert first["source_url"] == "https://example.com/article/1"
        # HTML should be stripped from summary
        assert "<b>" not in first["original_body"]
        assert "HTML" in first["original_body"]
        assert first["engagement_metric"] == 0

        second = results[1]
        assert second["original_title"] == "Another Article"


# ===========================================================================
# Canonical format verification
# ===========================================================================

class TestCanonicalFormat:

    def test_normalize_returns_canonical_format(self):
        """Verify all required fields present in normalized output."""
        fetcher = RedditFetcher("id", "secret", "agent")

        raw = {
            "title": "Test",
            "selftext": "Body",
            "ups": 10,
            "num_comments": 2,
            "permalink": "/r/anime/test",
            "subreddit": "anime",
            "author": "user",
            "_subreddit": "anime",
        }
        result = fetcher.normalize(raw)

        required_fields = {"source", "source_url", "original_title", "original_body",
                          "source_metadata", "engagement_metric"}
        assert required_fields.issubset(set(result.keys()))

        assert result["source"] == "reddit"
        assert isinstance(result["source_url"], str)
        assert isinstance(result["original_title"], str)
        assert isinstance(result["original_body"], str)
        assert isinstance(result["source_metadata"], dict)
        assert isinstance(result["engagement_metric"], int)
