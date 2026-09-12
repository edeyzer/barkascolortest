# app/handlers.py - Multi-language
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.database import fetchone, execute
from app.admin import is_admin
from app.codes import get_image_by_code
from app.color_generator import ColorSquareGenerator
from app.color_detector import SimpleColorDetector
from app.utils import logger, check_rate_limit, get_color_name, get_user_lang
from app.translations import get_text
from app.notifications import notify_new_code
from config import DB_TYPE
import re
import asyncio


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    lang = await get_user_lang(user_id)
    
    if not await is_admin(user_id):
        await update.message.reply_text("🔄 Rasm tahlil qilinmoqda..." if lang == "uz" else "🔄 Анализирую изображение...")
        hex_color = await SimpleColorDetector.get_dominant_color(update.message.photo[-1])
        
        if hex_color:
            color_name = await get_color_name(hex_color)
            await update.message.reply_text(
                f"🎨 **Rasm tahlili:**\n🏆 Asosiy rang: `{hex_color}`\n📝 **{color_name}**"
                if lang == "uz" else
                f"🎨 **Анализ изображения:**\n🏆 Основной цвет: `{hex_color}`\n📝 **{color_name}**",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Xatolik." if lang == "uz" else "❌ Ошибка.")
        return

    # ADMIN
    photo = update.message.photo[-1]
    file_id = photo.file_id
    hex_color = await SimpleColorDetector.get_dominant_color(photo)
    color_name = await get_color_name(hex_color)

    if "editing_code" in context.user_data:
        code = context.user_data.pop("editing_code")
        if DB_TYPE == "sqlite":
            q = "UPDATE images SET file_id=?, dominant_hex=?, color_name=? WHERE code=?"
        else:
            q = "UPDATE images SET file_id=$1, dominant_hex=$2, color_name=$3 WHERE code=$4"
        await execute(q, file_id, hex_color, color_name, code)
        await update.message.reply_text(
            f"✅ `{code}` yangilandi!\n🎨 {hex_color} ({color_name})",
            parse_mode="Markdown"
        )
        return

    if "photo_queue" not in context.user_data:
        context.user_data["photo_queue"] = []
    
    context.user_data["photo_queue"].append({
        "file_id": file_id,
        "hex": hex_color,
        "name": color_name
    })
    
    queue = context.user_data["photo_queue"]
    total = len(queue)
    
    if not context.user_data.get("waiting_code_for_queue"):
        context.user_data["waiting_code_for_queue"] = True
        context.user_data["current_queue_index"] = 0
        
        current = queue[0]
        await update.message.reply_text(
            f"📩 Rasm qabul qilindi! (1/{total})\n"
            f"🎨 Asosiy rang: {current['hex']} ({current['name']})\n\n"
            f"💡 1-rasm uchun kodni kiriting:"
        )
    else:
        await update.message.reply_text(
            f"📥 Rasm navbatga qo‘shildi ({total} ta).\nHozirgi rasm uchun kodni yozing."
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    text = update.message.text.strip()
    lang = await get_user_lang(user_id)

        # ===== Ommaviy xabar jarayoni =====
    if context.user_data.get("waiting_broadcast"):
        if not await is_admin(user_id):
            context.user_data.clear()
            return

        context.user_data["waiting_broadcast"] = False
        context.user_data["broadcast_message"] = update.message

        buttons = [[
            InlineKeyboardButton("✅ Ha, yuborish", callback_data="broadcast_yes"),
            InlineKeyboardButton("❌ Bekor", callback_data="broadcast_no")
        ]]
        await update.message.reply_text(
            "📢 Xabar qabul qilindi. Barcha foydalanuvchilarga yuborilsinmi?",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Tugmalar
    if text in [get_text("uz", "btn_search"), get_text("ru", "btn_search")]:
        await update.message.reply_text(get_text(lang, "search_prompt"))
        return
    if text in [get_text("uz", "btn_history"), get_text("ru", "btn_history")]:
        from app.general import history_cmd
        await history_cmd(update, context)
        return
    if text in [get_text("uz", "btn_help"), get_text("ru", "btn_help")]:
        from app.general import help_cmd
        await help_cmd(update, context)
        return
    if text in [get_text("uz", "btn_lang"), get_text("ru", "btn_lang")]:
        from app.general import language_cmd
        await language_cmd(update, context)
        return
    if text in [get_text("uz", "btn_stats"), get_text("ru", "btn_stats")]:
        from app.general import stats_cmd
        await stats_cmd(update, context)
        return
    if text in [get_text("uz", "btn_codes"), get_text("ru", "btn_codes")]:
        from app.admin_commands import list_codes_cmd
        await list_codes_cmd(update, context)
        return

    # HEX
    hex_match = re.search(r'#?[0-9A-Fa-f]{6}', text, re.IGNORECASE)
    if hex_match and len(text) <= 9:
        hex_color = hex_match.group().upper()
        if not hex_color.startswith('#'):
            hex_color = '#' + hex_color
        img_buffer = ColorSquareGenerator.create_color_square(hex_color)
        if img_buffer:
            color_name = await get_color_name(hex_color)
            await update.message.reply_photo(
                photo=img_buffer,
                caption=f"🎨 **Rang:** `{hex_color}`\n📝 **{color_name}**",
                parse_mode="Markdown"
            )
        return

    # Ko‘p rasm navbati
    if context.user_data.get("waiting_code_for_queue"):
        if not await is_admin(user_id):
            context.user_data.clear()
            return

        if len(text) < 2:
            await update.message.reply_text("⚠️ Kod kamida 2 ta belgi bo‘lishi kerak.")
            return

        queue = context.user_data.get("photo_queue", [])
        idx = context.user_data.get("current_queue_index", 0)
        
        if idx >= len(queue):
            context.user_data.pop("waiting_code_for_queue", None)
            context.user_data.pop("photo_queue", None)
            context.user_data.pop("current_queue_index", None)
            await update.message.reply_text("✅ Barcha rasmlar qayta ishlandi.")
            return

        current = queue[idx]
        photo_id = current["file_id"]
        hex_color = current["hex"]
        color_name = current["name"]

        existing = await fetchone(
            "SELECT code FROM images WHERE code = ?" if DB_TYPE == "sqlite" else "SELECT code FROM images WHERE code = $1",
            text
        )

        if existing:
            buttons = [[
                InlineKeyboardButton("✅ Ha, yangilash", callback_data=f"update_yes:{text}"),
                InlineKeyboardButton("❌ Yo‘q", callback_data="update_no")
            ]]
            context.user_data["pending_update"] = {
                "code": text, "photo_id": photo_id, "hex": hex_color, "name": color_name
            }
            await update.message.reply_text(
                f"⚠️ `{text}` allaqachon mavjud. Yangilashni xohlaysizmi?",
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown"
            )
            return

        try:
            if DB_TYPE == "sqlite":
                q = "INSERT INTO images (code, file_id, dominant_hex, color_name) VALUES (?, ?, ?, ?)"
            else:
                q = "INSERT INTO images (code, file_id, dominant_hex, color_name) VALUES ($1, $2, $3, $4)"
            await execute(q, text, photo_id, hex_color, color_name)

            # Yangi kod haqida obunachilarga xabar (asosiy oqimni bloklamaydi)
            asyncio.create_task(notify_new_code(context.bot, text, photo_id, hex_color, color_name))

            await update.message.reply_text(
                f"✅ `{text}` saqlandi! ({idx+1}/{len(queue)})\n🎨 {hex_color} ({color_name})",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Saqlash xatosi: {e}")
            await update.message.reply_text("❌ Saqlashda xatolik.")
            return

        idx += 1
        context.user_data["current_queue_index"] = idx
        
        if idx < len(queue):
            next_photo = queue[idx]
            await update.message.reply_text(
                f"📩 Keyingi rasm ({idx+1}/{len(queue)})\n"
                f"🎨 Asosiy rang: {next_photo['hex']} ({next_photo['name']})\n\n"
                f"💡 {idx+1}-rasm uchun kodni kiriting:"
            )
        else:
            context.user_data.pop("waiting_code_for_queue", None)
            context.user_data.pop("photo_queue", None)
            context.user_data.pop("current_queue_index", None)
            await update.message.reply_text("🎉 Barcha rasmlar muvaffaqiyatli saqlandi!")
        return

    if not check_rate_limit(user_id):
        await update.message.reply_text(get_text(lang, "rate_limit"))
        return

    await get_image_by_code(update, context, text)