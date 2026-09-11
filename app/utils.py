# app/utils.py - Multi-language qo‘llab-quvvatlash bilan
import os
import re
import logging
import time
from rapidfuzz import fuzz
from app.database import fetchall, fetchone, execute
from config import DB_TYPE
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from telegram import Bot 

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

_user_last_time = {}

def check_rate_limit(user_id: int, delay: float = 1.0) -> bool:
    now = time.time()
    last = _user_last_time.get(user_id, 0)
    if now - last < delay:
        return False
    _user_last_time[user_id] = now
    return True


def normalize_code(code: str) -> str:
    return code.strip().lower()


def validate_code_format(code: str) -> bool:
    return len(code.strip()) >= 1


async def get_similar_codes(user_code: str, limit: int = 3):
    q = "SELECT code FROM images"
    rows = await fetchall(q)
    if not rows:
        return []

    codes = [r[0] if isinstance(r, tuple) else r.get("code") for r in rows]
    user_norm = normalize_code(user_code)

    scored = []
    for c in codes:
        score = fuzz.ratio(user_norm, normalize_code(c))
        scored.append((c, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = [code for code, score in scored if score >= 40][:limit]
    return top


async def get_color_name(hex_color: str) -> str:
    if not hex_color:
        return "Noma'lum"
    
    try:
        hex_color = hex_color.lstrip('#').upper()
        if len(hex_color) != 6:
            return "Rang"
            
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        max_c = max(r, g, b)
        min_c = min(r, g, b)
        diff = max_c - min_c
        
        if diff < 30:
            if max_c > 220:
                return "Oq"
            elif max_c < 40:
                return "Qora"
            elif max_c > 160:
                return "Och kulrang"
            else:
                return "Kulrang"
        
        if r == max_c:
            if g > 180 and b < 100:
                return "Sariq"
            elif g > 140 and b < 80:
                return "Oltin / Sariq"
            elif b > 150:
                return "Pushti / Binafsha"
            elif g > 100:
                return "To'q sariq / Xavorang"
            else:
                return "Qizil"
                
        elif g == max_c:
            if r > 150 and b < 100:
                return "Sariq-yashil"
            elif b > 150:
                return "Moviy-yashil"
            else:
                return "Yashil"
                
        else:
            if r > 150 and g < 100:
                return "Binafsha"
            elif g > 150:
                return "Moviy"
            else:
                return "Ko'k"
                
    except Exception:
        return "Rang"


async def get_user_lang(user_id: int) -> str:
    try:
        if DB_TYPE == "sqlite":
            row = await fetchone("SELECT language FROM users WHERE user_id = ?", user_id)
        else:
            row = await fetchone("SELECT language FROM users WHERE user_id = $1", user_id)
        
        if row:
            return row[0] if isinstance(row, tuple) else row.get("language", "uz")
    except Exception:
        pass
    return "uz"


async def set_user_lang(user_id: int, lang: str):
    try:
        if DB_TYPE == "sqlite":
            await execute(
                "INSERT INTO users (user_id, language) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET language = excluded.language",
                user_id, lang
            )
        else:
            await execute(
                "INSERT INTO users (user_id, language) VALUES ($1, $2) "
                "ON CONFLICT (user_id) DO UPDATE SET language = $2",
                user_id, lang
            )
    except Exception as e:
        logger.error(f"set_user_lang xato: {e}")


async def add_watermark(bot: Bot, file_id: str, text: str = "@Barkascolor_bot") -> BytesIO:
    """
    Telegram file_id dan rasmni olib, watermark qo‘yib BytesIO qaytaradi
    """
    try:
        # Rasmni yuklab olish
        file = await bot.get_file(file_id)
        bio = BytesIO()
        await file.download_to_memory(bio)
        bio.seek(0)

        # Rasmni ochish
        img = Image.open(bio).convert("RGBA")
        width, height = img.size

        # Shaffof qatlam
        txt_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        # Shrift (agar tizimda bo‘lmasa default ishlatiladi)
        try:
            font_size = 16
            font = ImageFont.truetype("arial.ttf", font_size)
        except:
            font = ImageFont.load_default()

        # Matn o‘lchami
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Pastki o‘ng burchak
        x = width - text_width - 20
        y = height - text_height - 20

        # Soyali yozuv (o‘qilishi oson bo‘lishi uchun)
        draw.text((x+2, y+2), text, font=font, fill=(0, 0, 0, 160))
        draw.text((x, y), text, font=font, fill=(255, 255, 255, 200))

        # Birlashtirish
        watermarked = Image.alpha_composite(img, txt_layer)
        watermarked = watermarked.convert("RGB")

        output = BytesIO()
        watermarked.save(output, format="JPEG", quality=92)
        output.seek(0)
        output.name = "color.jpg"
        return output

    except Exception as e:
        logger.error(f"Watermark xatosi: {e}")
        return None







