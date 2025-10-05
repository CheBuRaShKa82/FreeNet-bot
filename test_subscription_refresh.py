"""
Тестирование системы обновления ссылок подписки
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import json

def test_webhook_endpoint():
    """Тестирование endpoint обновления конфигураций"""
    print("=== Тестирование endpoint обновления конфигураций ===")
    
    # Тест с примером purchase_id
    test_purchase_id = "1"
    webhook_url = f"http://localhost:8080/admin/update_configs/{test_purchase_id}"
    headers = {
        'Authorization': 'Bearer your-secret-key'
    }
    
    try:
        response = requests.post(webhook_url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Обновление успешно")
        else:
            print("❌ Обновление не удалось")
            
    except Exception as e:
        print(f"Ошибка в тесте: {e}")

def test_subscription_endpoint():
    """Тестирование endpoint подписки"""
    print("\n=== Тестирование endpoint подписки ===")
    
    # Тест с примером sub_id
    test_sub_id = "test123"
    webhook_url = f"http://localhost:8080/sub/{test_sub_id}"
    
    try:
        response = requests.get(webhook_url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type')}")
        print(f"Response Length: {len(response.text)}")
        
        if response.status_code == 200:
            print("✅ Ссылка подписки доступна")
            print(f"Пример содержимого: {response.text[:100]}...")
        else:
            print(f"Ошибка: {response.text}")
            
    except Exception as e:
        print(f"Ошибка в тесте: {e}")

def test_admin_api_key():
    """Тестирование API-ключа администратора"""
    print("\n=== Тестирование API-ключа администратора ===")
    
    # Тест с неверным API-ключом
    test_purchase_id = "1"
    webhook_url = f"http://localhost:8080/admin/update_configs/{test_purchase_id}"
    headers = {
        'Authorization': 'Bearer wrong-key'
    }
    
    try:
        response = requests.post(webhook_url, headers=headers, timeout=10)
        print(f"Status Code (wrong key): {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Аутентификация работает корректно")
        else:
            print("❌ Проблема с аутентификацией")
            
    except Exception as e:
        print(f"Ошибка в тесте: {e}")

def test_missing_auth():
    """Тестирование без аутентификации"""
    print("\n=== Тестирование без аутентификации ===")
    
    test_purchase_id = "1"
    webhook_url = f"http://localhost:8080/admin/update_configs/{test_purchase_id}"
    
    try:
        response = requests.post(webhook_url, timeout=10)
        print(f"Status Code (no auth): {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Аутентификация обязательна")
        else:
            print("❌ Аутентификация не обязательна")
            
    except Exception as e:
        print(f"Ошибка в тесте: {e}")

if __name__ == "__main__":
    print("🚀 Начало тестирования системы обновления ссылок подписки\n")
    
    test_webhook_endpoint()
    test_subscription_endpoint()
    test_admin_api_key()
    test_missing_auth()
    
    print("\n✅ Тесты завершены!")
    print("\n📝 Важные заметки:")
    print("1. Система обновления ссылок получает данные из основной панели")
    print("2. Администратор может обновить все ссылки одновременно")
    print("3. Пользователи могут обновлять свои ссылки отдельно")
    print("4. Аутентификация осуществляется с помощью API-ключа")
    print("5. В случае ошибки система использует данные из кэша")