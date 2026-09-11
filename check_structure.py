import os

# Loyihaning asosiy tuzilmasi
REQUIRED_STRUCTURE = {
    "root_files": ["bot.py", "config.py", ".env", "requirements.txt"],
    "folders": {
        "app": [
            "__init__.py",
            "admin.py",
            "callbacks.py",
            "codes.py",
            "database.py",
            "general.py",
            "handlers.py",
            "utils.py",
        ],
        "data": [
            "logs"
        ]
    }
}

def check_files(base_path):
    print("🔍 Loyiha tuzilmasi tekshirilmoqda...\n")

    # Root fayllarni tekshirish
    print("📁 Asosiy fayllar:")
    for file in REQUIRED_STRUCTURE["root_files"]:
        path = os.path.join(base_path, file)
        if os.path.exists(path):
            print(f"✅ {file} — mavjud")
        else:
            print(f"❌ {file} — topilmadi")

    print("\n📂 Papkalar ichidagi fayllar:")

    # app/ ichidagi fayllar
    app_path = os.path.join(base_path, "app")
    if not os.path.exists(app_path):
        print("❌ app/ papkasi yo‘q!")
    else:
        for file in REQUIRED_STRUCTURE["folders"]["app"]:
            path = os.path.join(app_path, file)
            if os.path.exists(path):
                print(f"   ✅ app/{file} — mavjud")
            else:
                print(f"   ❌ app/{file} — topilmadi")

    # data/logs papkasi
    data_path = os.path.join(base_path, "data")
    if not os.path.exists(data_path):
        print("\n❌ data/ papkasi yo‘q!")
    else:
        logs_path = os.path.join(data_path, "logs")
        if os.path.exists(logs_path):
            print("   ✅ data/logs/ mavjud")
        else:
            print("   ❌ data/logs/ topilmadi")

    print("\n✅ Tekshiruv yakunlandi.")
    print("Agar ❌ belgilar chiqsa, tegishli fayl yoki papkani yaratishni unutmang!")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    check_files(base_dir)
