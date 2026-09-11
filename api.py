# api.py - Mini App + API server (OPTIMALLASHTIRILGAN)
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import aiosqlite
import aiohttp
import os

# Config
DB_PATH = os.getenv("DB_PATH", "bot.db")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# .env dan BOT_TOKEN ni olish
if not BOT_TOKEN:
    from dotenv import load_dotenv
    load_dotenv()
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")

app = FastAPI(title="BarkasColor API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# TELEGRAM FILE URL OLISH
# ============================================

async def get_telegram_file_url(file_id: str) -> str:
    """Telegram file_id dan rasm URL olish"""
    if not file_id or not BOT_TOKEN:
        return None

    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                if not data.get("ok"):
                    return None
                file_path = data["result"]["file_path"]
            return f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    except Exception as e:
        print(f"Telegram file URL olishda xato: {e}")
        return None

# ============================================
# API ENDPOINTS
# ============================================

@app.get("/")
async def root():
    """Mini App sahifasini ochish"""
    return FileResponse("miniapp/index.html")

@app.get("/api/colors")
async def get_initial_state():
    """
    BOSHLANG'ICH HOLAT (OPTIMAL):
    Hamma rasmni yuklamaymiz! Faqat umumiy sonini qaytaramiz.
    Bu ilovani tez ochilishini ta'minlaydi.
    """
    async with aiosqlite.connect(DB_PATH) as db:
        # Faqat sonini sanaymiz (Juda tez ishlaydi)
        cursor = await db.execute("SELECT COUNT(*) FROM images")
        total = (await cursor.fetchone())[0]

    # colors ro'yxatini bo'sh qaytaramiz, frontend buni tushunadi
    return {"colors": [], "total": total}

@app.get("/api/colors/search")
async def search_colors(q: str = ""):
    """Ranglarni qidirish"""
    # Agar qidiruv so'zi juda qisqa bo'lsa, hech narsa qaytarmaymiz
    if not q or len(q) < 1:
        return {"colors": [], "total": 0}

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """SELECT code, file_id, dominant_hex, color_name FROM images
               WHERE code LIKE ? OR color_name LIKE ? OR dominant_hex LIKE ?
               ORDER BY code LIMIT 20""",
            (f"%{q}%", f"%{q}%", f"%{q}%")
        )
        rows = await cursor.fetchall()

    colors = []
    for row in rows:
        file_id = row[1]
        image_url = await get_telegram_file_url(file_id) if file_id else None

        colors.append({
            "code": row[0],
            "file_id": file_id,
            "image_url": image_url,
            "hex": row[2] or "#CCCCCC",
            "name": row[3] or "Noma'lum"
        })

    return {"colors": colors, "total": len(colors)}

@app.get("/api/colors/{code}")
async def get_color_by_code(code: str):
    """Kod bo'yicha rang olish"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT code, file_id, dominant_hex, color_name FROM images WHERE code = ?",
            (code,)
        )
        row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Kod topilmadi")

    file_id = row[1]
    image_url = await get_telegram_file_url(file_id) if file_id else None

    return {
        "code": row[0],
        "file_id": file_id,
        "image_url": image_url,
        "hex": row[2] or "#CCCCCC",
        "name": row[3] or "Noma'lum"
    }

# ============================================
# RUN SERVER
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
