# Task 004: Source Fetchers Test

**depends-on**: task-001

## Description

Write failing tests for the source fetcher system: base fetcher pattern, Reddit fetcher, AniList fetcher, Steam fetcher, and RSS fetcher. Tests should use HTTP mocking (httpx mock or respx) to isolate from external APIs.

## Execution Context

**Task Number**: 004 of 009
**Phase**: Core Features
**Prerequisites**: Backend project structure exists (task-001)

## BDD Scenario

```gherkin
Scenario: Fetch posts from all sources successfully (happy path - fetcher side)
  Given all external APIs are available
  When the Reddit fetcher runs
  Then it fetches hot posts from r/anime, r/manga, r/Games (25 each)
  And it extracts title, selftext (truncated to 500 chars), upvotes, comment_count, permalink
  When the AniList fetcher runs
  Then it fetches trending anime and manga via GraphQL
  And it extracts title, description, trending score, siteUrl
  When the Steam fetcher runs
  Then it fetches top sellers and new releases
  And it extracts name, short_description, review_count, store_url
  When the RSS fetcher runs
  Then it fetches from Anime! Anime! and MANTANWEB
  And it extracts title, summary, link, pubDate

Scenario: Reddit API is down
  Given the Reddit API returns HTTP 500 or times out
  When the Reddit fetcher runs
  Then it returns an empty list (no crash)
  And it logs a WARNING

Scenario: AniList API is down
  Given the AniList GraphQL endpoint returns an error or times out
  When the AniList fetcher runs
  Then it returns an empty list (no crash)
  And it logs a WARNING

Scenario: Partial source failure with retry
  Given the Steam API returns HTTP 429 (rate limited)
  When the Steam fetcher runs
  Then it waits and retries once
  And if retry fails, it returns empty list and logs WARNING

Scenario: Long body text is truncated to 500 characters
  Given Reddit returns a post with selftext of 1500 characters
  When the fetcher processes this item
  Then original_body is stored as the first 500 characters of the selftext

Scenario: Short body text is stored as-is
  Given AniList returns a media item with description of 200 characters
  When the fetcher processes this item
  Then original_body is stored as the full 200-character description
```

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `backend/tests/test_source_fetchers.py`

## Steps

### Step 1: Create test file
- Create `tests/test_source_fetchers.py`
- Use `httpx` mock transport or `respx` library to mock external API calls
- No real network calls — all external dependencies isolated with test doubles

### Step 2: Write failing tests
- `test_reddit_fetcher_happy_path`: Mock Reddit OAuth + hot posts response, verify normalized items returned
- `test_reddit_fetcher_timeout`: Mock timeout, verify empty list returned
- `test_reddit_fetcher_500`: Mock HTTP 500, verify empty list + no crash
- `test_anilist_fetcher_happy_path`: Mock GraphQL response, verify normalized items
- `test_anilist_fetcher_error`: Mock GraphQL error, verify empty list
- `test_steam_fetcher_happy_path`: Mock Store API response, verify normalized items
- `test_steam_fetcher_429_retry`: Mock 429 then success, verify retry + items returned
- `test_rss_fetcher_happy_path`: Mock RSS feed XML, verify normalized items
- `test_rss_fetcher_parse_error`: Mock malformed XML, verify empty list
- `test_body_truncation_long`: Verify body > 500 chars is truncated
- `test_body_truncation_short`: Verify body < 500 chars is stored as-is
- `test_normalize_returns_canonical_format`: Each fetcher's normalize() returns dict with: source, source_url, original_title, original_body, source_metadata, engagement_metric

### Step 3: Verify tests fail (Red)
- Run pytest — all should FAIL

## Verification Commands

```bash
cd backend
pytest tests/test_source_fetchers.py -v  # All should FAIL
```

## Success Criteria

- All fetcher tests exist and fail
- Tests mock all external HTTP calls (no real network)
- Tests cover happy path, errors, timeouts, body truncation for each fetcher
