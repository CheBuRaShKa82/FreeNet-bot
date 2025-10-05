"""
Тестирование новых возможностей трафика
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils import helpers
from database.db_manager import DatabaseManager

def test_traffic_formatting():
    """Тестирование функции преобразования объёма"""
    print("=== Тестирование преобразования объёма ===")
    
    test_cases = [
        0,
        1024,
        1024 * 1024,
        1024 * 1024 * 1024,
        1024 * 1024 * 1024 * 2.5,
        None
    ]
    
    for value in test_cases:
        formatted = helpers.format_traffic_size(value)
        print(f"{value} -> {formatted}")

def test_days_calculation():
    """Тестирование расчёта оставшихся дней"""
    print("\n=== Тестирование расчёта оставшихся дней ===")
    
    from datetime import datetime, timedelta
    
    # Тестирование различных дат
    now = datetime.now()
    test_cases = [
        now + timedelta(days=5),  # 5 дней вперёд
        now + timedelta(days=1),  # Завтра
        now,                      # Сегодня
        now - timedelta(days=1),  # Вчера
        None                      # Без даты
    ]
    
    for date in test_cases:
        days = helpers.calculate_days_remaining(date)
        print(f"{date} -> {days} дней осталось")

def test_database_functions():
    """Тестирование функций базы данных"""
    print("\n=== Тестирование функций базы данных ===")
    
    try:
        db = DatabaseManager()
        
        # Тестирование получения UUID клиентов
        user_id = 1  # Тест с пользователем ID 1
        uuids = db.get_all_client_uuids_for_user(user_id)
        print(f"UUID клиентов для пользователя {user_id}: {len(uuids)} записей")
        
        for uuid_info in uuids:
            print(f"  - UUID: {uuid_info['client_uuid']}, Server: {uuid_info['server_id']}")
            
            # Тестирование получения информации о трафике
            traffic_info = db.get_client_traffic_info(uuid_info['client_uuid'])
            if traffic_info:
                print(f"    Трафик: {traffic_info}")
            else:
                print(f"    Трафик: Недоступен")
                
    except Exception as e:
        print(f"Ошибка в тесте базы данных: {e}")

if __name__ == "__main__":
    print("🚀 Начало тестирования возможностей трафика\n")
    
    test_traffic_formatting()
    test_days_calculation()
    test_database_functions()
    
    print("\n✅ Тесты завершены!")