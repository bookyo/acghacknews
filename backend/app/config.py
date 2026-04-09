from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(env_file=".env")

    deepseek_api_key: str
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "acgfeed/1.0"
    database_path: str = "./data/acgfeed.db"
    admin_api_key: str = ""
    frontend_url: str = "http://localhost:3000"
    log_level: str = "INFO"
    retention_days: int = 7
    fetch_interval_minutes: int = 30
