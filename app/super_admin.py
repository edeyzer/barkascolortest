# app/super_admin.py - TO'LIQ
from telegram import Update
from telegram.ext import ContextTypes
from app.admin import is_super_admin
from app.database import fetchall, execute, fetchone
from config import DB_TYPE


# =========================================================
#  ADMIN QO'SHISH — /addadmin <id> yoki @username
# =========================================================
async def add_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_super_admin(user_id):
        await update.message.reply_text("❌ Faqat super adminlar yangi admin qo'shishi mumkin.")
        return
    
    if not context.args:
        await update.message.reply_text("⚠️ Foydalanish: /addadmin <ID yoki @username>")
        return
    
    target = context.args[0]
    try:
        if target.startswith("@"):
            chat = await context.bot.get_chat(target)
            target_id = chat.id
            username = target
        else:
            target_id = int(target)
            username = f"ID: {target_id}"
    except Exception:
        await update.message.reply_text("❌ Noto'g'ri foydalanuvchi ID yoki username.")
        return
    
    # Admin bazada bormi?
    q_check = "SELECT user_id FROM admins WHERE user_id = ?" if DB_TYPE == "sqlite" else \
              "SELECT user_id FROM admins WHERE user_id = $1"
    
    existing = await fetchone(q_check, target_id)
    if existing:
        await update.message.reply_text("⚠️ Bu foydalanuvchi allaqachon admin.")
        return
    
    # Yangi admin qo'shish
    q_insert = "INSERT INTO admins (user_id, is_super) VALUES (?, ?)" if DB_TYPE == "sqlite" else \
               "INSERT INTO admins (user_id, is_super) VALUES ($1, $2)"
    
    await execute(q_insert, target_id, 0)
    await update.message.reply_text(f"✅ {username} admin sifatida qo'shildi.")


# =========================================================
#  ADMINLAR RO'YXATI — /listadmins
# =========================================================
async def list_admins_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not await is_super_admin(user_id):
        await update.message.reply_text("❌ Faqat super adminlar adminlar ro'yxatini ko'rishi mumkin.")
        return
    
    q = "SELECT user_id, is_super FROM admins ORDER BY is_super DESC, user_id"
    
    rows = await fetchall(q)
    if not rows:
        await update.message.reply_text("📝 Hozircha adminlar mavjud emas.")
        return
    
    admins_list = []
    for row in rows:
        uid = row[0] if isinstance(row, tuple) else row.get("user_id")
        is_super = row[1] if isinstance(row, tuple) else row.get("is_super")
        role = "👑 Super Admin" if is_super else "👤 Admin"
        admins_list.append(f"{role}: `{uid}`")
    
    admins_text = "\n".join(admins_list)
    await update.message.reply_text(f"📋 Adminlar ro'yxati:\n\n{admins_text}", parse_mode="Markdown")


# =========================================================
#  /deleteadmin — Adminni o'chirish
# =========================================================
async def delete_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_super_admin(user_id):
        await update.message.reply_text("❌ Siz super admin emassiz.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Foydalanish: /deleteadmin <admin_id>")
        return

    try:
        target_id = int(context.args[0])
    except:
        await update.message.reply_text("❌ Admin ID raqam bo'lishi kerak.")
        return

    # O'zini o'chirib tashlashdan saqlash
    if target_id == user_id:
        await update.message.reply_text("❌ O'zingizni o'chirib yubora olmaysiz.")
        return

    # Admin mavjudligini tekshirish
    q_check = "SELECT user_id FROM admins WHERE user_id = ?" if DB_TYPE == "sqlite" else \
              "SELECT user_id FROM admins WHERE user_id = $1"

    row = await fetchone(q_check, target_id)
    if not row:
        await update.message.reply_text("❌ Bunday admin mavjud emas.")
        return

    # O'chirish
    q_delete = "DELETE FROM admins WHERE user_id = ?" if DB_TYPE == "sqlite" else \
               "DELETE FROM admins WHERE user_id = $1"

    await execute(q_delete, target_id)
    await update.message.reply_text(f"🗑 Admin o'chirildi: `{target_id}`", parse_mode="Markdown")


# =========================================================
#  /promote — Oddiy user → Admin
# =========================================================
async def promote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_super_admin(user_id):
        await update.message.reply_text("❌ Siz super admin emassiz.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Foydalanish: /promote <user_id>")
        return

    try:
        target_id = int(context.args[0])
    except:
        await update.message.reply_text("❌ user_id raqam bo'lishi kerak.")
        return

    # Admin bo'lgan-bo'lmaganini tekshirish
    q_check = "SELECT user_id FROM admins WHERE user_id = ?" if DB_TYPE == "sqlite" else \
              "SELECT user_id FROM admins WHERE user_id = $1"

    exists = await fetchone(q_check, target_id)

    if exists:
        await update.message.reply_text("⚠️ Bu user allaqachon admin.")
        return

    # Admin qilish
    q_insert = "INSERT INTO admins (user_id, is_super) VALUES (?, ?)" if DB_TYPE == "sqlite" else \
               "INSERT INTO admins (user_id, is_super) VALUES ($1, $2)"

    await execute(q_insert, target_id, 0)
    await update.message.reply_text(f"🔼 Foydalanuvchi admin qilindi: `{target_id}`", parse_mode="Markdown")


# =========================================================
#  /demote — Admin → Oddiy user
# =========================================================
async def demote_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not await is_super_admin(user_id):
        await update.message.reply_text("❌ Siz super admin emassiz.")
        return

    if not context.args:
        await update.message.reply_text("⚠️ Foydalanish: /demote <admin_id>")
        return

    try:
        target_id = int(context.args[0])
    except:
        await update.message.reply_text("❌ admin_id raqam bo'lishi kerak.")
        return

    # O'zini pasaytirmaslik
    if target_id == user_id:
        await update.message.reply_text("❌ O'zingizni demote qila olmaysiz.")
        return

    # Admin mavjudligini tekshirish
    q_check = "SELECT user_id, is_super FROM admins WHERE user_id = ?" if DB_TYPE == "sqlite" else \
              "SELECT user_id, is_super FROM admins WHERE user_id = $1"

    row = await fetchone(q_check, target_id)

    if not row:
        await update.message.reply_text("❌ Bu user admin emas.")
        return

    # Super adminni oddiy admin qilib bo'lmaydi
    is_super_flag = row[1] if isinstance(row, tuple) else row["is_super"]
    if is_super_flag == 1:
        await update.message.reply_text("❌ Super adminni demote qilib bo'lmaydi.")
        return

    # Adminlikdan tushirish
    q_delete = "DELETE FROM admins WHERE user_id = ?" if DB_TYPE == "sqlite" else \
               "DELETE FROM admins WHERE user_id = $1"

    await execute(q_delete, target_id)
    await update.message.reply_text(f"🔽 Adminlikdan tushirildi: `{target_id}`", parse_mode="Markdown")
