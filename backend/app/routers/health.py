from datetime import datetime, timezone

from fastapi import APIRouter

from app.models import HealthResponse, SourceConfig
from app.repository import FeedRepository
from app.config import Settings

router = APIRouter(prefix="/api")

SOURCES = [
    SourceConfig(name="reddit", label="Reddit", enabled=True),
    SourceConfig(name="anilist", label="AniList", enabled=True),
    SourceConfig(name="steam", label="Steam", enabled=True),
    SourceConfig(name="anime_news", label="Anime News (JP)", enabled=True),
]


def get_repo() -> FeedRepository:
    """Return the FeedRepository instance stored on app.state."""
    raise NotImplementedError("Dependency override required")


def get_settings() -> Settings:
    """Return the Settings instance stored on app.state."""
    raise NotImplementedError("Dependency override required")


@router.get("/health", response_model=HealthResponse)
async def health():
    """Return application health status including last fetch info."""
    repo = get_repo()
    last_fetch_at_str = await repo.get_metadata("last_fetch_at")
    last_fetch_status = await repo.get_metadata("last_fetch_status")
    total_items = await repo.count_items()
    db_size = await repo.get_db_size_mb()

    # Determine status
    status = "healthy"
    if last_fetch_at_str:
        try:
            last_dt = datetime.fromisoformat(last_fetch_at_str)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            age_hours = (datetime.now(timezone.utc) - last_dt).total_seconds() / 3600
            if age_hours > 2 or last_fetch_status == "all_sources_failed":
                status = "degraded"
        except Exception:
            status = "degraded"
    else:
        status = "healthy"  # Fresh start, no fetch yet

    return HealthResponse(
        status=status,
        last_fetch_at=last_fetch_at_str,
        total_items=total_items,
        db_size_mb=db_size,
        last_fetch_status=last_fetch_status,
    )


@router.get("/sources", response_model=list[SourceConfig])
async def sources():
    """Return the list of configured feed sources."""
    return SOURCES
