#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RiF Activator Project Cleaner
تنظيف المشروع وحذف الملفات غير المفيدة
"""

import os
import shutil
import glob
from pathlib import Path

class ProjectCleaner:
    """منظف المشروع"""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        
        # الملفات والمجلدات المهمة (لا نحذفها)
        self.keep_files = {
            # ملفات التطبيق الأساسية
            "app.py",
            "main.py", 
            "device_ui.py",
            "requirements.txt",
            "README.md",
            
            # ملفات قاعدة البيانات المهمة
            "serials.db",
            
            # ملفات الإعدادات
            ".env",
            ".env.example",
            
            # أدوات libimobiledevice مهمة
            "ideviceinfo.exe",
            "idevicepair.exe", 
            "idevicediagnostics.exe",
            
            # مجلدات مهمة
            "templates/",
            "static/",
            ".venv/",
            
            # ملفات مفيدة للمستخدم
            "mobile_gestalt_parser.py",
            "read_real_device.py",
            "real_device_test.py",
            "system_test.py",
            
            # ملفات البيانات المهمة
            "com.apple.MobileGestalt.plist",
            "real_device_info.json",
            "device_analysis.json"
        }
        
        # الملفات التي يجب حذفها (غير مفيدة)
        self.delete_files = {
            # ملفات نسخ احتياطية غير مفيدة
            "device_ui.py.backup",
            "device_ui_new.py",
            "api_integration_backup.py",
            
            # ملفات تحذيرية (تمت قراءتها)
            "bypass_script_warning.py",
            "system_modification_warning.py", 
            "final_no_bypass.py",
            "bypass_guide.py",
            "rif_bypass_simulation.py",
            
            # ملفات توثيق إضافية
            "api_documentation.py",
            "api_documentation.json",
            "api_documentation.yaml",
            "API_DOCUMENTATION_GUIDE.md",
            "FINAL_API_DOCUMENTATION_REPORT.md",
            "REPORTS_README.md",
            "README_DEPLOY.md",
            
            # ملفات إعداد غير مستخدمة
            "docker-compose.yml",
            "docker-compose.no-tls.yml", 
            "Dockerfile",
            "Caddyfile",
            "deploy.sh",
            "run_prod.py",
            "requirements-prod.txt",
            "main.spec",
            
            # ملفات إضافية غير مهمة
            "add_supported_models.py",
            "check_db.py", 
            "create_sample_data.py",
            "notification_manager.py",
            "reports_cli.py",
            "reports_manager.py",
            "report_scheduler.py",
            "security_manager.py",
            "swagger_ui.py",
            
            # ملفات بيانات مؤقتة
            "model_map.json",
            "report_schedules.json",
            "safety_report.json",
            "rif_report_30d.pdf",
            
            # ملفات الدليل التعليمية
            "real_device_guide.py",
            "safe_old_device_test.py"
        }
        
        # ملفات Log يمكن حذفها
        self.delete_patterns = [
            "*.log",
            "serials.db.bak_*",
            "serials.db.*Z.bak",
            "activations.db",
            "activator.db"
        ]
        
        # مجلدات يمكن حذفها
        self.delete_folders = {
            "extracted_bypass_files/",
            "logs/",
            "reports_output/", 
            "scripts/",
            "__pycache__/"
        }
    
    def analyze_project(self):
        """تحليل الملفات في المشروع"""
        print("🔍 تحليل ملفات المشروع...")
        print("="*50)
        
        all_files = []
        total_size = 0
        
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                filepath = os.path.join(root, file)
                relative_path = os.path.relpath(filepath, self.project_root)
                size = os.path.getsize(filepath)
                all_files.append((relative_path, size))
                total_size += size
        
        print(f"📊 إجمالي الملفات: {len(all_files)}")
        print(f"💾 الحجم الكلي: {total_size / (1024*1024):.2f} MB")
        
        return all_files, total_size
    
    def identify_files_to_delete(self):
        """تحديد الملفات للحذف"""
        files_to_delete = []
        size_to_save = 0
        
        # ملفات محددة للحذف
        for filename in self.delete_files:
            filepath = os.path.join(self.project_root, filename)
            if os.path.exists(filepath):
                size = os.path.getsize(filepath)
                files_to_delete.append((filename, size, "ملف غير مفيد"))
                size_to_save += size
        
        # ملفات بالنمط
        for pattern in self.delete_patterns:
            matches = glob.glob(os.path.join(self.project_root, pattern))
            for match in matches:
                relative_path = os.path.relpath(match, self.project_root)
                if relative_path not in [item[0] for item in files_to_delete]:
                    size = os.path.getsize(match)
                    files_to_delete.append((relative_path, size, "ملف مؤقت"))
                    size_to_save += size
        
        # مجلدات للحذف
        for folder in self.delete_folders:
            folder_path = os.path.join(self.project_root, folder)
            if os.path.exists(folder_path):
                folder_size = self.get_folder_size(folder_path)
                files_to_delete.append((folder, folder_size, "مجلد غير مفيد"))
                size_to_save += folder_size
        
        return files_to_delete, size_to_save
    
    def get_folder_size(self, folder_path):
        """حساب حجم المجلد"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
    
    def show_cleanup_plan(self, files_to_delete, size_to_save):
        """عرض خطة التنظيف"""
        print(f"\n🗑️ خطة التنظيف:")
        print("="*50)
        
        categories = {}
        for filename, size, category in files_to_delete:
            if category not in categories:
                categories[category] = []
            categories[category].append((filename, size))
        
        for category, items in categories.items():
            print(f"\n📂 {category}:")
            category_size = 0
            for filename, size in items:
                print(f"   🗑️ {filename} ({size/1024:.1f} KB)")
                category_size += size
            print(f"   💾 إجمالي الفئة: {category_size/1024:.1f} KB")
        
        print(f"\n📊 ملخص التنظيف:")
        print(f"   🗑️ ملفات للحذف: {len(files_to_delete)}")
        print(f"   💾 مساحة ستوفر: {size_to_save/(1024*1024):.2f} MB")
    
    def perform_cleanup(self, files_to_delete):
        """تنفيذ التنظيف"""
        print(f"\n🧹 بدء تنظيف المشروع...")
        print("="*30)
        
        deleted_count = 0
        failed_count = 0
        
        for filename, size, category in files_to_delete:
            filepath = os.path.join(self.project_root, filename)
            
            try:
                if os.path.isdir(filepath):
                    shutil.rmtree(filepath)
                    print(f"✅ حذف مجلد: {filename}")
                elif os.path.isfile(filepath):
                    os.remove(filepath)
                    print(f"✅ حذف ملف: {filename}")
                else:
                    continue
                    
                deleted_count += 1
                
            except Exception as e:
                print(f"❌ فشل حذف {filename}: {e}")
                failed_count += 1
        
        print(f"\n📊 نتائج التنظيف:")
        print(f"   ✅ تم حذف: {deleted_count} عنصر")
        if failed_count > 0:
            print(f"   ❌ فشل حذف: {failed_count} عنصر")
    
    def create_project_summary(self):
        """إنشاء ملخص المشروع النهائي"""
        remaining_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            for file in files:
                relative_path = os.path.relpath(os.path.join(root, file), self.project_root)
                remaining_files.append(relative_path)
        
        summary = {
            "project_name": "RiF Activator A12+",
            "cleaned_date": "2025-11-05",
            "remaining_files": len(remaining_files),
            "important_files": {
                "main_app": "app.py",
                "gui_app": "device_ui.py", 
                "server": "main.py",
                "database": "serials.db",
                "device_parser": "mobile_gestalt_parser.py",
                "device_reader": "read_real_device.py",
                "system_test": "system_test.py"
            },
            "key_features": [
                "آمن 100% - لا تعديل في النظام",
                "يدعم iPhone XS و iOS 18.7.1+", 
                "واجهة ويب وسطح مكتب",
                "قراءة معلومات الجهاز الحقيقي",
                "تفعيل عبر الخادم الآمن"
            ]
        }
        
        with open("project_summary.json", "w", encoding="utf-8") as f:
            import json
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 تم إنشاء ملخص المشروع: project_summary.json")

def main():
    """الدالة الرئيسية"""
    cleaner = ProjectCleaner()
    
    print("🧹 RiF Activator Project Cleaner")
    print("="*40)
    
    # تحليل المشروع
    all_files, total_size = cleaner.analyze_project()
    
    # تحديد ملفات الحذف
    files_to_delete, size_to_save = cleaner.identify_files_to_delete()
    
    # عرض خطة التنظيف
    cleaner.show_cleanup_plan(files_to_delete, size_to_save)
    
    # طلب التأكيد
    print(f"\n❓ هل تريد المتابعة مع التنظيف؟ (y/n): ", end="")
    response = input().lower()
    
    if response in ['y', 'yes', 'نعم', '1']:
        # تنفيذ التنظيف
        cleaner.perform_cleanup(files_to_delete)
        
        # إنشاء ملخص المشروع
        cleaner.create_project_summary()
        
        print(f"\n🎉 تم تنظيف المشروع بنجاح!")
        print(f"💾 تم توفير {size_to_save/(1024*1024):.2f} MB من المساحة")
        
    else:
        print(f"\n❌ تم إلغاء التنظيف")
    
    print(f"\n✅ انتهت عملية التحليل")

if __name__ == "__main__":
    main()