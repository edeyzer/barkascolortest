# app/translations.py
TEXTS = {
    "uz": {
        "welcome": """🎨 <b>BarkasColor</b> ga xush kelibsiz!

Sochiq ranglarini tez va oson topish uchun yordamchi bot.

🔍 <b>Qanday foydalanish:</b>
Rang kodini yozing yoki pastdagi tugmalardan foydalaning.
Misol: <code>01-001</code>, <code>G-048</code>""",
        
        "help": """📘 <b>Yordam</b>

🎨 <b>BarkasColor</b> — Sochiq ranglari katalogi

<b>🔍 Rang qidirish:</b>
Kodni yozing yoki tugmalardan foydalaning.
Misol: <code>01-001</code>, <code>G-048</code>

<b>📜 Tarixim:</b>
Oxirgi qidirgan kodlaringizni ko‘rish

<b>💡 Qo‘shimcha:</b>
• Guruhda ham ishlaydi
• Bir nechta kodni vergul bilan yozing""",

        "history_empty": "📭 Siz hali hech narsa qidirmagansiz.",
        "history_title": "📜 <b>Oxirgi qidiruvlaringiz:</b>\n\n",
        "search_prompt": "Kodni yozing (masalan: 01-001):",
        "rate_limit": "⏳ Sekinroq — iltimos biroz kuting.",
        "language_changed_uz": "✅ Til o‘zgartirildi: O‘zbekcha",
        "language_changed_ru": "✅ Til o‘zgartirildi: Русский",
        "choose_language": "🌐 Tilni tanlang / Выберите язык:",
        "btn_search": "🔍 Kod qidirish",
        "btn_history": "📜 Tarixim",
        "btn_help": "ℹ️ Yordam",
        "btn_stats": "📊 Statistika",
        "btn_codes": "📋 Kodlar ro‘yxati",
        "btn_lang": "🌐 Til",
    },
    "ru": {
        "welcome": """🎨 Добро пожаловать в <b>BarkasColor</b>!

Бот-помощник для быстрого поиска цветов платков.

🔍 <b>Как пользоваться:</b>
Напишите код цвета или используйте кнопки ниже.
Пример: <code>01-001</code>, <code>G-048</code>""",
        
        "help": """📘 <b>Помощь</b>

🎨 <b>BarkasColor</b> — Каталог цветов платков

<b>🔍 Поиск цвета:</b>
Напишите код или используйте кнопки.
Пример: <code>01-001</code>, <code>G-048</code>

<b>📜 История:</b>
Ваши последние поиски

<b>💡 Дополнительно:</b>
• Работает и в группах
• Можно искать несколько кодов через запятую""",

        "history_empty": "📭 Вы ещё ничего не искали.",
        "history_title": "📜 <b>Ваши последние поиски:</b>\n\n",
        "search_prompt": "Напишите код (например: 01-001):",
        "rate_limit": "⏳ Помедленнее — пожалуйста, подождите.",
        "language_changed_uz": "✅ Язык изменён: O‘zbekcha",
        "language_changed_ru": "✅ Язык изменён: Русский",
        "choose_language": "🌐 Tilni tanlang / Выберите язык:",
        "btn_search": "🔍 Поиск кода",
        "btn_history": "📜 История",
        "btn_help": "ℹ️ Помощь",
        "btn_stats": "📊 Статистика",
        "btn_codes": "📋 Список кодов",
        "btn_lang": "🌐 Язык",
    }
}


def get_text(lang: str, key: str) -> str:
    return TEXTS.get(lang, TEXTS["uz"]).get(key, TEXTS["uz"].get(key, key))