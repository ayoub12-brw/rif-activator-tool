#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RiF Activator Server Manager
مدير خادم RiF Activator - إعادة تشغيل وإصلاح المشاكل
"""

import os
import sys
import subprocess
import time
import requests
import psutil

def kill_existing_servers():
    """إيقاف الخوادم الموجودة"""
    print("🔄 إيقاف الخوادم الموجودة...")
    
    killed_count = 0
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] == 'python.exe' or proc.info['name'] == 'python':
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'main.py' in cmdline or 'app.py' in cmdline or 'device_ui.py' in cmdline:
                    print(f"   ⏹️ إيقاف العملية: PID {proc.info['pid']}")
                    proc.kill()
                    killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    if killed_count > 0:
        print(f"   ✅ تم إيقاف {killed_count} عملية")
        time.sleep(2)  # انتظار حتى تتوقف العمليات
    else:
        print("   📝 لا توجد عمليات لإيقافها")

def check_server_status():
    """التحقق من حالة الخادم"""
    print("🔍 التحقق من حالة الخادم...")
    
    try:
        response = requests.get('http://127.0.0.1:5000/api/live_stats', timeout=3)
        if response.status_code == 200:
            data = response.json()
            stats = data.get('stats', {})
            print("   ✅ الخادم يعمل بشكل صحيح")
            print(f"   📊 المستخدمين النشطين: {stats.get('active_users', 0)}")
            print(f"   📈 معدل النجاح: {stats.get('success_rate', '0%')}")
            return True
        else:
            print(f"   ⚠️ الخادم يرد بكود خطأ: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("   ❌ لا يمكن الاتصال بالخادم")
        return False
    except Exception as e:
        print(f"   ❌ خطأ في الاتصال: {e}")
        return False

def start_server():
    """تشغيل الخادم الجديد"""
    print("🚀 تشغيل خادم جديد...")
    
    try:
        # التأكد من وجود الملفات المطلوبة
        required_files = ['main.py', 'app.py', 'serials.db']
        missing_files = [f for f in required_files if not os.path.exists(f)]
        
        if missing_files:
            print(f"   ❌ ملفات مفقودة: {', '.join(missing_files)}")
            return False
        
        # تشغيل الخادم
        print("   ⏳ بدء تشغيل main.py...")
        
        process = subprocess.Popen(
            [sys.executable, 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # انتظار قصير للتأكد من بدء التشغيل
        time.sleep(3)
        
        # التحقق من أن العملية لا تزال تعمل
        if process.poll() is None:
            print("   ✅ تم تشغيل الخادم بنجاح")
            return True
        else:
            stdout, stderr = process.communicate()
            print(f"   ❌ فشل في تشغيل الخادم")
            if stderr:
                print(f"   خطأ: {stderr[:200]}...")
            return False
            
    except Exception as e:
        print(f"   ❌ خطأ في تشغيل الخادم: {e}")
        return False

def diagnose_connection_issues():
    """تشخيص مشاكل الاتصال"""
    print("🔧 تشخيص مشاكل الاتصال...")
    
    # فحص المنفذ 5000
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex(('127.0.0.1', 5000))
        sock.close()
        
        if result == 0:
            print("   ✅ المنفذ 5000 متاح للاتصال")
        else:
            print("   ❌ المنفذ 5000 غير متاح")
            
    except Exception as e:
        print(f"   ⚠️ خطأ في فحص المنفذ: {e}")
    
    # فحص قاعدة البيانات
    if os.path.exists('serials.db'):
        print("   ✅ قاعدة البيانات موجودة")
        
        try:
            import sqlite3
            conn = sqlite3.connect('serials.db')
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM supported_models')
            count = c.fetchone()[0]
            conn.close()
            print(f"   📊 الموديلات المدعومة: {count}")
        except Exception as e:
            print(f"   ⚠️ مشكلة في قاعدة البيانات: {e}")
    else:
        print("   ❌ قاعدة البيانات مفقودة")
    
    # فحص الملفات المهمة
    important_files = {
        'main.py': 'ملف الخادم الرئيسي',
        'app.py': 'تطبيق Flask',
        'device_ui.py': 'واجهة الجهاز',
        'templates/': 'قوالب HTML'
    }
    
    print("   📁 فحص الملفات المهمة:")
    for file_path, description in important_files.items():
        if os.path.exists(file_path):
            print(f"     ✅ {description}: موجود")
        else:
            print(f"     ❌ {description}: مفقود")

def fix_common_issues():
    """إصلاح المشاكل الشائعة"""
    print("🔧 إصلاح المشاكل الشائعة...")
    
    # إنشاء مجلد logs إذا لم يكن موجود
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("   ✅ تم إنشاء مجلد logs")
    
    # إنشاء مجلد static إذا لم يكن موجود
    if not os.path.exists('static'):
        os.makedirs('static')
        print("   ✅ تم إنشاء مجلد static")
    
    # التحقق من أذونات الملفات
    try:
        test_file = 'test_permissions.tmp'
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        print("   ✅ أذونات الكتابة متاحة")
    except Exception as e:
        print(f"   ⚠️ مشكلة في أذونات الملفات: {e}")

def main():
    """الدالة الرئيسية"""
    print("🔧 RiF Activator Server Manager")
    print("="*50)
    
    print("المرحلة 1: إيقاف الخوادم الموجودة")
    kill_existing_servers()
    
    print("\nالمرحلة 2: تشخيص المشاكل")
    diagnose_connection_issues()
    
    print("\nالمرحلة 3: إصلاح المشاكل الشائعة")
    fix_common_issues()
    
    print("\nالمرحلة 4: تشغيل خادم جديد")
    if start_server():
        print("\nالمرحلة 5: التحقق من الخادم الجديد")
        time.sleep(2)
        if check_server_status():
            print("\n🎉 تم إصلاح المشكلة بنجاح!")
            print("\nيمكنك الآن:")
            print("   • فتح المتصفح على: http://127.0.0.1:5000")
            print("   • تشغيل device_ui.py")
            print("   • استخدام التطبيق بشكل طبيعي")
        else:
            print("\n❌ مازالت هناك مشكلة في الخادم")
    else:
        print("\n❌ فشل في تشغيل خادم جديد")
        
    print("\n" + "="*50)

if __name__ == "__main__":
    main()