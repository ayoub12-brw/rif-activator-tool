@echo off
chcp 65001 > nul
title RiF Activator A12+ Server
color 0A

echo.
echo =====================================
echo    RiF Activator A12+ Server
echo =====================================
echo.
echo 🚀 جاري تشغيل الخادم...
echo.

cd /d "%~dp0"

echo 📋 التحقق من المتطلبات...
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python غير مثبت!
    echo 💡 يرجى تثبيت Python من python.org
    pause
    exit /b 1
)

echo ✅ Python متوفر

echo.
echo 📦 تثبيت المتطلبات...
pip install flask > nul 2>&1

echo.
echo 🌐 تشغيل الخادم على العنوان: http://127.0.0.1:5000
echo 🛑 لإيقاف الخادم اضغط Ctrl+C
echo.
echo =====================================
echo.

python app_simple.py

pause