from enum import Enum
from datetime import datetime

from pydantic import BaseModel


class SourceEnum(str, Enum):
    reddit = "reddit"
    anilist = "anilist"
    steam = "steam"
    anime_news = "anime_news"


class FeedItemBase(BaseModel):
    source: SourceEnum
    source_url: str
    original_title: str
    translated_title: str
    original_body: str
    translated_body: str
    heat_score: float = 0.0
    source_metadata: dict = {}
    language: str = "zh-CN"


class FeedItem(FeedItemBase):
    id: str
    fetched_at: datetime
    translated_at: datetime | None = None


class FeedResponse(BaseModel):
    items: list[FeedItem]
    total: int
    page: int
    per_page: int
    has_next: bool


class HealthResponse(BaseModel):
    status: str
    last_fetch_at: datetime | None = None
    total_items: int = 0
    db_size_mb: float = 0.0
    last_fetch_status: str | None = None


class FeedItemCreate(BaseModel):
    """Schema for manually creating a feed item."""
    source: SourceEnum
    source_url: str
    original_title: str
    translated_title: str
    original_body: str = ""
    translated_body: str = ""
    heat_score: float = 0.0
    source_metadata: dict = {}
    language: str = "zh-CN"


class SourceConfig(BaseModel):
    name: str
    label: str
    enabled: bool = True
