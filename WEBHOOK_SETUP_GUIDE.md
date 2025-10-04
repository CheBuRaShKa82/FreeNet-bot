# راهنمای راه‌اندازی Webhook Server

## 🔧 مشکل دکمه "بروزرسانی همه لینک‌ها"

اگر دکمه **"🔄 بروزرسانی همه لینک‌ها"** کار نمی‌کند، احتمالاً webhook server در حال اجرا نیست.

## 🚀 راه‌اندازی Webhook Server

### 1. بررسی تنظیمات .env

اطمینان حاصل کنید که این متغیرها در فایل `.env` تنظیم شده‌اند:

```bash
# دامنه webhook
WEBHOOK_DOMAIN="paytest.alamornetwork.ir"

# کلید API ادمین
ADMIN_API_KEY="your-secret-key"
```

### 2. اجرای Webhook Server

```bash
# در ترمینال جداگانه
python webhook_server.py
```

یا با systemd:

```bash
# راه‌اندازی سرویس
sudo systemctl start alamorwebhook

# بررسی وضعیت
sudo systemctl status alamorwebhook

# فعال‌سازی در بوت
sudo systemctl enable alamorwebhook
```

### 3. بررسی عملکرد

```bash
# تست endpoint
curl -X POST https://paytest.alamornetwork.ir/admin/update_configs/1 \
  -H "Authorization: Bearer your-secret-key"
```

## 🔍 عیب‌یابی

### مشکل 1: "webhook server در دسترس نیست"

**راه حل:**
1. اطمینان حاصل کنید که webhook server در حال اجرا است
2. بررسی کنید که پورت 8080 باز است
3. بررسی کنید که فایروال اجازه دسترسی می‌دهد

### مشکل 2: "خطای 401 Unauthorized"

**راه حل:**
1. بررسی کنید که `ADMIN_API_KEY` در `.env` تنظیم شده است
2. اطمینان حاصل کنید که کلید در webhook server و ربات یکسان است

### مشکل 3: "خطای 404 Not Found"

**راه حل:**
1. بررسی کنید که endpoint `/admin/update_configs/{purchase_id}` در webhook server موجود است
2. اطمینان حاصل کنید که purchase_id معتبر است

## 📊 عملکرد دکمه

وقتی دکمه **"🔄 بروزرسانی همه لینک‌ها"** را کلیک کنید:

1. **بررسی تنظیمات**: WEBHOOK_DOMAIN و ADMIN_API_KEY
2. **دریافت خریدهای فعال**: از دیتابیس
3. **ارسال درخواست**: به webhook server برای هر خرید
4. **نمایش آمار**: تعداد موفق، ناموفق و خطاهای اتصال
5. **دکمه بازگشت**: به منوی ادمین

## 🎯 نمونه خروجی موفق

```
🔄 بروزرسانی لینک‌های Subscription

📊 نتایج:
• ✅ موفق: 12 لینک
• ❌ ناموفق: 0 لینک
• 📡 خطای اتصال: 0 لینک
• 📈 کل: 12 لینک

🎉 برخی لینک‌ها با موفقیت بروزرسانی شدند.
```

## 🎯 نمونه خروجی خطا

```
🔄 بروزرسانی لینک‌های Subscription

📊 نتایج:
• ✅ موفق: 0 لینک
• ❌ ناموفق: 0 لینک
• 📡 خطای اتصال: 12 لینک
• 📈 کل: 12 لینک

⚠️ مشکل: webhook server در دسترس نیست.
لطفاً اطمینان حاصل کنید که webhook server در حال اجرا است.
```

## 💡 نکات مهم

1. **webhook server باید همیشه در حال اجرا باشد**
2. **ADMIN_API_KEY باید امن و منحصر به فرد باشد**
3. **WEBHOOK_DOMAIN باید قابل دسترس باشد**
4. **پورت 8080 باید باز باشد**
5. **SSL certificate باید معتبر باشد**

## 🔧 دستورات مفید

```bash
# بررسی وضعیت webhook server
ps aux | grep webhook_server

# بررسی پورت 8080
netstat -tlnp | grep 8080

# بررسی لاگ‌ها
tail -f /var/log/alamorwebhook.log

# تست اتصال
curl -I https://paytest.alamornetwork.ir/admin/update_configs/1
```
