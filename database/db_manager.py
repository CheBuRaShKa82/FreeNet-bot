# database/db_manager.py

import psycopg2
import psycopg2.extras
import logging
from cryptography.fernet import Fernet
import os
import json
import sqlite3
from config import ENCRYPTION_KEY, DB_TYPE, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DATABASE_NAME

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.db_type = DB_TYPE
        if self.db_type == "postgres":
            self.db_name = DB_NAME
            self.db_user = DB_USER
            self.db_password = DB_PASSWORD
            self.db_host = DB_HOST
            self.db_port = DB_PORT
            logger.info(f"DatabaseManager initialized for PostgreSQL DB: {self.db_name}")
        else:
            self.db_path = DATABASE_NAME
            logger.info(f"DatabaseManager initialized for SQLite DB: {self.db_path}")
        
        self.fernet = Fernet(ENCRYPTION_KEY.encode('utf-8'))

    def _get_connection(self):
        """Establishes a new connection to the database."""
        if self.db_type == "postgres":
            return psycopg2.connect(
                dbname=self.db_name, user=self.db_user, password=self.db_password,
                host=self.db_host, port=self.db_port
            )
        else:
            return sqlite3.connect(self.db_path)

    def _encrypt(self, data: str) -> str:
        if data is None: return None
        return self.fernet.encrypt(data.encode('utf-8')).decode('utf-8')

    def _decrypt(self, encrypted_data: str) -> str:
        if encrypted_data is None: return None
        return self.fernet.decrypt(encrypted_data.encode('utf-8')).decode('utf-8')

    def create_tables(self):
        """
        Создаёт необходимые таблицы в правильном порядке зависимостей в базе данных PostgreSQL. (Финальная и полная версия)
        """
        # --- список полных инструкций по созданию таблиц в правильном порядке ---
        commands = [
            # --- Раздел 1: Базовые таблицы (без зависимости от других таблиц проекта) ---
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                is_admin BOOLEAN DEFAULT FALSE, 
                join_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS servers (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                panel_type TEXT NOT NULL DEFAULT 'x-ui',
                panel_url TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                subscription_base_url TEXT NOT NULL,
                subscription_path_prefix TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                last_checked TIMESTAMPTZ,
                is_online BOOLEAN DEFAULT FALSE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS plans (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                plan_type TEXT NOT NULL,
                volume_gb REAL,
                duration_days INTEGER,
                price REAL,
                per_gb_price REAL,
                is_active BOOLEAN DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS tutorials (
                id SERIAL PRIMARY KEY,
                platform TEXT NOT NULL,
                app_name TEXT NOT NULL,
                forward_chat_id BIGINT NOT NULL,
                forward_message_id BIGINT NOT NULL,
                UNIQUE (platform, app_name)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                per_gb_price REAL NOT NULL,
                duration_days INTEGER NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS subscription_domains (
                id SERIAL PRIMARY KEY,
                domain_name TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS payment_gateways (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL,
                card_number TEXT,
                card_holder_name TEXT,
                merchant_id TEXT,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                priority INTEGER DEFAULT 0
            )
            """,
            # --- Раздел 2: Зависимые таблицы (с Foreign Key на базовые таблицы) ---
            """
            CREATE TABLE IF NOT EXISTS synced_configs (
                id SERIAL PRIMARY KEY,
                server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
                inbound_id INTEGER NOT NULL,
                remark TEXT,
                port INTEGER,
                protocol TEXT,
                settings TEXT,
                stream_settings TEXT,
                UNIQUE (server_id, inbound_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS server_inbounds (
                id SERIAL PRIMARY KEY,
                server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
                inbound_id INTEGER NOT NULL,
                remark TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                UNIQUE (server_id, inbound_id)
            )
            CREATE TABLE IF NOT EXISTS profile_inbounds (
                id SERIAL PRIMARY KEY,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
                inbound_id INTEGER NOT NULL,
                UNIQUE (profile_id, server_id, inbound_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                server_id INTEGER NOT NULL REFERENCES servers(id) ON DELETE CASCADE,
                plan_id INTEGER REFERENCES plans(id) ON DELETE SET NULL,
                profile_id INTEGER REFERENCES profiles(id) ON DELETE SET NULL,
                purchase_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                expire_date TIMESTAMPTZ,
                initial_volume_gb REAL NOT NULL,
                client_uuid TEXT,
                client_email TEXT,
                sub_id TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                single_configs_json TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS free_test_usage (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                usage_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                amount REAL NOT NULL,
                payment_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                receipt_message_id BIGINT,
                is_confirmed BOOLEAN DEFAULT FALSE,
                admin_confirmed_by BIGINT,
                confirmation_date TIMESTAMPTZ,
                order_details_json TEXT,
                admin_notification_message_id BIGINT,
                authority TEXT,
                ref_id TEXT
            )
            """
        ]
        
        conn = None
        try:
            conn = self._get_connection()
            with conn.cursor() as cur:
                logger.info("Dropping potentially outdated tables (purchases, payments) to ensure schema is up-to-date...")
                cur.execute("DROP TABLE IF EXISTS purchases CASCADE;")
                cur.execute("DROP TABLE IF EXISTS payments CASCADE;")

                logger.info("Creating all tables in the correct order...")
                for command in commands:
                    cur.execute(command)

            conn.commit()
            logger.info("Database tables created or updated successfully.")
        except psycopg2.Error as e:
            logger.error(f"Error creating PostgreSQL tables: {e}")
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

    def _decrypt_server_row(self, server_row: psycopg2.extras.DictRow) -> dict or None:
        """Helper function to decrypt a single server record."""
        if not server_row:
            return None
        server_dict = dict(server_row)
        try:
            server_dict['panel_url'] = self._decrypt(server_dict['panel_url'])
            server_dict['username'] = self._decrypt(server_dict['username'])
            server_dict['password'] = self._decrypt(server_dict['password'])
            server_dict['subscription_base_url'] = self._decrypt(server_dict['subscription_base_url'])
            server_dict['subscription_path_prefix'] = self._decrypt(server_dict['subscription_path_prefix'])
            return server_dict
        except Exception as e:
            logger.error(f"Could not decrypt credentials for server ID {server_dict.get('id')}: {e}")
            return None

    # --- User Functions ---
    def add_or_update_user(self, telegram_id, first_name, last_name=None, username=None):
        sql = """
            INSERT INTO users (telegram_id, first_name, last_name, username, last_activity)
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (telegram_id) DO UPDATE SET
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                username = EXCLUDED.username,
                last_activity = CURRENT_TIMESTAMP
            RETURNING id;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (telegram_id, first_name, last_name, username))
                    user_id = cursor.fetchone()[0]
                    conn.commit()
                    logger.info(f"User {telegram_id} added or updated.")
                    return user_id
        except psycopg2.Error as e:
            logger.error(f"Error adding/updating user {telegram_id}: {e}")
            return None

    def get_all_users(self):
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    # Добавляем столбцы is_admin и balance в запрос
                    cursor.execute("SELECT id, telegram_id, first_name, username, join_date, is_admin, balance FROM users ORDER BY id DESC")
                    return [dict(user) for user in cursor.fetchall()]
        except psycopg2.Error as e:
            logger.error(f"Error getting all users: {e}")
            return []

    def get_user_by_telegram_id(self, telegram_id):
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute("SELECT * FROM users WHERE telegram_id = %s", (telegram_id,))
                    user = cursor.fetchone()
                    return dict(user) if user else None
        except psycopg2.Error as e:
            log...(truncated 104857 characters)...     
        
    def deduct_from_user_balance(self, user_id: int, amount: float):
        """
        Вычитает указанную сумму из баланса кошелька пользователя.
        Чтобы предотвратить отрицательный баланс, в запросе добавлено условие.
        """
        sql = "UPDATE users SET balance = balance - %s WHERE id = %s AND balance >= %s;"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (amount, user_id, amount))
                    conn.commit()
                    # Если строка обновлена, значит баланса было достаточно
                    return cursor.rowcount > 0
        except psycopg2.Error as e:
            logger.error(f"Error deducting balance for user {user_id}: {e}")
            return False
        
        
    # Найдите эти две функции в db_manager.py и замените их

    def update_server_inbound_template(self, server_id: int, inbound_id: int, params_json: str, raw_template: str):
        """Обновляет параметры и сырой текст шаблона для конкретного inbound сервера."""
        sql = "UPDATE server_inbounds SET config_params = %s, raw_template = %s WHERE server_id = %s AND inbound_id = %s"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (params_json, raw_template, server_id, inbound_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except psycopg2.Error as e:
            logger.error(f"Error updating server inbound template for s:{server_id}-i:{inbound_id}: {e}")
            return False

    def update_profile_inbound_template(self, profile_id: int, server_id: int, inbound_id: int, params_json: str, raw_template: str):
        """Обновляет параметры и сырой текст шаблона для конкретного inbound профиля."""
        sql = "UPDATE profile_inbounds SET config_params = %s, raw_template = %s WHERE profile_id = %s AND server_id = %s AND inbound_id = %s"
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, (params_json, raw_template, profile_id, server_id, inbound_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except psycopg2.Error as e:
            logger.error(f"Error updating profile inbound template for p:{profile_id}-s:{server_id}-i:{inbound_id}: {e}")
            return False
        
        
    def get_all_profile_inbounds_for_debug(self):
        """Возвращает все записи таблицы profile_inbounds с читаемыми именами."""
        sql = """
            SELECT 
                pi.profile_id, p.name as profile_name,
                pi.server_id, s.name as server_name,
                pi.inbound_id
            FROM profile_inbounds pi
            JOIN profiles p ON pi.profile_id = p.id
            JOIN servers s ON pi.server_id = s.id
            ORDER BY pi.profile_id, pi.server_id, pi.inbound_id;
        """
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute(sql)
                    return [dict(row) for row in cursor.fetchall()]
        except psycopg2.Error as e:
            logger.error(f"Error getting all profile inbounds for debug: {e}")
            return []
        
        
    def _seed_messages_table(self):
        """Заполняет таблицу bot_messages значениями по умолчанию из файла messages.py."""
        import utils.messages as messages_module
        from psycopg2.extras import execute_batch
        
        all_messages = {
            key: getattr(messages_module, key)
            for key in dir(messages_module)
            if not key.startswith('__') and isinstance(getattr(messages_module, key), str)
        }
        if not all_messages: return

        sql = "INSERT INTO bot_messages (message_key, message_text) VALUES (%s, %s) ON CONFLICT (message_key) DO NOTHING;"
        data_to_insert = list(all_messages.items())
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                execute_batch(cur, sql, data_to_insert)
                conn.commit()
                logger.info(f"Successfully seeded {len(data_to_insert)} message keys into the database.")

    def get_all_bot_messages(self):
        """Читает все ключи и тексты сообщений из базы данных."""
        sql = "SELECT message_key, message_text FROM bot_messages ORDER BY message_key;"
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(sql)
                return [dict(row) for row in cur.fetchall()]

    def get_message_by_key(self, key: str):
        """Читает текст сообщения по его ключу из базы данных."""
        sql = "SELECT message_text FROM bot_messages WHERE message_key = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (key,))
                result = cur.fetchone()
                return result[0] if result else None

    def update_bot_message(self, message_key: str, new_text: str):
        """Обновляет текст конкретного сообщения в базе данных."""
        sql = "UPDATE bot_messages SET message_text = %s WHERE message_key = %s;"
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (new_text, message_key))
                conn.commit()
                return cur.rowcount > 0
            
            
    def set_user_role(self, telegram_id, role):
        """Изменяет роль пользователя (например, на 'user', 'admin', 'reseller')."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Вместо boolean-значения обновляем текст (role) в базе данных
                cur.execute("UPDATE users SET role = %s WHERE telegram_id = %s", (role, telegram_id))
                conn.commit()
                return cur.rowcount > 0
        except psycopg2.Error as e:
            logger.error(f"Error setting role for {telegram_id}: {e}")
            if conn: conn.rollback()
            return False
        finally:
            if conn: conn.close()
            
            
    def get_all_active_purchases(self):
        """Получение всех активных покупок"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM purchases 
                        WHERE is_active = TRUE 
                        ORDER BY purchase_date DESC
                    """)
                    purchases = cursor.fetchall()
                    return [dict(purchase) for purchase in purchases]
        except Exception as e:
            logger.error(f"Error getting active purchases: {e}")
            return []

    def update_purchase_sub_id(self, purchase_id, new_sub_id):
        """Обновление sub_id для покупки"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE purchases 
                        SET sub_id = %s 
                        WHERE id = %s
                    """, (new_sub_id, purchase_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating purchase sub_id: {e}")
            return False

    def get_client_traffic_info(self, client_uuid):
        """Получение информации о трафике клиента из панели"""
        try:
            # Проверка наличия client_uuid
            if not client_uuid:
                logger.error("client_uuid is None or empty")
                return None
                
            # Сначала находим сервер, связанный с этим клиентом
            purchase = self.get_purchase_by_client_uuid(client_uuid)
            if not purchase:
                logger.warning(f"No purchase found for client_uuid: {client_uuid}")
                return None
            
            server = self.get_server_by_id(purchase['server_id'])
            if not server:
                logger.error(f"No server found for purchase {purchase['id']}")
                return None
            
            # Выбор подходящего API Client
            from api_client.factory import get_api_client
            api_client = get_api_client(server)
            
            if not api_client:
                logger.error(f"Could not create API client for server {server['id']}")
                return None
            
            # Получение информации о клиенте
            client_info = api_client.get_client_info(client_uuid)
            if not client_info:
                logger.warning(f"No client info returned for UUID: {client_uuid}")
                return None
                
            return client_info
            
        except Exception as e:
            logger.error(f"Error getting client traffic info for {client_uuid}: {e}")
            return None

    def get_purchase_by_client_uuid(self, client_uuid):
        """Получение покупки по UUID клиента"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM purchases 
                        WHERE client_uuid = %s AND is_active = TRUE
                    """, (client_uuid,))
                    purchase = cursor.fetchone()
                    if purchase:
                        try:
                            return dict(purchase)
                        except Exception as dict_error:
                            logger.error(f"Error converting purchase to dict: {dict_error}")
                            return None
                    return None
        except Exception as e:
            logger.error(f"Error getting purchase by client UUID {client_uuid}: {e}")
            return None

    def get_all_client_uuids_for_user(self, user_id):
        """Получение всех UUID клиентов для пользователя"""
        try:
            with self._get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
                    cursor.execute("""
                        SELECT client_uuid, server_id, id as purchase_id 
                        FROM purchases 
                        WHERE user_id = %s AND is_active = TRUE AND client_uuid IS NOT NULL
                    """, (user_id,))
                    purchases = cursor.fetchall()
                    result = []
                    for purchase in purchases:
                        try:
                            result.append(dict(purchase))
                        except Exception as dict_error:
                            logger.error(f"Error converting purchase to dict: {dict_error}")
                            continue
                    return result
        except Exception as e:
            logger.error(f"Error getting client UUIDs for user {user_id}: {e}")
            return []
            
    def update_purchase_configs(self, purchase_id, configs_json):
        """Обновление сохранённых конфигураций для покупки"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE purchases 
                        SET single_configs_json = %s, 
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                    """, (configs_json, purchase_id))
                    conn.commit()
                    return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating purchase configs for {purchase_id}: {e}")
            return False