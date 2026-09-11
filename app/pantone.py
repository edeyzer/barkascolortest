# app/pantone.py - Rasmiy Pantone TCX bazasi bo'yicha rang qidirish
import json
import logging
import os

logger = logging.getLogger(__name__)

# Pantone bazasi odatda loyihaning data/ papkasida joylashishi kerak, lekin
# ba'zan tasodifan tub papkaga qo'yib qo'yilishi mumkin — shu sabab bir nechta
# joydan qidiramiz, birinchi topilgani ishlatiladi. Bu xato joylashuv botni
# butunlay "hech narsa topa olmaydigan" holatga tushirib qo'ymasligi uchun.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_APP_DIR, ".."))

_CANDIDATE_PATHS = [
    os.path.join(_PROJECT_ROOT, "data", "pantone_tcx.json"),  # tavsiya etilgan joy
    os.path.join(_PROJECT_ROOT, "pantone_tcx.json"),           # loyiha tub papkasi
    os.path.join(_APP_DIR, "pantone_tcx.json"),                 # app/ papkasi ichida
]

DATA_FILE = next((p for p in _CANDIDATE_PATHS if os.path.exists(p)), _CANDIDATE_PATHS[0])

_pantone_db = []


def _normalize_tcx(code: str) -> str:
    """Kod taqqoslash uchun: chiziqcha/bo'shliqlarni olib tashlab, kichik harfga o'tkazadi."""
    return (code or "").strip().lower().replace("-", "").replace(" ", "").replace("_", "")


def load_pantone_db() -> None:
    """Pantone TCX bazasini diskdan yuklaydi. Xato bo'lsa, bot yiqilmaydi — bo'sh baza bilan davom etadi."""
    global _pantone_db

    if not os.path.exists(DATA_FILE):
        logger.warning(f"⚠️ Pantone bazasi topilmadi: {DATA_FILE} — Pantone qidiruvi o'chirilgan bo'ladi.")
        _pantone_db = []
        return

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        db = []
        for item in raw_data:
            name = str(item.get("name") or "").strip()
            hex_code = str(item.get("hex") or "").strip()
            tcx = str(item.get("tcx") or "").strip()

            if name and tcx:
                db.append({
                    "name": name,
                    "tcx": tcx,
                    "hex": hex_code if hex_code.startswith("#") else f"#{hex_code}"
                })

        _pantone_db = db
        logger.info(f"✅ Pantone TCX bazasi yuklandi: {len(_pantone_db)} ta rasmiy rang")

    except Exception as e:
        logger.error(f"❌ Pantone bazasini yuklashda xatolik: {e}")
        _pantone_db = []


# Modul import qilinganda bir marta yuklanadi
load_pantone_db()


def find_by_tcx(code: str):
    """TCX kod bo'yicha aniq moslikni qidiradi ('11-4201', '114201', '11 4201' — barchasi bir xil natija beradi)."""
    if not code:
        return None
    target = _normalize_tcx(code)
    if not target:
        return None
    for item in _pantone_db:
        if _normalize_tcx(item["tcx"]) == target:
            return item
    return None


def find_by_name(query: str, limit: int = 5):
    """Rang nomi bo'yicha qidiradi. Avval aniq moslik, topilmasa qisman moslik qaytariladi."""
    if not query or len(query.strip()) < 2:
        return []

    q = query.strip().lower()

    exact = [it for it in _pantone_db if it["name"].lower() == q]
    if exact:
        return exact

    partial = [it for it in _pantone_db if q in it["name"].lower()]
    return partial[:limit]


def find_match(query: str, allow_partial: bool = True):
    """
    TCX kod va rang nomi bo'yicha eng mos Pantone rangini qidiradi.
    allow_partial=False bo'lsa, faqat aniq (to'liq) nom moslashuvi qabul qilinadi —
    bu bir nechta so'zga bo'lingan alohida bo'laklarni (masalan "Cloud" so'zini
    "Cloud Dancer" nomiga) noto'g'ri moslashtirib yubormaslik uchun ishlatiladi.
    Qaytaradi: (topilgan_element_yoki_None, jami_mos_natijalar_soni)
    """
    match = find_by_tcx(query)
    if match:
        return match, 1

    if allow_partial:
        matches = find_by_name(query)
    else:
        q = (query or "").strip().lower()
        matches = [it for it in _pantone_db if it["name"].lower() == q] if q else []

    if matches:
        return matches[0], len(matches)

    return None, 0


def build_caption(item: dict, extra_count: int = 0) -> str:
    """Pantone rangi uchun xabar matnini tayyorlaydi."""
    caption = (
        f"🎨 Pantone TCX\n"
        f"📌 Kod: `{item['tcx']}`\n"
        f"🏷 Nomi: {item['name']}\n"
        f"♯ HEX: `{item['hex']}`"
    )
    if extra_count > 1:
        caption += f"\n\nℹ️ Yana {extra_count - 1} ta mos natija bor, aniqroq nom yozing."
    return caption