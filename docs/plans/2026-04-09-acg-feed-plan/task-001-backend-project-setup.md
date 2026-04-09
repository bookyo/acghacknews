# Task 001: Backend Project Setup

**depends-on**: (none)

## Description

Scaffold the Python backend project with FastAPI, including directory structure, dependency management, configuration, and development tooling. This creates the foundation all other backend tasks build upon.

## Execution Context

**Task Number**: 001 of 009
**Phase**: Setup
**Prerequisites**: Python 3.12+ installed

## BDD Scenario

No specific BDD scenario — this is project scaffolding.

## Files to Modify/Create

- Create: `backend/pyproject.toml` (or `requirements.txt`)
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py` (FastAPI app factory)
- Create: `backend/app/config.py` (pydantic-settings configuration)
- Create: `backend/.env.example`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py` (pytest fixtures)

## Steps

### Step 1: Create project structure
- Create `backend/` directory with `app/` and `tests/` subdirectories
- Initialize with pyproject.toml or requirements.txt including:
  - fastapi, uvicorn, apscheduler, httpx, pydantic, pydantic-settings, feedparser, aiosqlite, openai
  - dev: pytest, pytest-asyncio, httpx (for TestClient)

### Step 2: Create configuration module
- Create `app/config.py` using pydantic-settings `BaseSettings`
- Settings class with fields:
  - `deepseek_api_key: str`
  - `reddit_client_id: str = ""`
  - `reddit_client_secret: str = ""`
  - `reddit_user_agent: str = "acgfeed/1.0"`
  - `database_path: str = "./data/acgfeed.db"`
  - `admin_api_key: str = ""`
  - `frontend_url: str = "http://localhost:3000"`
  - `log_level: str = "INFO"`
  - `retention_days: int = 7`
  - `fetch_interval_minutes: int = 30`

### Step 3: Create FastAPI app factory
- Create `app/main.py` with `create_app()` function that returns a FastAPI instance
- Configure CORS with `frontend_url` as allowed origin
- Include a placeholder health endpoint `GET /api/health`
- Configure structured JSON logging

### Step 4: Create .env.example
- List all required environment variables with placeholder values

### Step 5: Create test configuration
- Create `tests/conftest.py` with pytest fixtures:
  - `test_client`: httpx AsyncClient or FastAPI TestClient
  - `test_settings`: Settings with test values (mock API keys, temp DB path)
  - `temp_db`: temporary SQLite database for tests

### Step 6: Verify setup
- Run `pip install -e ".[dev]"` or `pip install -r requirements.txt`
- Run `pytest` — should find 0 tests and exit cleanly
- Run `uvicorn app.main:app` — should start without errors
- Hit `GET /api/health` — should return `{"status": "healthy"}`

## Verification Commands

```bash
cd backend
pip install -e ".[dev]"  # or pip install -r requirements.txt
pytest  # should exit cleanly, 0 tests collected
uvicorn app.main:app --host 0.0.0.0 --port 8000  # should start
curl http://localhost:8000/api/health  # should return healthy
```

## Success Criteria

- Project installs without errors
- pytest runs without errors
- FastAPI starts and responds to health check
- Configuration loads from .env file
