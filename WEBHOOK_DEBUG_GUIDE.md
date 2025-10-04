# 🔧 راهنمای رفع مشکل Webhook Server

## 🚨 **مشکل فعلی:**
خطاهای HTTP 500 در endpoint `/admin/update_configs/<purchase_id>`

## 🔍 **مراحل عیب‌یابی:**

### 1. **بررسی تنظیمات محیطی**
```bash
# بررسی متغیرهای محیطی
echo $WEBHOOK_DOMAIN
echo $ADMIN_API_KEY
```

### 2. **تست endpoint های webhook**
```bash
# تست endpoint اطلاعات purchase
curl -X GET "https://YOUR_DOMAIN/admin/test/1"

# تست endpoint بروزرسانی configs
curl -X POST "https://YOUR_DOMAIN/admin/update_configs/1" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### 3. **بررسی لاگ‌های webhook server**
```bash
# بررسی لاگ‌های webhook server
tail -f /var/log/webhook_server.log
```

## 🛠️ **راه‌حل‌های پیاده‌سازی شده:**

### ✅ **1. بهبود Error Handling**
- اضافه شدن logging دقیق‌تر
- بررسی وجود sub_id و server_id
- بررسی وضعیت active بودن purchase
- Fallback mechanism برای profile purchases

### ✅ **2. Endpoint تست جدید**
- `/admin/test/<purchase_id>` برای بررسی وضعیت purchase
- نمایش اطلاعات کامل purchase بدون نیاز به API key

### ✅ **3. بهبود Validation**
- بررسی ADMIN_API_KEY
- بررسی وجود purchase در دیتابیس
- بررسی وضعیت active بودن purchase

## 🔧 **نحوه استفاده از Debug Tool:**

### **1. اجرای debug script:**
```bash
python debug_webhook.py
```

### **2. بررسی لاگ‌های بهبود یافته:**
لاگ‌های جدید شامل اطلاعات دقیق‌تری هستند:
- نوع purchase (profile یا normal)
- وضعیت server و sub_id
- تعداد config های یافت شده
- خطاهای دقیق با traceback

## 📋 **چک‌لیست عیب‌یابی:**

### **برای هر purchase که خطا می‌دهد:**
1. ✅ آیا purchase در دیتابیس وجود دارد؟
2. ✅ آیا sub_id دارد؟
3. ✅ آیا server_id دارد (برای خریدهای عادی)؟
4. ✅ آیا profile_id دارد (برای خریدهای پروفایل)؟
5. ✅ آیا وضعیت active است؟
6. ✅ آیا server مربوطه در دسترس است؟

### **برای webhook server:**
1. ✅ آیا ADMIN_API_KEY تنظیم شده؟
2. ✅ آیا WEBHOOK_DOMAIN صحیح است؟
3. ✅ آیا webhook server در حال اجرا است؟
4. ✅ آیا دیتابیس در دسترس است؟

## 🚀 **مرحله بعدی:**

بعد از اجرای debug script، نتایج را بررسی کنید تا مشکل دقیق مشخص شود. احتمالاً مشکل از یکی از موارد زیر است:

1. **Purchase های ناقص:** خریدهایی که sub_id یا server_id ندارند
2. **Server های غیرفعال:** سرورهایی که در دسترس نیستند
3. **Profile های ناقص:** پروفایل‌هایی که inbound ندارند
4. **مشکلات شبکه:** عدم دسترسی به panel های X-UI

## 📞 **در صورت نیاز به کمک بیشتر:**

نتایج debug script را ارسال کنید تا مشکل دقیق مشخص شود.
