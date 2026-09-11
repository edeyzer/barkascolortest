# app/codes.py - to‘liq to‘g‘rilangan

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from app.database import fetchone, execute
from app.utils import get_similar_codes, logger, add_watermark
from app.color_generator import ColorSquareGenerator
from app import pantone
from config import DB_TYPE, BOSS_ADMIN_ID
import re

AUTO_SUGGEST = True


async def get_image_by_code(update, context, text):
    user_id = update.effective_user.id
    original_text = text.strip()

    hex_match = re.search(r'#?[0-9A-Fa-f]{6}', original_text, re.IGNORECASE)
    if hex_match and len(original_text) <= 8:
        return

    codes = [c.strip() for c in re.split(r'[,;\s]+', original_text) if c.strip()]
    
    if not codes:
        await update.message.reply_text("⚠️ Kod kiriting!")
        return

    if len(codes) == 1:
        await _send_single_code(update, codes[0], user_id)
        return

    found = 0
    for code in codes[:8]:
        success = await _send_single_code(update, code, user_id, silent_not_found=True)
        if success:
            found += 1

    if found == 0:
        # Balki bu ko'p so'zli Pantone nomi (masalan "Cloud Dancer") — bitta so'z
        # bo'lganda buni allaqachon _send_single_code o'zi tekshirgan, shuning
        # uchun bu yerda faqat ko'p so'zli holatlar uchun butun matnni sinaymiz.
        pantone_match, count = pantone.find_match(original_text)
        if pantone_match:
            await _send_pantone_match(update, pantone_match, extra_count=count)
            return
        await update.message.reply_text("❌ Hech qanday kod topilmadi.")
    elif found < len(codes):
        await update.message.reply_text(f"ℹ️ {found}/{len(codes)} ta kod topildi.")


async def _send_single_code(update, code: str, user_id: int = None, silent_not_found: bool = False) -> bool:
    if DB_TYPE == "sqlite":
        q = "SELECT file_id, dominant_hex, color_name, album FROM images WHERE code = ?"
    else:
        q = "SELECT file_id, dominant_hex, color_name, album FROM images WHERE code = $1"

    row = await fetchone(q, code)
    
    if not row:
        # ===== Pantone TCX bazasidan qidirish (fallback) =====
        # Foydalanuvchining o'ziga tegishli kodlar bazasida topilmasa, rasmiy
        # Pantone TCX kod/nomi bo'yicha ham tekshiramiz (masalan "11-4201", "Coral").
        # allow_partial=False — bu yerda faqat bitta so'z/kod tekshirilyapti, shuning
        # uchun qisman moslikka yo'l qo'ymaymiz (ko'p so'zli nomlar butun matn
        # bo'yicha get_image_by_code ichida alohida tekshiriladi).
        pantone_match, count = pantone.find_match(code, allow_partial=False)
        if pantone_match:
            return await _send_pantone_match(update, pantone_match, extra_count=count)

        if not silent_not_found:
            if AUTO_SUGGEST:
                suggestions = await get_similar_codes(code)
                if suggestions:
                    buttons = [[InlineKeyboardButton(f"✅ {s}", callback_data=f"suggest_yes:{s}")] for s in suggestions]
                    buttons.append([InlineKeyboardButton("❌ Yo‘q", callback_data="suggest_no")])
                    await update.message.reply_text(
                        f"❌ \"{code}\" topilmadi.\n\nBalki shu kodlardan birimi?",
                        reply_markup=InlineKeyboardMarkup(buttons),
                    )
                    return False
            await update.message.reply_text(f"❌ \"{code}\" topilmadi.")
        return False

    # search_count + history
    try:
        if DB_TYPE == "sqlite":
            await execute("UPDATE images SET search_count = COALESCE(search_count, 0) + 1 WHERE code = ?", code)
            if user_id:
                await execute("INSERT INTO search_history (user_id, code) VALUES (?, ?)", user_id, code)
        else:
            await execute("UPDATE images SET search_count = COALESCE(search_count, 0) + 1 WHERE code = $1", code)
            if user_id:
                await execute("INSERT INTO search_history (user_id, code) VALUES ($1, $2)", user_id, code)
    except Exception as e:
        logger.error(f"History/search_count xato: {e}")

    file_id = row[0] if isinstance(row, tuple) else row.get("file_id")
    hex_color = row[1] if isinstance(row, tuple) else row.get("dominant_hex")
    color_name = row[2] if isinstance(row, tuple) else row.get("color_name")
    album = row[3] if isinstance(row, tuple) else row.get("album")
    
    caption = f"🎨 Kod: `{code}`"
    if hex_color:
        caption += f"\n🎯 HEX: `{hex_color}`"
    if color_name:
        caption += f"\n📝 {color_name}"
    if album:
        caption += f"\n📁 Albom: {album}"
    
    buttons = [
        [
            InlineKeyboardButton("📤 Ulashish", switch_inline_query=code),
            InlineKeyboardButton("🔍 O‘xshashlar", callback_data=f"similar:{code}")
        ]
    ]
    
    # ========== Watermark + xato ushlash ==========
    try:
        watermarked = await add_watermark(update.get_bot(), file_id)
        
        if watermarked:
            await update.message.reply_photo(
                photo=watermarked,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        else:
            await update.message.reply_photo(
                photo=file_id,
                caption=caption,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(buttons)
            )
        return True

    except BadRequest as e:
        error_text = str(e).lower()
        
        if any(x in error_text for x in ["wrong file identifier", "file is too big", "failed to get http url content", "invalid file"]):
            logger.warning(f"Eskirgan file_id: {code} → {file_id}")
            
            await update.message.reply_text(
                f"⚠️ `{code}` kodi topildi, lekin rasm vaqtincha mavjud emas.\n"
                f"Adminlarga xabar berildi.",
                parse_mode="Markdown"
            )
            
            try:
                bot = update.get_bot()
                admin_text = (
                    f"🚨 <b>Eskirgan file_id</b>\n\n"
                    f"Kod: <code>{code}</code>\n"
                    f"File ID: <code>{file_id}</code>\n\n"
                    f"Qayta yuklash uchun:\n"
                    f"/editcode {code}"
                )
                await bot.send_message(BOSS_ADMIN_ID, admin_text, parse_mode="HTML")
            except Exception as admin_err:
                logger.error(f"Adminga xabar yuborishda xato: {admin_err}")
            
            return False
        else:
            logger.error(f"reply_photo BadRequest ({code}): {e}")
            await update.message.reply_text(f"❌ `{code}` yuborishda xatolik yuz berdi.")
            return False

    except Exception as e:
        logger.error(f"reply_photo umumiy xato ({code}): {e}")
        await update.message.reply_text(f"❌ `{code}` yuborishda kutilmagan xatolik.")
        return False


async def _send_pantone_match(update, item: dict, extra_count: int = 0) -> bool:
    """Rasmiy Pantone TCX rangini foydalanuvchiga rasm+ma'lumot bilan yuboradi."""
    caption = pantone.build_caption(item, extra_count=extra_count)
    img_buffer = ColorSquareGenerator.create_color_square(item["hex"])

    try:
        if img_buffer:
            await update.message.reply_photo(photo=img_buffer, caption=caption, parse_mode="Markdown")
        else:
            await update.message.reply_text(caption, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Pantone rasm yuborishda xato ({item.get('tcx')}): {e}")
        await update.message.reply_text(caption, parse_mode="Markdown")

    return True