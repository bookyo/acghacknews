from fastapi import APIRouter, Depends, HTTPException, Query

from app.models import FeedItem, FeedResponse, SourceEnum
from app.repository import FeedRepository
from app.config import Settings

router = APIRouter(prefix="/api")


def get_repo() -> FeedRepository:
    """Return the FeedRepository instance stored on app.state."""
    raise NotImplementedError("Dependency override required")


def get_settings() -> Settings:
    """Return the Settings instance stored on app.state."""
    raise NotImplementedError("Dependency override required")


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    sort: str = Query("hot", pattern=r"^(hot|new)$"),
    sources: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=50),
):
    """Return a paginated, sorted list of feed items."""
    source_list = sources.split(",") if sources else None
    if source_list:
        valid = [s.value for s in SourceEnum]
        source_list = [s for s in source_list if s in valid]
    repo = get_repo()
    return await repo.get_feed(
        sources=source_list, sort=sort, page=page, per_page=per_page
    )


@router.get("/feed/{item_id}", response_model=FeedItem)
async def get_feed_item(item_id: str):
    """Return a single feed item by its ID."""
    repo = get_repo()
    item = await repo.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feed item not found")
    return item
