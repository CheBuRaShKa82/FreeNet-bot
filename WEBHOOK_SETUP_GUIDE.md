# Руководство по настройке Webhook Server

## 🔧 Проблема с кнопкой "Обновить все ссылки"

Если кнопка **"🔄 Обновить все ссылки"** не работает, вероятно, webhook server не запущен.

## 🚀 Настройка Webhook Server

### 1. Проверка настроек .env

Убедитесь, что эти переменные установлены в файле `.env`:

```bash
# Домен webhook
WEBHOOK_DOMAIN="paytest.alamornetwork.ir"

# Ключ API админа
ADMIN_API_KEY="your-secret-key"
```

### 2. Запуск Webhook Server

```bash
# В отдельном терминале
python webhook_server.py
```

Или с помощью systemd:

```bash
# Запуск сервиса
sudo systemctl start alamorwebhook

# Проверка статуса
sudo systemctl status alamorwebhook

# Включение при загрузке
sudo systemctl enable alamorwebhook
```

### 3. Проверка работы

```bash
# Тест endpoint
curl -X POST https://paytest.alamornetwork.ir/admin/update_configs/1 \
  -H "Authorization: Bearer your-secret-key"
```

## 🔍 Устранение неисправностей

### Проблема 1: "webhook server недоступен"

**Решение:**
1. Убедитесь, что webhook server запущен
2. Проверьте, что порт 8080 открыт
3. Проверьте, что фаервол разрешает доступ

### Проблема 2: "Ошибка 401 Unauthorized"

**Решение:**
1. Проверьте, что `ADMIN_API_KEY` установлен в `.env`
2. Убедитесь, что ключ одинаковый в webhook server и боте

### Проблема 3: "Ошибка 404 Not Found"

**Решение:**
1. Проверьте, что endpoint `/admin/update_configs/{purchase_id}` существует в webhook server
2. Убедитесь, что purchase_id действителен

## 📊 Работа кнопки

Когда вы нажимаете кнопку **"🔄 Обновить все ссылки"**:

1. **Проверка настроек**: WEBHOOK_DOMAIN и ADMIN_API_KEY
2. **Получение активных покупок**: Из базы данных
3. **Отправка запроса**: На webhook server для каждой покупки
4. **Отображение статистики**: Количество успешных, неудачных и ошибок соединения
5. **Кнопка возврата**: В меню админа

## 🎯 Пример успешного вывода

```
🔄 Обновление ссылок Subscription

📊 Результаты:
• ✅ Успешно: 12 ссылок
• ❌ Неудачно: 0 ссылок
• 📡 Ошибка соединения: 0 ссылок
• 📈 Всего: 12 ссылок

🎉 Некоторые ссылки успешно обновлены.
```

## 🎯 Пример вывода ошибки

```
🔄 Обновление ссылок Subscription

📊 Результаты:
• ✅ Успешно: 0 ссылок
• ❌ Неудачно: 0 ссылок
• 📡 Ошибка соединения: 12 ссылок
• 📈 Всего: 12 ссылок

⚠️ Проблема: webhook server недоступен.
Пожалуйста, убедитесь, что webhook server запущен.
```

## 💡 Важные советы

1. **webhook server должен всегда быть запущен**
2. **ADMIN_API_KEY должен быть безопасным и уникальным**
3. **WEBHOOK_DOMAIN должен быть доступен**
4. **Порт 8080 должен быть открыт**
5. **SSL certificate должен быть действительным**

## 🔧 Полезные команды

```bash
# Проверка статуса webhook server
ps aux | grep webhook_server

# Проверка порта 8080
netstat -tlnp | grep 8080

# Проверка логов
tail -f /var/log/alamorwebhook.log

# Тест соединения
curl -I https://paytest.alamornetwork.ir/admin/update_configs/1
```