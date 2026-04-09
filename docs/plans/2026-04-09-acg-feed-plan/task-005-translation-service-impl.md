# Task 005: Translation Service Impl

**depends-on**: task-005-translation-service-test

## Description

Implement the DeepSeek V3 translation service with batch processing, ACG-aware system prompt, retry logic, and graceful fallback for failed translations.

## Execution Context

**Task Number**: 005 of 009
**Phase**: Core Features
**Prerequisites**: Translation tests exist and fail (task-005-test)

## BDD Scenario

Same scenarios as task-005-test — implementation makes them pass.

**Spec Source**: `../2026-04-09-acg-feed-design/bdd-specs.md`

## Files to Modify/Create

- Create: `backend/app/translation.py`

## Steps

### Step 1: Implement TranslationService
- Create `app/translation.py`
- Class `TranslationService`:
  - Constructor: `api_key: str`, `batch_size: int = 10`
  - Uses `openai.OpenAI` client with `base_url="https://api.deepseek.com"`
  - `async def translate_items(items: list[dict]) -> list[dict]`: Main entry point
    - Groups items into batches of `batch_size`
    - For each batch, call `_translate_batch()`
    - Returns items with translated_title, translated_body, translated_at populated

### Step 2: Implement batch translation
- `_translate_batch(batch: list[dict]) -> list[dict]`:
  - Build multi-item prompt with numbered items
  - System prompt includes ACG terminology rules:
    - Use established Chinese names (Jujutsu Kaisen → 咒术回战, One Piece → 海贼王)
    - Keep original in parentheses for unknown terms
    - Preserve season/chapter numbers
  - Response format: JSON with items array
  - Retry up to 3 times with backoff [1, 3, 5] seconds
  - On permanent failure: mark with [TRANSLATION_PENDING] prefix, set translated_at to None

### Step 3: Implement fallback logic
- If batch translation fails (malformed JSON), retry with stricter prompt
- If still fails, fall back to individual item translation
- Handle empty bodies: skip translation, keep original

### Step 4: Verify tests pass (Green)
- Run `pytest tests/test_translation.py -v`

## Verification Commands

```bash
cd backend
pytest tests/test_translation.py -v  # All should PASS
pytest -v  # Full suite passes
```

## Success Criteria

- All translation tests pass
- Batch processing groups items correctly
- ACG-aware system prompt includes terminology examples
- Retry logic with exponential backoff
- Graceful fallback: batch → single item → [TRANSLATION_PENDING]
