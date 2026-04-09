from fastapi import APIRouter, HTTPException, Request

from app.config import Settings

router = APIRouter(prefix="/api/admin")


def get_settings() -> Settings:
    """Return the Settings instance stored on app.state."""
    raise NotImplementedError("Dependency override required")


@router.post("/trigger-fetch")
async def trigger_fetch(request: Request):
    """Trigger a manual fetch of all feed sources.

    Requires a valid X-Admin-Key header matching the configured admin_api_key.
    """
    admin_key = request.headers.get("X-Admin-Key")
    settings = get_settings()
    if not admin_key or admin_key != settings.admin_api_key:
        raise HTTPException(status_code=401, detail="Unauthorized")
    # The actual fetch orchestration is wired separately.
    # This endpoint signals that a fetch should begin.
    return {"status": "fetch_triggered"}
