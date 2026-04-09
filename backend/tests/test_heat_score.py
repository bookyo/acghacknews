"""BDD tests for heat score calculation.

Covers 8 scenarios:
  1. Reddit upvotes
  2. AniList trending
  3. Steam reviews
  4. RSS recency-only
  5. Old item decay
  6. Fresh beats old
  7. Zero engagement
  8. Recalculate at query time
"""

from datetime import datetime, timezone, timedelta

from app.scoring import calculate_heat_score


# Fixed epoch for deterministic tests
_EPOCH = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _hours_ago(hours: float) -> datetime:
    """Return a datetime that is *hours* before _EPOCH."""
    return _EPOCH - timedelta(hours=hours)


# ---------------------------------------------------------------------------
# Scenario 1: Reddit post with 1234 upvotes, fetched 2 hours ago
# ---------------------------------------------------------------------------
def test_reddit_upvotes():
    fetched_at = _hours_ago(2)
    score = calculate_heat_score(
        engagement=1234,
        fetched_at=fetched_at,
        source="reddit",
        now=_EPOCH,
    )
    # 1234^0.7 ≈ 145.88, recency=1/(1+2/24) ≈ 0.9231
    # product ≈ 134.64
    assert abs(score - 134.64) < 1.0, f"Expected ~134.64, got {score}"


# ---------------------------------------------------------------------------
# Scenario 2: AniList trending entry, engagement=85, fetched 6 hours ago
# ---------------------------------------------------------------------------
def test_anilist_trending():
    fetched_at = _hours_ago(6)
    score = calculate_heat_score(
        engagement=85,
        fetched_at=fetched_at,
        source="anilist",
        now=_EPOCH,
    )
    # 85^0.7 ≈ 22.42, recency=1/(1+6/24)=0.8
    # product ≈ 17.93
    assert abs(score - 17.93) < 1.0, f"Expected ~17.93, got {score}"


# ---------------------------------------------------------------------------
# Scenario 3: Steam game with 50000 reviews, fetched 1 hour ago
# ---------------------------------------------------------------------------
def test_steam_reviews():
    fetched_at = _hours_ago(1)
    score = calculate_heat_score(
        engagement=50000,
        fetched_at=fetched_at,
        source="steam",
        now=_EPOCH,
    )
    # 50000^0.7 ≈ 1946.70, recency=1/(1+1/24) ≈ 0.96
    # product ≈ 1868.75
    assert abs(score - 1868.75) < 5.0, f"Expected ~1868.75, got {score}"


# ---------------------------------------------------------------------------
# Scenario 4: RSS feed (anime_news) with recency-only scoring
# ---------------------------------------------------------------------------
def test_rss_recency_only():
    fetched_at = _hours_ago(3)
    score = calculate_heat_score(
        engagement=0,
        fetched_at=fetched_at,
        source="anime_news",
        now=_EPOCH,
    )
    # anime_news path: 1/(1+3/12) = 1/1.25 = 0.8
    assert abs(score - 0.8) < 0.01, f"Expected 0.8, got {score}"


# ---------------------------------------------------------------------------
# Scenario 5: Old item (48 hours) with engagement=500 should be heavily decayed
# ---------------------------------------------------------------------------
def test_old_item_decay():
    fetched_at = _hours_ago(48)
    score = calculate_heat_score(
        engagement=500,
        fetched_at=fetched_at,
        source="reddit",
        now=_EPOCH,
    )
    # 500^0.7 ≈ 77.48, recency=1/(1+48/24)=1/3=0.3333
    # product ≈ 25.83
    assert abs(score - 25.83) < 1.0, f"Expected ~25.83, got {score}"


# ---------------------------------------------------------------------------
# Scenario 6: Fresh item (1hr, engagement 500) should score higher than
#             old item (48hr, engagement 500) — same engagement, recency wins
# ---------------------------------------------------------------------------
def test_fresh_beats_old():
    fresh_score = calculate_heat_score(
        engagement=500,
        fetched_at=_hours_ago(1),
        source="reddit",
        now=_EPOCH,
    )
    old_score = calculate_heat_score(
        engagement=500,
        fetched_at=_hours_ago(48),
        source="reddit",
        now=_EPOCH,
    )
    assert fresh_score > old_score, (
        f"Fresh ({fresh_score}) should beat old ({old_score})"
    )


# ---------------------------------------------------------------------------
# Scenario 7: Zero engagement on a non-anime_news source returns 0.0
# ---------------------------------------------------------------------------
def test_zero_engagement():
    fetched_at = _hours_ago(1)
    score = calculate_heat_score(
        engagement=0,
        fetched_at=fetched_at,
        source="reddit",
        now=_EPOCH,
    )
    assert score == 0.0, f"Expected 0.0, got {score}"


# ---------------------------------------------------------------------------
# Scenario 8: Same item scored at different query times — score decreases
#             as time passes (recalculation at query time).
# ---------------------------------------------------------------------------
def test_recalculate_at_query_time():
    fetched_at = _hours_ago(0)  # fetched "now"

    score_now = calculate_heat_score(
        engagement=1000,
        fetched_at=fetched_at,
        source="reddit",
        now=_EPOCH,
    )
    score_12h = calculate_heat_score(
        engagement=1000,
        fetched_at=fetched_at,
        source="reddit",
        now=_EPOCH + timedelta(hours=12),
    )
    score_48h = calculate_heat_score(
        engagement=1000,
        fetched_at=fetched_at,
        source="reddit",
        now=_EPOCH + timedelta(hours=48),
    )

    assert score_now > score_12h > score_48h, (
        f"Scores should monotonically decrease: {score_now} > {score_12h} > {score_48h}"
    )
