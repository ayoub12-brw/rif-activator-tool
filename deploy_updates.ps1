# 🚀 RiF Activator A12+ - نشر التحديثات السريع (Windows PowerShell)

Write-Host "🚀 بدء نشر التحديثات..." -ForegroundColor Green

# التأكد من أننا في المجلد الصحيح
if (!(Test-Path "app_simple.py")) {
    Write-Host "❌ خطأ: لا يمكن العثور على app_simple.py" -ForegroundColor Red
    Write-Host "تأكد من أنك في مجلد المشروع الصحيح" -ForegroundColor Yellow
    exit 1
}

Write-Host "📋 التحقق من الملفات المُحدَّثة..." -ForegroundColor Cyan
git status --porcelain

Write-Host ""
$response = Read-Host "هل تريد المتابعة مع النشر؟ (y/N)"

if ($response -notmatch "^[Yy]$") {
    Write-Host "❌ تم إلغاء النشر" -ForegroundColor Red
    exit 1
}

Write-Host "📦 إضافة الملفات المُحدَّثة..." -ForegroundColor Cyan
git add .

Write-Host "💬 كتابة رسالة التحديث..." -ForegroundColor Cyan
$commitMsg = @"
✨ تحديثات النشر: إضافة صفحات اختبار النشر وتحسين التوجيه

- إضافة صفحة deployment-success.html لتأكيد نجح النشر
- إضافة صفحة test-deployment.html لاختبار شامل  
- إضافة deployment_test.py لفحص جميع المسارات
- تحديث sitemap.html لتشمل الصفحات الجديدة
- تحسين إحصائيات خريطة الموقع
- إضافة routes جديدة في app_simple.py
- تحسين تجربة المستخدم على Render
"@

git commit -m $commitMsg

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ خطأ في إنشاء commit" -ForegroundColor Red
    exit 1
}

Write-Host "🌐 رفع التحديثات إلى GitHub..." -ForegroundColor Cyan
git push origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ تم النشر بنجاح!" -ForegroundColor Green
    Write-Host "🎉 التحديثات موجودة الآن على:" -ForegroundColor Yellow
    Write-Host "   📱 GitHub: https://github.com/YOUR_USERNAME/rif-activator-tool" -ForegroundColor Blue
    Write-Host "   🌐 Render: https://rif-activator-tool.onrender.com" -ForegroundColor Blue
    Write-Host ""
    Write-Host "🧪 يمكنك الآن اختبار النشر باستخدام:" -ForegroundColor Cyan
    Write-Host "   python deployment_test.py https://rif-activator-tool.onrender.com" -ForegroundColor White
    Write-Host ""
    Write-Host "📄 الصفحات الجديدة:" -ForegroundColor Yellow
    Write-Host "   🎉 /deployment-success - صفحة تأكيد النشر" -ForegroundColor White
    Write-Host "   🧪 /test-deployment - صفحة اختبار شاملة" -ForegroundColor White
    Write-Host ""
}
else {
    Write-Host "❌ خطأ في الرفع إلى GitHub" -ForegroundColor Red
    Write-Host "تحقق من اتصال الإنترنت وصلاحيات Git" -ForegroundColor Yellow
    exit 1
}