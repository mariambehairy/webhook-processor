import asyncio
import logging
import os

import asyncpg

logger = logging.getLogger("webhook.db")

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://webhook:webhook@localhost:5432/webhooks"
)

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS alerts (
    id           SERIAL PRIMARY KEY,
    event_id     TEXT UNIQUE NOT NULL,
    source       TEXT NOT NULL,
    message      TEXT NOT NULL,
    timestamp    TIMESTAMPTZ NOT NULL,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""


async def create_pool(retries: int = 15, delay: float = 2.0) -> asyncpg.Pool:
    """Connect to Postgres (retrying while it starts up) and ensure the table exists."""
    for attempt in range(1, retries + 1):
        try:
            pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
            async with pool.acquire() as conn:
                await conn.execute(CREATE_TABLE)
            logger.info("Connected to database")
            return pool
        except (OSError, asyncpg.PostgresError) as exc:
            logger.warning("DB not ready (attempt %d/%d): %s", attempt, retries, exc)
            await asyncio.sleep(delay)
    raise RuntimeError("Could not connect to the database")


async def get_alert(pool: asyncpg.Pool, event_id: str):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT event_id, source, message, timestamp, processed_at "
            "FROM alerts WHERE event_id = $1",
            event_id,
        )


async def insert_alert(pool: asyncpg.Pool, alert):
    """Insert an alert. Returns the row, or None if event_id already exists."""
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """
            INSERT INTO alerts (event_id, source, message, timestamp)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (event_id) DO NOTHING
            RETURNING event_id, source, message, timestamp, processed_at
            """,
            alert.event_id,
            alert.source,
            alert.message,
            alert.timestamp,
        )


async def list_alerts(pool: asyncpg.Pool):
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT event_id, source, message, timestamp, processed_at "
            "FROM alerts ORDER BY id"
        )
