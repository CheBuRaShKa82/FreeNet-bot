import logging
import os
from dotenv import load_dotenv
from database.db_manager import DatabaseManager

load_dotenv()

logging.basicConfig(level=logging.INFO)

db_type = os.getenv("DB_TYPE", "sqlite")
print(f"Attempting to connect to {db_type.upper()} and create tables...")

try:
    db = DatabaseManager()
    db.create_tables()
    print(f"\n✅ Success! Tables were created or already exist in your {db_type.upper()} database.")
except Exception as e:
    print(f"\n❌ An error occurred: {e}")
    print("\n🔧 Troubleshooting tips:")
    if db_type == "postgres":
        print("1. Make sure PostgreSQL is running")
        print("2. Check your DB_NAME, DB_USER, DB_PASSWORD in .env file")
        print("3. Ensure the database exists and user has proper permissions")
    else:
        print("1. Make sure the database directory exists")
        print("2. Check your DATABASE_NAME in .env file")
        print("3. Ensure write permissions to the database directory")