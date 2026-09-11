# app/backup.py - YANGILANGAN VA TUZATILGAN
import json
import datetime
import os
from telegram import Update
from telegram.ext import ContextTypes
from app.database import fetchall
from app.admin import is_super_admin
from config import DB_TYPE

async def backup_data_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ma'lumotlarni .json faylga backup qilib yuboradi."""
    user_id = update.effective_user.id

    # Super admin tekshiruvi
    if not await is_super_admin(user_id):
        await update.message.reply_text("❌ Faqat super adminlar backup olishi mumkin.")
        return

    await update.message.reply_text("🔄 Backup tayyorlanmoqda...")

    # Ma'lumotlarni olish
    q = "SELECT code, file_id, dominant_hex, color_name FROM images"
    rows = await fetchall(q)

    backup_data = {
        "backup_date": datetime.datetime.now().isoformat(),
        "total_codes": len(rows),
        "codes": []
    }

    for row in rows:
        if isinstance(row, tuple):
            backup_data["codes"].append({
                "code": row[0],
                "file_id": row[1],
                "dominant_hex": row[2],
                "color_name": row[3]
            })
        else:
            backup_data["codes"].append({
                "code": row.get("code"),
                "file_id": row.get("file_id"),
                "dominant_hex": row.get("dominant_hex"),
                "color_name": row.get("color_name")
            })

    # 🔥 MUHIM: Universal vaqtinchalik papka (Windows + Linux)
    temp_dir = (
        os.getenv("TMP")
        or os.getenv("TEMP")
        or "/tmp"     # Linux serverlar uchun
    )

    os.makedirs(temp_dir, exist_ok=True)

    filename = f"backup_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(temp_dir, filename)

    try:
        # JSON yozish
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        # Foydalanuvchiga faylni yuborish
        with open(filepath, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=filename,
                caption=(
                    f"📦 Backup tayyor!\n"
                    f"📊 Jami kodlar: {len(rows)} ta\n"
                    f"📅 Sana: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
                )
            )

        # Faylni o'chirish
        os.remove(filepath)

    except Exception as e:
        await update.message.reply_text(f"❌ Backup xatosi: {e}")
