import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a professional translator specializing in ACG (Anime, Comic, Games) content. Translate the following text to simplified Chinese (zh-CN).

Rules:
1. Use established Chinese names for anime/manga titles:
   - "Jujutsu Kaisen" → "咒术回战"
   - "One Piece" → "海贼王"
   - "Oshi no Ko" → "我推的孩子"
   - "Demon Slayer" → "鬼灭之刃"
   - "Attack on Titan" → "进击的巨人"
   - "My Hero Academia" → "我的英雄学院"
2. Keep character names in accepted Chinese forms.
3. For terms without established translations, provide transliteration and keep original in parentheses: "中文 (Original Term)"
4. Preserve season numbers, chapter numbers, and other numeric references.
5. Maintain the tone and style of the original.
"""

BATCH_SYSTEM_PROMPT = SYSTEM_PROMPT + """
6. You will receive multiple items numbered 1-N. Translate ALL items.
7. Respond with a JSON object: {"translations": [{"id": "...", "title": "...", "body": "..."}, ...]}
"""

SINGLE_PROMPT = SYSTEM_PROMPT + """
6. Respond with a JSON object: {"title": "...", "body": "..."}
"""


class TranslationService:
    def __init__(self, api_key: str, batch_size: int = 10):
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        self.batch_size = batch_size

    async def translate_items(self, items: list[dict]) -> list[dict]:
        """Translate a list of items. Returns items with translated fields populated."""
        results = []
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]
            translated = await self._translate_batch(batch)
            results.extend(translated)
        return results

    async def _translate_batch(self, batch: list[dict]) -> list[dict]:
        """Translate a batch with retry logic."""
        for attempt in range(3):
            try:
                return await self._call_batch_api(batch)
            except Exception as e:
                if attempt == 2:
                    logger.error(f"Translation failed after 3 attempts: {e}")
                    return self._mark_pending(batch)
                backoff = [1, 3, 5][attempt]
                logger.warning(
                    f"Translation attempt {attempt+1} failed, retrying in {backoff}s: {e}"
                )
                await asyncio.sleep(backoff)
        return self._mark_pending(batch)

    async def _call_batch_api(self, batch: list[dict]) -> list[dict]:
        """Single batch API call."""
        user_content = self._build_batch_prompt(batch)
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": BATCH_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        translations = parsed.get("translations", [])

        # Map translations back to items by index
        results = []
        for idx, item in enumerate(batch):
            if idx < len(translations):
                t = translations[idx]
                item["translated_title"] = t.get("title", item["original_title"])
                item["translated_body"] = t.get("body", item.get("original_body", ""))
            else:
                item["translated_title"] = item["original_title"]
                item["translated_body"] = item.get("original_body", "")
            item["translated_at"] = datetime.now(timezone.utc).isoformat()
            results.append(item)
        return results

    def _build_batch_prompt(self, batch: list[dict]) -> str:
        """Build multi-item prompt."""
        lines = []
        for i, item in enumerate(batch, 1):
            lines.append(f"Item {i} (id: {item.get('id', i)}):")
            lines.append(f"Title: {item['original_title']}")
            body = item.get("original_body", "")
            if body:
                lines.append(f"Body: {body}")
            else:
                lines.append("Body: (empty)")
            lines.append("")
        return "\n".join(lines)

    async def _translate_single(self, item: dict) -> dict:
        """Fallback: translate single item."""
        user_content = (
            f"Title: {item['original_title']}\nBody: {item.get('original_body', '')}"
        )
        response = self.client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": SINGLE_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.3,
            max_tokens=2048,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        parsed = json.loads(content)
        item["translated_title"] = parsed.get("title", item["original_title"])
        item["translated_body"] = parsed.get("body", item.get("original_body", ""))
        item["translated_at"] = datetime.now(timezone.utc).isoformat()
        return item

    def _mark_pending(self, batch: list[dict]) -> list[dict]:
        """Mark items as translation pending."""
        for item in batch:
            item["translated_title"] = f"[TRANSLATION_PENDING] {item['original_title']}"
            item["translated_body"] = item.get("original_body", "")
            item["translated_at"] = None
        return batch
