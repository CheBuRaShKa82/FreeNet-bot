#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт полного переноса из SQLite в PostgreSQL. Этот скрипт переносит все данные из базы данных SQLite в PostgreSQL.
"""

import sqlite3
import psycopg2
import psycopg2.extras
import json
import logging
import os
import sys
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройки логов
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('migration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

def check_environment():
    """Проверка настроек окружения"""
    logging.info("🔍 Checking environment configuration...")
    
    # Проверка типа базы данных
    db_type = os.getenv("DB_TYPE", "sqlite")
    if db_type != "postgres":
        logging.error("❌ DB_TYPE must be set to 'postgres' for migration")
        return False
    
    # Проверка переменных PostgreSQL
    pg_vars = {
        "DB_NAME": os.getenv("DB_NAME"),
        "DB_USER": os.getenv("DB_USER"),
        "DB_PASSWORD": os.getenv("DB_PASSWORD"),
        "DB_HOST": os.getenv("DB_HOST", "localhost"),
        "DB_PORT": os.getenv("DB_PORT", "5432")
    }
    
    missing_vars = [k for k, v in pg_vars.items() if not v]
    if missing_vars:
        logging.error(f"❌ Missing PostgreSQL environment variables: {', '.join(missing_vars)}")
        return False
    
    # Проверка наличия файла SQLite
    sqlite_path = os.getenv("DATABASE_NAME", "database/freenet_vpn.db")
    if not os.path.exists(sqlite_path):
        logging.error(f"❌ SQLite database file not found: {sqlite_path}")
        return False
    
    logging.info("✅ Environment configuration is valid")
    return True

def test_connections():
    """Тестирование подключения к обеим базам данных"""
    logging.info("🔌 Testing database connections...")
    
    # Тестирование подключения SQLite
    sqlite_path = os.getenv("DATABASE_NAME", "database/freenet_vpn.db")
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        sqlite_conn.close()
        logging.info("✅ SQLite connection successful")
    except Exception as e:
        logging.error(f"❌ SQLite connection failed: {e}")
        return False
    
    # Тестирование подключения PostgreSQL
    pg_config = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432")
    }
    
    try:
        pg_conn = psycopg2.connect(**pg_config)
        pg_conn.close()
        logging.info("✅ PostgreSQL connection successful")
    except Exception as e:
        logging.error(f"❌ PostgreSQL connection failed: {e}")
        return False
    
    return True

def get_table_info(sqlite_conn):
    """Получение информации о таблицах SQLite"""
    cursor = sqlite_conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    table_info = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        table_info[table] = [col[1] for col in columns]  # Имена столбцов
    
    return table_info

def migrate_table(sqlite_conn, pg_conn, table_name, columns):
    """Перенос одной таблицы"""
    logging.info(f"📦 Migrating table: {table_name}")
    
    try:
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            logging.info(f"   ℹ️ Table '{table_name}' is empty. Skipping.")
            return True
        
        pg_cursor = pg_conn.cursor()
        placeholders = ', '.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
        
        data = [tuple(row) for row in rows]
        pg_cursor.executemany(insert_query, data)
        
        logging.info(f"   ✅ Migrated {len(rows)} rows to '{table_name}'")
        return True
        
    except Exception as e:
        logging.error(f"   ❌ Failed to migrate '{table_name}': {e}")
        return False

def reset_sequences(pg_conn, tables):
    """Сброс последовательностей"""
    logging.info("🔄 Resetting PostgreSQL sequences...")
    
    pg_cursor = pg_conn.cursor()
    for table in tables:
        try:
            # Проверка наличия столбца id
            pg_cursor.execute(f"""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = '{table}' AND column_name = 'id'
            """)
            if pg_cursor.fetchone():
                pg_cursor.execute(f"""
                    SELECT setval(pg_get_serial_sequence('{table}', 'id'), 
                    COALESCE(MAX(id), 1)) FROM {table}
                """)
                logging.info(f"   ✅ Reset sequence for '{table}'")
        except Exception as e:
            logging.warning(f"   ⚠️ Could not reset sequence for '{table}': {e}")

def main():
    """Основная функция переноса"""
    logging.info("🚀 Starting SQLite to PostgreSQL migration...")
    
    # Проверка окружения
    if not check_environment():
        sys.exit(1)
    
    # Тестирование подключений
    if not test_connections():
        sys.exit(1)
    
    # Подключение к базам данных
    sqlite_path = os.getenv("DATABASE_NAME", "database/freenet_vpn.db")
    pg_config = {
        "dbname": os.getenv("DB_NAME"),
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432")
    }
    
    try:
        sqlite_conn = sqlite3.connect(sqlite_path)
        pg_conn = psycopg2.connect(**pg_config)
        
        # Получение информации о таблицах
        table_info = get_table_info(sqlite_conn)
        logging.info(f"📋 Found {len(table_info)} tables in SQLite")
        
        # Порядок миграции (для соблюдения foreign keys)
        migration_order = [
            'users', 'settings', 'servers', 'plans', 'server_inbounds',
            'payment_gateways', 'free_test_usage', 'payments', 'purchases', 'tutorials'
        ]
        
        # Фильтрация существующих таблиц
        tables_to_migrate = [t for t in migration_order if t in table_info]
        
        # Начало миграции
        success_count = 0
        for table in tables_to_migrate:
            if migrate_table(sqlite_conn, pg_conn, table, table_info[table]):
                success_count += 1
            else:
                logging.error(f"❌ Migration failed for table '{table}', rolling back...")
                pg_conn.rollback()
                break
        
        if success_count == len(tables_to_migrate):
            # Сброс последовательностей
            reset_sequences(pg_conn, tables_to_migrate)
            
            # Фиксация изменений
            pg_conn.commit()
            logging.info("🎉 Migration completed successfully!")
            logging.info(f"📊 Migrated {success_count}/{len(tables_to_migrate)} tables")
        else:
            logging.error("❌ Migration failed!")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"❌ Critical error during migration: {e}")
        sys.exit(1)
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        if 'pg_conn' in locals():
            pg_conn.close()
        logging.info("🔌 Database connections closed")

if __name__ == "__main__":
    main()