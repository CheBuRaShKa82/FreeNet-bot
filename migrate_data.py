# migrate_data.py
import sqlite3
import psycopg2
import psycopg2.extras
import json
import logging
import os
from dotenv import load_dotenv

# --- Начальные настройки ---
# Загрузка переменных из файла .env
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Информация о подключении к базам данных ---
# SQLite (источник)
SQLITE_DB_PATH = os.getenv("DATABASE_NAME", "database/freenet_vpn.db")

# PostgreSQL (цель) - использование новых переменных
PG_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}

# Проверка наличия переменных PostgreSQL
if not all([PG_CONFIG["dbname"], PG_CONFIG["user"], PG_CONFIG["password"]]):
    logging.error("❌ Переменные PostgreSQL в файле .env не настроены!")
    logging.error("Пожалуйста, настройте DB_NAME, DB_USER и DB_PASSWORD в файле .env.")
    exit(1)

# Порядок таблиц для соблюдения зависимостей (Foreign Keys)
TABLES_IN_ORDER = [
    'users',
    'settings',
    'servers',
    'plans',
    'server_inbounds',
    'payment_gateways',
    'free_test_usage',
    'payments',
    'purchases',
    'tutorials'
]

def migrate_data():
    """
    Переносит данные из базы данных SQLite в PostgreSQL.
    """
    try:
        # Подключение к базе-источнику (SQLite)
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cur = sqlite_conn.cursor()
        logging.info(f"✅ Connected to source SQLite database: {SQLITE_DB_PATH}")

        # Подключение к базе-цели (PostgreSQL)
        pg_conn = psycopg2.connect(**PG_CONFIG)
        pg_cur = pg_conn.cursor()
        logging.info(f"✅ Connected to destination PostgreSQL database: {PG_CONFIG['dbname']}")

    except Exception as e:
        logging.error(f"❌ Database connection failed: {e}")
        return

    # Начало процесса миграции таблицы за таблицей
    for table_name in TABLES_IN_ORDER:
        try:
            logging.info(f"--- Starting migration for table: {table_name} ---")
            
            # 1. Чтение всех данных из таблицы источника
            sqlite_cur.execute(f"SELECT * FROM {table_name}")
            rows = sqlite_cur.fetchall()
            
            if not rows:
                logging.info(f"Table '{table_name}' is empty. Skipping.")
                continue

            # 2. Получение имён столбцов
            columns = [description[0] for description in sqlite_cur.description]
            
            # 3. Построение запроса INSERT для PostgreSQL
            placeholders = ', '.join(['%s'] * len(columns))
            pg_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"

            # 4. Преобразование данных в список кортежей для psycopg2
            data_to_insert = [tuple(row) for row in rows]
            
            # 5. Выполнение запроса со всеми данными сразу
            pg_cur.executemany(pg_query, data_to_insert)
            
            logging.info(f"✅ Migrated {len(rows)} rows to table '{table_name}'.")

        except Exception as e:
            logging.error(f"❌ FAILED to migrate table '{table_name}'. Error: {e}")
            logging.error("Rolling back all changes. Aborting migration.")
            pg_conn.rollback() # В случае ошибки в одной таблице, откат всех изменений
            return # Выход из процесса
            
    # Если все таблицы перенесены успешно, фиксируем изменения
    logging.info("\n🎉 All tables migrated successfully! Committing changes.")
    pg_conn.commit()

    # Сброс последовательностей для автоинкрементных ID
    try:
        logging.info("--- Resetting primary key sequences in PostgreSQL ---")
        for table in TABLES_IN_ORDER:
            # Эта команда выполняется только для таблиц с столбцом id
            pg_cur.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{table}' AND column_name = 'id'")
            if pg_cur.fetchone():
                # Устанавливаем последовательность на максимальное значение id
                pg_cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), COALESCE(MAX(id), 1)) FROM {table};")
        pg_conn.commit()
        logging.info("✅ Sequences reset successfully.")
    except Exception as e:
        logging.warning(f"⚠️ Could not reset sequences. This is usually not critical. Error: {e}")
        pg_conn.rollback()

    # Закрытие всех подключений
    sqlite_conn.close()
    pg_conn.close()
    logging.info("--- Migration process finished. ---")

if __name__ == "__main__":
    migrate_data()