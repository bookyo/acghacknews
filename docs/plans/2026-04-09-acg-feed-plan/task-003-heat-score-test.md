# Task 003: Heat Score Calculation Test

**depends-on**: task-001

## Description

Write failing tests for the heat score calculation algorithm. The heat score formula combines source engagement with recency decay to rank feed items.

## Execution Context

**Task Number**: 003 of 009
**Phase**: Core Features
**Prerequisites**: Backend project structure exists (task-001)

## BDD Scenario

```gherkin
Scenario: Reddit post with upvotes
  Given a Reddit post with 1234 upvotes fetched 2 hours ago
  When the heat score is calculated
  Then engagement = 1234
  And engagement_factor = 1234 ^ 0.7 = approximately 201.7
  And recency_factor = 1 / (1 + 2/24) = approximately 0.923
  And heat_score = 201.7 * 0.923 = approximately 186.2

Scenario: AniList entry with trending score
  Given an AniList anime entry with trending score 85 fetched 6 hours ago
  When the heat score is calculated
  Then engagement = 85
  And engagement_factor = 85 ^ 0.7 = approximately 30.1
  And recency_factor = 1 / (1 + 6/24) = approximately 0.8
  And heat_score = 30.1 * 0.8 = approximately 24.1

Scenario: Steam game with review count
  Given a Steam game with 50000 total reviews fetched 1 hour ago
  When the heat score is calculated
  Then engagement = 50000
  And engagement_factor = 50000 ^ 0.7 = approximately 2759.5
  And recency_factor = 1 / (1 + 1/24) = approximately 0.96
  And heat_score = 2759.5 * 0.96 = approximately 2649.1

Scenario: RSS feed item with no engagement data (recency-only scoring)
  Given an RSS item from Anime! Anime! with no engagement data fetched 3 hours ago
  When the heat score is calculated
  Then engagement is not used
  And recency_factor = 1 / (1 + 3/12) = 1 / 1.25 = 0.8
  And heat_score = 0.8

Scenario: Item fetched 48 hours ago has very low heat score
  Given a Reddit post with 500 upvotes fetched 48 hours ago
  When the heat score is calculated
  Then engagement_factor = 500 ^ 0.7 = approximately 102.4
  And recency_factor = 1 / (1 + 48/24) = 1/3 = approximately 0.333
  And heat_score = 102.4 * 0.333 = approximately 34.1

Scenario: Fresh high-engagement item ranks above old high-engagement item
  Given a Reddit post with 500 upvotes fetched 1 hour ago (heat ~474)
  And a Reddit post with 5000 upvotes fetched 48 hours ago (heat ~189)
  When items are sorted by heat_score descending
  Then the fresh 500-upvote post appears before the old 5000-upvote post

Scenario: Item with zero engagement
  Given a Reddit post with 0 upvotes fetched 1 hour ago
  When the heat score is calculated
  Then engagement = 0
  And engagement_factor = 0 ^ 0.7 = 0
  And heat_score = 0

Scenario: Heat score is recalculated at query time
  Given a Reddit post with 1000 upvotes was inserted 12 hours ago
  And the stored heat_score was calculated at insert time
  When a user requests the feed sorted by heat
  Then the system recalculates the heat_score using current time
  And the recency_factor reflects the actual age of the item
  And items become less hot as they age, even without re-fetching
```

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `backend/tests/test_heat_score.py`

## Steps

### Step 1: Create test file
- Create `tests/test_heat_score.py`
- Import `calculate_heat_score` function (does not exist yet — Red phase)
- Use test doubles: no database or network calls needed — heat score is a pure function

### Step 2: Write failing tests for each scenario
- `test_reddit_upvotes`: Verify score for Reddit post with 1234 upvotes, 2 hours old, is ~186.2 (within 1.0 tolerance)
- `test_anilist_trending`: Verify score for AniList trending 85, 6 hours old, is ~24.1
- `test_steam_reviews`: Verify score for Steam 50000 reviews, 1 hour old, is ~2649.1
- `test_rss_recency_only`: Verify score for RSS (no engagement), 3 hours old, is 0.8
- `test_old_item_decay`: Verify score for 500 upvotes, 48 hours old, is ~34.1
- `test_fresh_beats_old`: Verify 500 upvotes/1hr ranks higher than 5000 upvotes/48hr
- `test_zero_engagement`: Verify score for 0 upvotes is 0
- `test_recalculate_at_query_time`: Verify score changes when time advances (mock datetime)
- Use `freezegun` or manual datetime mocking to control time in tests

### Step 3: Verify tests fail (Red)
- Run pytest — all tests should FAIL (import error or assertion failure)

## Verification Commands

```bash
cd backend
pytest tests/test_heat_score.py -v  # All should FAIL
```

## Success Criteria

- All 8 test functions exist and fail (Red phase)
- Tests use no external dependencies (pure function testing)
- Tests cover all heat score BDD scenarios
