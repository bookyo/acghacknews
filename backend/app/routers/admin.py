import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from app.config import Settings
from app.models import FeedItem, FeedItemCreate, SourceEnum
from app.repository import FeedRepository

router = APIRouter(prefix="/api/admin")


def get_settings() -> Settings:
    """Return the Settings instance stored on app.state."""
    raise NotImplementedError("Dependency override required")


def get_repo() -> FeedRepository:
    """Return the FeedRepository instance stored on app.state."""
    raise NotImplementedError("Dependency override required")


def _check_admin(request: Request, settings: Settings) -> None:
    admin_key = request.headers.get("X-Admin-Key")
    if not admin_key or admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/trigger-fetch")
async def trigger_fetch(request: Request):
    """Trigger a manual fetch of all feed sources."""
    _check_admin(request, get_settings())
    return {"status": "fetch_triggered"}


@router.post("/items")
async def create_items(request: Request, body: dict):
    """Manually insert feed items.

    Request body:
        items: list of FeedItemCreate objects

    Fields source, source_url, original_title, translated_title are required.
    id and fetched_at are auto-generated. source_url is used for dedup.
    """
    _check_admin(request, get_settings())

    raw_items = body.get("items", [])
    if not raw_items or not isinstance(raw_items, list):
        raise HTTPException(status_code=400, detail="items must be a non-empty list")

    now = datetime.now(timezone.utc)
    feed_items: list[FeedItem] = []
    for raw in raw_items:
        try:
            create = FeedItemCreate(**raw)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid item: {e}")

        feed_items.append(FeedItem(
            id=uuid.uuid4().hex,
            source=create.source,
            source_url=create.source_url,
            original_title=create.original_title,
            translated_title=create.translated_title,
            original_body=create.original_body,
            translated_body=create.translated_body,
            heat_score=create.heat_score,
            source_metadata=create.source_metadata,
            language=create.language,
            fetched_at=now,
            translated_at=now,
        ))

    repo = get_repo()
    inserted = await repo.insert_items(feed_items)
    return {"status": "ok", "inserted": inserted, "total": len(feed_items)}
