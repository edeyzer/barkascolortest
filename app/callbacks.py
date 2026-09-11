# app/callbacks.py - Multi-language + admin + similar + file_id himoyasi
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from app.database import fetchone, execute, fetchall
from app.utils import validate_code_format, logger, get_similar_codes, get_user_lang, set_user_lang
from app.admin import is_admin
from app.translations import get_text
from app.admin_commands import _send_codes_page
from config import DB_TYPE, BOSS_ADMIN_ID
from app.admin import is_super_admin

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if not await is_super_admin(user_id):
        await query.answer("❌ Ruxsat yo‘q", show_alert=True)
        return

    if data == "broadcast_no":
        context.user_data.pop("broadcast_message", None)
        await query.message.edit_text("❌ Ommaviy xabar bekor qilindi.")
        await query.answer()
        return

    if data == "broadcast_yes":
        msg = context.user_data.get("broadcast_message")
        if not msg:
            await query.answer("Xabar topilmadi", show_alert=True)
            return

        await query.message.edit_text("📤 Xabar yuborilmoqda...")

        # Barcha foydalanuvchilarni olish
        rows = await fetchall("SELECT user_id FROM users")
        users = [row[0] if isinstance(row, tuple) else row.get("user_id") for row in rows]

        success = 0
        failed = 0

        for uid in users:
            try:
                await msg.copy(chat_id=uid)
                success += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)  # flooddan saqlanish

        await query.message.edit_text(
            f"✅ Ommaviy xabar yuborildi!\n\n"
            f"Muvaffaqiyatli: <b>{success}</b>\n"
            f"Xato: <b>{failed}</b>",
            parse_mode="HTML"
        )
        context.user_data.pop("broadcast_message", None)
        await query.answer()

async def handle_suggestions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("suggest_yes:"):
        code = data.split(":", 1)[1]
        
        if not validate_code_format(code):
            await query.answer("⚠️ Kod formati noto'g'ri!", show_alert=True)
            return

        if DB_TYPE == "sqlite":
            q = "SELECT file_id, dominant_hex, color_name FROM images WHERE code = ?"
        else:
            q = "SELECT file_id, dominant_hex, color_name FROM images WHERE code = $1"
        
        row = await fetchone(q, code)
        
        if not row:
            await query.message.reply_text("❌ Kod topilmadi.")
            await query.answer()
            return

        file_id = row[0] if isinstance(row, tuple) else row.get("file_id")
        hex_color = row[1] if isinstance(row, tuple) else row.get("dominant_hex")
        color_name = row[2] if isinstance(row, tuple) else row.get("color_name")
        
        caption = f"🎨 Kod: `{code}`"
        if hex_color:
            caption += f"\n🎯 HEX: `{hex_color}`"
        if color_name:
            caption += f"\n📝 Rang: {color_name}"
        
        try:
            await query.message.reply_photo(
                photo=file_id, 
                caption=caption,
                parse_mode="Markdown"
            )
        except BadRequest as e:
            error_text = str(e).lower()
            if any(x in error_text for x in ["wrong file identifier", "file is too big", "invalid file"]):
                logger.warning(f"Eskirgan file_id (suggest): {code}")
                await query.message.reply_text(
                    f"⚠️ `{code}` topildi, lekin rasm vaqtincha mavjud emas.\nAdminlarga xabar berildi.",
                    parse_mode="Markdown"
                )
                try:
                    await context.bot.send_message(
                        BOSS_ADMIN_ID,
                        f"🚨 Eskirgan file_id (suggest)\nKod: <code>{code}</code>",
                        parse_mode="HTML"
                    )
                except:
                    pass
            else:
                await query.message.reply_text(f"⚠️ `{code}` yuborib bo‘lmadi.")
        except Exception as e:
            logger.error(f"Suggestion xatosi: {e}")
            await query.message.reply_text("❌ Rasm yuborishda xatolik yuz berdi.")
        
        await query.answer()

    elif data == "suggest_no":
        await query.message.reply_text("🔁 Yana urinib ko'ring.")
        await query.answer()


async def handle_update_decision(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("update_yes:"):
        code = data.split(":", 1)[1]
        pending = context.user_data.get("pending_update")

        if not pending or pending.get("code") != code:
            await query.answer("⚠️ Ma'lumot eskirgan. Qaytadan rasm yuboring.", show_alert=True)
            return

        photo_id = pending["photo_id"]
        hex_color = pending["hex"]
        color_name = pending["name"]

        try:
            if DB_TYPE == "sqlite":
                q = "UPDATE images SET file_id = ?, dominant_hex = ?, color_name = ? WHERE code = ?"
            else:
                q = "UPDATE images SET file_id = $1, dominant_hex = $2, color_name = $3 WHERE code = $4"
            
            await execute(q, photo_id, hex_color, color_name, code)
            context.user_data.pop("pending_update", None)
            
            await query.message.edit_text(
                f"✅ `{code}` muvaffaqiyatli yangilandi!\n"
                f"🎨 Asosiy rang: {hex_color} ({color_name})",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Yangilashda xato: {e}")
            await query.message.edit_text("❌ Yangilashda xatolik yuz berdi.")
        
        await query.answer()

    elif data == "update_no":
        context.user_data.pop("pending_update", None)
        await query.message.edit_text("❌ Yangilash bekor qilindi.")
        await query.answer()


async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if not await is_admin(user_id):
        await query.answer("❌ Faqat adminlar!", show_alert=True)
        return

    if data.startswith("admin_page:"):
        page = int(data.split(":")[1])
        await _send_codes_page(update, context, page=page, edit=True)
        await query.answer()
        return

    if data.startswith("admin_view:"):
        code = data.split(":", 1)[1]
        if DB_TYPE == "sqlite":
            q = "SELECT file_id, dominant_hex, color_name FROM images WHERE code = ?"
        else:
            q = "SELECT file_id, dominant_hex, color_name FROM images WHERE code = $1"
        
        row = await fetchone(q, code)
        if not row:
            await query.answer("Kod topilmadi", show_alert=True)
            return
        
        file_id = row[0] if isinstance(row, tuple) else row.get("file_id")
        hex_color = row[1] if isinstance(row, tuple) else row.get("dominant_hex")
        color_name = row[2] if isinstance(row, tuple) else row.get("color_name")
        
        caption = f"🎨 `{code}`"
        if hex_color:
            caption += f"\nHEX: `{hex_color}`"
        if color_name:
            caption += f"\n{color_name}"
        
        try:
            await query.message.reply_photo(photo=file_id, caption=caption, parse_mode="Markdown")
        except BadRequest as e:
            error_text = str(e).lower()
            if any(x in error_text for x in ["wrong file identifier", "invalid file"]):
                await query.message.reply_text(
                    f"⚠️ `{code}` — file_id eskirgan.\nQayta yuklash: /editcode {code}",
                    parse_mode="Markdown"
                )
            else:
                await query.message.reply_text(caption, parse_mode="Markdown")
        except Exception:
            await query.message.reply_text(caption, parse_mode="Markdown")
        
        await query.answer()
        return

    if data.startswith("admin_del:"):
        code = data.split(":", 1)[1]
        buttons = [
            [
                InlineKeyboardButton("✅ Ha, o‘chirish", callback_data=f"admin_del_confirm:{code}"),
                InlineKeyboardButton("❌ Bekor", callback_data="admin_del_cancel")
            ]
        ]
        await query.message.reply_text(
            f"⚠️ `{code}` ni o‘chirishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
        await query.answer()
        return

    if data.startswith("admin_del_confirm:"):
        code = data.split(":", 1)[1]
        if DB_TYPE == "sqlite":
            await execute("DELETE FROM images WHERE code = ?", code)
        else:
            await execute("DELETE FROM images WHERE code = $1", code)
        
        await query.message.edit_text(f"✅ `{code}` o‘chirildi.", parse_mode="Markdown")
        await query.answer("O‘chirildi")
        return

    if data == "admin_del_cancel":
        await query.message.edit_text("❌ O‘chirish bekor qilindi.")
        await query.answer()
        return

    if data.startswith("admin_edit:"):
        code = data.split(":", 1)[1]
        context.user_data["editing_code"] = code
        await query.message.reply_text(
            f"📤 Endi `{code}` uchun yangi rasm yuboring.",
            parse_mode="Markdown"
        )
        await query.answer()
        return


async def handle_similar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data.startswith("similar:"):
        code = data.split(":", 1)[1]
        suggestions = await get_similar_codes(code, limit=5)
        
        if not suggestions:
            await query.answer("O‘xshash kod topilmadi", show_alert=True)
            return
        
        buttons = [
            [InlineKeyboardButton(f"✅ {s}", callback_data=f"suggest_yes:{s}")]
            for s in suggestions
        ]
        
        await query.message.reply_text(
            f"🔍 `{code}` ga o‘xshash kodlar:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
        await query.answer()


async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Til tanlash callbacki"""
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    if data == "lang_uz":
        await set_user_lang(user_id, "uz")
        await query.answer("O‘zbekcha tanlandi")
        await query.message.edit_text(get_text("uz", "language_changed_uz"))
        
        from app.general import get_main_keyboard
        from app.admin import is_admin
        is_adm = await is_admin(user_id)
        await query.message.reply_text(
            "⬇️",
            reply_markup=get_main_keyboard(is_adm, "uz")
        )

    elif data == "lang_ru":
        await set_user_lang(user_id, "ru")
        await query.answer("Русский выбран")
        await query.message.edit_text(get_text("ru", "language_changed_ru"))
        
        from app.general import get_main_keyboard
        from app.admin import is_admin
        is_adm = await is_admin(user_id)
        await query.message.reply_text(
            "⬇️",
            reply_markup=get_main_keyboard(is_adm, "ru")
        )