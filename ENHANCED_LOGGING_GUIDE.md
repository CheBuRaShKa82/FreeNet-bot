# 📊 Руководство по улучшенным логам для обновления Subscription

## 🎯 **Цель:**

Более точные логи для устранения неисправностей обновления subscription, включая:
- Точные адреса запросов
- Информация о доменах
- Детали серверов и панелей
- Статус механизма fallback

## 🔍 **Новые логи:**

### **1. Информация о доменах:**
```
INFO: 🌐 Webhook Domain: yourdomain.com
INFO: 🔗 Active Domain (User Subscriptions): userdomain.com
```

### **2. Детали запроса к панели:**
```
INFO: 📡 Panel Request Details:
INFO:    Server ID: 1
INFO:    Server Name: Germany-Hetzner
INFO:    Panel URL: http://1.2.3.4:54321
INFO:    Subscription Path: sub
INFO:    Sub ID: abc123def456
INFO:    Final URL: http://1.2.3.4:54321/sub/abc123def456
```

### **3. Детали профиля:**
```
INFO: 📋 Profile Details:
INFO:    Profile ID: 1
INFO:    Total Inbounds: 5
INFO:    Sub ID: abc123def456
INFO:    Servers involved:
INFO:      - Server 1: Germany-Hetzner (2 inbounds)
INFO:      - Server 2: Netherlands-OVH (3 inbounds)
```

### **4. Обработка каждого сервера:**
```
INFO: 🔄 Processing Server Germany-Hetzner (ID: 1)
INFO:    Inbounds on this server: 2
INFO: 📡 Panel Request Details:
INFO:    Server ID: 1
INFO:    Server Name: Germany-Hetzner
INFO:    Panel URL: http://1.2.3.4:54321
INFO:    Subscription Path: sub
INFO:    Sub ID: abc123def456
INFO:    Final URL: http://1.2.3.4:54321/sub/abc123def456
INFO:    ✅ Success: Added 2 configs from server Germany-Hetzner
```

### **5. Информация о полученных данных:**
```
INFO: ✅ Successfully fetched subscription data for purchase 1
INFO:    📄 Data length: 2048 characters
INFO:    📊 Data source: Panel
INFO:    🔓 Content type: Base64 (decoded)
INFO: ✅ Found 5 valid configs for purchase 1
INFO:    📋 Config types: vmess, vless, trojan
```

### **6. Использование кэшированных данных:**
```
WARNING: ⚠️ Could not fetch subscription data from panel for purchase 1, using cached data
INFO: ✅ Using cached configs for purchase 1: 5 configs
INFO:    📄 Cached data length: 2048 characters
```

### **7. Сохранение в базу данных:**
```
INFO: 💾 Saving configs to database for purchase 1
INFO: ✅ Successfully updated cached configs for purchase 1
INFO:    📊 Summary: 5 configs saved to database
```

## 🚀 **Преимущества новых логов:**

### **1. Точное устранение неисправностей:**
- Полные адреса запросов
- Обнаружение сетевых проблем
- Идентификация проблемных серверов

### **2. Мониторинг производительности:**
- Количество обработанных config
- Тип полученного содержимого
- Скорость обработки

### **3. Управление доменами:**
- Отображение текущего домена webhook
- Отображение домена subscription пользователей
- Обнаружение проблем с доменами

## 📋 **Как использовать:**

### **1. Проверка логов:**
```bash
# Проверка логов webhook server
tail -f /var/log/webhook_server.log | grep "📡\|🌐\|🔗\|📋\|🔄\|✅\|❌\|⚠️"
```

### **2. Фильтрация логов:**
```bash
# Только логи для конкретной покупки
grep "purchase 1" /var/log/webhook_server.log

# Только логи для конкретного сервера
grep "Germany-Hetzner" /var/log/webhook_server.log

# Только ошибки
grep "❌" /var/log/webhook_server.log
```

### **3. Проверка проблем:**
```bash
# Проверка неудачных запросов
grep "Could not fetch" /var/log/webhook_server.log

# Проверка использования кэшированных данных
grep "using cached data" /var/log/webhook_server.log

# Проверка проблем с доменами
grep "Webhook Domain\|Active Domain" /var/log/webhook_server.log
```

## 🔧 **Пример устранения неисправностей:**

### **Проблема: HTTP 500 в обновлении**
```
INFO: Starting update_cached_configs_from_panel for purchase 1
INFO: 🌐 Webhook Domain: yourdomain.com
INFO: 🔗 Active Domain (User Subscriptions): userdomain.com
INFO: Processing normal purchase 1 with server_id 1
INFO: 📡 Panel Request Details:
INFO:    Server ID: 1
INFO:    Server Name: Germany-Hetzner
INFO:    Panel URL: http://1.2.3.4:54321
INFO:    Subscription Path: sub
INFO:    Sub ID: abc123def456
INFO:    Final URL: http://1.2.3.4:54321/sub/abc123def456
ERROR: Error fetching subscription data from panel: Connection timeout
WARNING: ⚠️ Could not fetch subscription data from panel for purchase 1, using cached data
INFO: ✅ Using cached configs for purchase 1: 5 configs
```

### **Решение:**
1. Проверьте доступ к панели: `http://1.2.3.4:54321`
2. Проверьте наличие sub_id в панели
3. Проверьте сетевые настройки

## 🎉 **Результат:**

**Теперь вы можете точно видеть:**
- К какому адресу идет запрос
- Какие домены установлены
- Где проблема
- Почему используются кэшированные данные

---
**Дата обновления:** $(date)
**Статус:** ✅ Реализовано и готово к использованию