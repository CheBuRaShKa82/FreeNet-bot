# Руководство по миграции с SQLite на PostgreSQL

## Введение
Это руководство поможет вам перенести данные из базы данных SQLite в PostgreSQL.

## Предварительные требования

### 1. Установка PostgreSQL
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql postgresql-server postgresql-contrib

# Windows
# Скачайте и установите с официального сайта PostgreSQL
```

### 2. Установка psycopg2
```bash
pip install psycopg2-binary
```

### 3. Создание базы данных PostgreSQL
```sql
-- Вход в PostgreSQL
sudo -u postgres psql

-- Создание пользователя
CREATE USER alamor_user WITH PASSWORD 'your_password';

-- Создание базы данных
CREATE DATABASE alamor_vpn OWNER alamor_user;

-- Предоставление прав
GRANT ALL PRIVILEGES ON DATABASE alamor_vpn TO alamor_user;

-- Выход
\q
```

## Шаги миграции

### Шаг 1: Настройка файла .env
Отредактируйте файл `.env`:

```env
# Изменение типа базы данных
DB_TYPE=postgres

# Настройки PostgreSQL
DB_NAME=alamor_vpn
DB_USER=alamor_user
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# Сохранение пути SQLite для миграции
DATABASE_NAME_ALAMOR=database/alamor_vpn.db
```

### Шаг 2: Создание таблиц PostgreSQL
```bash
python init_db.py
```

### Шаг 3: Выполнение миграции
```bash
python migrate_sqlite_to_postgres.py
```

### Шаг 4: Проверка результатов
```bash
# Проверка лога миграции
cat migration.log

# Тест соединения
python -c "
from database.db_manager import DatabaseManager
db = DatabaseManager()
print('✅ Database connection successful')
print(f'Database type: {db.db_type}')
"
```

## Устранение неисправностей

### Ошибка соединения с PostgreSQL
```
❌ PostgreSQL connection failed: connection to server at "localhost" (127.0.0.1), port 5432 failed
```

**Решение:**
1. Проверьте, запущен ли PostgreSQL:
   ```bash
   sudo systemctl status postgresql
   ```

2. Если не запущен, запустите его:
   ```bash
   sudo systemctl start postgresql
   sudo systemctl enable postgresql
   ```

### Ошибка прав
```
❌ permission denied for database alamor_vpn
```

**Решение:**
```sql
-- Вход в PostgreSQL
sudo -u postgres psql

-- Предоставление дополнительных прав
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO alamor_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO alamor_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO alamor_user;
```

### Ошибка файла SQLite
```
❌ SQLite database file not found
```

**Решение:**
1. Проверьте наличие файла SQLite:
   ```bash
   ls -la database/alamor_vpn.db
   ```

2. Установите правильный путь в `.env`:
   ```env
   DATABASE_NAME_ALAMOR=/path/to/your/alamor_vpn.db
   ```

## Проверка после миграции

### 1. Проверка количества записей
```sql
-- В PostgreSQL
SELECT 
    'users' as table_name, COUNT(*) as count FROM users
UNION ALL
SELECT 'servers', COUNT(*) FROM servers
UNION ALL
SELECT 'plans', COUNT(*) FROM plans
UNION ALL
SELECT 'purchases', COUNT(*) FROM purchases;
```

### 2. Тест работы бота
```bash
python main.py
```

### 3. Проверка настроек брендинга
- Войдите в панель админа
- Перейдите в раздел настроек брендинга
- Измените название бренда
- Проверьте, что оно отображается в сообщениях бота

## Возврат к SQLite (если нужно)

Если нужно вернуться к SQLite:

```env
# Изменение типа базы данных
DB_TYPE=sqlite

# Настройки SQLite
DATABASE_NAME_ALAMOR=database/alamor_vpn.db

# Отключение переменных PostgreSQL
# DB_NAME=
# DB_USER=
# DB_PASSWORD=
# DB_HOST=
# DB_PORT=
```

## Важные советы

1. **Резервное копирование:** Перед миграцией обязательно сделайте резервную копию базы данных SQLite:
   ```bash
   cp database/alamor_vpn.db database/alamor_vpn_backup.db
   ```

2. **Тестирование:** Сначала выполните миграцию в тестовой среде.

3. **Время:** Выполняйте миграцию в часы низкой нагрузки.

4. **Мониторинг:** Во время миграции проверяйте файл `migration.log`.

## Поддержка

В случае проблем:
1. Проверьте файл `migration.log`
2. Скопируйте сообщения об ошибках
3. Обратитесь в службу поддержки