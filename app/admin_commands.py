# app/admin_commands.py - to‘liq to‘g‘rilangan

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest
from app.admin import is_admin, is_super_admin
from app.database import fetchone, execute, fetchall
from app.utils import logger
from config import DB_TYPE, BOSS_ADMIN_ID

CODES_PER_PAGE = 8


async def edit_code_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Faqat adminlar buyruqdan foydalanishi mumkin.")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Iltimos, kodni kiriting: /editcode <kod>")
        return
    
    code = context.args[0]
    context.user_data["editing_code"] = code
    await update.message.reply_text(f"📤 Endi `{code}` uchun yangi rasm yuboring.", parse_mode="Markdown")


async def delete_code_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Faqat adminlar buyruqdan foydalanishi mumkin.")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Iltimos, kodni kiriting: /deletecode <kod>")
        return
    
    code = context.args[0]
    if DB_TYPE == "sqlite":
        q = "DELETE FROM images WHERE code = ?"
    else:
        q = "DELETE FROM images WHERE code = $1"
    
    await execute(q, code)
    await update.message.reply_text(f"✅ `{code}` o'chirildi.", parse_mode="Markdown")


async def list_codes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Faqat adminlar buyruqdan foydalanishi mumkin.")
        return
    
    await _send_codes_page(update, context, page=0)


async def _send_codes_page(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0, edit: bool = False):
    if DB_TYPE == "sqlite":
        q = "SELECT code FROM images ORDER BY code"
    else:
        q = "SELECT code FROM images ORDER BY code"
    
    rows = await fetchall(q)
    if not rows:
        text = "📝 Hozircha hech qanday kod mavjud emas."
        if edit:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return
    
    codes = [row[0] if isinstance(row, tuple) else row.get("code") for row in rows]
    total = len(codes)
    total_pages = (total + CODES_PER_PAGE - 1) // CODES_PER_PAGE
    page = max(0, min(page, total_pages - 1))
    
    start = page * CODES_PER_PAGE
    end = start + CODES_PER_PAGE
    page_codes = codes[start:end]
    
    text = f"📋 **Mavjud kodlar** ({total} ta)\n"
    text += f"📄 Sahifa: {page + 1}/{total_pages}\n\n"
    
    buttons = []
    for code in page_codes:
        buttons.append([
            InlineKeyboardButton(f"🎨 {code}", callback_data=f"admin_view:{code}"),
            InlineKeyboardButton("🗑", callback_data=f"admin_del:{code}"),
            InlineKeyboardButton("✏️", callback_data=f"admin_edit:{code}")
        ])
    
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"admin_page:{page-1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"admin_page:{page+1}"))
    
    if nav:
        buttons.append(nav)
    
    markup = InlineKeyboardMarkup(buttons)
    
    if edit:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


async def set_album_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Faqat adminlar.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Foydalanish: /setalbum <kod> <albom nomi>")
        return
    
    code = context.args[0]
    album = " ".join(context.args[1:])
    
    if DB_TYPE == "sqlite":
        await execute("UPDATE images SET album = ? WHERE code = ?", album, code)
    else:
        await execute("UPDATE images SET album = $1 WHERE code = $2", album, code)
    
    await update.message.reply_text(f"✅ `{code}` → **{album}** albomiga biriktirildi.", parse_mode="Markdown")


async def list_albums_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Faqat adminlar.")
        return
    
    rows = await fetchall("SELECT DISTINCT album FROM images WHERE album IS NOT NULL AND album != '' ORDER BY album")
    if not rows:
        await update.message.reply_text("📭 Hali albomlar yo‘q.")
        return
    
    text = "📁 <b>Mavjud albomlar:</b>\n\n"
    for row in rows:
        album = row[0] if isinstance(row, tuple) else row.get("album")
        text += f"• {album}\n"
    
    await update.message.reply_text(text, parse_mode="HTML")


async def check_files_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eskirgan file_id larni tekshirish"""
    user_id = update.effective_user.id
    if not await is_admin(user_id):
        await update.message.reply_text("❌ Faqat adminlar.")
        return

    await update.message.reply_text("🔍 Rasmlar tekshirilmoqda... Bu biroz vaqt olishi mumkin.")

    rows = await fetchall("SELECT code, file_id FROM images WHERE file_id IS NOT NULL AND file_id != ''")

    if not rows:
        await update.message.reply_text("📭 Bazada rasm topilmadi.")
        return

    broken = []
    total = len(rows)
    checked = 0

    for row in rows:
        code = row[0] if isinstance(row, tuple) else row.get("code")
        file_id = row[1] if isinstance(row, tuple) else row.get("file_id")
        
        try:
            await context.bot.get_file(file_id)
        except BadRequest:
            broken.append(code)
        except Exception as e:
            logger.error(f"check_files xato ({code}): {e}")
            broken.append(code)
        
        checked += 1
        if checked % 30 == 0:
            try:
                await update.message.reply_text(f"⏳ Tekshirildi: {checked}/{total}")
            except:
                pass

    if not broken:
        await update.message.reply_text(f"✅ Barcha rasmlar yaxshi! ({total} ta tekshirildi)")
        return

    text = f"⚠️ <b>Eskirgan file_id lar topildi:</b> {len(broken)} ta\n\n"
    
    for i, code in enumerate(broken[:40], 1):
        text += f"{i}. <code>{code}</code>\n"
    
    if len(broken) > 40:
        text += f"\n... va yana {len(broken) - 40} ta"
    
    text += f"\n\nJami tekshirildi: {total}"
    text += "\n\nQayta yuklash uchun: <code>/editcode KOD</code>"

    await update.message.reply_text(text, parse_mode="HTML")


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ommaviy xabar yuborish"""
    user_id = update.effective_user.id
    
    if not await is_super_admin(user_id):
        await update.message.reply_text("❌ Faqat Super Adminlar foydalanishi mumkin.")
        return

    context.user_data["waiting_broadcast"] = True
    await update.message.reply_text(
        "📢 <b>Ommaviy xabar yuborish</b>\n\n"
        "Yubormoqchi bo‘lgan xabaringizni yozing (matn, rasm, video va h.k.).\n\n"
        "Bekor qilish uchun: /cancel",
        parse_mode="HTML"
    )


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Har qanday jarayonni bekor qilish"""
    context.user_data.clear()
    await update.message.reply_text("❌ Bekor qilindi.")


import asyncio
from telegram.error import BadRequest
from config import BOSS_ADMIN_ID


async def auto_check_files(bot):
    """Avtomatik eskirgan file_id larni tekshirish"""
    logger.info("🔄 Avtomatik file_id tekshiruvi boshlandi...")
    
    try:
        rows = await fetchall("SELECT code, file_id FROM images WHERE file_id IS NOT NULL AND file_id != ''")
        
        if not rows:
            logger.info("Bazada rasm topilmadi")
            return

        broken = []
        total = len(rows)

        for row in rows:
            code = row[0] if isinstance(row, tuple) else row.get("code")
            file_id = row[1] if isinstance(row, tuple) else row.get("file_id")
            
            try:
                await bot.get_file(file_id)
            except BadRequest:
                broken.append(code)
            except Exception:
                broken.append(code)
            
            await asyncio.sleep(0.03)

        if broken:
            text = (
                f"⚠️ <b>Avtomatik tekshiruv natijasi</b>\n\n"
                f"Eskirgan file_id lar: <b>{len(broken)}</b> ta\n"
                f"Jami tekshirildi: {total}\n\n"
            )
            for i, code in enumerate(broken[:30], 1):
                text += f"{i}. <code>{code}</code>\n"
            
            if len(broken) > 30:
                text += f"\n... va yana {len(broken) - 30} ta"
            
            text += "\n\nQayta yuklash uchun: <code>/editcode KOD</code>"
            
            await bot.send_message(BOSS_ADMIN_ID, text, parse_mode="HTML")
            logger.warning(f"Avtomatik tekshiruv: {len(broken)} ta eskirgan file_id topildi")
        else:
            logger.info(f"✅ Avtomatik tekshiruv: barcha {total} ta rasm yaxshi")
            
    except Exception as e:
        logger.error(f"Avtomatik file_id tekshiruvida xato: {e}")   