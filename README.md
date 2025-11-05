# RiF Activator A12+ 📱✨

<div align="center">
  <img src="https://img.shields.io/badge/iOS-A12%2B-blue" alt="iOS Support">
  <img src="https://img.shields.io/badge/Python-3.8%2B-green" alt="Python Version">
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License">
  <img src="https://img.shields.io/badge/Status-Active-success" alt="Status">
</div>

## 🌟 نظرة عامة

**RiF Activator A12+** هو نظام متقدم لتفعيل أجهزة iPhone المدعومة بمعالجات A12 وأحدث. يوفر واجهة ويب حديثة وواجهة سطح مكتب لإدارة عمليات التفعيل بشكل آمن وسهل.

## ✨ المميزات الرئيسية

- 🚀 **دعم شامل**: يدعم 25+ موديل من iPhone (A12 - A18)
- 🔒 **آمان عالي**: نظام حماية متقدم مع تشفير البيانات
- 🌐 **واجهة ويب**: تصميم Glass Morphism مع دعم PWA
- 🖥️ **واجهة سطح المكتب**: PyQt5 لإدارة الأجهزة المتصلة
- 📊 **تقارير مفصلة**: إحصائيات مباشرة وتقارير شاملة
- 🔄 **تحديث مباشر**: Socket.IO للتحديثات الفورية
- 🌙 **الوضع الليلي**: واجهة متجاوبة مع الأوضاع المختلفة

## 🔧 المتطلبات التقنية

### متطلبات النظام
- **نظام التشغيل**: Windows 10/11, macOS 10.15+, Linux
- **Python**: 3.8 أو أحدث
- **RAM**: 4GB كحد أدنى
- **مساحة القرص**: 500MB

## 🚀 التثبيت والإعداد

### 1. تحميل المشروع
```bash
git clone https://github.com/yourusername/rif-activator-a12plus.git
cd rif-activator-a12plus
```

### 2. إنشاء بيئة افتراضية
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux  
source venv/bin/activate
```

### 3. تثبيت المتطلبات
```bash
pip install -r requirements.txt
```

### 4. تشغيل الخادم
```bash
# الطريقة المبسطة
python app_simple.py

# أو استخدام ملف التشغيل
start_server.bat
```

## 📱 الأجهزة المدعومة

| الموديل | الاسم التجاري | إصدارات iOS |
|---------|-------------|-------------|
| iPhone11,2 | iPhone XS | 12.0-18.x |
| iPhone12,1 | iPhone 11 | 13.0-18.x |
| iPhone13,2 | iPhone 12 | 14.0-18.x |
| iPhone14,5 | iPhone 13 | 15.0-18.x |
| iPhone15,2 | iPhone 14 Pro | 16.0-18.x |
| iPhone16,1 | iPhone 15 Pro | 17.0-18.x |
| iPhone17,1 | iPhone 16 Pro | 18.0-18.x |

*والمزيد...*

## 🖥️ الاستخدام

### واجهة الويب
1. افتح المتصفح على: `http://127.0.0.1:5000`
2. اختر "فحص الجهاز"
3. أدخل معلومات الجهاز
4. انتظر النتيجة

### واجهة سطح المكتب
```bash
python device_ui.py
# أو
start_device_ui.bat
```

Open http://127.0.0.1:5000 in your browser. Use the Register form to add serials (stored in `serials.db`). The list supports search, refresh, and delete operations.

Admin / delete operations
- To delete serials you must log in as admin. The app reads an `ADMIN_PASSWORD` environment variable (defaults to `admin` in development). You can set it before running:

```powershell
$env:ADMIN_PASSWORD='yourpassword'; $env:FLASK_SECRET='a-secret'; python "c:\Users\ayoub\OneDrive\Bureau\rif-activator tool\app.py"
```

- Use the "Admin Login" button on the site, enter the password, and delete buttons will appear next to each serial.

API endpoints (internal)
- `GET /api/list_serials?q=` — returns JSON: {serials: [...]}
- `POST /` — accepts JSON {serial: "..."} or form POST to register a serial (returns JSON on AJAX)
- `POST /api/delete_serial` — delete a serial (requires admin session)
- `POST /login` — admin login (JSON {password: '...'})
- `POST /logout` — admin logout
- `GET /api/is_admin` — check admin session

Notes & next steps
- Replace `static/img/logo.svg` and `static/img/telegram.svg` with your official assets for branding.
- Consider adding persistent user accounts or stronger auth if exposing this server publicly.
