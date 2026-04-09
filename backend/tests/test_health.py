"""Smoke tests for the backend project setup."""


def test_health_endpoint(test_client):
    """Verify the health endpoint returns a valid health payload."""
    response = test_client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "total_items" in data
    assert "db_size_mb" in data


def test_test_settings_fixture(test_settings):
    """Verify the test_settings fixture provides expected values."""
    assert test_settings.deepseek_api_key == "test-key"
    assert test_settings.reddit_client_id == "test-reddit-id"
    assert test_settings.log_level == "WARNING"
    assert test_settings.retention_days == 1


def test_temp_db_fixture(temp_db):
    """Verify the temp_db fixture returns a path string."""
    assert isinstance(temp_db, str)
    assert "test_acgfeed.db" in temp_db
