# Task 005: Translation Service Test

**depends-on**: task-001

## Description

Write failing tests for the DeepSeek V3 translation service that handles batch translation of feed items from English/Japanese to zh-CN with ACG terminology awareness.

## Execution Context

**Task Number**: 005 of 009
**Phase**: Core Features
**Prerequisites**: Backend project structure exists (task-001)

## BDD Scenario

```gherkin
Scenario: Translate title and body to zh-CN (happy path)
  Given the DeepSeek API is available
  And there are 15 new items to translate
  When the translation pipeline processes the items
  Then items are grouped into batches of up to 10
  And each batch is sent as a single API call to DeepSeek V3
  And the system prompt instructs ACG-aware translation to zh-CN
  And the response is parsed as JSON with "title" and "body" fields
  And each item's translated_title and translated_body are populated
  And the translated_at timestamp is set to the current time

Scenario: Translation API rate limited
  Given the DeepSeek API returns HTTP 429 on the first attempt
  When the translation pipeline processes a batch
  Then the system waits 60 seconds and retries once
  And if the retry succeeds, translations are processed normally
  And if all retries are exhausted, the batch is marked as translation failed

Scenario: ACG-specific terminology (anime titles)
  Given an item with original_title "Jujutsu Kaisen Season 3 Announced"
  And an item with original_title "One Piece Chapter 1120 Discussion"
  When the translation pipeline processes these items
  Then "Jujutsu Kaisen" is translated to "咒术回战"
  And "One Piece" is translated to "海贼王"
  And the system prompt includes a reminder to use established Chinese transliterations

Scenario: Translation API completely down
  Given the DeepSeek API returns HTTP 500 or is unreachable
  When the translation pipeline attempts to process the items
  Then the system retries 3 times with exponential backoff (1s, 3s, 5s)
  And after 3 failures, items are stored with original text
  And translated_title is prefixed with "[TRANSLATION_PENDING] "
  And translated_at is set to null

Scenario: Translation returns malformed JSON
  Given the DeepSeek API returns a response that cannot be parsed as JSON
  When the translation pipeline processes the batch
  Then the system retries once with a stricter prompt
  And if the retry fails, falls back to translating items individually

Scenario: Item with empty or very short body text
  Given an item with original_title "New anime trailer released"
  And original_body is empty or contains fewer than 20 characters
  When the translation pipeline processes this item
  Then the title is translated normally
  And the body is set to the original text
  And no error is raised

Scenario: Batch translation maintains item ordering
  Given a batch of 10 items in a specific order
  When the translation pipeline sends them to DeepSeek V3
  Then each translation is correctly mapped back to its original item by ID
  And no items are lost or reordered
```

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `backend/tests/test_translation.py`

## Steps

### Step 1: Create test file
- Create `tests/test_translation.py`
- Mock the OpenAI/DeepSeek client — no real API calls in tests

### Step 2: Write failing tests
- `test_batch_translation_happy_path`: 15 items, verify 2 batches (10+5), verify translated_title/body populated, verify translated_at set
- `test_batch_translation_ordering`: 10 items with IDs, verify correct mapping back
- `test_translation_rate_limited_429`: Mock 429 then success, verify retry
- `test_translation_api_down`: Mock 500 x3, verify [TRANSLATION_PENDING] prefix, translated_at is None
- `test_translation_malformed_json`: Mock non-JSON response, verify retry + fallback to individual
- `test_empty_body_translation`: Item with empty body, verify title translated, body kept as-is
- `test_acg_terminology_in_prompt`: Verify system prompt contains "咒术回战" example and ACG translation rules

### Step 3: Verify tests fail (Red)

## Verification Commands

```bash
cd backend
pytest tests/test_translation.py -v  # All should FAIL
```

## Success Criteria

- All 7 translation tests exist and fail
- No real DeepSeek API calls (all mocked)
- Tests cover happy path, errors, edge cases, ACG terminology prompt
