import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from app.db import get_connection
from app.models import FeedItem, FeedResponse


def truncate_body(text: str, max_length: int = 500) -> str:
    """Truncate text to max_length characters."""
    if len(text) <= max_length:
        return text
    return text[:max_length]


def _row_to_feed_item(row: Any) -> FeedItem:
    """Convert a sqlite3.Row (or dict-like) to a FeedItem instance."""
    metadata_raw = row["source_metadata"]
    if isinstance(metadata_raw, str):
        metadata = json.loads(metadata_raw)
    else:
        metadata = metadata_raw if metadata_raw else {}

    translated_at_raw = row["translated_at"]
    if isinstance(translated_at_raw, str):
        translated_at = datetime.fromisoformat(translated_at_raw)
    elif isinstance(translated_at_raw, datetime):
        translated_at = translated_at_raw
    else:
        translated_at = None

    fetched_at_raw = row["fetched_at"]
    if isinstance(fetched_at_raw, str):
        fetched_at = datetime.fromisoformat(fetched_at_raw)
    else:
        fetched_at = fetched_at_raw

    return FeedItem(
        id=row["id"],
        source=row["source"],
        source_url=row["source_url"],
        original_title=row["original_title"],
        translated_title=row["translated_title"],
        original_body=row["original_body"],
        translated_body=row["translated_body"],
        heat_score=row["heat_score"],
        source_metadata=metadata,
        language=row["language"],
        fetched_at=fetched_at,
        translated_at=translated_at,
    )


class FeedRepository:
    """Async repository for feed_items and system_metadata tables."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def insert_items(self, items: list[FeedItem]) -> int:
        """Batch INSERT with dedup by source_url (INSERT OR IGNORE). Return count inserted."""
        if not items:
            return 0

        async with get_connection(self.db_path) as db:
            rows = []
            for item in items:
                metadata_json = json.dumps(item.source_metadata, ensure_ascii=False)
                translated_at_val = (
                    item.translated_at.isoformat() if item.translated_at else None
                )
                rows.append((
                    item.id,
                    item.source.value if isinstance(item.source, SourceEnum) else item.source,
                    item.source_url,
                    item.original_title,
                    item.translated_title,
                    item.original_body,
                    item.translated_body,
                    item.heat_score,
                    metadata_json,
                    item.language,
                    item.fetched_at.isoformat(),
                    translated_at_val,
                ))

            cursor = await db.executemany(
                """
                INSERT OR IGNORE INTO feed_items
                    (id, source, source_url, original_title, translated_title,
                     original_body, translated_body, heat_score, source_metadata,
                     language, fetched_at, translated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            await db.commit()
            return cursor.rowcount

    async def get_feed(
        self,
        sources: list[str] | None = None,
        sort: str = "hot",
        page: int = 1,
        per_page: int = 20,
    ) -> FeedResponse:
        """Query feed items with source filters, sorting, and pagination."""
        async with get_connection(self.db_path) as db:
            conditions: list[str] = []
            params: list[Any] = []

            if sources:
                placeholders = ", ".join("?" for _ in sources)
                conditions.append(f"source IN ({placeholders})")
                params.extend(sources)

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            # Count total matching items
            count_sql = f"SELECT COUNT(*) as cnt FROM feed_items {where_clause}"
            cursor = await db.execute(count_sql, params)
            row = await cursor.fetchone()
            total = row["cnt"] if row else 0

            # Determine sort order
            if sort == "new":
                order_clause = "ORDER BY fetched_at DESC"
            else:
                order_clause = "ORDER BY heat_score DESC"

            offset = (page - 1) * per_page
            query_sql = f"""
                SELECT * FROM feed_items
                {where_clause}
                {order_clause}
                LIMIT ? OFFSET ?
            """
            cursor = await db.execute(query_sql, params + [per_page, offset])
            rows = await cursor.fetchall()

            items = [_row_to_feed_item(r) for r in rows]
            has_next = (offset + per_page) < total

            return FeedResponse(
                items=items,
                total=total,
                page=page,
                per_page=per_page,
                has_next=has_next,
            )

    async def get_item(self, item_id: str) -> FeedItem | None:
        """Single item lookup by id."""
        async with get_connection(self.db_path) as db:
            cursor = await db.execute(
                "SELECT * FROM feed_items WHERE id = ?", (item_id,)
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return _row_to_feed_item(row)

    async def count_items(self) -> int:
        """Return the total number of items in feed_items."""
        async with get_connection(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) as cnt FROM feed_items")
            row = await cursor.fetchone()
            return row["cnt"] if row else 0

    async def get_existing_urls(self, urls: list[str]) -> set[str]:
        """Return the subset of urls that already exist in the database."""
        if not urls:
            return set()

        async with get_connection(self.db_path) as db:
            placeholders = ", ".join("?" for _ in urls)
            cursor = await db.execute(
                f"SELECT source_url FROM feed_items WHERE source_url IN ({placeholders})",
                urls,
            )
            rows = await cursor.fetchall()
            return {row["source_url"] for row in rows}

    async def cleanup_old_items(self, retention_days: int) -> int:
        """Delete items older than N days. Return count deleted.

        Catches database errors gracefully and returns 0 on failure.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        cutoff_iso = cutoff.isoformat()

        try:
            async with get_connection(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM feed_items WHERE fetched_at < ?", (cutoff_iso,)
                )
                await db.commit()
                return cursor.rowcount
        except Exception:
            return 0

    async def get_metadata(self, key: str) -> str | None:
        """Retrieve a value from the system_metadata table by key."""
        async with get_connection(self.db_path) as db:
            cursor = await db.execute(
                "SELECT value FROM system_metadata WHERE key = ?", (key,)
            )
            row = await cursor.fetchone()
            return row["value"] if row else None

    async def set_metadata(self, key: str, value: str) -> None:
        """Upsert a key/value pair into the system_metadata table."""
        async with get_connection(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO system_metadata (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (key, value),
            )
            await db.commit()

    async def get_db_size_mb(self) -> float:
        """Return the database file size in megabytes."""
        if not os.path.exists(self.db_path):
            return 0.0
        size_bytes = os.path.getsize(self.db_path)
        return round(size_bytes / (1024 * 1024), 4)


# Imported here to avoid circular imports at module level; SourceEnum is used
# in insert_items for the .value access on enum members.
from app.models import SourceEnum  # noqa: E402
