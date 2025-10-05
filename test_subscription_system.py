"""
Тестирование новой системы подписки
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import base64
import json

def test_subscription_endpoint():
    """Тестирование endpoint подписки"""
    print("=== Тестирование endpoint подписки ===")
    
    # Тест с примером sub_id
    test_sub_id = "test123"
    webhook_url = "http://localhost:8080/sub/" + test_sub_id
    
    try:
        response = requests.get(webhook_url, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Content Type: {response.headers.get('content-type')}")
        print(f"Response Length: {len(response.text)}")
        
        if response.status_code == 200:
            # Проверка, является ли содержимое Base64
            try:
                decoded = base64.b64decode(response.text)
                print(f"✅ Содержимое в формате Base64. Длина декодированного: {len(decoded)}")
                print(f"Пример содержимого: {decoded[:100]}...")
            except:
                print("❌ Содержимое не в формате Base64")
                print(f"Пример содержимого: {response.text[:100]}...")
        else:
            print(f"Ошибка: {response.text}")
            
    except Exception as e:
        print(f"Ошибка в тесте: {e}")

def test_content_detection():
    """Тестирование определения типа содержимого"""
    print("\n=== Тестирование определения типа содержимого ===")
    
    test_cases = [
        ("vmess://test123", "v2ray_config"),
        ("vless://test123", "v2ray_config"),
        ("trojan://test123", "v2ray_config"),
        (base64.b64encode(b"test content").decode(), "base64"),
        ('{"key": "value"}', "json"),
        ("plain text content", "plain_text")
    ]
    
    for content, expected_type in test_cases:
        detected_type = detect_content_type(content)
        status = "✅" if detected_type == expected_type else "❌"
        print(f"{status} {content[:20]}... -> {detected_type} (ожидается: {expected_type})")

def detect_content_type(content):
    """Определение типа содержимого подписки"""
    # Проверка, является ли содержимое Base64
    try:
        decoded = base64.b64decode(content)
        return 'base64'
    except:
        pass
    
    # Проверка, является ли содержимое JSON
    try:
        json.loads(content)
        return 'json'
    except:
        pass
    
    # Проверка, является ли содержимое конфигурацией V2Ray
    if 'vmess://' in content or 'vless://' in content or 'trojan://' in content:
        return 'v2ray_config'
    
    # По умолчанию: обычный текст
    return 'plain_text'

def test_panel_data_fetch():
    """Тестирование получения данных из основной панели"""
    print("\n=== Тестирование получения данных из основной панели ===")
    
    # Этот тест требует реальных настроек
    print("⚠️ Этот тест требует реальных настроек")
    print("Для полного тестирования, пожалуйста, настройте параметры панели в файле config.py")

if __name__ == "__main__":
    print("🚀 Начало тестирования новой системы подписки\n")
    
    test_subscription_endpoint()
    test_content_detection()
    test_panel_data_fetch()
    
    print("\n✅ Тесты завершены!")
    print("\n📝 Важные заметки:")
    print("1. Новая система всегда сначала получает данные из основной панели")
    print("2. Если основная панель недоступна, используется база данных")
    print("3. Содержимое автоматически определяется и обрабатывается")
    print("4. Администратор может вручную обновлять конфигурации")