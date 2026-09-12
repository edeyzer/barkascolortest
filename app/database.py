# app/database.py - Multi-language + history + album
import logging
from config import DB_TYPE, DB_PATH, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

logger = logging.getLogger(__name__)
_pool = None


async def init_db():
    global _pool
    
    if DB_TYPE == "postgresql":
        import asyncpg
        _pool = await asyncpg.create_pool(
            host=DB_HOST, port=DB_PORT, user=DB_USER,
            password=DB_PASSWORD, database=DB_NAME,
            min_size=2, max_size=10
        )
        
        async with _pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS images (
                    code TEXT PRIMARY KEY, 
                    file_id TEXT,
                    dominant_hex TEXT,
                    color_name TEXT,
                    search_count INTEGER DEFAULT 0,
                    album TEXT DEFAULT NULL
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY, 
                    is_super INTEGER DEFAULT 0
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS search_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    code TEXT,
                    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    language TEXT DEFAULT 'uz'
                )
            ''')
            
            for col in ["search_count INTEGER DEFAULT 0", "album TEXT DEFAULT NULL"]:
                try:
                    await conn.execute(f"ALTER TABLE images ADD COLUMN {col}")
                except Exception:
                    pass

            try:
                await conn.execute("ALTER TABLE users ADD COLUMN subscribed INTEGER DEFAULT 1")
            except Exception:
                pass

        logger.info("✅ PostgreSQL bazasi tayyor")
    
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS images (
                code TEXT PRIMARY KEY, 
                file_id TEXT,
                dominant_hex TEXT,
                color_name TEXT,
                search_count INTEGER DEFAULT 0,
                album TEXT DEFAULT NULL
            )''')
            await db.execute('''CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY, 
                is_super INTEGER DEFAULT 0
            )''')
            await db.execute('''CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                code TEXT,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            await db.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'uz'
            )''')
            
            for col in ["search_count INTEGER DEFAULT 0", "album TEXT"]:
                try:
                    await db.execute(f"ALTER TABLE images ADD COLUMN {col}")
                except Exception:
                    pass

            try:
                await db.execute("ALTER TABLE users ADD COLUMN subscribed INTEGER DEFAULT 1")
            except Exception:
                pass

            await db.commit()
        logger.info("✅ SQLite bazasi tayyor")


async def fetchone(query, *params):
    if DB_TYPE == "postgresql":
        async with _pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)
            return tuple(row.values()) if row else None
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(query, params)
            row = await cursor.fetchone()
            await cursor.close()
            return row


async def fetchall(query, *params):
    if DB_TYPE == "postgresql":
        async with _pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [tuple(row.values()) for row in rows]
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            await cursor.close()
            return rows


async def execute(query, *params):
    if DB_TYPE == "postgresql":
        async with _pool.acquire() as conn:
            await conn.execute(query, *params)
    else:
        import aiosqlite
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(query, params)
            await db.commit()


async def close_db():
    global _pool
    if _pool and DB_TYPE == "postgresql":
        await _pool.close()