#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File Cleanup Tool - RiF Activator
أداة تنظيف الملفات - RiF Activator
"""

import os
import shutil
import glob

def clean_unnecessary_files():
    """حذف الملفات غير الضرورية"""
    print("🧹 تنظيف الملفات غير الضرورية...")
    
    # ملفات مؤقتة للحذف
    temp_patterns = [
        '*.tmp',
        '*.log',
        '*.pyc',
        '__pycache__/*',
        '.DS_Store',
        'Thumbs.db',
        '*.bak',
        '*.swp',
        '*.swo',
        'test_*.py',  # ملفات الاختبار المؤقتة
        '*_test.py'   # ملفات اختبار إضافية
    ]
    
    cleaned_count = 0
    
    for pattern in temp_patterns:
        files = glob.glob(pattern, recursive=True)
        for file_path in files:
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"   🗑️ حذف ملف: {file_path}")
                    cleaned_count += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    print(f"   🗑️ حذف مجلد: {file_path}")
                    cleaned_count += 1
            except Exception as e:
                print(f"   ⚠️ لا يمكن حذف {file_path}: {e}")
    
    # حذف ملفات اختبار معينة
    test_files = [
        'real_device_test.py',
        'test_permissions.tmp',
        'device_test.py',
        'server_test.py'
    ]
    
    for file_path in test_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"   🗑️ حذف ملف اختبار: {file_path}")
                cleaned_count += 1
            except Exception as e:
                print(f"   ⚠️ لا يمكن حذف {file_path}: {e}")
    
    # تنظيف مجلد logs القديمة
    if os.path.exists('logs'):
        log_files = glob.glob('logs/*.log')
        for log_file in log_files:
            try:
                # الاحتفاظ بآخر 3 ملفات سجل فقط
                if len(log_files) > 3:
                    os.remove(log_file)
                    print(f"   🗑️ حذف سجل قديم: {log_file}")
                    cleaned_count += 1
            except Exception as e:
                print(f"   ⚠️ لا يمكن حذف {log_file}: {e}")
    
    print(f"   ✅ تم تنظيف {cleaned_count} ملف/مجلد")

def organize_project_structure():
    """تنظيم هيكل المشروع"""
    print("📁 تنظيم هيكل المشروع...")
    
    # إنشاء المجلدات المطلوبة
    required_dirs = [
        'static/css',
        'static/js',
        'static/img',
        'templates',
        'logs',
        'backups',
        'tools'
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
            print(f"   📂 إنشاء مجلد: {dir_path}")
    
    # نقل الأدوات إلى مجلد tools
    tool_files = [
        'mobile_gestalt_parser.py',
        'server_manager.py',
        'file_cleanup.py'
    ]
    
    for tool_file in tool_files:
        if os.path.exists(tool_file) and not os.path.exists(f'tools/{tool_file}'):
            try:
                shutil.copy2(tool_file, f'tools/{tool_file}')
                print(f"   📋 نسخ أداة: {tool_file} → tools/")
            except Exception as e:
                print(f"   ⚠️ لا يمكن نقل {tool_file}: {e}")

def backup_important_files():
    """نسخ احتياطي للملفات المهمة"""
    print("💾 إنشاء نسخة احتياطية...")
    
    important_files = [
        'main.py',
        'app.py', 
        'device_ui.py',
        'serials.db'
    ]
    
    # إنشاء مجلد النسخ الاحتياطية
    backup_dir = 'backups'
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    for file_path in important_files:
        if os.path.exists(file_path):
            try:
                backup_path = f'{backup_dir}/{file_path}_{timestamp}.bak'
                shutil.copy2(file_path, backup_path)
                print(f"   💾 نسخ احتياطي: {file_path} → {backup_path}")
            except Exception as e:
                print(f"   ⚠️ لا يمكن نسخ {file_path}: {e}")

def check_file_integrity():
    """التحقق من سلامة الملفات"""
    print("🔍 التحقق من سلامة الملفات...")
    
    # فحص الملفات الأساسية
    core_files = {
        'main.py': 'ملف الخادم الرئيسي',
        'app.py': 'تطبيق Flask الأساسي', 
        'device_ui.py': 'واجهة المستخدم',
        'serials.db': 'قاعدة البيانات',
        'requirements.txt': 'متطلبات Python'
    }
    
    issues = []
    
    for file_path, description in core_files.items():
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            if size > 0:
                print(f"   ✅ {description}: موجود ({size} بايت)")
            else:
                print(f"   ⚠️ {description}: ملف فارغ")
                issues.append(f"{description} فارغ")
        else:
            print(f"   ❌ {description}: مفقود")
            issues.append(f"{description} مفقود")
    
    # فحص المجلدات
    required_dirs = ['templates', 'static', 'libimobiledevice-windows-master']
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path):
            files_count = len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
            print(f"   ✅ مجلد {dir_path}: موجود ({files_count} ملف)")
        else:
            print(f"   ❌ مجلد {dir_path}: مفقود")
            issues.append(f"مجلد {dir_path} مفقود")
    
    if issues:
        print(f"\n⚠️ تم العثور على {len(issues)} مشكلة:")
        for issue in issues:
            print(f"   • {issue}")
    else:
        print("\n✅ جميع الملفات سليمة!")

def show_project_summary():
    """عرض ملخص المشروع"""
    print("📊 ملخص المشروع:")
    print("="*40)
    
    # حساب عدد الملفات والمجلدات
    total_files = 0
    total_dirs = 0
    
    for root, dirs, files in os.walk('.'):
        # تجاهل المجلدات المخفية
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        total_dirs += len(dirs)
        total_files += len(files)
    
    print(f"📁 المجلدات: {total_dirs}")
    print(f"📄 الملفات: {total_files}")
    
    # حساب حجم المشروع
    total_size = 0
    for root, dirs, files in os.walk('.'):
        for file in files:
            file_path = os.path.join(root, file)
            try:
                total_size += os.path.getsize(file_path)
            except:
                pass
    
    size_mb = total_size / (1024 * 1024)
    print(f"💽 حجم المشروع: {size_mb:.1f} ميجابايت")
    
    # أهم الملفات
    print("\n📋 الملفات الأساسية:")
    key_files = ['main.py', 'app.py', 'device_ui.py', 'serials.db']
    for file_path in key_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path) / 1024  # KB
            print(f"   ✅ {file_path}: {size:.1f} KB")

def main():
    """الدالة الرئيسية"""
    print("🧹 File Cleanup Tool - RiF Activator")
    print("="*50)
    
    print("المرحلة 1: إنشاء نسخة احتياطية")
    backup_important_files()
    
    print("\nالمرحلة 2: تنظيف الملفات غير الضرورية")
    clean_unnecessary_files()
    
    print("\nالمرحلة 3: تنظيم هيكل المشروع")
    organize_project_structure()
    
    print("\nالمرحلة 4: التحقق من سلامة الملفات")
    check_file_integrity()
    
    print("\nالمرحلة 5: ملخص المشروع")
    show_project_summary()
    
    print("\n🎉 تم الانتهاء من تنظيف المشروع!")
    print("="*50)

if __name__ == "__main__":
    main()