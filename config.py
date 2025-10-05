# config.py (Финальная версия с продвинутой отладкой)

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv

# =============================================================================
# SECTION: Продвинутая отладка файла .env
# =============================================================================
print("\n--- Начало отладки файла .env ---")
env_path = Path(__file__).parent.resolve() / '.env'
print(f"1. Ожидаемый абсолютный путь для файла .env:\n   {env_path}")

# --- Проверка шага 1: Существует ли файл? ---
if not env_path.exists():
    print("\n2. ❌ Результат: Неудача!")
    print("   Причина: Файл .env не существует по указанному пути.")
    print("   Решение: Убедитесь, что файл с точным именем '.env' (с точкой в начале) находится в корневой папке проекта.")
    sys.exit(1) # Выход из программы
print("2. ✅ Результат: Файл .env найден.")

# --- Проверка шага 2: Является ли это файлом (а не папкой)? ---
if not env_path.is_file():
    print("\n3. ❌ Результат: Неудача!")
    print("   Причина: Найденный путь не является файлом, а является папкой.")
    sys.exit(1) # Выход из программы
print("3. ✅ Результат: Найденный путь является файлом.")

# --- Проверка шага 3: Является ли файл читаемым и содержит ли данные? ---
try:
    content = env_path.read_text(encoding='utf-8')
    if not content.strip():
        print("\n4. ❌ Результат: Неудача!")
        print("   Причина: Файл .env пуст.")
        sys.exit(1) # Выход из программы
    print("4. ✅ Результат: Файл .env читаем и содержит данные.")
    print("\n--- Содержимое, прочитанное из файла .env ---")
    print(content)
    print("--------------------------------------\n")
except Exception as e:
    print(f"\n4. ❌ Результат: Неудача!")
    print(f"   Причина: Произошла ошибка при чтении файла: {e}")
    print("   Решение: Проверьте права доступа к файлу (Permissions). Также убедитесь, что файл сохранён в кодировке UTF-8.")
    sys.exit(1) # Выход из программы

# =============================================================================
# SECTION: Загрузка и обработка переменных
# =============================================================================
# Теперь, когда мы уверены в наличии файла, загружаем его
load_dotenv(dotenv_path=env_path, override=True)

print("✅ Переменные из файла .env загружены. Обработка...")

# Настройки Telegram-бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Умный и надёжный код для чтения ID администраторов
admin_ids_str = os.getenv("ADMIN_IDS", "")
try:
    ADMIN_IDS = [int(s) for s in re.findall(r'\d+', admin_ids_str)]
except Exception as e:
    print(f"Warning: Could not parse admin IDs from '{admin_ids_str}': {e}")
    ADMIN_IDS = []

# Настройки базы данных
DB_TYPE = os.getenv("DB_TYPE", "sqlite")

if DB_TYPE == "postgres":
    # Чтение новых переменных для PostgreSQL
    DB_NAME = os.getenv("DB_NAME")
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DATABASE_NAME = None  # Не используется для PostgreSQL
else:
    # Старая логика для SQLite (для совместимости в будущем)
    DATABASE_NAME = os.getenv("DATABASE_NAME", "database/freenet_vpn.db")
    DB_NAME = None
    DB_USER = None
    DB_PASSWORD = None
    DB_HOST = None
    DB_PORT = None

# Настройки шифрования
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Проверка наличия критических переменных
if not BOT_TOKEN or not ADMIN_IDS or not ENCRYPTION_KEY:
    print("="*60)
    print("❌ Критическая ошибка: Одна или несколько основных переменных (BOT_TOKEN, ADMIN_IDS, ENCRYPTION_KEY) не найдены в файле .env или имеют пустое значение.")
    print("Пожалуйста, проверьте содержимое файла .env, которое было напечатано выше.")
    print("="*60)
    sys.exit(1)

print(f"✅ Обнаруженные администраторы: {ADMIN_IDS}")

# --- Дополнительные настройки ---
SUPPORT_CHANNEL_LINK = os.getenv("SUPPORT_CHANNEL_LINK", "https://t.me/YourSupportChannel")
REQUIRED_CHANNEL_ID_STR = os.getenv("REQUIRED_CHANNEL_ID")
REQUIRED_CHANNEL_ID = int(REQUIRED_CHANNEL_ID_STR) if REQUIRED_CHANNEL_ID_STR and REQUIRED_CHANNEL_ID_STR.lstrip('-').isdigit() else None
REQUIRED_CHANNEL_LINK = os.getenv("REQUIRED_CHANNEL_LINK", "https://t.me/YourChannelLink")
MAX_API_RETRIES = 3
# Настройки платёжного шлюза
WEBHOOK_DOMAIN = os.getenv("WEBHOOK_DOMAIN")
ZARINPAL_MERCHANT_ID = os.getenv("ZARINPAL_MERCHANT_ID")
ZARINPAL_SANDBOX = os.getenv("ZARINPAL_SANDBOX", "False").lower() in ['true', '1', 't']
BOT_USERNAME = os.getenv("BOT_USERNAME", "YourBotUsername")