# 🚀 Руководство по быстрому тестированию Webhook Server

## 🔍 **Шаги тестирования:**

### **1. Простой тест webhook server:**
```bash
# Запустите на сервере
curl -X GET "https://YOUR_DOMAIN/test"
```

**Ожидание:** JSON ответ с статусом "ok"

### **2. Тест endpoint информации purchase:**
```bash
# Тест purchase с ID 1
curl -X GET "https://YOUR_DOMAIN/admin/test/1"
```

**Ожидание:** JSON ответ с информацией purchase

### **3. Проверка логов webhook server:**
```bash
# Логи системы
tail -f /var/log/syslog | grep webhook

# Или специфические логи
tail -f /var/log/syslog | grep "🔍\|✅\|❌\|⚠️"
```

### **4. Тест кнопки "Обновить все ссылки":**
1. В боте перейдите в меню админа
2. Нажмите кнопку "🔄 Обновить все ссылки"
3. Проверьте логи

## 📋 **Ожидаемые результаты:**

### **✅ Успех:**
```
INFO: 🔍 Simple test endpoint called
INFO: ✅ Simple test successful
INFO: 🌐 Webhook Domain: yourdomain.com
INFO: 🔗 Active Domain (User Subscriptions): userdomain.com
INFO: 📡 Panel Request Details:
INFO:    Server ID: 1
INFO:    Server Name: Germany-Hetzner
INFO:    Panel URL: http://1.2.3.4:54321
INFO:    Final URL: http://1.2.3.4:54321/sub/abc123
INFO: ✅ Successfully fetched subscription data for purchase 1
```

### **❌ Проблема:**
```
ERROR: ❌ Error in get_profile_subscription_data: 'sub_id' is not defined
ERROR: ❌ Traceback: ...
```

## 🛠️ **Решения проблем:**

### **Проблема 1: Webhook server не работает**
```bash
# Проверка процесса
ps aux | grep webhook

# Перезапуск
cd /var/www/alamorvpn_bot
python3 webhook_server.py
```

### **Проблема 2: Ошибка sub_id**
- Проблема решена в новом коде
- Перезапустите webhook server

### **Проблема 3: Логи не отображаются**
```bash
# Проверка логов системы
journalctl -u your-bot-service -f

# Или прямые логи
tail -f /var/log/syslog | grep python3
```

## 🎯 **Следующий шаг:**

После выполнения тестов выше, сообщите результаты, чтобы точно определить проблему.

---
**Дата:** $(date)
**Статус:** Готов к тестированию