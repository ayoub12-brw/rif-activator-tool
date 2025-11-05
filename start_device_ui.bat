@echo off
chcp 65001 > nul
title RiF Activator A12+ Device Interface
color 0B

echo.
echo =====================================
echo   RiF Activator A12+ Device Interface
echo =====================================
echo.
echo 📱 جاري تشغيل واجهة الجهاز...
echo.

cd /d "%~dp0"

echo 📋 التحقق من المتطلبات...
python --version > nul 2>&1
if errorlevel 1 (
    echo ❌ Python غير مثبت!
    pause
    exit /b 1
)

echo ✅ Python متوفر

echo.
echo 📦 تثبيت المتطلبات...
pip install PyQt5 requests > nul 2>&1

echo.
echo 🔌 تأكد من توصيل جهاز iPhone
echo 🖥️ جاري فتح واجهة المستخدم...
echo.
echo =====================================
echo.

python device_ui.py

pause