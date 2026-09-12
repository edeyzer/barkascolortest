# bot.py - Multi-language
import asyncio
import sys
import uvicorn
from uuid import uuid4
from telegram import (
    MenuButtonWebApp,
    WebAppInfo,
    InlineQueryResultCachedPhoto,
    BotCommand,
    BotCommandScopeDefault,
    BotCommandScopeChat,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    InlineQueryHandler,
    filters
)

try:
    from api import app as fastapi_app
except ImportError:
    print("XATOLIK: api.py fayli topilmadi!")
    sys.exit(1)

from config import BOT_TOKEN, MINI_APP_URL, BOSS_ADMIN_ID
from app.database import init_db, fetchall
from app.utils import logger
from app.general import start, help_cmd, stats_cmd, history_cmd, language_cmd
from app.handlers import handle_photo, handle_text
from app.callbacks import (
    handle_suggestions,
    handle_update_decision,
    handle_admin_actions,
    handle_similar,
    handle_language,
    handle_broadcast
)
from app.admin import ensure_boss
from app.admin_commands import (
    edit_code_cmd, delete_code_cmd, list_codes_cmd,
    set_album_cmd, list_albums_cmd,
    check_files_cmd, broadcast_cmd,
    cancel_cmd
)
from app.super_admin import (
    add_admin_cmd, list_admins_cmd, delete_admin_cmd, promote_cmd, demote_cmd
)
from app.backup import backup_data_cmd
from app.group_handlers import handle_group_text, handle_group_photo
from app.export import export_cmd, handle_export
from app.notifications import subscribe_cmd, unsubscribe_cmd


async def inline_query(update, context):
    query = update.inline_query.query.strip()
    if not query or len(query) < 1:
        return

    results = []
    try:
        rows = await fetchall(
            "SELECT code, file_id, dominant_hex, color_name FROM images WHERE code LIKE ? LIMIT 20",
            f"%{query}%"
        )

        if not rows:
            await update.inline_query.answer([], cache_time=5)
            return

        for row in rows:
            if isinstance(row, tuple):
                code, file_id, hex_val, name = row
            else:
                code = row.get("code")
                file_id = row.get("file_id")
                hex_val = row.get("dominant_hex")
                name = row.get("color_name")

            name = name if name else "Rang"
            hex_val = hex_val if hex_val else ""

            if file_id:
                results.append(
                    InlineQueryResultCachedPhoto(
                        id=str(uuid4()),
                        photo_file_id=file_id,
                        title=f"{code}",
                        caption=(
                            f"🎨 **Kod:** {code}\n"
                            f"🏷 **Nom:** {name}\n"
                            f"🧬 **HEX:** {hex_val}\n\n"
                            f"🤖 @{context.bot.username}"
                        ),
                        parse_mode='Markdown'
                    )
                )

        await update.inline_query.answer(results, cache_time=3)

    except Exception as e:
        logger.error(f"Inline qidiruvda xato: {e}")
        await update.inline_query.answer([], cache_time=5)


async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN topilmadi!")
        sys.exit(1)

    await init_db()
    await ensure_boss()

    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .build()
    )

    # ===== Buyruqlar menyusi =====
    user_commands = [
        BotCommand("start", "Botni ishga tushirish"),
        BotCommand("help", "Yordam"),
        BotCommand("history", "Qidiruv tarixi"),
        BotCommand("language", "Tilni o‘zgartirish"),
        BotCommand("lang", "Tilni o‘zgartirish"),
        BotCommand("subscribe", "Yangi kodlar haqida xabar olish"),
        BotCommand("unsubscribe", "Bildirishnomalarni o‘chirish"),
    ]

    admin_commands = user_commands + [
        BotCommand("stats", "Statistika"),
        BotCommand("listcodes", "Kodlar ro‘yxati"),
        BotCommand("check_files", "Eskirgan rasmlarni tekshirish"),
        BotCommand("editcode", "Kodni tahrirlash"),
        BotCommand("deletecode", "Kodni o‘chirish"),
        BotCommand("setalbum", "Albom biriktirish"),
        BotCommand("listalbums", "Albomlar ro‘yxati"),
        BotCommand("export", "Katalogni Excel/PDF eksport qilish"),
    ]

    super_admin_commands = admin_commands + [
        BotCommand("broadcast", "Ommaviy xabar yuborish"),
        BotCommand("addadmin", "Admin qo‘shish"),
        BotCommand("listadmins", "Adminlar ro‘yxati"),
        BotCommand("deleteadmin", "Adminni o‘chirish"),
        BotCommand("promote", "Super Admin qilish"),
        BotCommand("demote", "Super Adminlikdan olish"),
        BotCommand("backup", "Backup olish"),
        BotCommand("cancel", "Jarayonni bekor qilish"),
    ]

    # Oddiy foydalanuvchilar uchun
    await application.bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())

    # Adminlar uchun
    try:
        rows = await fetchall("SELECT user_id, is_super FROM admins")
        
        for row in rows:
            uid = row[0] if isinstance(row, tuple) else row.get("user_id")
            is_super = row[1] if isinstance(row, tuple) else row.get("is_super", 0)
            
            if int(is_super) == 1:
                await application.bot.set_my_commands(
                    super_admin_commands,
                    scope=BotCommandScopeChat(chat_id=uid)
                )
            else:
                await application.bot.set_my_commands(
                    admin_commands,
                    scope=BotCommandScopeChat(chat_id=uid)
                )
    except Exception as e:
        logger.error(f"Buyruqlar menyusini o‘rnatishda xato: {e}")

    # Boss adminni kafolatlash
    try:
        await application.bot.set_my_commands(
            super_admin_commands,
            scope=BotCommandScopeChat(chat_id=BOSS_ADMIN_ID)
        )
    except Exception as e:
        logger.error(f"Boss admin buyruqlarida xato: {e}")

    # ===== Handlerlar =====
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    application.add_handler(CommandHandler("history", history_cmd))
    application.add_handler(CommandHandler("language", language_cmd))
    application.add_handler(CommandHandler("lang", language_cmd))
    application.add_handler(CommandHandler("setalbum", set_album_cmd))
    application.add_handler(CommandHandler("listalbums", list_albums_cmd))
    application.add_handler(CommandHandler("broadcast", broadcast_cmd))
    application.add_handler(CommandHandler("cancel", cancel_cmd))
    application.add_handler(CommandHandler("subscribe", subscribe_cmd))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe_cmd))
    application.add_handler(CommandHandler("export", export_cmd))

    # Admin
    application.add_handler(CommandHandler("editcode", edit_code_cmd))
    application.add_handler(CommandHandler("deletecode", delete_code_cmd))
    application.add_handler(CommandHandler("listcodes", list_codes_cmd))
    application.add_handler(CommandHandler("check_files", check_files_cmd))
    application.add_handler(CommandHandler("checkfiles", check_files_cmd))

    # Super Admin
    application.add_handler(CommandHandler("addadmin", add_admin_cmd))
    application.add_handler(CommandHandler("listadmins", list_admins_cmd))
    application.add_handler(CommandHandler("deleteadmin", delete_admin_cmd))
    application.add_handler(CommandHandler("promote", promote_cmd))
    application.add_handler(CommandHandler("demote", demote_cmd))
    application.add_handler(CommandHandler("backup", backup_data_cmd))

    # Inline
    application.add_handler(InlineQueryHandler(inline_query))

    # Callback
    application.add_handler(CallbackQueryHandler(handle_suggestions, pattern="^suggest_"))
    application.add_handler(CallbackQueryHandler(handle_update_decision, pattern="^update_"))
    application.add_handler(CallbackQueryHandler(handle_admin_actions, pattern="^admin_"))
    application.add_handler(CallbackQueryHandler(handle_similar, pattern="^similar:"))
    application.add_handler(CallbackQueryHandler(handle_language, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(handle_broadcast, pattern="^broadcast_"))
    application.add_handler(CallbackQueryHandler(handle_export, pattern="^export_"))

    # Guruh
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.TEXT & ~filters.COMMAND,
        handle_group_text
    ))
    application.add_handler(MessageHandler(
        filters.ChatType.GROUPS & filters.PHOTO,
        handle_group_photo
    ))

    # Private
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Mini App
    menu_url = MINI_APP_URL or "https://t.me/barkascolor_bot/app"
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="🎨 Mini App",
            web_app=WebAppInfo(url=menu_url)
        )
    )

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("✅ Bot ishga tushdi (Multi-language)...")


    # ===== Avtomatik file_id tekshiruv (har 24 soatda) =====
    from app.admin_commands import auto_check_files

    async def schedule_auto_check():
        await asyncio.sleep(3600)  # 1 soat kutadi
        while True:
            try:
                await auto_check_files(application.bot)
            except Exception as e:
                logger.error(f"Schedule xatosi: {e}")
            await asyncio.sleep(24 * 60 * 60)

    asyncio.create_task(schedule_auto_check())
    
    config = uvicorn.Config(app=fastapi_app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

    await application.stop()
    await application.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot to'xtatildi.")