# Task 002: Database Layer

**depends-on**: task-001

## Description

Create the SQLite database schema, data access repository, and Pydantic models for feed items and system metadata. Implement deduplication logic, data retention cleanup, and startup catch-up check.

## Execution Context

**Task Number**: 002 of 009
**Phase**: Foundation
**Prerequisites**: Backend project structure exists (task-001)

## BDD Scenario

```gherkin
Scenario: Duplicate detection by source_url
  Given the database contains a feed item with source_url "https://reddit.com/r/anime/comments/abc123"
  When the Reddit fetcher returns an item with the same source_url
  Then the deduplication filter detects the duplicate
  And the duplicate item is skipped without error
  And no duplicate entry is created in the database

Scenario: Auto-cleanup removes items older than 7 days
  Given the database contains items from the past 10 days
  And the cleanup job runs daily
  When the cleanup job executes
  Then all items with fetched_at older than 7 days are deleted
  And items from the past 7 days are retained
  And the system logs INFO "Cleaned up N expired items"

Scenario: Cleanup preserves all items from the past 7 days
  Given the database contains 500 items from the past 7 days
  And 200 items older than 7 days
  When the cleanup job executes
  Then the 500 recent items are preserved
  And the 200 old items are deleted

Scenario: Cleanup runs once per day at off-peak hours
  Given the APScheduler has a cleanup job configured
  When the daily schedule triggers (e.g., 04:00 UTC)
  Then the cleanup job executes DELETE FROM feed_items WHERE fetched_at < datetime('now', '-7 days')
  And the job logs the number of deleted items
  And the job updates system_metadata with last_cleanup_at

Scenario: Database size stays under 500 MB with retention policy
  Given the system fetches approximately 200 items per day
  And each item averages approximately 1 KB in the database
  And the retention policy is 7 days
  When the system is at steady state
  Then the maximum number of active items is approximately 1400 (200 x 7)
  And the database size is approximately 1.4 MB

Scenario: Cleanup handles database errors
  Given the SQLite database is temporarily locked or corrupted
  When the cleanup job executes
  Then the DELETE query fails
  And the system logs an ERROR "Cleanup failed: {error details}"
  And the job does not crash the application
  And the next scheduled cleanup will retry

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

- Create: `backend/app/db.py` (database initialization, connection management)
- Create: `backend/app/models.py` (Pydantic models)
- Create: `backend/app/repository.py` (data access layer)
- Create: `backend/tests/test_database.py`

## Steps

### Step 1: Create Pydantic models
- Create `app/models.py` with:
  - `SourceEnum(str, Enum)`: reddit, anilist, steam, anime_news
  - `FeedItemBase`: source, source_url, original_title, translated_title, original_body, translated_body, heat_score, source_metadata (dict), language (default "zh-CN")
  - `FeedItem(FeedItemBase)`: id (UUID), fetched_at, translated_at
  - `FeedResponse`: items (list[FeedItem]), total, page, per_page, has_next
  - `HealthResponse`: status, last_fetch_at, total_items, db_size_mb, last_fetch_status (optional)
  - `SourceConfig`: name, label, enabled

### Step 2: Create database module
- Create `app/db.py` with:
  - `init_db(db_path: str)`: Create tables and indexes
  - SQL schema:
    - `feed_items` table: id TEXT PK, source TEXT, source_url TEXT UNIQUE, original_title TEXT, translated_title TEXT, original_body TEXT, translated_body TEXT, heat_score REAL, source_metadata TEXT (JSON), fetched_at TEXT, translated_at TEXT, language TEXT
    - Indexes on heat_score DESC, fetched_at DESC, source, source_url
    - `system_metadata` table: key TEXT PK, value TEXT
  - Enable WAL mode on connection
  - `get_connection(db_path: str)`: async context manager returning aiosqlite connection

### Step 3: Create repository
- Create `app/repository.py` with:
  - `FeedRepository` class taking db_path in constructor
  - `insert_items(items: list[FeedItem])`: Batch INSERT with dedup by source_url (INSERT OR IGNORE)
  - `get_feed(source: list[str] | None, sort: str, page: int, per_page: int) -> FeedResponse`: Query with filters and pagination
  - `get_item(item_id: str) -> FeedItem | None`: Single item lookup
  - `count_items() -> int`: Total item count
  - `get_existing_urls(urls: list[str]) -> set[str]`: For dedup check
  - `cleanup_old_items(retention_days: int) -> int`: Delete items older than N days, return count
  - `get_metadata(key: str) -> str | None`: Read system_metadata
  - `set_metadata(key: str, value: str)`: Write system_metadata
  - `get_db_size_mb() -> float`: Get database file size
  - Body truncation helper: `truncate_body(text: str, max_length: int = 500) -> str`

### Step 4: Implement tests
- Create `tests/test_database.py` with tests for:
  - Database initialization creates correct tables and indexes
  - Insert items and retrieve them
  - Dedup: inserting same source_url twice only keeps one
  - Body truncation: 1500 char body truncated to 500
  - Body truncation: short body stored as-is
  - Cleanup: items older than 7 days deleted, recent kept
  - Cleanup: returns correct deleted count
  - Cleanup: handles database error gracefully
  - get_feed: pagination, source filtering, sorting
  - Metadata: get/set roundtrip
  - Use in-memory SQLite (`:memory:`) for tests
  - Use test doubles: no external dependencies

### Step 5: Verify
- Run tests, ensure all pass

## Verification Commands

```bash
cd backend
pytest tests/test_database.py -v
```

## Success Criteria

- All database tests pass
- Dedup works by source_url
- Cleanup deletes items older than retention period
- Body truncation works correctly
- WAL mode enabled
- Repository provides all needed query methods
