# migrate.py

import logging
import os
from dotenv import load_dotenv
from database.db_manager import DatabaseManager

# Загрузка переменных окружения
load_dotenv()

# Начальные настройки для отображения логов в терминале
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_migrations():
    """
    Выполняет скрипт для применения изменений схемы базы данных. Этот скрипт спроектирован так, что многократное выполнение не вызывает проблем.
    """
    logging.info("Starting database migration script...")
    
    db_type = os.getenv("DB_TYPE", "sqlite")
    logging.info(f"Database type: {db_type}")
    
    db_manager = DatabaseManager()
    conn = None
    
    try:
        conn = db_manager._get_connection()
        
        if db_type == "postgres":
            logging.info("Successfully connected to the PostgreSQL database.")
            
            # Список команд SQL для PostgreSQL
            migrations = [
                """
                ALTER TABLE server_inbounds 
                ADD COLUMN IF NOT EXISTS config_params JSONB;
                """,
                """
                ALTER TABLE profile_inbounds 
                ADD COLUMN IF NOT EXISTS config_params JSONB;
                """
            ]
        else:
            logging.info("Successfully connected to the SQLite database.")
            
            # Список команд SQL для SQLite
            migrations = [
                """
                ALTER TABLE server_inbounds 
                ADD COLUMN config_params TEXT;
                """,
                """
                ALTER TABLE profile_inbounds 
                ADD COLUMN config_params TEXT;
                """
            ]
        
        with conn.cursor() as cur:
            for i, migration_sql in enumerate(migrations, 1):
                try:
                    logging.info(f"Applying migration #{i}...")
                    cur.execute(migration_sql)
                    logging.info(f"Migration #{i} applied successfully.")
                except Exception as e:
                    # В SQLite, если столбец уже существует, выдаёт ошибку
                    if db_type == "sqlite" and "duplicate column name" in str(e).lower():
                        logging.info(f"Column already exists in SQLite. Skipping migration #{i}.")
                    else:
                        logging.error(f"Error applying migration #{i}: {e}")
                        # В случае ошибки, откатываем изменения
                        if db_type == "postgres":
                            conn.rollback()
                        return

        # Если все команды выполнены успешно, фиксируем изменения
        if db_type == "postgres":
            conn.commit()
        else:
            conn.commit()
        logging.info("All migrations completed successfully!")
        
    except Exception as e:
        logging.error(f"A critical error occurred during the migration process: {e}")
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")

if __name__ == "__main__":
    run_migrations()