#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RiF Activator A12+ - Simplified Main Entry Point
نقطة الدخول المبسطة لـ RiF Activator A12+
"""

import os
import sys

try:
    # تشغيل الإصدار المبسط
    from app_simple import app
    
    print("🚀 RiF Activator A12+ Server (Simplified) Starting...")
    print("=" * 50)
    
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=False,
        use_reloader=False
    )
    
except ImportError as e:
    print(f"❌ خطأ في الاستيراد: {e}")
    print("💡 تأكد من وجود جميع الملفات المطلوبة")
    sys.exit(1)
    
except KeyboardInterrupt:
    print("\n🛑 تم إيقاف الخادم")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ خطأ غير متوقع: {e}")
    sys.exit(1)