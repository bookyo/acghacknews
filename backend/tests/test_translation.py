"""Tests for TranslationService with mocked OpenAI client."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.translation import BATCH_SYSTEM_PROMPT, SYSTEM_PROMPT, TranslationService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_items(n: int, body_template: str = "Body of item {i}") -> list[dict]:
    """Create *n* fake feed items for translation."""
    return [
        {
            "id": f"item-{i}",
            "original_title": f"Title {i}",
            "original_body": body_template.format(i=i),
        }
        for i in range(n)
    ]


def _mock_api_response(translations: list[dict]) -> MagicMock:
    """Build a mock OpenAI response whose .choices[0].message.content is JSON."""
    payload = {"translations": translations}
    mock_msg = MagicMock()
    mock_msg.content = json.dumps(payload)
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    return mock_resp


def _mock_api_response_single(title: str, body: str) -> MagicMock:
    """Build a mock OpenAI response for the single-item endpoint."""
    payload = {"title": title, "body": body}
    mock_msg = MagicMock()
    mock_msg.content = json.dumps(payload)
    mock_choice = MagicMock()
    mock_choice.message = mock_msg
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    return mock_resp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def translation_service():
    """Return a TranslationService with a mocked OpenAI client."""
    with patch("app.translation.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        MockOpenAI.return_value = mock_client
        svc = TranslationService(api_key="test-key", batch_size=10)
        assert svc.client is mock_client
        yield svc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBatchTranslationHappyPath:
    """15 items, verify 2 batches called, fields populated."""

    @pytest.mark.asyncio
    async def test_batch_translation_happy_path(self, translation_service):
        items = _make_items(15)

        # Track how many times the API is called
        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            user_content = kwargs["messages"][1]["content"]
            # Count how many items are in this batch by counting "Item " occurrences
            batch_n = user_content.count("Item ")
            translations = [
                {"id": f"item-{i}", "title": f"翻译标题 {i}", "body": f"翻译正文 {i}"}
                for i in range(batch_n)
            ]
            return _mock_api_response(translations)

        translation_service.client.chat.completions.create = MagicMock(
            side_effect=fake_create
        )

        results = await translation_service.translate_items(items)

        assert len(results) == 15
        assert call_count == 2  # 10 + 5 = two batches

        for r in results:
            assert r["translated_title"].startswith("翻译标题")
            assert r["translated_body"].startswith("翻译正文")
            assert r["translated_at"] is not None


class TestBatchTranslationOrdering:
    """10 items with IDs, verify correct mapping."""

    @pytest.mark.asyncio
    async def test_batch_translation_ordering(self, translation_service):
        items = _make_items(10)

        def fake_create(**kwargs):
            # Return translations with titles that encode the original title info
            translations = [
                {
                    "id": f"item-{i}",
                    "title": f"Order-{i}",
                    "body": f"Body-{i}",
                }
                for i in range(10)
            ]
            return _mock_api_response(translations)

        translation_service.client.chat.completions.create = MagicMock(
            side_effect=fake_create
        )

        results = await translation_service.translate_items(items)

        assert len(results) == 10
        for i, r in enumerate(results):
            assert r["id"] == f"item-{i}"
            assert r["translated_title"] == f"Order-{i}"
            assert r["translated_body"] == f"Body-{i}"
            assert r["translated_at"] is not None


class TestTranslationRateLimited429:
    """First call raises exception, second succeeds."""

    @pytest.mark.asyncio
    async def test_translation_rate_limited_429(self, translation_service):
        items = _make_items(5)

        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 Rate Limited")
            translations = [
                {"id": f"item-{i}", "title": f"Retry-{i}", "body": f"RBody-{i}"}
                for i in range(5)
            ]
            return _mock_api_response(translations)

        translation_service.client.chat.completions.create = MagicMock(
            side_effect=fake_create
        )

        # Patch asyncio.sleep to avoid real delays
        with patch("app.translation.asyncio.sleep", new_callable=AsyncMock):
            results = await translation_service.translate_items(items)

        assert len(results) == 5
        assert call_count == 2  # first failed, second succeeded
        for i, r in enumerate(results):
            assert r["translated_title"] == f"Retry-{i}"
            assert r["translated_body"] == f"RBody-{i}"


class TestTranslationApiDown:
    """All calls failing 3x, verify [TRANSLATION_PENDING] prefix."""

    @pytest.mark.asyncio
    async def test_translation_api_down(self, translation_service):
        items = _make_items(5)

        def fake_create(**kwargs):
            raise Exception("503 Service Unavailable")

        translation_service.client.chat.completions.create = MagicMock(
            side_effect=fake_create
        )

        with patch("app.translation.asyncio.sleep", new_callable=AsyncMock):
            results = await translation_service.translate_items(items)

        assert len(results) == 5
        for r in results:
            assert r["translated_title"].startswith("[TRANSLATION_PENDING]")
            assert r["translated_at"] is None


class TestTranslationMalformedJson:
    """Mock non-JSON response, verify retry."""

    @pytest.mark.asyncio
    async def test_translation_malformed_json(self, translation_service):
        items = _make_items(3)

        call_count = 0

        def fake_create(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                # Return malformed JSON
                mock_msg = MagicMock()
                mock_msg.content = "this is not valid json {{"
                mock_choice = MagicMock()
                mock_choice.message = mock_msg
                mock_resp = MagicMock()
                mock_resp.choices = [mock_choice]
                return mock_resp
            # Third call returns valid data
            translations = [
                {"id": f"item-{i}", "title": f"Fixed-{i}", "body": f"FBody-{i}"}
                for i in range(3)
            ]
            return _mock_api_response(translations)

        translation_service.client.chat.completions.create = MagicMock(
            side_effect=fake_create
        )

        with patch("app.translation.asyncio.sleep", new_callable=AsyncMock):
            results = await translation_service.translate_items(items)

        assert call_count == 3  # two malformed, one good
        assert len(results) == 3
        for i, r in enumerate(results):
            assert r["translated_title"] == f"Fixed-{i}"


class TestEmptyBodyTranslation:
    """Item with empty body, title translated, body kept empty."""

    @pytest.mark.asyncio
    async def test_empty_body_translation(self, translation_service):
        items = [
            {
                "id": "empty-1",
                "original_title": "One Piece Chapter 1050",
                "original_body": "",
            }
        ]

        def fake_create(**kwargs):
            translations = [
                {
                    "id": "empty-1",
                    "title": "海贼王 第1050话",
                    "body": "",
                }
            ]
            return _mock_api_response(translations)

        translation_service.client.chat.completions.create = MagicMock(
            side_effect=fake_create
        )

        results = await translation_service.translate_items(items)

        assert len(results) == 1
        assert results[0]["translated_title"] == "海贼王 第1050话"
        assert results[0]["translated_body"] == ""
        assert results[0]["translated_at"] is not None


class TestACGTerminologyInPrompt:
    """Verify system prompt contains ACG terminology rules."""

    def test_acg_terminology_in_prompt(self):
        # Check that the base SYSTEM_PROMPT contains key ACG terms
        assert "Jujutsu Kaisen" in SYSTEM_PROMPT
        assert "咒术回战" in SYSTEM_PROMPT
        assert "One Piece" in SYSTEM_PROMPT
        assert "海贼王" in SYSTEM_PROMPT
        assert "Oshi no Ko" in SYSTEM_PROMPT
        assert "我推的孩子" in SYSTEM_PROMPT
        assert "Demon Slayer" in SYSTEM_PROMPT
        assert "鬼灭之刃" in SYSTEM_PROMPT
        assert "Attack on Titan" in SYSTEM_PROMPT
        assert "进击的巨人" in SYSTEM_PROMPT
        assert "My Hero Academia" in SYSTEM_PROMPT
        assert "我的英雄学院" in SYSTEM_PROMPT

        # BATCH_SYSTEM_PROMPT should extend SYSTEM_PROMPT
        assert "translate ALL items" in BATCH_SYSTEM_PROMPT.lower() or "Translate ALL items" in BATCH_SYSTEM_PROMPT
        assert "translations" in BATCH_SYSTEM_PROMPT
