""""""

Reports Manager for RiF Activator  نظام إدارة التقارير المتقدم - RiF Activator A12+

إدارة التقارير لـ RiF Activatorيوفر تقارير مفصلة وإحصائيات شاملة مع رسوم بيانية تفاعلية

""""""



import jsonimport sqlite3

import sqlite3import json

from datetime import datetime, timedeltaimport os

from datetime import datetime, timedelta, timezone

class ReportsManager:from collections import defaultdict

    def __init__(self, db_path='serials.db'):import io

        self.db_path = db_pathimport base64

        import matplotlib

    def get_device_stats(self):matplotlib.use('Agg')  # Use non-GUI backend

        """إحصائيات الأجهزة"""import matplotlib.pyplot as plt

        try:import matplotlib.dates as mdates

            conn = sqlite3.connect(self.db_path)from matplotlib.patches import Rectangle

            c = conn.cursor()import seaborn as sns

            import pandas as pd

            c.execute('SELECT COUNT(*) FROM supported_models')import numpy as np

            total_models = c.fetchone()[0]from fpdf import FPDF

            import arabic_reshaper

            conn.close()from bidi.algorithm import get_display

            

            return {# تكوين matplotlib للعربية

                'total_supported_models': total_models,plt.rcParams['font.size'] = 10

                'most_popular': 'iPhone11,2',plt.rcParams['axes.unicode_minus'] = False

                'success_rate': '98.4%'

            }# تكوين seaborn

        except:sns.set_style("whitegrid")

            return {sns.set_palette("husl")

                'total_supported_models': 25,

                'most_popular': 'iPhone11,2', class ReportsManager:

                'success_rate': '98.4%'    """مدير التقارير المتقدم"""

            }    

                def __init__(self, db_path='activations.db'):

    def generate_daily_report(self):        self.db_path = db_path

        """تقرير يومي"""        self.ensure_reports_tables()

        return {    

            'date': datetime.now().strftime('%Y-%m-%d'),    def ensure_reports_tables(self):

            'activations': 45,        """إنشاء جداول التقارير إذا لم تكن موجودة"""

            'success_rate': '97.8%',        conn = sqlite3.connect(self.db_path)

            'top_devices': ['iPhone11,2', 'iPhone12,1', 'iPhone13,2']        c = conn.cursor()

        }        

                # جدول التقارير المجدولة

    def generate_weekly_report(self):        c.execute('''

        """تقرير أسبوعي"""            CREATE TABLE IF NOT EXISTS scheduled_reports (

        return {                id INTEGER PRIMARY KEY AUTOINCREMENT,

            'week_start': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),                name TEXT NOT NULL,

            'week_end': datetime.now().strftime('%Y-%m-%d'),                report_type TEXT NOT NULL,

            'total_activations': 312,                frequency TEXT NOT NULL,

            'success_rate': '98.1%',                recipients TEXT,

            'peak_day': 'Wednesday'                config TEXT,

        }                last_sent TIMESTAMP,

                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

# إنشاء مثيل عام                is_active BOOLEAN DEFAULT 1

reports_manager = ReportsManager()            )
        ''')
        
        # جدول إحصائيات الأداء
        c.execute('''
            CREATE TABLE IF NOT EXISTS performance_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                total_activations INTEGER DEFAULT 0,
                successful_activations INTEGER DEFAULT 0,
                failed_activations INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0,
                peak_users INTEGER DEFAULT 0,
                revenue REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date)
            )
        ''')
        
        # جدول تحليل الأجهزة
        c.execute('''
            CREATE TABLE IF NOT EXISTS device_analytics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_model TEXT,
                ios_version TEXT,
                activation_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0,
                avg_time REAL DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(device_model, ios_version)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_activation_statistics(self, days=30):
        """احصائيات التفعيلات خلال فترة محددة"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # إجمالي الإحصائيات
        c.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) * 100 as success_rate
            FROM activations 
            WHERE timestamp >= ?
        ''', (start_date.isoformat(),))
        
        total_stats = c.fetchone()
        
        # إحصائيات يومية
        c.execute('''
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
            FROM activations 
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''', (start_date.isoformat(),))
        
        daily_stats = c.fetchall()
        
        # أهم الأجهزة
        c.execute('''
            SELECT 
                device_info,
                COUNT(*) as count,
                AVG(CASE WHEN success = 1 THEN 1.0 ELSE 0.0 END) * 100 as success_rate
            FROM activations 
            WHERE timestamp >= ?
            GROUP BY device_info
            ORDER BY count DESC
            LIMIT 10
        ''', (start_date.isoformat(),))
        
        top_devices = c.fetchall()
        
        conn.close()
        
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat(), 'days': days},
            'total_stats': {
                'total': total_stats[0] or 0,
                'successful': total_stats[1] or 0,
                'failed': total_stats[2] or 0,
                'success_rate': round(total_stats[3] or 0, 2)
            },
            'daily_stats': daily_stats,
            'top_devices': top_devices
        }
    
    def get_security_report(self, days=30):
        """تقرير الأمان ومحاولات الاختراق"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # محاولات تسجيل الدخول
        c.execute('''
            SELECT 
                COUNT(*) as total_attempts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_logins,
                COUNT(DISTINCT ip_address) as unique_ips
            FROM login_attempts 
            WHERE timestamp >= ?
        ''', (start_date.isoformat(),))
        
        login_stats = c.fetchone()
        
        # أكثر عناوين IP نشاطاً
        c.execute('''
            SELECT 
                ip_address,
                COUNT(*) as attempts,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                MAX(timestamp) as last_attempt
            FROM login_attempts 
            WHERE timestamp >= ?
            GROUP BY ip_address
            ORDER BY attempts DESC
            LIMIT 20
        ''', (start_date.isoformat(),))
        
        ip_stats = c.fetchall()
        
        # محاولات مشبوهة
        c.execute('''
            SELECT 
                ip_address,
                COUNT(*) as failed_attempts,
                MIN(timestamp) as first_attempt,
                MAX(timestamp) as last_attempt
            FROM login_attempts 
            WHERE success = 0 AND timestamp >= ?
            GROUP BY ip_address
            HAVING COUNT(*) >= 5
            ORDER BY failed_attempts DESC
        ''', (start_date.isoformat(),))
        
        suspicious_ips = c.fetchall()
        
        conn.close()
        
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat(), 'days': days},
            'login_stats': {
                'total_attempts': login_stats[0] or 0,
                'successful_logins': login_stats[1] or 0,
                'unique_ips': login_stats[2] or 0,
                'success_rate': round((login_stats[1] or 0) / max(login_stats[0] or 1, 1) * 100, 2)
            },
            'ip_stats': ip_stats,
            'suspicious_ips': suspicious_ips
        }
    
    def get_revenue_analytics(self, days=30):
        """تحليل الإيرادات والأداء المالي"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # الإيرادات الإجمالية (افتراضية بناء على التفعيلات الناجحة)
        activation_price = 10.0  # سعر افتراضي للتفعيل الواحد
        
        c.execute('''
            SELECT 
                COUNT(*) as total_activations,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as paid_activations,
                DATE(timestamp) as date
            FROM activations 
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''', (start_date.isoformat(),))
        
        daily_revenue = []
        total_revenue = 0
        
        for row in c.fetchall():
            revenue = row[1] * activation_price
            total_revenue += revenue
            daily_revenue.append({
                'date': row[2],
                'activations': row[0],
                'paid_activations': row[1],
                'revenue': revenue
            })
        
        # أفضل أيام الأسبوع
        c.execute('''
            SELECT 
                CASE CAST(strftime('%w', timestamp) AS INTEGER)
                    WHEN 0 THEN 'الأحد'
                    WHEN 1 THEN 'الاثنين'
                    WHEN 2 THEN 'الثلاثاء'
                    WHEN 3 THEN 'الأربعاء'
                    WHEN 4 THEN 'الخميس'
                    WHEN 5 THEN 'الجمعة'
                    WHEN 6 THEN 'السبت'
                END as day_name,
                COUNT(*) as activations,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful
            FROM activations 
            WHERE timestamp >= ?
            GROUP BY strftime('%w', timestamp)
            ORDER BY successful DESC
        ''', (start_date.isoformat(),))
        
        weekday_stats = c.fetchall()
        
        conn.close()
        
        return {
            'period': {'start': start_date.isoformat(), 'end': end_date.isoformat(), 'days': days},
            'total_revenue': total_revenue,
            'avg_daily_revenue': total_revenue / max(days, 1),
            'activation_price': activation_price,
            'daily_revenue': daily_revenue,
            'weekday_stats': weekday_stats
        }
    
    def create_chart_activation_trend(self, data, width=12, height=6):
        """إنشاء رسم بياني لاتجاه التفعيلات"""
        fig, ax = plt.subplots(figsize=(width, height))
        
        dates = [datetime.fromisoformat(item['date']).date() for item in data['daily_revenue']]
        activations = [item['activations'] for item in data['daily_revenue']]
        successful = [item['paid_activations'] for item in data['daily_revenue']]
        
        ax.plot(dates, activations, marker='o', linewidth=2, label='إجمالي التفعيلات', color='#3498db')
        ax.plot(dates, successful, marker='s', linewidth=2, label='التفعيلات الناجحة', color='#2ecc71')
        
        ax.fill_between(dates, successful, alpha=0.3, color='#2ecc71')
        ax.set_xlabel('التاريخ')
        ax.set_ylabel('عدد التفعيلات')
        ax.set_title('اتجاه التفعيلات اليومية', fontsize=16, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # تنسيق التاريخ
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # تحويل إلى base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return image_base64
    
    def create_chart_device_distribution(self, data, width=10, height=8):
        """رسم بياني لتوزيع الأجهزة"""
        if not data['top_devices']:
            return None
            
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(width, height))
        
        # استخراج أسماء الأجهزة (مبسطة)
        devices = []
        counts = []
        success_rates = []
        
        for device_info, count, success_rate in data['top_devices'][:8]:
            try:
                # محاولة استخراج اسم الجهاز من JSON
                device_data = json.loads(device_info) if device_info.startswith('{') else {'model': device_info}
                device_name = device_data.get('model', 'غير محدد')[:15] + ('...' if len(device_data.get('model', '')) > 15 else '')
            except:
                device_name = str(device_info)[:15] + ('...' if len(str(device_info)) > 15 else '')
            
            devices.append(device_name)
            counts.append(count)
            success_rates.append(success_rate)
        
        # رسم دائري للتوزيع
        colors = plt.cm.Set3(np.linspace(0, 1, len(devices)))
        wedges, texts, autotexts = ax1.pie(counts, labels=devices, autopct='%1.1f%%', 
                                          colors=colors, startangle=90)
        ax1.set_title('توزيع الأجهزة', fontsize=14, fontweight='bold')
        
        # رسم بياني شريطي لمعدل النجاح
        bars = ax2.barh(devices, success_rates, color=colors)
        ax2.set_xlabel('معدل النجاح (%)')
        ax2.set_title('معدل نجاح التفعيل حسب الجهاز', fontsize=14, fontweight='bold')
        ax2.set_xlim(0, 100)
        
        # إضافة قيم على الأشرطة
        for i, (bar, rate) in enumerate(zip(bars, success_rates)):
            ax2.text(rate + 1, i, f'{rate:.1f}%', va='center')
        
        plt.tight_layout()
        
        # تحويل إلى base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return image_base64
    
    def create_chart_security_overview(self, data, width=12, height=8):
        """رسم بياني شامل للأمان"""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(width, height))
        
        # 1. إحصائيات تسجيل الدخول
        login_labels = ['نجح', 'فشل']
        login_values = [
            data['login_stats']['successful_logins'],
            data['login_stats']['total_attempts'] - data['login_stats']['successful_logins']
        ]
        login_colors = ['#2ecc71', '#e74c3c']
        
        ax1.pie(login_values, labels=login_labels, autopct='%1.1f%%', colors=login_colors)
        ax1.set_title('محاولات تسجيل الدخول', fontweight='bold')
        
        # 2. أكثر IP نشاطاً
        if data['ip_stats']:
            top_ips = data['ip_stats'][:6]
            ips = [ip[0] for ip in top_ips]
            attempts = [ip[1] for ip in top_ips]
            
            bars = ax2.bar(range(len(ips)), attempts, color='#3498db')
            ax2.set_title('أكثر عناوين IP نشاطاً', fontweight='bold')
            ax2.set_ylabel('عدد المحاولات')
            ax2.set_xticks(range(len(ips)))
            ax2.set_xticklabels([ip[:10] + '...' if len(ip) > 10 else ip for ip in ips], rotation=45)
            
            # إضافة قيم على الأشرطة
            for bar, attempt in zip(bars, attempts):
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                        str(attempt), ha='center', va='bottom')
        
        # 3. المحاولات المشبوهة
        if data['suspicious_ips']:
            susp_ips = [ip[0] for ip in data['suspicious_ips'][:6]]
            susp_attempts = [ip[1] for ip in data['suspicious_ips'][:6]]
            
            bars = ax3.bar(range(len(susp_ips)), susp_attempts, color='#e74c3c')
            ax3.set_title('المحاولات المشبوهة', fontweight='bold')
            ax3.set_ylabel('محاولات فاشلة')
            ax3.set_xticks(range(len(susp_ips)))
            ax3.set_xticklabels([ip[:10] + '...' if len(ip) > 10 else ip for ip in susp_ips], rotation=45)
        
        # 4. معدل الأمان العام
        total_attempts = data['login_stats']['total_attempts']
        suspicious_count = len(data['suspicious_ips'])
        
        if total_attempts > 0:
            security_score = max(0, 100 - (suspicious_count / max(total_attempts/100, 1)) * 10)
            
            # مقياس دائري للأمان
            theta = np.linspace(0, 2*np.pi, 100)
            r = np.ones_like(theta)
            
            # خلفية رمادية
            ax4.fill_between(theta, 0, r, color='#ecf0f1', alpha=0.3)
            
            # المقياس الملون حسب النتيجة
            score_theta = theta[:int(security_score)]
            color = '#2ecc71' if security_score > 80 else '#f39c12' if security_score > 60 else '#e74c3c'
            ax4.fill_between(score_theta, 0, r[:len(score_theta)], color=color, alpha=0.7)
            
            ax4.text(0, 0, f'{security_score:.1f}%\nنقاط الأمان', ha='center', va='center', 
                    fontsize=14, fontweight='bold')
            ax4.set_xlim(-1.2, 1.2)
            ax4.set_ylim(-1.2, 1.2)
            ax4.set_aspect('equal')
            ax4.axis('off')
            ax4.set_title('مؤشر الأمان العام', fontweight='bold')
        
        plt.tight_layout()
        
        # تحويل إلى base64
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        plt.close()
        
        return image_base64
    
    def generate_comprehensive_report(self, days=30, include_charts=True):
        """إنشاء تقرير شامل"""
        print(f"🔄 إنشاء تقرير شامل لآخر {days} يوم...")
        
        # جمع البيانات
        activation_stats = self.get_activation_statistics(days)
        security_report = self.get_security_report(days)
        revenue_analytics = self.get_revenue_analytics(days)
        
        report = {
            'metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'period_days': days,
                'report_type': 'comprehensive'
            },
            'activation_statistics': activation_stats,
            'security_report': security_report,
            'revenue_analytics': revenue_analytics,
            'charts': {}
        }
        
        if include_charts:
            print("📊 إنشاء الرسوم البيانية...")
            
            # رسم اتجاه التفعيلات
            if revenue_analytics['daily_revenue']:
                report['charts']['activation_trend'] = self.create_chart_activation_trend(revenue_analytics)
            
            # رسم توزيع الأجهزة
            if activation_stats['top_devices']:
                report['charts']['device_distribution'] = self.create_chart_device_distribution(activation_stats)
            
            # رسم نظرة عامة على الأمان
            if security_report['login_stats']['total_attempts'] > 0:
                report['charts']['security_overview'] = self.create_chart_security_overview(security_report)
        
        print("✅ تم إنشاء التقرير بنجاح!")
        return report
    
    def export_to_pdf(self, report_data, filename=None):
        """تصدير التقرير إلى PDF"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'report_{timestamp}.pdf'
        
        print(f"📄 تصدير التقرير إلى PDF: {filename}")
        
        class ArabicPDF(FPDF):
            def __init__(self):
                super().__init__()
                self.set_auto_page_break(auto=True, margin=15)
        
        pdf = ArabicPDF()
        pdf.add_page()
        pdf.set_font('Arial', 'B', 16)
        
        # عنوان التقرير
        pdf.cell(0, 10, 'RiF Activator A12+ - Comprehensive Report', 0, 1, 'C')
        pdf.ln(5)
        
        # معلومات التقرير
        pdf.set_font('Arial', '', 12)
        generated_at = datetime.fromisoformat(report_data['metadata']['generated_at'].replace('Z', '+00:00'))
        pdf.cell(0, 8, f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}", 0, 1)
        pdf.cell(0, 8, f"Period: {report_data['metadata']['period_days']} days", 0, 1)
        pdf.ln(5)
        
        # إحصائيات التفعيل
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Activation Statistics', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        stats = report_data['activation_statistics']['total_stats']
        pdf.cell(0, 6, f"Total Activations: {stats['total']}", 0, 1)
        pdf.cell(0, 6, f"Successful: {stats['successful']}", 0, 1)
        pdf.cell(0, 6, f"Failed: {stats['failed']}", 0, 1)
        pdf.cell(0, 6, f"Success Rate: {stats['success_rate']}%", 0, 1)
        pdf.ln(5)
        
        # إحصائيات الأمان
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Security Report', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        sec_stats = report_data['security_report']['login_stats']
        pdf.cell(0, 6, f"Login Attempts: {sec_stats['total_attempts']}", 0, 1)
        pdf.cell(0, 6, f"Successful Logins: {sec_stats['successful_logins']}", 0, 1)
        pdf.cell(0, 6, f"Unique IPs: {sec_stats['unique_ips']}", 0, 1)
        pdf.cell(0, 6, f"Suspicious IPs: {len(report_data['security_report']['suspicious_ips'])}", 0, 1)
        pdf.ln(5)
        
        # الإيرادات
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, 'Revenue Analytics', 0, 1)
        pdf.set_font('Arial', '', 11)
        
        revenue = report_data['revenue_analytics']
        pdf.cell(0, 6, f"Total Revenue: ${revenue['total_revenue']:.2f}", 0, 1)
        pdf.cell(0, 6, f"Average Daily Revenue: ${revenue['avg_daily_revenue']:.2f}", 0, 1)
        pdf.cell(0, 6, f"Activation Price: ${revenue['activation_price']:.2f}", 0, 1)
        
        # حفظ الملف
        pdf_path = os.path.join(os.path.dirname(self.db_path), filename)
        pdf.output(pdf_path)
        
        print(f"✅ تم حفظ التقرير: {pdf_path}")
        return pdf_path

# إنشاء مثيل عام لمدير التقارير
reports_manager = ReportsManager()