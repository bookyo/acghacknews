# Task 003: Heat Score Calculation Impl

**depends-on**: task-003-heat-score-test

## Description

Implement the heat score calculation function that makes all tests from task-003-heat-score-test pass. The function is a pure calculation combining source engagement with recency decay.

## Execution Context

**Task Number**: 003 of 009
**Phase**: Core Features
**Prerequisites**: Heat score tests exist and fail (task-003-test)

## BDD Scenario

Same scenarios as task-003-test — implementation makes them pass.

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `backend/app/scoring.py`

## Steps

### Step 1: Implement calculate_heat_score
- Create `app/scoring.py`
- Function signature: `calculate_heat_score(engagement: float, fetched_at: datetime, source: str, now: datetime | None = None) -> float`
- Formula: `score = (engagement ^ 0.7) * (1 / (1 + hours_since_fetch / 24))`
- RSS (source == "anime_news") or engagement <= 0: recency-only `1.0 * (1 / (1 + hours_since_fetch / 12))`
- `now` parameter defaults to `datetime.now(timezone.utc)` but can be overridden for testing
- Return rounded to 2 decimal places

### Step 2: Verify tests pass (Green)
- Run `pytest tests/test_heat_score.py -v` — all tests should now PASS

### Step 3: Run full test suite
- Ensure no regressions

## Verification Commands

```bash
cd backend
pytest tests/test_heat_score.py -v  # All should PASS
pytest -v  # Full suite passes
```

## Success Criteria

- All 8 heat score tests pass
- Pure function with no side effects
- `now` parameter supports testing with controlled time
