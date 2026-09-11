# app/stats.py - 3-BOSQICH (Statistika)
from app.database import fetchone, fetchall
from config import DB_TYPE

async def get_stats():
    """Bot statistikasini olish"""
    
    # Asosiy sonlar
    images_count = await fetchone("SELECT COUNT(*) FROM images")
    admins_count = await fetchone("SELECT COUNT(*) FROM admins")
    
    # Eng ko‘p qidirilgan 10 ta kod
    top_codes = await fetchall(
        "SELECT code, search_count FROM images WHERE search_count > 0 ORDER BY search_count DESC LIMIT 10"
    )
    
    # Jami qidiruvlar soni
    total_searches = await fetchone("SELECT COALESCE(SUM(search_count), 0) FROM images")
    
    return {
        "images": images_count[0] if images_count else 0,
        "admins": admins_count[0] if admins_count else 0,
        "total_searches": total_searches[0] if total_searches else 0,
        "top_codes": top_codes or []
    }