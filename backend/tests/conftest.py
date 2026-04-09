import asyncio

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.db import init_db
from app.main import create_app


@pytest.fixture
def temp_db(tmp_path):
    """Provide a temporary directory for the test database."""
    db_dir = tmp_path / "data"
    db_dir.mkdir()
    db_path = str(db_dir / "test_acgfeed.db")
    return db_path


@pytest.fixture
def test_settings(temp_db):
    """Return a Settings instance configured for testing."""
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
def test_client(test_settings):
    """Provide a FastAPI TestClient configured with test settings.

    The database is initialised before the client is returned so that
    endpoints can query tables immediately.
    """
    application = create_app(settings=test_settings)
    # Initialise the database tables synchronously before returning the client.
    # The lifespan does not run with TestClient (unless used as a context
    # manager), so we must do this manually.
    asyncio.get_event_loop().run_until_complete(init_db(test_settings.database_path))
    return TestClient(application)
