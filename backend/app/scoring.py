import math
from datetime import datetime, timezone


def calculate_heat_score(
    engagement: float,
    fetched_at: datetime,
    source: str,
    now: datetime | None = None,
) -> float:
    """Calculate heat score for a feed item.

    Formula: score = (engagement ^ 0.7) * (1 / (1 + hours_since_fetch / 24))
    RSS feeds (no engagement): score = 1.0 * (1 / (1 + hours_since_fetch / 12))
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # Ensure fetched_at is timezone-aware
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)

    hours_since = max(0, (now - fetched_at).total_seconds() / 3600)

    if source == "anime_news" or engagement <= 0:
        if source == "anime_news":
            recency_factor = 1.0 / (1.0 + hours_since / 12.0)
            return round(recency_factor, 2)
        return 0.0

    engagement_factor = math.pow(engagement, 0.7)
    recency_factor = 1.0 / (1.0 + hours_since / 24.0)
    return round(engagement_factor * recency_factor, 2)
