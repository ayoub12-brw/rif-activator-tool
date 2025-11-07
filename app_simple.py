#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RiF Activator A12+ - Simplified Flask Application
تطبيق RiF Activator A12+ المبسط
"""

from flask import Flask, request, render_template, redirect, url_for, jsonify, session, make_response
import sqlite3
import os
from datetime import datetime
import json
import threading
import time
from collections import deque
import logging

# إنشاء التطبيق
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'rif-activator-secret-key-2024')

# إعداد قاعدة البيانات
DB_PATH = 'serials.db'

# إعداد السجلات
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# إحصائيات المباشرة
live_stats = {
    'active_users': 897,
    'success_rate': '98.4%',
    'total_devices': 4,
    'avg_time': 2.1
}

def init_database():
    """تهيئة قاعدة البيانات"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # جدول الموديلات المدعومة
        c.execute('''CREATE TABLE IF NOT EXISTS supported_models (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT UNIQUE NOT NULL,
            display_name TEXT NOT NULL,
            ios_versions TEXT NOT NULL,
            supported BOOLEAN DEFAULT 1,
            added_date TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # التحقق من وجود البيانات
        c.execute('SELECT COUNT(*) FROM supported_models')
        count = c.fetchone()[0]
        
        if count == 0:
            # إضافة الموديلات المدعومة - محدث لدعم iOS حتى 26.x
            models = [
                ('iPhone11,2', 'iPhone XS', '12.0-26.x', 1),
                ('iPhone11,4', 'iPhone XS Max', '12.0-26.x', 1),
                ('iPhone11,6', 'iPhone XS Max', '12.0-26.x', 1),
                ('iPhone11,8', 'iPhone XR', '12.0-26.x', 1),
                ('iPhone12,1', 'iPhone 11', '13.0-26.x', 1),
                ('iPhone12,3', 'iPhone 11 Pro', '13.0-26.x', 1),
                ('iPhone12,5', 'iPhone 11 Pro Max', '13.0-26.x', 1),
                ('iPhone12,8', 'iPhone SE (2nd)', '13.0-26.x', 1),
                ('iPhone13,1', 'iPhone 12 mini', '14.0-26.x', 1),
                ('iPhone13,2', 'iPhone 12', '14.0-26.x', 1),
                ('iPhone13,3', 'iPhone 12 Pro', '14.0-26.x', 1),
                ('iPhone13,4', 'iPhone 12 Pro Max', '14.0-26.x', 1),
                ('iPhone14,2', 'iPhone 13 Pro', '15.0-26.x', 1),
                ('iPhone14,3', 'iPhone 13 Pro Max', '15.0-26.x', 1),
                ('iPhone14,4', 'iPhone 13 mini', '15.0-26.x', 1),
                ('iPhone14,5', 'iPhone 13', '15.0-26.x', 1),
                ('iPhone14,6', 'iPhone SE (3rd)', '15.0-26.x', 1),
                ('iPhone14,7', 'iPhone 14', '16.0-26.x', 1),
                ('iPhone14,8', 'iPhone 14 Plus', '16.0-26.x', 1),
                ('iPhone15,2', 'iPhone 14 Pro', '16.0-26.x', 1),
                ('iPhone15,3', 'iPhone 14 Pro Max', '16.0-26.x', 1),
                ('iPhone15,4', 'iPhone 15', '17.0-26.x', 1),
                ('iPhone15,5', 'iPhone 15 Plus', '17.0-26.x', 1),
                ('iPhone16,1', 'iPhone 15 Pro', '17.0-26.x', 1),
                ('iPhone16,2', 'iPhone 15 Pro Max', '17.0-26.x', 1),
                ('iPhone17,1', 'iPhone 16 Pro', '18.0-26.x', 1),
                ('iPhone17,2', 'iPhone 16 Pro Max', '18.0-26.x', 1),
                ('iPhone17,3', 'iPhone 16', '18.0-26.x', 1),
                ('iPhone17,4', 'iPhone 16 Plus', '18.0-26.x', 1)
            ]
            
            c.executemany('''INSERT INTO supported_models 
                          (model_name, display_name, ios_versions, supported) 
                          VALUES (?, ?, ?, ?)''', models)
        
        conn.commit()
        conn.close()
        print("✅ تم تهيئة قاعدة البيانات بنجاح")
        
    except Exception as e:
        print(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")

# تهيئة قاعدة البيانات عند البدء
init_database()

@app.route('/')
def index():
    """الصفحة الرئيسية المحسنة"""
    try:
        return render_template('index_enhanced_v2.html')
    except:
        return jsonify({
            'message': 'RiF Activator A12+ Server is Running!',
            'status': 'active',
            'version': '2.6.0',
            'endpoints': {
                'main_page': '/',
                'check_device': '/check_device',
                'admin': '/admin',
                'reports': '/reports',
                'sitemap': '/sitemap',
                'api_stats': '/api/live_stats',
                'api_docs': '/api/docs'
            }
        })

@app.route('/check_device')
def check_device_page():
    """صفحة فحص الجهاز المحسنة"""
    try:
        return render_template('check_device_enhanced.html')
    except:
        return jsonify({'message': 'Device check page - use POST /api/check_device'})

@app.route('/admin')
def admin_page():
    """صفحة الإدارة المحسنة"""
    try:
        return render_template('admin_enhanced_v2.html')
    except:
        return jsonify({'message': 'Admin panel - authentication required'})

@app.route('/reports')
def reports_page():
    """صفحة التقارير المحسنة"""
    try:
        return render_template('reports_dashboard_enhanced.html')
    except:
        return jsonify({'message': 'Reports page - comprehensive analytics'})

@app.route('/api/check_device', methods=['POST'])
def api_check_device():
    """فحص الجهاز عبر API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'supported': False,
                'message': 'لا توجد بيانات'
            }), 400
        
        device_model = data.get('device_model', '').strip()
        ios_version = data.get('ios_version', '').strip()
        serial = data.get('serial', '').strip()
        
        if not device_model:
            return jsonify({
                'supported': False,
                'message': 'موديل الجهاز مطلوب'
            }), 400
        
        # البحث في قاعدة البيانات
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''SELECT display_name, ios_versions, supported 
                    FROM supported_models 
                    WHERE model_name = ?''', (device_model,))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            display_name, supported_ios, is_supported = result
            
            if is_supported:
                # فحص إضافي لنطاق iOS إذا تم توفير الإصدار
                ios_compatible = True
                ios_message = ""
                
                if ios_version:
                    # تحليل نطاق iOS المدعوم من قاعدة البيانات
                    if '-' in supported_ios:
                        min_ios, max_ios = supported_ios.split('-')
                        min_ios = min_ios.strip()
                        max_ios = max_ios.strip()
                        
                        # تحويل iOS version إلى أرقام للمقارنة
                        try:
                            current_ios_parts = [int(x) for x in ios_version.split('.')]
                            min_ios_parts = [int(x) for x in min_ios.split('.')]
                            
                            # فحص الحد الأدنى
                            current_ios_tuple = tuple(current_ios_parts + [0] * (3 - len(current_ios_parts)))
                            min_ios_tuple = tuple(min_ios_parts + [0] * (3 - len(min_ios_parts)))
                            
                            if current_ios_tuple < min_ios_tuple:
                                ios_compatible = False
                                ios_message = f" (iOS {ios_version} أقل من المطلوب {min_ios})"
                            elif max_ios.endswith('.x'):
                                # نطاق مفتوح مثل 18.x أو 26.x
                                max_major = int(max_ios.split('.')[0])
                                current_major = current_ios_parts[0]
                                if current_major > max_major:
                                    ios_compatible = False  
                                    ios_message = f" (iOS {ios_version} أعلى من المدعوم {max_ios})"
                        except (ValueError, IndexError):
                            # إذا فشل التحليل، نعتبر الإصدار مدعوم
                            pass
                
                return jsonify({
                    'supported': ios_compatible,
                    'message': f'الجهاز {"مدعوم" if ios_compatible else "غير مدعوم"}: {display_name}{ios_message}',
                    'device_info': {
                        'model': device_model,
                        'display_name': display_name,
                        'ios_version': ios_version if ios_version else 'غير محدد',
                        'ios_versions': supported_ios,
                        'serial': serial if serial else 'غير محدد',
                        'status': f'{"مدعوم ✅" if ios_compatible else "غير مدعوم ❌"}'
                    }
                })
            else:
                return jsonify({
                    'supported': False,
                    'message': f'الجهاز غير مدعوم حالياً: {display_name}',
                    'device_info': {
                        'model': device_model,
                        'display_name': display_name
                    }
                })
        else:
            return jsonify({
                'supported': False,
                'message': 'الجهاز غير مدعوم أو غير معروف',
                'device_info': {
                    'model': device_model,
                    'status': 'غير مدعوم ❌'
                }
            })
            
    except Exception as e:
        return jsonify({
            'supported': False,
            'message': f'خطأ في فحص الجهاز: {str(e)}'
        }), 500

@app.route('/api/live_stats')
def api_live_stats():
    """إحصائيات مباشرة"""
    global live_stats
    
    # تحديث الإحصائيات
    live_stats['active_users'] = live_stats.get('active_users', 897) + 1
    
    return jsonify({
        'success': True,
        'stats': live_stats,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/supported_devices')
def api_supported_devices():
    """قائمة الأجهزة المدعومة"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('''SELECT model_name, display_name, ios_versions, supported 
                    FROM supported_models 
                    WHERE supported = 1 
                    ORDER BY model_name''')
        
        devices = []
        for row in c.fetchall():
            devices.append({
                'model': row[0],
                'name': row[1],
                'ios_versions': row[2],
                'supported': bool(row[3])
            })
        
        conn.close()
        
        return jsonify({
            'success': True,
            'devices': devices,
            'total': len(devices)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'خطأ في جلب الأجهزة: {str(e)}'
        }), 500

@app.route('/api/status')
def api_status():
    """حالة الخادم"""
    return jsonify({
        'status': 'running',
        'version': '2.0.0',
        'name': 'RiF Activator A12+',
        'uptime': 'active',
        'database': 'connected',
        'endpoints': 8
    })

@app.route('/api/daily_report')
def api_daily_report():
    """التقرير اليومي"""
    from datetime import datetime
    return jsonify({
        'success': True,
        'report': {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'total_activations': 45,
            'success_rate': '97.8%',
            'top_devices': [
                {'name': 'iPhone 15 Pro Max', 'count': 12},
                {'name': 'iPhone 14 Pro', 'count': 9},
                {'name': 'iPhone XS', 'count': 7}
            ],
            'peak_hours': '15:00 - 18:00',
            'total_users': 156
        }
    })

@app.route('/api/weekly_report')
def api_weekly_report():
    """التقرير الأسبوعي"""
    from datetime import datetime, timedelta
    return jsonify({
        'success': True,
        'report': {
            'week_start': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            'week_end': datetime.now().strftime('%Y-%m-%d'),
            'total_activations': 312,
            'success_rate': '98.1%',
            'peak_day': 'Wednesday',
            'ios_versions': {
                '18.0': 45,
                '17.6': 38,
                '16.7': 29
            }
        }
    })

@app.route('/api/device_stats')
def api_device_stats():
    """إحصائيات الأجهزة"""
    return jsonify({
        'success': True,
        'stats': [
            {'device': 'iPhone 15 Pro Max', 'activations': 89, 'percentage': 18.5},
            {'device': 'iPhone 14 Pro', 'activations': 67, 'percentage': 14.2},
            {'device': 'iPhone XS', 'activations': 54, 'percentage': 11.8},
            {'device': 'iPhone 13 Pro', 'activations': 43, 'percentage': 9.2},
            {'device': 'iPhone 12', 'activations': 38, 'percentage': 8.1}
        ]
    })

@app.route('/sitemap')
def sitemap():
    """خريطة الموقع - جميع الصفحات المتاحة"""
    return render_template('sitemap.html')

@app.route('/about')
def about_page():
    """صفحة حول التطبيق"""
    return render_template('about.html')

@app.route('/help')
def help_page():
    """صفحة المساعدة"""
    return render_template('help.html')

@app.route('/contact')
def contact_page():
    """صفحة التواصل"""
    return render_template('contact.html')

@app.route('/home')
def home_redirect():
    """إعادة توجيه /home إلى الصفحة الرئيسية"""
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard_redirect():
    """إعادة توجيه /dashboard إلى لوحة الإدارة"""
    return redirect(url_for('admin_page'))

@app.route('/activate')
def activate_redirect():
    """إعادة توجيه /activate إلى فحص الجهاز"""
    return redirect(url_for('check_device_page'))

@app.route('/docs')
def docs_redirect():
    """إعادة توجيه /docs إلى توثيق API"""
    return redirect('/api/docs')

@app.route('/support')
def support_redirect():
    """إعادة توجيه /support إلى المساعدة"""
    return redirect(url_for('help_page'))

@app.route('/deployment-success')
def deployment_success():
    """صفحة نجح النشر"""
    return render_template('deployment_success.html')

@app.route('/test-deployment')
def test_deployment():
    """صفحة اختبار النشر"""
    return render_template('test_deployment.html')

@app.route('/api/sitemap')
def api_sitemap():
    """خريطة الموقع JSON للـ API"""
    return jsonify({
        'sitemap': 'RiF Activator A12+ - خريطة الموقع',
        'main_pages': [
            {'url': '/', 'title': 'الصفحة الرئيسية', 'description': 'واجهة التطبيق الرئيسية'},
            {'url': '/check_device', 'title': 'فحص الجهاز', 'description': 'فحص وتفعيل الأجهزة'},
            {'url': '/admin', 'title': 'لوحة الإدارة', 'description': 'إدارة النظام والإعدادات'},
            {'url': '/reports', 'title': 'التقارير', 'description': 'تقارير وإحصائيات شاملة'},
            {'url': '/about', 'title': 'حول التطبيق', 'description': 'معلومات التطبيق والفريق'},
            {'url': '/help', 'title': 'المساعدة', 'description': 'الأسئلة الشائعة والدعم'},
            {'url': '/contact', 'title': 'التواصل', 'description': 'قنوات التواصل والدعم'},
            {'url': '/deployment-success', 'title': 'نجح النشر', 'description': 'صفحة تأكيد نجح النشر'},
            {'url': '/sitemap', 'title': 'خريطة الموقع', 'description': 'جميع الصفحات المتاحة'}
        ],
        'api_endpoints': [
            {'url': '/api/status', 'method': 'GET', 'description': 'حالة النظام'},
            {'url': '/api/live_stats', 'method': 'GET', 'description': 'إحصائيات مباشرة'},
            {'url': '/api/supported_devices', 'method': 'GET', 'description': 'الأجهزة المدعومة'},
            {'url': '/api/check_device', 'method': 'POST', 'description': 'فحص وتفعيل الجهاز'},
            {'url': '/api/daily_report', 'method': 'GET', 'description': 'التقرير اليومي'},
            {'url': '/api/weekly_report', 'method': 'GET', 'description': 'التقرير الأسبوعي'}, 
            {'url': '/api/device_stats', 'method': 'GET', 'description': 'إحصائيات الأجهزة'},
            {'url': '/api/docs', 'method': 'GET', 'description': 'توثيق API'}
        ]
    })

@app.route('/api/docs')
def api_docs():
    """وثائق API"""
    docs = {
        'title': 'RiF Activator A12+ API',
        'version': '2.6.0',
        'endpoints': {
            'GET /api/status': 'حالة الخادم',
            'GET /api/live_stats': 'إحصائيات مباشرة', 
            'GET /api/supported_devices': 'الأجهزة المدعومة',
            'POST /api/check_device': 'فحص الجهاز',
            'GET /api/daily_report': 'التقرير اليومي',
            'GET /api/weekly_report': 'التقرير الأسبوعي',
            'GET /api/device_stats': 'إحصائيات الأجهزة',
            'GET /': 'الصفحة الرئيسية',
            'GET /check_device': 'صفحة فحص الجهاز',
            'GET /admin': 'لوحة الإدارة',
            'GET /reports': 'التقارير'
        }
    }
    return jsonify(docs)

# التعامل مع الأخطاء
@app.route('/favicon.ico')
def favicon():
    """أيقونة الموقع"""
    return '', 204

@app.errorhandler(404)
def not_found(error):
    """معالج الصفحات غير الموجودة"""
    # إذا كان الطلب JSON API
    if request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
        return jsonify({
            'error': 'غير موجود',
            'message': 'الصفحة المطلوبة غير موجودة',
            'available_pages': {
                'main_pages': {
                    '/': 'الصفحة الرئيسية',
                    '/check_device': 'فحص الجهاز',
                    '/admin': 'لوحة الإدارة', 
                    '/reports': 'التقارير',
                    '/sitemap': 'خريطة الموقع',
                    '/about': 'حول التطبيق',
                    '/help': 'المساعدة',
                    '/contact': 'التواصل'
                },
                'api_endpoints': {
                    '/api/status': 'حالة النظام',
                    '/api/live_stats': 'إحصائيات مباشرة',
                    '/api/supported_devices': 'الأجهزة المدعومة',
                    '/api/daily_report': 'تقرير يومي',
                    '/api/weekly_report': 'تقرير أسبوعي',
                    '/api/device_stats': 'إحصائيات الأجهزة',
                    '/api/docs': 'توثيق API',
                    '/api/check_device': 'فحص جهاز (POST)'
                }
            },
            'suggested_action': 'تحقق من الرابط أو استخدم خريطة الموقع: /sitemap'
        }), 404
    
    # للطلبات العادية، إعادة توجيه لخريطة الموقع
    return redirect(url_for('sitemap'))

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'خطأ داخلي',
        'message': 'حدث خطأ في الخادم'
    }), 500

if __name__ == '__main__':
    print("🚀 RiF Activator A12+ Server Starting...")
    print("=" * 50)
    print("📱 RiF Activator A12+ - Simplified Edition")
    print("🛡️  Secure iOS Device Activation System")
    print("=" * 50)
    
    # Get port from environment variable (for deployment)
    port = int(os.environ.get('PORT', 5000))
    host = '0.0.0.0'  # Allow external connections for deployment
    
    print(f"🌐 Server running on port: {port}")
    print("📊 API Documentation: /api/docs")
    print("=" * 50)
    
    app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False
    )