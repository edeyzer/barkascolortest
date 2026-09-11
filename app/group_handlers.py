# app/group_handlers.py - 3-BOSQICH (kod qidiruv + tugmalar) + avtomatik o'chirish
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.color_generator import ColorSquareGenerator
from app.color_detector import SimpleColorDetector
from app.utils import get_color_name, get_similar_codes, logger
from app.database import fetchone, execute
from app import pantone
from config import DB_TYPE
import re
import asyncio

# Rang kodlari odatda qisqa bo'ladi va harf/raqam + bitta chiziqchadan iborat
CODE_TOKEN_RE = re.compile(r'^(?=.*\d)[A-Za-z0-9]{1,10}(?:[-_][A-Za-z0-9]{1,10})?$')
MAX_GROUP_TEXT_LEN = 20

# ==================== AVTOMATIK O'CHIRISH ====================
async def delete_messages_later(bot, chat_id: int, message_ids: list[int], delay: int = 60):
    """Guruhda xabarlarni belgilangan vaqtdan keyin o'chiradi"""
    await asyncio.sleep(delay)
    for msg_id in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception as e:
            # Bot admin emas, xabar allaqachon o'chirilgan yoki boshqa sabab
            logger.warning(f"Xabarni o'chirishda xato (chat={chat_id}, msg={msg_id}): {e}")


def schedule_delete(bot, chat_id: int, *message_ids, delay: int = 60):
    """Xabarlarni o'chirish vazifasini ishga tushirish"""
    ids = [mid for mid in message_ids if mid is not None]
    if ids:
        asyncio.create_task(delete_messages_later(bot, chat_id, ids, delay))
# =============================================================


async def handle_group_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruhdagi matnli xabarlarni qayta ishlash"""
    text = update.message.text.strip()
    user = update.message.from_user
    chat_id = update.effective_chat.id
    user_msg_id = update.message.message_id
    bot = context.bot

    # 1. HEX kod tekshirish
    hex_match = re.search(r'#?[0-9A-Fa-f]{6}', text, re.IGNORECASE)
    if hex_match and len(text) <= 9:
        hex_color = hex_match.group().upper()
        if not hex_color.startswith('#'):
            hex_color = '#' + hex_color
        
        color_name = await get_color_name(hex_color)
        img_buffer = ColorSquareGenerator.create_color_square(hex_color)
        
        if img_buffer:
            sent = await update.message.reply_photo(
                photo=img_buffer,
                caption=f"🎨 Rang: `{hex_color}`\n📝 {color_name}\n👤 {user.first_name}",
                parse_mode="Markdown",
                reply_to_message_id=user_msg_id
            )
            schedule_delete(bot, chat_id, user_msg_id, sent.message_id)
        return

    # 2. Rang kodi qidirish
    bot_username = (context.bot.username or "").lower()
    is_mentioned = bool(bot_username and f"@{bot_username}" in text.lower())
    clean_text = text
    if is_mentioned:
        clean_text = re.sub(rf"@{bot_username}", "", text, flags=re.IGNORECASE).strip()
    
    codes = [c.strip() for c in re.split(r'[,;\s]+', clean_text) if c.strip()]
    
    if not codes:
        return

    if not is_mentioned:
        if len(clean_text) > MAX_GROUP_TEXT_LEN:
            return
        if not all(CODE_TOKEN_RE.match(c) for c in codes[:3]):
            return

    code = codes[0]
    
    if DB_TYPE == "sqlite":
        q = "SELECT file_id, dominant_hex, color_name FROM images WHERE code = ?"
    else:
        q = "SELECT file_id, dominant_hex, color_name FROM images WHERE code = $1"
    
    row = await fetchone(q, code)
    
    if row:
        try:
            if DB_TYPE == "sqlite":
                await execute("UPDATE images SET search_count = COALESCE(search_count, 0) + 1 WHERE code = ?", code)
            else:
                await execute("UPDATE images SET search_count = COALESCE(search_count, 0) + 1 WHERE code = $1", code)
        except Exception:
            pass

        file_id = row[0] if isinstance(row, tuple) else row.get("file_id")
        hex_color = row[1] if isinstance(row, tuple) else row.get("dominant_hex")
        color_name = row[2] if isinstance(row, tuple) else row.get("color_name")
        
        caption = f"🎨 Kod: `{code}`"
        if hex_color:
            caption += f"\n🎯 HEX: `{hex_color}`"
        if color_name:
            caption += f"\n📝 {color_name}"
        caption += f"\n👤 {user.first_name}"
        
        buttons = [
            [
                InlineKeyboardButton("🔍 O‘xshashlar", callback_data=f"similar:{code}"),
            ]
        ]
        
        try:
            sent = await update.message.reply_photo(
                photo=file_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons),
                reply_to_message_id=user_msg_id
            )
            schedule_delete(bot, chat_id, user_msg_id, sent.message_id)
        except Exception as e:
            logger.error(f"Guruhda rasm yuborishda xato: {e}")
            sent = await update.message.reply_text(
                f"✅ Kod topildi: `{code}`\nLekin rasm yuborib bo‘lmadi.",
                parse_mode="Markdown",
                reply_to_message_id=user_msg_id
            )
            schedule_delete(bot, chat_id, user_msg_id, sent.message_id)
        return
    
    # Pantone TCX
    pantone_match = pantone.find_by_tcx(code)
    if pantone_match:
        caption = pantone.build_caption(pantone_match)
        caption += f"\n👤 {user.first_name}"
        img_buffer = ColorSquareGenerator.create_color_square(pantone_match["hex"])
        try:
            if img_buffer:
                sent = await update.message.reply_photo(
                    photo=img_buffer,
                    caption=caption,
                    parse_mode="Markdown",
                    reply_to_message_id=user_msg_id
                )
            else:
                sent = await update.message.reply_text(
                    caption, parse_mode="Markdown", reply_to_message_id=user_msg_id
                )
            schedule_delete(bot, chat_id, user_msg_id, sent.message_id)
        except Exception as e:
            logger.error(f"Guruhda Pantone rasm yuborishda xato: {e}")
            sent = await update.message.reply_text(
                caption, parse_mode="Markdown", reply_to_message_id=user_msg_id
            )
            schedule_delete(bot, chat_id, user_msg_id, sent.message_id)
        return

    # O'xshashlar taklifi
    suggestions = await get_similar_codes(code, limit=3)
    if suggestions:
        buttons = [
            [InlineKeyboardButton(f"✅ {s}", callback_data=f"suggest_yes:{s}")]
            for s in suggestions
        ]
        sent = await update.message.reply_text(
            f"❌ `{code}` topilmadi.\nBalki shulardan biri?",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown",
            reply_to_message_id=user_msg_id
        )
        schedule_delete(bot, chat_id, user_msg_id, sent.message_id)


async def handle_group_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruhdagi rasmlarni qayta ishlash"""
    user = update.message.from_user
    chat_id = update.effective_chat.id
    user_msg_id = update.message.message_id
    bot = context.bot
    
    try:
        photo = update.message.photo[-1]
        hex_color = await SimpleColorDetector.get_dominant_color(photo)
        
        if hex_color:
            color_name = await get_color_name(hex_color)
            img_buffer = ColorSquareGenerator.create_color_square(hex_color)
            
            if img_buffer:
                sent = await update.message.reply_photo(
                    photo=img_buffer,
                    caption=f"🎨 Rasm tahlili:\n"
                           f"🏆 Asosiy rang: `{hex_color}`\n"
                           f"📝 {color_name}\n"
                           f"👤 {user.first_name}",
                    parse_mode="Markdown",
                    reply_to_message_id=user_msg_id
                )
            else:
                sent = await update.message.reply_text(
                    f"🎨 Asosiy rang: `{hex_color}`\n📝 {color_name}",
                    parse_mode="Markdown",
                    reply_to_message_id=user_msg_id
                )
            schedule_delete(bot, chat_id, user_msg_id, sent.message_id)
        else:
            sent = await update.message.reply_text(
                "❌ Rasmni tahlil qilishda xatolik.",
                reply_to_message_id=user_msg_id
            )
            schedule_delete(bot, chat_id, user_msg_id, sent.message_id)
    except Exception as e:
        logger.error(f"Guruh rasm xatosi: {e}")
        sent = await update.message.reply_text(
            "❌ Rasmni qayta ishlashda muammo.",
            reply_to_message_id=user_msg_id
        )
        schedule_delete(bot, chat_id, user_msg_id, sent.message_id)