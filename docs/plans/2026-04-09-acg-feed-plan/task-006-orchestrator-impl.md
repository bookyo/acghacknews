# Task 006: Fetch Orchestrator & Cron Impl

**depends-on**: task-006-orchestrator-test

## Description

Implement the fetch orchestrator that coordinates all components: parallel fetching, deduplication, translation, scoring, storage, and APScheduler configuration including startup catch-up and daily cleanup.

## Execution Context

**Task Number**: 006 of 009
**Phase**: Integration
**Prerequisites**: Orchestrator tests exist and fail (task-006-test)

## BDD Scenario

Same scenarios as task-006-test — implementation makes them pass.

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `backend/app/orchestrator.py`
- Modify: `backend/app/main.py` (wire up scheduler and startup)

## Steps

### Step 1: Implement FetchOrchestrator
- Create `app/orchestrator.py`
- Class `FetchOrchestrator`:
  - Constructor takes: fetchers (list), translation_service, repository, settings
  - `async def run_fetch_cycle()`: Main orchestration method
    1. Run all fetchers in parallel via `asyncio.gather(*[f.safe_fetch(client) for f in fetchers], return_exceptions=True)`
    2. Flatten results into single list
    3. Dedup: query repository for existing URLs, filter out duplicates
    4. Translate: call translation_service.translate_items(new_items)
    5. Score: call calculate_heat_score for each item
    6. Store: call repository.insert_items(items)
    7. Update metadata: set last_fetch_at, last_fetch_status
    8. Handle all-sources-failed case: log ERROR, set status

### Step 2: Configure APScheduler
- In `app/main.py`:
  - Create BackgroundScheduler with APScheduler
  - Add interval job: fetch_all_sources every 30 minutes, jitter 0-60 seconds
  - Add cron job: cleanup_old_items daily at 04:00 UTC
  - Startup event: check last_fetch_at, if >30 min ago, trigger immediate fetch

### Step 3: Wire everything together
- In `create_app()`:
  - Initialize database
  - Create fetcher instances with settings
  - Create TranslationService with API key
  - Create FetchOrchestrator
  - Register scheduler jobs
  - Add startup event handler for catch-up

### Step 4: Verify tests pass (Green)
- Run `pytest tests/test_orchestrator.py -v`

## Verification Commands

```bash
cd backend
pytest tests/test_orchestrator.py -v  # All should PASS
pytest -v  # Full suite passes
```

## Success Criteria

- All orchestrator tests pass
- APScheduler configured with 30-min fetch + daily cleanup
- Startup catch-up works when last_fetch is stale
- All components wired together correctly
