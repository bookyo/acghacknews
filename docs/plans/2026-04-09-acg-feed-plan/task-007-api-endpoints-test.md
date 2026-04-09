# Task 007: API Endpoints Test

**depends-on**: task-002

## Description

Write failing tests for all FastAPI endpoints: feed listing, single item, sources, health, and admin trigger.

## Execution Context

**Task Number**: 007 of 009
**Phase**: Core Features
**Prerequisites**: Database layer exists (task-002)

## BDD Scenario

```gherkin
Scenario: Display feed items with pagination
  Given the database contains 200 feed items
  When the client requests GET /api/feed?sort=hot&page=1&per_page=20
  Then the response contains 20 items sorted by heat_score descending
  And total is 200, page is 1, per_page is 20, has_next is true

Scenario: Filter feed by source
  When the client requests GET /api/feed?sources=reddit,anilist
  Then only reddit and anilist items are returned

Scenario: Sort feed by New
  When the client requests GET /api/feed?sort=new
  Then items are sorted by fetched_at descending

Scenario: Health endpoint shows current system state
  Given the system is running normally
  When a client requests GET /api/health
  Then the response contains status, last_fetch_at, total_items, db_size_mb

Scenario: Health endpoint shows degraded state
  Given the last 3 fetch cycles all failed
  When a client requests GET /api/health
  Then the response status is "degraded"

Scenario: Sources endpoint returns source configuration
  When a client requests GET /api/sources
  Then the response lists reddit, anilist, steam, anime_news with labels and enabled status

Scenario: Admin triggers manual fetch successfully
  When a POST request is sent to /api/admin/trigger-fetch with valid X-Admin-Key header
  Then the response status is 200 and contains "status": "fetch_triggered"

Scenario: Admin endpoint rejects invalid key
  When a POST request is sent to /api/admin/trigger-fetch with an invalid X-Admin-Key
  Then the response status is 401
```

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `backend/tests/test_api_endpoints.py`

## Steps

### Step 1: Create test file
- Create `tests/test_api_endpoints.py`
- Use FastAPI TestClient (httpx)
- Use in-memory SQLite with pre-populated test data

### Step 2: Write failing tests
- `test_feed_endpoint_default`: 200 items in DB, GET /api/feed returns paginated results sorted by heat
- `test_feed_endpoint_source_filter`: Filter by sources parameter
- `test_feed_endpoint_sort_new`: Sort by fetched_at descending
- `test_feed_endpoint_pagination`: Verify page/per_page/has_next
- `test_feed_item_endpoint`: GET /api/feed/{id} returns single item
- `test_feed_item_404`: GET /api/feed/nonexistent-id returns 404
- `test_health_healthy`: Verify health response with healthy status
- `test_health_degraded`: Verify health response with degraded status after failed fetches
- `test_sources_endpoint`: Verify source list
- `test_admin_trigger_success`: Valid admin key triggers fetch
- `test_admin_trigger_invalid_key`: Invalid key returns 401
- `test_admin_trigger_missing_key`: Missing key returns 401

### Step 3: Verify tests fail (Red)

## Verification Commands

```bash
cd backend
pytest tests/test_api_endpoints.py -v  # All should FAIL
```

## Success Criteria

- All API endpoint tests exist and fail
- Tests use FastAPI TestClient with test database
- Tests cover happy paths, error cases, and auth
