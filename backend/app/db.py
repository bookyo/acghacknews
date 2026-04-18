import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

import aiosqlite


def _connect(db_path: str) -> aiosqlite.Connection:
    """Open an aiosqlite connection, handling shared-cache in-memory URIs."""
    if db_path.startswith("file:"):
        return aiosqlite.connect(db_path, uri=True)
    return aiosqlite.connect(db_path)


async def init_db(db_path: str) -> None:
    """Create database tables and indexes if they do not already exist."""
    if not db_path.startswith(("file:", ":memory:")):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with _connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL")

        await db.execute("""
            CREATE TABLE IF NOT EXISTS feed_items (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_url TEXT NOT NULL UNIQUE,
                original_title TEXT NOT NULL,
                translated_title TEXT NOT NULL,
                original_body TEXT NOT NULL DEFAULT '',
                translated_body TEXT NOT NULL DEFAULT '',
                heat_score REAL NOT NULL DEFAULT 0.0,
                source_metadata TEXT NOT NULL DEFAULT '{}',
                language TEXT NOT NULL DEFAULT 'zh-CN',
                fetched_at TEXT NOT NULL,
                translated_at TEXT
            )
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_feed_items_heat_score
            ON feed_items (heat_score DESC)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_feed_items_fetched_at
            ON feed_items (fetched_at DESC)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_feed_items_source
            ON feed_items (source)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_feed_items_source_url
            ON feed_items (source_url)
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        await db.commit()


@asynccontextmanager
async def get_connection(db_path: str) -> AsyncGenerator[aiosqlite.Connection, None]:
    """Provide an aiosqlite connection with row_factory set to sqlite3.Row and WAL mode enabled."""
    db = await _connect(db_path)
    db.row_factory = sqlite3.Row
    await db.execute("PRAGMA journal_mode=WAL")
    try:
        yield db
    finally:
        await db.close()
