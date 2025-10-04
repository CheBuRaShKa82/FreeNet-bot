# 🧪 راهنمای تست Config Builder

## 🎯 **هدف:**

تست سیستم جدید ساخت کانفیگ‌ها مستقیماً از دیتای پنل، بدون نیاز به subscription link.

## 🚀 **نحوه استفاده:**

### **1. دسترسی به منوی تست:**
1. در ربات، منوی ادمین برید
2. دکمه "🧪 تست Config Builder" رو بزنید

### **2. انتخاب سرور:**
- لیست سرورهای موجود نمایش داده می‌شه
- دکمه "🧪 تست [نام سرور]" رو بزنید

### **3. نتیجه تست:**
سیستم به صورت خودکار:
- به پنل متصل می‌شه
- اولین inbound رو انتخاب می‌کنه
- اولین کلاینت رو انتخاب می‌کنه
- کانفیگ رو می‌سازه
- نتیجه رو نمایش می‌ده

## 📋 **نتایج مورد انتظار:**

### **✅ موفق:**
```
✅ تست موفق!

سرور: Germany-Hetzner
پروتکل: vmess
کلاینت: user123@example.com
Inbound: 1

کانفیگ ساخته شده:
vmess://eyJ2IjoiMiIsInBzIjoiQWxhbW9yLXVzZXIxMjNAZXhhbXBsZS5jb20iLCJhZGQiOiIxLjIuMy40IiwicG9ydCI6NDQzLCJpZCI6IjEyMzQ1Njc4LTkwYWItMTFlZC1hNzE1LTAyNDJhYzEyMDAwYiIsImFpZCI6IjAiLCJuZXQiOiJ0Y3AiLCJ0eXBlIjoibm9uZSIsImhvc3QiOiIiLCJwYXRoIjoiIiwidGxzIjoibm9uZSJ9

🎉 Config Builder کار می‌کند!
```

### **❌ خطاهای احتمالی:**

#### **خطا در اتصال به پنل:**
```
❌ خطا در اتصال به پنل

سرور: Germany-Hetzner
نمی‌توان به پنل متصل شد.
لطفاً اطلاعات ورود را بررسی کنید.
```

#### **هیچ inbound یافت نشد:**
```
❌ هیچ inbound یافت نشد

سرور: Germany-Hetzner
هیچ inbound فعالی در پنل وجود ندارد.
```

#### **هیچ کلاینت یافت نشد:**
```
❌ هیچ کلاینت یافت نشد

سرور: Germany-Hetzner
Inbound: VMess-443
هیچ کلاینت فعالی در این inbound وجود ندارد.
```

## 🔧 **مزایای سیستم جدید:**

### **1. استقلال از subscription link:**
- کانفیگ‌ها مستقیماً از پنل ساخته می‌شن
- نیازی به subscription link نیست
- مشکلات فیلترینگ حل می‌شن

### **2. دقت بالا:**
- اطلاعات دقیق از پنل دریافت می‌شه
- تنظیمات TLS و WebSocket درست اعمال می‌شن
- نام‌گذاری با برندینگ

### **3. پشتیبانی از پروتکل‌های مختلف:**
- VMess
- VLESS
- Trojan

## 📊 **نحوه عملکرد:**

### **1. اتصال به پنل:**
```python
api_client = XuiAPIClient(panel_url, username, password)
api_client.check_login()
```

### **2. دریافت اطلاعات:**
```python
inbound_info = api_client.get_inbound(inbound_id)
client_info = api_client.get_client_info(client_id)
```

### **3. ساخت کانفیگ:**
```python
config = build_vmess_config(client_info, inbound_info, server_info)
```

### **4. نتیجه:**
کانفیگ کامل با تمام تنظیمات

## 🎉 **مرحله بعدی:**

اگر تست موفق بود، می‌تونیم:
1. سیستم subscription رو به Config Builder تغییر بدیم
2. دکمه "بروزرسانی همه لینک‌ها" رو بهبود بدیم
3. کانفیگ‌ها رو مستقیماً از پنل بسازیم

---
**تاریخ:** $(date)
**وضعیت:** آماده برای تست
