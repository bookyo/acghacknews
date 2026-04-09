# Task 004: Source Fetchers Impl

**depends-on**: task-004-source-fetchers-test

## Description

Implement the base fetcher pattern and all four source fetchers (Reddit, AniList, Steam, RSS) with error handling, retries, and body truncation.

## Execution Context

**Task Number**: 004 of 009
**Phase**: Core Features
**Prerequisites**: Source fetcher tests exist and fail (task-004-test)

## BDD Scenario

Same scenarios as task-004-test — implementation makes them pass.

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `backend/app/fetchers/__init__.py`
- Create: `backend/app/fetchers/base.py` (BaseFetcher abstract class)
- Create: `backend/app/fetchers/reddit.py` (RedditFetcher)
- Create: `backend/app/fetchers/anilist.py` (AniListFetcher)
- Create: `backend/app/fetchers/steam.py` (SteamFetcher)
- Create: `backend/app/fetchers/rss.py` (RSSFetcher)

## Steps

### Step 1: Implement BaseFetcher
- Create `app/fetchers/base.py`
- Abstract class with:
  - `TIMEOUT = 10.0`, `MAX_RETRIES = 2`
  - `async def fetch(self, client: httpx.AsyncClient) -> list[dict]` (abstract)
  - `def normalize(self, raw: dict) -> dict` (abstract) — returns canonical format: {source, source_url, original_title, original_body, source_metadata, engagement_metric}
  - `async def safe_fetch(self, client: httpx.AsyncClient) -> list[dict]` — wraps fetch() with timeout/error handling, returns [] on failure, logs warnings

### Step 2: Implement RedditFetcher
- Create `app/fetchers/reddit.py`
- OAuth2 client_credentials flow: POST /api/v1/access_token, cache token in memory
- Fetch hot posts from r/anime, r/manga, r/Games (25 each)
- Extract: title, selftext, ups, num_comments, permalink, url
- Normalize to canonical format with source="reddit"
- Body truncation: selftext truncated to 500 chars
- Engagement metric: ups (upvotes)

### Step 3: Implement AniListFetcher
- Create `app/fetchers/anilist.py`
- GraphQL query for trending anime (25) + trending manga (15) + seasonal anime (25)
- Extract: title (romaji/native), description, trending, popularity, siteUrl
- Normalize to canonical format with source="anilist"
- Body truncation: description truncated to 500 chars
- Engagement metric: trending score (fallback to popularity)

### Step 4: Implement SteamFetcher
- Create `app/fetchers/steam.py`
- GET /api/featuredcategories/ for top_sellers + coming_soon
- GET /api/appdetails/{id} for review counts
- Extract: name, short_description, recommendations.total, header_image, store_url
- Normalize to canonical format with source="steam"
- Body truncation: short_description truncated to 500 chars
- Engagement metric: recommendations.total (review count)

### Step 5: Implement RSSFetcher
- Create `app/fetchers/rss.py`
- Parse Anime! Anime! (RDF) and MANTANWEB (RSS 2.0) via feedparser
- Strip HTML tags from summary
- Extract: title, summary, link, published date
- Normalize to canonical format with source="anime_news"
- Engagement metric: None (recency-only scoring)
- Handle encoding issues (Shift-JIS, EUC-JP)

### Step 6: Verify tests pass (Green)
- Run `pytest tests/test_source_fetchers.py -v`

## Verification Commands

```bash
cd backend
pytest tests/test_source_fetchers.py -v  # All should PASS
pytest -v  # Full suite passes
```

## Success Criteria

- All source fetcher tests pass
- Each fetcher handles errors gracefully (returns empty list, logs warning)
- Body text is truncated to 500 chars
- OAuth token caching works for Reddit
- All external calls use httpx with timeout
