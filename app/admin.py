from app.database import fetchone, fetchall, execute
from config import BOSS_ADMIN_ID, DB_TYPE
import logging

logger = logging.getLogger(__name__)

async def ensure_boss():
    """
    Ensure boss admin exists in DB (call on startup)
    """
    # placeholder: check and insert boss
    if DB_TYPE == "sqlite":
        q_check = "SELECT user_id FROM admins WHERE user_id = ?"
        q_insert = "INSERT OR IGNORE INTO admins (user_id, is_super) VALUES (?, ?)"
    else:
        q_check = "SELECT user_id FROM admins WHERE user_id = $1"
        q_insert = "INSERT INTO admins (user_id, is_super) VALUES ($1, $2) ON CONFLICT DO NOTHING"

    row = await fetchone(q_check, BOSS_ADMIN_ID)
    if not row:
        await execute(q_insert, BOSS_ADMIN_ID, 1)
        logger.info("Inserted boss admin: %s", BOSS_ADMIN_ID)

async def is_admin(user_id):
    if DB_TYPE == "sqlite":
        q = "SELECT user_id FROM admins WHERE user_id = ?"
    else:
        q = "SELECT user_id FROM admins WHERE user_id = $1"
    row = await fetchone(q, user_id)
    return row is not None

async def is_super_admin(user_id):
    if DB_TYPE == "sqlite":
        q = "SELECT is_super FROM admins WHERE user_id = ?"
    else:
        q = "SELECT is_super FROM admins WHERE user_id = $1"
    row = await fetchone(q, user_id)
    if not row:
        return False
    # row shape: sqlite -> tuple, postgres -> Record
    value = row[0] if isinstance(row, tuple) else row.get("is_super", row.get("is_super"))
    return int(value) == 1
