# Task 007: API Endpoints Impl

**depends-on**: task-007-api-endpoints-test

## Description

Implement all FastAPI endpoints: feed listing with filtering/sorting/pagination, single item, sources list, health status, and admin trigger with authentication.

## Execution Context

**Task Number**: 007 of 009
**Phase**: Core Features
**Prerequisites**: API endpoint tests exist and fail (task-007-test)

## BDD Scenario

Same scenarios as task-007-test — implementation makes them pass.

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `backend/app/routers/feed.py` (feed + item endpoints)
- Create: `backend/app/routers/health.py` (health + sources)
- Create: `backend/app/routers/admin.py` (admin trigger)
- Modify: `backend/app/main.py` (register routers)

## Steps

### Step 1: Create feed router
- Create `app/routers/feed.py` with APIRouter prefix="/api"
- `GET /feed`: Query params sort, sources (comma-separated), page, per_page
  - Validate sources against allowed values
  - Clamp per_page to max 50
  - Call repository.get_feed()
  - Return FeedResponse model

- `GET /feed/{item_id}`: Return single FeedItem or 404

### Step 2: Create health router
- Create `app/routers/health.py`
- `GET /health`: Return HealthResponse from repository + metadata
  - status: "healthy" if last fetch < 2 hours ago, "degraded" otherwise
  - total_items from repository count
  - db_size_mb from repository

- `GET /sources`: Return static list of source configurations

### Step 3: Create admin router
- Create `app/routers/admin.py`
- `POST /admin/trigger-fetch`: Validate X-Admin-Key header against settings
  - 401 on missing/invalid key
  - Trigger fetch cycle asynchronously on success

### Step 4: Register routers
- In `app/main.py`, include all routers

### Step 5: Verify tests pass (Green)

## Verification Commands

```bash
cd backend
pytest tests/test_api_endpoints.py -v  # All should PASS
pytest -v  # Full suite passes
```

## Success Criteria

- All API endpoint tests pass
- Feed endpoint supports filtering, sorting, pagination
- Health endpoint reflects system state
- Admin endpoint validates API key
- All endpoints use Pydantic models for request/response validation
