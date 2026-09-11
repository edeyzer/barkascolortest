# app/general.py - Multi-language
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.utils import check_rate_limit, get_user_lang, set_user_lang
from app.admin import is_admin, is_super_admin
from app.stats import get_stats
from app.database import fetchall
from app.translations import get_text
from config import DB_TYPE


def get_main_keyboard(is_admin_user: bool = False, lang: str = "uz"):
    buttons = [
        [KeyboardButton(get_text(lang, "btn_search")), KeyboardButton(get_text(lang, "btn_history"))],
        [KeyboardButton(get_text(lang, "btn_help")), KeyboardButton(get_text(lang, "btn_lang"))]
    ]
    if is_admin_user:
        buttons.append([
            KeyboardButton(get_text(lang, "btn_stats")),
            KeyboardButton(get_text(lang, "btn_codes"))
        ])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = await get_user_lang(uid)
    
    if not check_rate_limit(uid):
        await update.message.reply_text(get_text(lang, "rate_limit"))
        return
    
    is_adm = await is_admin(uid)
    text = get_text(lang, "welcome")
    
    if is_adm:
        text += "\n\n🔐 <i>Admin rejimi faol</i>" if lang == "uz" else "\n\n🔐 <i>Режим администратора</i>"
        if await is_super_admin(uid):
            text += "\n👑 <i>Super Admin</i>"
    
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(is_adm, lang)
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = await get_user_lang(uid)
    is_user_admin = await is_admin(uid)
    is_user_super_admin = await is_super_admin(uid)
    
    text = get_text(lang, "help")
    
    if is_user_admin:
        if lang == "uz":
            text += """

<b>🔐 Admin buyruqlari:</b>
/editcode, /deletecode, /listcodes
/stats — Statistika
/setalbum — Albom biriktirish
/listalbums — Albomlar"""
        else:
            text += """

<b>🔐 Команды админа:</b>
/editcode, /deletecode, /listcodes
/stats — Статистика
/setalbum — Привязать альбом
/listalbums — Список альбомов"""
    
    if is_user_super_admin:
        text += "\n\n👑 Super Admin: /addadmin, /deleteadmin, /promote, /demote, /backup"
    
    text += "\n\n━━━━━━━━━━━━━━━━━━\n📞 @edeyzers"
    
    await update.message.reply_text(text, parse_mode="HTML")


async def history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    lang = await get_user_lang(uid)
    
    if DB_TYPE == "sqlite":
        q = "SELECT code FROM search_history WHERE user_id = ? ORDER BY searched_at DESC LIMIT 15"
    else:
        q = "SELECT code FROM search_history WHERE user_id = $1 ORDER BY searched_at DESC LIMIT 15"
    
    rows = await fetchall(q, uid)
    
    if not rows:
        await update.message.reply_text(get_text(lang, "history_empty"))
        return
    
    text = get_text(lang, "history_title")
    for i, row in enumerate(rows, 1):
        code = row[0] if isinstance(row, tuple) else row.get("code")
        text += f"{i}. <code>{code}</code>\n"
    
    await update.message.reply_text(text, parse_mode="HTML")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not await is_admin(uid):
        await update.message.reply_text("❌ Faqat adminlar uchun." if await get_user_lang(uid) == "uz" else "❌ Только для админов.")
        return

    data = await get_stats()
    text = (
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"🎨 Ranglar: <b>{data['images']}</b>\n"
        f"🔍 Jami qidiruvlar: <b>{data['total_searches']}</b>\n"
        f"👮 Adminlar: <b>{data['admins']}</b>\n"
    )
    if data["top_codes"]:
        text += "\n🔥 <b>Eng ko‘p qidirilgan:</b>\n"
        for i, row in enumerate(data["top_codes"], 1):
            code = row[0] if isinstance(row, tuple) else row.get("code")
            count = row[1] if isinstance(row, tuple) else row.get("search_count")
            text += f"{i}. <code>{code}</code> — <b>{count}</b>\n"
    
    await update.message.reply_text(text, parse_mode="HTML")


async def language_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Til tanlash"""
    buttons = [
        [
            InlineKeyboardButton("🇺🇿 O‘zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")
        ]
    ]
    lang = await get_user_lang(update.effective_user.id)
    await update.message.reply_text(
        get_text(lang, "choose_language"),
        reply_markup=InlineKeyboardMarkup(buttons)
    )