# Task 006: Fetch Orchestrator & Cron Test

**depends-on**: task-002, task-003-heat-score-impl, task-004-source-fetchers-impl, task-005-translation-service-impl

## Description

Write failing tests for the fetch orchestrator that coordinates all fetchers, deduplication, translation, scoring, storage, and the APScheduler cron job.

## Execution Context

**Task Number**: 006 of 009
**Phase**: Integration
**Prerequisites**: Database, heat score, fetchers, and translation service all implemented

## BDD Scenario

```gherkin
Scenario: Fetch posts from all sources successfully (orchestration)
  Given all external APIs are available
  And the last fetch cycle completed 30 minutes ago
  When the scheduler triggers a new fetch cycle
  Then all raw items are collected into an in-memory queue
  And the deduplication filter removes items with existing source_urls
  And new items are sent to the translation pipeline
  And heat scores are calculated for each new item
  And new items are inserted into the SQLite database
  And the system_metadata records last_fetch_at and last_fetch_status

Scenario: All sources fail
  Given all external APIs return errors or time out
  When the scheduler triggers a new fetch cycle
  Then the system logs an ERROR "All sources failed in this cycle"
  And no new items are inserted into the database
  And existing feed items remain unchanged
  And the health endpoint reflects the failed fetch status

Scenario: Fetch cycle runs every 30 minutes with jitter
  Given the APScheduler is configured with interval trigger of 30 minutes
  And jitter is set to 0-60 seconds
  When the system starts
  Then the first fetch cycle runs at startup
  And subsequent cycles run approximately every 30 minutes

Scenario: Backend triggers fetch on startup after missed cycle
  Given the backend has been restarted
  And system_metadata.last_fetch_at is 45 minutes ago
  When the backend finishes startup
  Then an immediate fetch cycle is triggered

Scenario: Backend skips startup fetch when recently fetched
  Given the backend has been restarted
  And system_metadata.last_fetch_at is 10 minutes ago
  When the backend finishes startup
  Then no immediate fetch cycle is triggered
```

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `backend/tests/test_orchestrator.py`

## Steps

### Step 1: Create test file
- Create `tests/test_orchestrator.py`
- Mock all fetchers and translation service
- Use in-memory SQLite for database operations

### Step 2: Write failing tests
- `test_full_fetch_cycle_happy_path`: Mock all fetchers returning items, mock translation, verify items stored in DB with correct scores
- `test_dedup_in_orchestrator`: Pre-populate DB with an item, verify duplicate is skipped
- `test_all_sources_fail`: Mock all fetchers returning empty, verify no crash, no DB changes, metadata updated
- `test_partial_sources_fail`: Mock Reddit failing, others succeeding, verify only working sources' items stored
- `test_startup_catch_up_missed`: Set last_fetch_at to 45 min ago, verify immediate fetch triggered
- `test_startup_catch_up_recent`: Set last_fetch_at to 10 min ago, verify no immediate fetch
- `test_cleanup_scheduled`: Verify cleanup job is registered with APScheduler
- `test_metadata_updated_after_fetch`: Verify last_fetch_at and last_fetch_status updated after cycle

### Step 3: Verify tests fail (Red)

## Verification Commands

```bash
cd backend
pytest tests/test_orchestrator.py -v  # All should FAIL
```

## Success Criteria

- All orchestrator tests exist and fail
- Tests mock external dependencies (fetchers, translation, time)
- Tests use real SQLite (in-memory) for database operations
