""""""

Report Scheduler for RiF Activatorنظام جدولة التقارير الدورية - RiF Activator A12+

جدولة التقارير لـ RiF Activatorيوفر جدولة تلقائية للتقارير مع إرسال عبر البريد الإلكتروني (اختياري)

""""""



import scheduleimport schedule

import timeimport time

import threadingimport threading

from datetime import datetimeimport json

import os

class ReportScheduler:from datetime import datetime

    def __init__(self):from reports_manager import reports_manager

        self.scheduled_reports = []from typing import Dict, List, Optional

        self.running = Falseimport smtplib

        from email.mime.multipart import MIMEMultipart

    def schedule_daily_report(self):from email.mime.text import MIMEText

        """جدولة تقرير يومي"""from email.mime.base import MIMEBase

        schedule.every().day.at("23:59").do(self.generate_daily_report)from email import encoders

        

    def schedule_weekly_report(self):class ReportScheduler:

        """جدولة تقرير أسبوعي"""    """مجدول التقارير الدورية"""

        schedule.every().sunday.at("23:59").do(self.generate_weekly_report)    

            def __init__(self, config_file='report_schedules.json'):

    def generate_daily_report(self):        self.config_file = config_file

        """إنشاء تقرير يومي"""        self.schedules = self.load_schedules()

        print(f"📊 تم إنشاء التقرير اليومي: {datetime.now()}")        self.is_running = False

                self.scheduler_thread = None

    def generate_weekly_report(self):    

        """إنشاء تقرير أسبوعي"""    def load_schedules(self) -> List[Dict]:

        print(f"📈 تم إنشاء التقرير الأسبوعي: {datetime.now()}")        """تحميل جداول التقارير من الملف"""

                if os.path.exists(self.config_file):

    def start_scheduler(self):            try:

        """بدء الجدولة"""                with open(self.config_file, 'r', encoding='utf-8') as f:

        self.running = True                    return json.load(f)

        self.schedule_daily_report()            except:

        self.schedule_weekly_report()                return []

                return []

        def run_scheduler():    

            while self.running:    def save_schedules(self):

                schedule.run_pending()        """حفظ جداول التقارير إلى الملف"""

                time.sleep(60)  # فحص كل دقيقة        with open(self.config_file, 'w', encoding='utf-8') as f:

                            json.dump(self.schedules, f, ensure_ascii=False, indent=2)

        scheduler_thread = threading.Thread(target=run_scheduler)    

        scheduler_thread.daemon = True    def add_schedule(self, name: str, frequency: str, days: int = 30, 

        scheduler_thread.start()                    format_type: str = 'pdf', email_recipients: List[str] = None):

                """إضافة جدول تقرير جديد"""

    def stop_scheduler(self):        schedule_config = {

        """إيقاف الجدولة"""            'id': len(self.schedules) + 1,

        self.running = False            'name': name,

        schedule.clear()            'frequency': frequency,  # daily, weekly, monthly

            'days': days,

# إنشاء مثيل عام            'format': format_type,

report_scheduler = ReportScheduler()            'email_recipients': email_recipients or [],
            'last_run': None,
            'active': True,
            'created_at': datetime.now().isoformat()
        }
        
        self.schedules.append(schedule_config)
        self.save_schedules()
        
        # جدولة المهمة
        self._schedule_task(schedule_config)
        
        print(f"✅ تم إضافة جدول التقرير: {name}")
        return schedule_config['id']
    
    def _schedule_task(self, config: Dict):
        """جدولة مهمة واحدة"""
        if not config['active']:
            return
        
        def job():
            try:
                self._generate_scheduled_report(config)
            except Exception as e:
                print(f"❌ خطأ في تشغيل التقرير المجدول {config['name']}: {e}")
        
        if config['frequency'] == 'daily':
            schedule.every().day.at("09:00").do(job).tag(f"report_{config['id']}")
        elif config['frequency'] == 'weekly':
            schedule.every().monday.at("09:00").do(job).tag(f"report_{config['id']}")
        elif config['frequency'] == 'monthly':
            schedule.every().day.at("09:00").do(self._check_monthly, config).tag(f"report_{config['id']}")
    
    def _check_monthly(self, config: Dict):
        """فحص التقرير الشهري (في اليوم الأول من الشهر)"""
        if datetime.now().day == 1:
            self._generate_scheduled_report(config)
    
    def _generate_scheduled_report(self, config: Dict):
        """توليد تقرير مجدول"""
        print(f"🔄 توليد التقرير المجدول: {config['name']}")
        
        try:
            # توليد التقرير
            report_data = reports_manager.generate_comprehensive_report(
                days=config['days'], 
                include_charts=True
            )
            
            # إنشاء اسم الملف
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"scheduled_{config['name']}_{timestamp}"
            
            output_dir = os.path.join(os.getcwd(), 'scheduled_reports')
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = None
            
            if config['format'] == 'pdf':
                file_path = reports_manager.export_to_pdf(
                    report_data, 
                    filename=os.path.join(output_dir, filename + '.pdf')
                )
            elif config['format'] == 'json':
                file_path = os.path.join(output_dir, filename + '.json')
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            # تحديث وقت آخر تشغيل
            config['last_run'] = datetime.now().isoformat()
            self.save_schedules()
            
            print(f"✅ تم إنشاء التقرير المجدول: {file_path}")
            
            # إرسال عبر البريد الإلكتروني إذا كان مكوناً
            if config['email_recipients'] and file_path:
                self._send_email_report(config, file_path, report_data)
                
        except Exception as e:
            print(f"❌ خطأ في توليد التقرير المجدول: {e}")
    
    def _send_email_report(self, config: Dict, file_path: str, report_data: Dict):
        """إرسال التقرير عبر البريد الإلكتروني"""
        try:
            # هذه دالة بسيطة - يحتاج تكوين SMTP
            print(f"📧 محاولة إرسال التقرير عبر البريد الإلكتروني إلى: {config['email_recipients']}")
            
            # يمكن إضافة تكوين SMTP هنا
            # smtp_server = "smtp.gmail.com"
            # smtp_port = 587
            # email = "your-email@gmail.com"
            # password = "your-app-password"
            
            print("ℹ️ إعداد SMTP غير مكون - تخطي إرسال البريد الإلكتروني")
            
        except Exception as e:
            print(f"❌ خطأ في إرسال البريد الإلكتروني: {e}")
    
    def start_scheduler(self):
        """بدء مجدول التقارير"""
        if self.is_running:
            print("⚠️ المجدول يعمل بالفعل")
            return
        
        print("🚀 بدء مجدول التقارير الدورية...")
        
        # جدولة جميع التقارير النشطة
        for config in self.schedules:
            if config['active']:
                self._schedule_task(config)
        
        # بدء الخيط المنفصل للمجدول
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        print("✅ تم بدء مجدول التقارير")
    
    def _run_scheduler(self):
        """تشغيل المجدول في خيط منفصل"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # فحص كل دقيقة
    
    def stop_scheduler(self):
        """إيقاف مجدول التقارير"""
        print("⏹️ إيقاف مجدول التقارير...")
        self.is_running = False
        schedule.clear()
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        
        print("✅ تم إيقاف مجدول التقارير")
    
    def list_schedules(self) -> List[Dict]:
        """عرض جميع الجداول"""
        return self.schedules
    
    def toggle_schedule(self, schedule_id: int, active: bool):
        """تفعيل/إلغاء تفعيل جدول"""
        for config in self.schedules:
            if config['id'] == schedule_id:
                config['active'] = active
                self.save_schedules()
                
                if active and self.is_running:
                    self._schedule_task(config)
                else:
                    schedule.clear(f"report_{schedule_id}")
                
                status = "مفعل" if active else "معطل"
                print(f"✅ تم تحديث الجدول {config['name']}: {status}")
                return True
        
        print(f"❌ لم يتم العثور على الجدول ID: {schedule_id}")
        return False
    
    def delete_schedule(self, schedule_id: int):
        """حذف جدول"""
        for i, config in enumerate(self.schedules):
            if config['id'] == schedule_id:
                # إلغاء الجدولة
                schedule.clear(f"report_{schedule_id}")
                
                # حذف من القائمة
                deleted_name = config['name']
                del self.schedules[i]
                self.save_schedules()
                
                print(f"✅ تم حذف الجدول: {deleted_name}")
                return True
        
        print(f"❌ لم يتم العثور على الجدول ID: {schedule_id}")
        return False

# إنشاء مثيل عام لمجدول التقارير
report_scheduler = ReportScheduler()

if __name__ == '__main__':
    # مثال على الاستخدام
    scheduler = ReportScheduler()
    
    # إضافة جدول تقرير يومي
    scheduler.add_schedule(
        name="تقرير يومي",
        frequency="daily",
        days=1,
        format_type="pdf"
    )
    
    # إضافة جدول تقرير أسبوعي
    scheduler.add_schedule(
        name="تقرير أسبوعي",
        frequency="weekly", 
        days=7,
        format_type="pdf",
        email_recipients=["admin@example.com"]
    )
    
    # عرض الجداول
    print("\n📋 الجداول المكونة:")
    for schedule_config in scheduler.list_schedules():
        print(f"- {schedule_config['name']} ({schedule_config['frequency']}) - {'نشط' if schedule_config['active'] else 'معطل'}")
    
    # بدء المجدول
    scheduler.start_scheduler()
    
    print("\n🔄 المجدول يعمل... اضغط Ctrl+C للإيقاف")
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        scheduler.stop_scheduler()
        print("\n👋 تم إيقاف المجدول")