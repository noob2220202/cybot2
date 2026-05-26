import time
import aiosqlite

DB_PATH = "cybot2.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS topic_settings (
                chat_id INTEGER NOT NULL,
                thread_id INTEGER NOT NULL DEFAULT 0,
                hours INTEGER NOT NULL,
                PRIMARY KEY (chat_id, thread_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                thread_id INTEGER NOT NULL DEFAULT 0,
                message_id INTEGER NOT NULL,
                sent_at REAL NOT NULL
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_message_log
            ON message_log (chat_id, thread_id, sent_at)
        """)
        await db.commit()


async def set_topic_hours(chat_id: int, thread_id: int, hours: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO topic_settings (chat_id, thread_id, hours)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, thread_id) DO UPDATE SET hours = excluded.hours
        """, (chat_id, thread_id, hours))
        await db.commit()


async def delete_topic_setting(chat_id: int, thread_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM topic_settings WHERE chat_id = ? AND thread_id = ?",
            (chat_id, thread_id)
        )
        await db.commit()


async def get_topic_hours(chat_id: int, thread_id: int) -> int | None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT hours FROM topic_settings WHERE chat_id = ? AND thread_id = ?",
            (chat_id, thread_id)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def get_all_topic_settings() -> list[tuple[int, int, int]]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT chat_id, thread_id, hours FROM topic_settings") as cursor:
            return await cursor.fetchall()


async def log_message(chat_id: int, thread_id: int, message_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO message_log (chat_id, thread_id, message_id, sent_at) VALUES (?, ?, ?, ?)",
            (chat_id, thread_id, message_id, time.time())
        )
        await db.commit()


async def get_expired_messages(chat_id: int, thread_id: int, hours: int) -> list[int]:
    cutoff = time.time() - hours * 3600
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message_id FROM message_log WHERE chat_id = ? AND thread_id = ? AND sent_at < ?",
            (chat_id, thread_id, cutoff)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


async def delete_logged_messages(chat_id: int, thread_id: int, message_ids: list[int]):
    if not message_ids:
        return
    placeholders = ",".join("?" * len(message_ids))
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"DELETE FROM message_log WHERE chat_id = ? AND thread_id = ? AND message_id IN ({placeholders})",
            (chat_id, thread_id, *message_ids)
        )
        await db.commit()


async def get_all_logged_messages(chat_id: int, thread_id: int) -> list[int]:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT message_id FROM message_log WHERE chat_id = ? AND thread_id = ?",
            (chat_id, thread_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [r[0] for r in rows]


async def delete_all_logged_messages(chat_id: int, thread_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM message_log WHERE chat_id = ? AND thread_id = ?",
            (chat_id, thread_id)
        )
        await db.commit()
