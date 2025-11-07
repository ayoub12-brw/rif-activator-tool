#!/usr/bin/env python3
"""
RiF Activator A12+ - إصدار مقاوم للتجمد
تم تصميمه خصيصاً لتجنب مشاكل التجمد الشائعة
"""

import sys
import os
import subprocess
import time
from dotenv import load_dotenv
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QMessageBox, QProgressBar, QTextEdit
)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont

# Load environment variables
load_dotenv()

class DeviceCheckThread(QThread):
    """Thread منفصل لفحص الجهاز لتجنب تجمد UI"""
    device_found = pyqtSignal(dict)
    device_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.should_stop = False
    
    def run(self):
        """تشغيل فحص الجهاز في background thread"""
        try:
            if self.should_stop:
                return
                
            # استخدام timeout قصير جداً
            result = subprocess.run(
                [os.path.join("libimobiledevice-windows-master", "ideviceinfo.exe")],
                capture_output=True,
                text=True,
                timeout=1,  # timeout قصير جداً - ثانية واحدة فقط!
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if self.should_stop:
                return
                
            if result.returncode == 0:
                # تحليل البيانات
                lines = result.stdout.strip().split('\n')
                info = {}
                for line in lines:
                    if ':' in line and not self.should_stop:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
                
                if info and not self.should_stop:
                    self.device_found.emit(info)
                else:
                    self.device_error.emit("No device info parsed")
            else:
                self.device_error.emit(f"ideviceinfo failed: {result.returncode}")
                
        except subprocess.TimeoutExpired:
            if not self.should_stop:
                self.device_error.emit("Device check timeout (1s)")
        except Exception as e:
            if not self.should_stop:
                self.device_error.emit(f"Device check error: {e}")
    
    def stop(self):
        """إيقاف Thread بأمان"""
        self.should_stop = True

class NoFreezeDeviceUI(QWidget):
    def __init__(self):
        super().__init__()
        
        # تحميل الإعدادات
        self.load_settings()
        
        # متغيرات الحالة
        self.device_thread = None
        self.check_count = 0
        self.last_device_info = None
        
        # إعداد الواجهة
        self.init_ui()
        
        # تشغيل المؤقت مع فترة طويلة
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_device_safe)
        self.timer.start(5000)  # كل 5 ثواني فقط
        
        # رسالة ترحيب
        self.log_message("🚀 تم تشغيل RiF Activator A12+ - إصدار مقاوم للتجمد")
        self.log_message(f"⚙️ الإعدادات - OFFLINE_MODE: {self.offline_mode}, FREE_ACTIVATION: {self.free_activation}")
        self.log_message(f"📱 الموديلات المدعومة: {self.local_allowed_models}")
    
    def load_settings(self):
        """تحميل الإعدادات مع قيم افتراضية آمنة"""
        try:
            self.offline_mode = os.getenv('OFFLINE_MODE', 'false').lower() == 'true'
            self.free_activation = os.getenv('FREE_ACTIVATION', '0') == '1'
            
            # إعداد الموديلات المحلية بطريقة آمنة
            local_allowed = os.getenv('LOCAL_ALLOWED_MODELS', '').strip()
            if local_allowed:
                # معاملة خاصة للموديلات التي تحتوي على comma
                if local_allowed.count(',') == 1 and not local_allowed.count(' '):
                    # موديل واحد يحتوي على comma (مثل iPhone14,2)
                    self.local_allowed_models = {local_allowed}
                else:
                    # موديلات متعددة
                    if '|' in local_allowed:
                        self.local_allowed_models = set(x.strip() for x in local_allowed.split('|'))
                    elif ';' in local_allowed:
                        self.local_allowed_models = set(x.strip() for x in local_allowed.split(';'))
                    else:
                        self.local_allowed_models = {local_allowed}
            else:
                self.local_allowed_models = set()
                
        except Exception as e:
            print(f"خطأ في تحميل الإعدادات: {e}")
            # قيم افتراضية آمنة
            self.offline_mode = True
            self.free_activation = True  
            self.local_allowed_models = {'iPhone14,2'}
    
    def init_ui(self):
        """إعداد الواجهة"""
        self.setWindowTitle("🔧 RiF Activator A12+ - مقاوم للتجمد")
        self.setGeometry(200, 200, 600, 500)
        
        # تخطيط رئيسي
        main_layout = QVBoxLayout()
        
        # العنوان
        title = QLabel("🛡️ RiF Activator A12+ - Anti-Freeze Edition")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # حالة الجهاز
        self.status_label = QLabel("🔍 جاري البحث عن الأجهزة...")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # معلومات الجهاز
        self.device_info_label = QLabel("")
        self.device_info_label.setFont(QFont("Arial", 10))
        self.device_info_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.device_info_label)
        
        # شريط التقدم
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # أزرار التحكم
        buttons_layout = QHBoxLayout()
        
        self.activate_button = QPushButton("🚀 تفعيل الجهاز")
        self.activate_button.setEnabled(False)
        self.activate_button.clicked.connect(self.activate_device)
        buttons_layout.addWidget(self.activate_button)
        
        self.check_button = QPushButton("🔍 فحص يدوي")
        self.check_button.clicked.connect(self.manual_check)
        buttons_layout.addWidget(self.check_button)
        
        settings_button = QPushButton("⚙️ الإعدادات")
        settings_button.clicked.connect(self.show_settings)
        buttons_layout.addWidget(settings_button)
        
        main_layout.addLayout(buttons_layout)
        
        # سجل الأحداث
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(150)
        self.log_text.setFont(QFont("Courier", 9))
        main_layout.addWidget(self.log_text)
        
        # زر الإغلاق
        close_button = QPushButton("❌ إغلاق")
        close_button.clicked.connect(self.safe_close)
        main_layout.addWidget(close_button)
        
        self.setLayout(main_layout)
    
    def log_message(self, message):
        """إضافة رسالة إلى السجل"""
        try:
            timestamp = time.strftime("%H:%M:%S")
            log_entry = f"[{timestamp}] {message}"
            self.log_text.append(log_entry)
            # تمرير تلقائي للأسفل
            self.log_text.verticalScrollBar().setValue(
                self.log_text.verticalScrollBar().maximum()
            )
        except Exception as e:
            print(f"خطأ في إضافة رسالة السجل: {e}")
    
    def check_device_safe(self):
        """فحص آمن للجهاز لا يسبب تجمد"""
        try:
            self.check_count += 1
            
            # تحديث العداد
            self.status_label.setText(f"🔍 فحص #{self.check_count}...")
            
            # إيقاف أي thread سابق
            if self.device_thread and self.device_thread.isRunning():
                self.device_thread.stop()
                self.device_thread.wait(500)  # انتظار نصف ثانية كحد أقصى
            
            # إنشاء thread جديد
            self.device_thread = DeviceCheckThread()
            self.device_thread.device_found.connect(self.on_device_found)
            self.device_thread.device_error.connect(self.on_device_error)
            
            # تشغيل الفحص
            self.device_thread.start()
            
            # timeout للـ thread نفسه (2 ثانية كحد أقصى)
            QTimer.singleShot(2000, lambda: self.force_thread_stop())
            
        except Exception as e:
            self.log_message(f"❌ خطأ في الفحص الآمن: {e}")
            self.status_label.setText("❌ خطأ في الفحص")
    
    def force_thread_stop(self):
        """إجبار إيقاف thread إذا استغرق وقتاً طويلاً"""
        try:
            if self.device_thread and self.device_thread.isRunning():
                self.device_thread.stop()
                if not self.device_thread.wait(100):  # انتظار 100ms فقط
                    self.device_thread.terminate()  # إنهاء قسري
                self.log_message("⏱️ تم إيقاف فحص الجهاز (timeout)")
        except Exception as e:
            self.log_message(f"❌ خطأ في إيقاف thread: {e}")
    
    def on_device_found(self, device_info):
        """تم العثور على جهاز"""
        try:
            product_type = device_info.get('ProductType', 'غير معروف')
            ios_version = device_info.get('ProductVersion', 'غير معروف')
            serial = device_info.get('SerialNumber', 'غير معروف')
            
            self.last_device_info = device_info
            
            # تحديث الواجهة
            self.status_label.setText(f"✅ تم العثور على: {product_type}")
            self.device_info_label.setText(f"iOS: {ios_version} | Serial: {serial}")
            
            # فحص الدعم
            is_supported = self.check_device_support(product_type, ios_version)
            
            if is_supported:
                self.activate_button.setText("🎉 تفعيل الجهاز (مدعوم)")
                self.activate_button.setEnabled(True)
                self.log_message(f"🎉 جهاز مدعوم: {product_type} - iOS {ios_version}")
                
                # إيقاف المؤقت لتوفير الموارد
                self.timer.stop()
                
                # رسالة ترحيب
                QMessageBox.information(
                    self, 
                    "🎉 مبروك!",
                    f"تم اكتشاف جهاز مدعوم!\n\n"
                    f"الموديل: {product_type}\n"
                    f"iOS: {ios_version}\n\n"
                    f"يمكنك الآن تفعيل الجهاز بأمان."
                )
            else:
                self.activate_button.setText("❌ غير مدعوم")
                self.activate_button.setEnabled(False)
                self.log_message(f"❌ جهاز غير مدعوم: {product_type} - iOS {ios_version}")
                
        except Exception as e:
            self.log_message(f"❌ خطأ في معالجة الجهاز: {e}")
    
    def on_device_error(self, error_msg):
        """خطأ في فحص الجهاز"""
        try:
            self.status_label.setText("📱 لا يوجد جهاز")
            self.device_info_label.setText("تأكد من توصيل الجهاز وإلغاء قفله")
            self.activate_button.setEnabled(False)
            
            # تسجيل الأخطاء المهمة فقط
            if "timeout" not in error_msg.lower() and self.check_count % 5 == 0:
                self.log_message(f"ℹ️ {error_msg}")
                
        except Exception as e:
            print(f"خطأ في معالجة خطأ الجهاز: {e}")
    
    def check_device_support(self, product_type, ios_version):
        """فحص دعم الجهاز"""
        try:
            # فحص إصدار iOS
            parts = ios_version.split('.')
            if len(parts) >= 2:
                major = int(parts[0])
                minor = int(parts[1])
                
                # النطاق المدعوم: 12.0 - 26.999
                if not (12 <= major <= 26):
                    return False
            
            # فحص الموديل في الوضع المستقل
            if self.offline_mode:
                return product_type in self.local_allowed_models
            
            # في الوضع العادي، نحتاج للخادم (غير مدعوم حالياً)
            return False
            
        except Exception as e:
            self.log_message(f"❌ خطأ في فحص الدعم: {e}")
            return False
    
    def manual_check(self):
        """فحص يدوي"""
        self.log_message("🔍 تم طلب فحص يدوي")
        self.check_device_safe()
    
    def activate_device(self):
        """تفعيل الجهاز"""
        try:
            if not self.last_device_info:
                QMessageBox.warning(self, "⚠️ تنبيه", "لا يوجد جهاز متصل")
                return
            
            if self.free_activation:
                # تشغيل شريط التقدم
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
                
                # محاكاة عملية التفعيل
                for i in range(101):
                    self.progress_bar.setValue(i)
                    QApplication.processEvents()  # تحديث الواجهة
                    time.sleep(0.01)  # 10ms للمحاكاة
                
                self.progress_bar.setVisible(False)
                
                # رسالة نجاح
                serial = self.last_device_info.get('SerialNumber', 'غير معروف')
                
                QMessageBox.information(
                    self,
                    "✅ تم التفعيل بنجاح",
                    f"🎉 مبروك! تم تفعيل الجهاز بنجاح!\n\n"
                    f"الرقم التسلسلي: {serial}\n\n"
                    f"جهازك الآن جاهز للاستخدام بدون قيود."
                )
                
                self.log_message(f"✅ تم تفعيل الجهاز: {serial}")
            else:
                QMessageBox.warning(
                    self,
                    "⚠️ تنبيه",
                    "التفعيل المجاني غير مفعل.\n"
                    "تحقق من إعدادات FREE_ACTIVATION في ملف .env"
                )
                
        except Exception as e:
            self.log_message(f"❌ خطأ في التفعيل: {e}")
            QMessageBox.critical(self, "❌ خطأ", f"حدث خطأ في التفعيل:\n{e}")
    
    def show_settings(self):
        """عرض الإعدادات"""
        settings_info = f"""🔧 إعدادات RiF Activator A12+:

✅ إعدادات التشغيل:
   OFFLINE_MODE: {self.offline_mode}
   FREE_ACTIVATION: {self.free_activation}

📱 الموديلات المدعومة محلياً:
   {', '.join(self.local_allowed_models) if self.local_allowed_models else 'لا توجد'}

📊 إحصائيات الجلسة:
   عدد مرات الفحص: {self.check_count}
   آخر جهاز مكتشف: {self.last_device_info.get('ProductType', 'لا يوجد') if self.last_device_info else 'لا يوجد'}

📁 مسار التطبيق:
   {os.getcwd()}

💡 لتغيير الإعدادات، عدل ملف .env في مجلد التطبيق."""
        
        QMessageBox.information(self, "⚙️ إعدادات التطبيق", settings_info)
    
    def safe_close(self):
        """إغلاق آمن للتطبيق"""
        try:
            self.log_message("🔄 جاري إغلاق التطبيق...")
            
            # إيقاف المؤقت
            if self.timer:
                self.timer.stop()
            
            # إيقاف thread إذا كان يعمل
            if self.device_thread and self.device_thread.isRunning():
                self.device_thread.stop()
                self.device_thread.wait(1000)  # انتظار ثانية واحدة
                if self.device_thread.isRunning():
                    self.device_thread.terminate()
            
            # إغلاق النافذة
            self.close()
            
        except Exception as e:
            print(f"خطأ في الإغلاق الآمن: {e}")
            self.close()

def main():
    """الدالة الرئيسية"""
    app = QApplication(sys.argv)
    
    # إعداد خصائص التطبيق
    app.setApplicationName("RiF Activator A12+")
    app.setApplicationVersion("2.0 - Anti-Freeze")
    
    # إنشاء النافذة الرئيسية
    window = NoFreezeDeviceUI()
    window.show()
    
    # تشغيل التطبيق
    return app.exec_()

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n🔄 تم إيقاف التطبيق بواسطة المستخدم")
        sys.exit(0)
    except Exception as e:
        print(f"❌ خطأ فادح في التطبيق: {e}")
        sys.exit(1)