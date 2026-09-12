# app/notifications.py - Yangi kod qo'shilganda obunachilarga bildirishnoma
import asyncio

from telegram import Update
from telegram.ext import ContextTypes

from app.database import fetchall, execute
from app.utils import get_user_lang, logger
from config import DB_TYPE

NOTIFY_DELAY = 0.05  # flooddan saqlanish uchun har xabar orasidagi kutish


async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/subscribe - foydalanuvchi yangi kodlar haqida bildirishnoma olishni yoqadi."""
    uid = update.effective_user.id
    lang = await get_user_lang(uid)
    try:
        if DB_TYPE == "sqlite":
            await execute(
                "INSERT INTO users (user_id, language, subscribed) VALUES (?, ?, 1) "
                "ON CONFLICT(user_id) DO UPDATE SET subscribed = 1",
                uid, lang
            )
        else:
            await execute(
                "INSERT INTO users (user_id, language, subscribed) VALUES ($1, $2, 1) "
                "ON CONFLICT (user_id) DO UPDATE SET subscribed = 1",
                uid, lang
            )
        await update.message.reply_text(
            "🔔 Yoqildi! Endi yangi mato qo'shilganda sizga xabar boradi.\n"
            "O'chirish uchun: /unsubscribe"
            if lang == "uz" else
            "🔔 Включено! Теперь вы будете получать уведомления о новых цветах.\n"
            "Чтобы отключить: /unsubscribe"
        )
    except Exception as e:
        logger.error(f"subscribe_cmd xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi.")


async def unsubscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/unsubscribe - bildirishnomalarni o'chiradi."""
    uid = update.effective_user.id
    lang = await get_user_lang(uid)
    try:
        if DB_TYPE == "sqlite":
            q = "UPDATE users SET subscribed = 0 WHERE user_id = ?"
        else:
            q = "UPDATE users SET subscribed = 0 WHERE user_id = $1"
        await execute(q, uid)
        await update.message.reply_text(
            "🔕 Yangi kodlar haqidagi bildirishnomalar o'chirildi.\n"
            "Qayta yoqish uchun: /subscribe"
            if lang == "uz" else
            "🔕 Уведомления о новых кодах отключены.\n"
            "Чтобы включить снова: /subscribe"
        )
    except Exception as e:
        logger.error(f"unsubscribe_cmd xato: {e}")
        await update.message.reply_text("❌ Xatolik yuz berdi.")


async def notify_new_code(bot, code: str, file_id: str, hex_color: str, color_name: str):
    """Yangi kod muvaffaqiyatli saqlangandan keyin barcha obunachilarga xabar yuboradi.
    Bu funksiya asosiy oqimni bloklamasligi uchun asyncio.create_task orqali chaqiriladi."""
    try:
        rows = await fetchall("SELECT user_id, language FROM users WHERE subscribed = 1")
    except Exception as e:
        logger.error(f"notify_new_code: obunachilarni olishda xato: {e}")
        return

    if not rows:
        return

    sent, failed = 0, 0
    for row in rows:
        uid = row[0] if isinstance(row, tuple) else row.get("user_id")
        lang = (row[1] if isinstance(row, tuple) else row.get("language")) or "uz"

        caption = (
            f"🆕 Yangi mato qo'shildi!\n\n🏷 Kod: {code}\n🎨 Rang: {color_name} ({hex_color})"
            if lang == "uz" else
            f"🆕 Добавлен новый цвет!\n\n🏷 Код: {code}\n🎨 Цвет: {color_name} ({hex_color})"
        )
        try:
            if file_id:
                await bot.send_photo(chat_id=uid, photo=file_id, caption=caption)
            else:
                await bot.send_message(chat_id=uid, text=caption)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(NOTIFY_DELAY)

    logger.info(f"Yangi kod bildirishnomasi: {sent} ta yuborildi, {failed} ta xato ({code})")