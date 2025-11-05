#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Alternative Server Configuration
إعداد خادم بديل للتطوير والإنتاج
"""

import os
import sys
from app_simple import app

def run_development_server():
    """تشغيل خادم التطوير"""
    print("🚀 تشغيل خادم التطوير Flask...")
    print("📱 RiF Activator A12+ - Development Server")
    print("🌐 الرابط: http://localhost:5000")
    print("⚠️  للإنتاج، استخدم Gunicorn على Linux/Unix")
    
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=False,  # False للأمان حتى في التطوير
        threaded=True,  # دعم التشغيل المتوازي
        use_reloader=False
    )

def run_waitress_server():
    """تشغيل خادم Waitress (بديل Gunicorn للويندوز)"""
    try:
        from waitress import serve
        print("🦄 تشغيل خادم Waitress...")
        print("📱 RiF Activator A12+ - Waitress Server")
        print("🌐 الرابط: http://localhost:5000")
        
        serve(
            app,
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 5000)),
            threads=4,
            connection_limit=1000,
            cleanup_interval=30,
            channel_timeout=120
        )
    except ImportError:
        print("❌ Waitress غير مثبت. جاري التبديل لخادم Flask...")
        run_development_server()

if __name__ == "__main__":
    # تحديد نوع الخادم حسب النظام والبيئة
    if sys.platform == "win32":
        # Windows - استخدم Waitress أو Flask
        if os.environ.get('USE_WAITRESS', 'true').lower() == 'true':
            run_waitress_server()
        else:
            run_development_server()
    else:
        # Linux/Unix - يمكن استخدام Gunicorn
        print("💡 على Linux/Unix، استخدم: gunicorn --config gunicorn_config.py wsgi:application")
        run_development_server()