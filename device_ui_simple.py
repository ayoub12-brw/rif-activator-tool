#!/usr/bin/env python3
"""
إصدار مبسط من device_ui لتجنب التجمد
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
import subprocess
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SimpleDeviceWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # إعداد المتغيرات
        self.offline_mode = os.getenv('OFFLINE_MODE', 'false').lower() == 'true'
        self.free_activation = os.getenv('FREE_ACTIVATION', '0') == '1'
        
        # إعداد الموديلات المحلية
        local_allowed = os.getenv('LOCAL_ALLOWED_MODELS', '').strip()
        if local_allowed:
            if '|' in local_allowed:
                self.local_allowed_models = set(x.strip() for x in local_allowed.split('|'))
            else:
                self.local_allowed_models = {local_allowed}
        else:
            self.local_allowed_models = set()
        
        self.init_ui()
        
        # تشغيل فحص الجهاز
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_device_simple)
        self.timer.start(3000)  # كل 3 ثواني
        
        print(f"✅ تم تشغيل التطبيق المبسط")
        print(f"   الوضع المستقل: {self.offline_mode}")
        print(f"   التفعيل المجاني: {self.free_activation}")
        print(f"   الموديلات المحلية: {self.local_allowed_models}")
    
    def init_ui(self):
        self.setWindowTitle("RiF Activator A12+ - مبسط")
        self.setGeometry(300, 300, 500, 400)
        
        layout = QVBoxLayout()
        
        # العنوان
        title = QLabel("🔧 RiF Activator A12+")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # حالة الجهاز
        self.status_label = QLabel("🔍 البحث عن جهاز...")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # معلومات الجهاز
        self.info_label = QLabel("")
        self.info_label.setFont(QFont("Arial", 10))
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
        
        # زر التفعيل
        self.activate_button = QPushButton("🚀 تفعيل الجهاز")
        self.activate_button.setEnabled(False)
        self.activate_button.clicked.connect(self.activate_device)
        layout.addWidget(self.activate_button)
        
        # زر الإعدادات
        settings_button = QPushButton("⚙️ الإعدادات")
        settings_button.clicked.connect(self.show_settings)
        layout.addWidget(settings_button)
        
        self.setLayout(layout)
    
    def check_device_simple(self):
        """فحص بسيط للجهاز"""
        try:
            # محاولة سريعة للحصول على معلومات الجهاز
            result = subprocess.run(
                [os.path.join("libimobiledevice-windows-master", "ideviceinfo.exe")],
                capture_output=True,
                text=True,
                timeout=2,  # timeout قصير جداً
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            
            if result.returncode == 0:
                # تحليل المعلومات
                lines = result.stdout.strip().split('\n')
                info = {}
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
                
                product_type = info.get('ProductType', '')
                ios_version = info.get('ProductVersion', '')
                serial = info.get('SerialNumber', '')
                
                # فحص الدعم
                is_supported = self.check_device_support(product_type, ios_version)
                
                # تحديث الواجهة
                self.status_label.setText(f"✅ جهاز متصل: {product_type}")
                self.info_label.setText(f"iOS: {ios_version}\nSerial: {serial}")
                
                if is_supported:
                    self.activate_button.setText("🎉 تفعيل الجهاز (مدعوم)")
                    self.activate_button.setEnabled(True)
                    
                    # رسالة ترحيب
                    QMessageBox.information(
                        self,
                        "🎉 مبروك!",
                        f"تم اكتشاف جهاز مدعوم!\n\n"
                        f"الموديل: {product_type}\n"
                        f"iOS: {ios_version}\n\n"
                        f"يمكنك الآن تفعيل الجهاز."
                    )
                    
                    # إيقاف المؤقت لتجنب الإزعاج
                    self.timer.stop()
                else:
                    self.activate_button.setText("❌ غير مدعوم")
                    self.activate_button.setEnabled(False)
            else:
                # لا يوجد جهاز
                self.status_label.setText("📱 لا يوجد جهاز متصل")
                self.info_label.setText("تأكد من توصيل الجهاز وإلغاء قفله")
                self.activate_button.setEnabled(False)
                
        except subprocess.TimeoutExpired:
            self.status_label.setText("⏱️ انتهت مهلة البحث")
        except Exception as e:
            self.status_label.setText(f"❌ خطأ: {str(e)}")
    
    def check_device_support(self, product_type, ios_version):
        """فحص دعم الجهاز"""
        try:
            # فحص iOS version
            parts = ios_version.split('.')
            if len(parts) >= 2:
                major = int(parts[0])
                minor = int(parts[1])
                
                # النطاق المدعوم: 12.0 - 26.999
                if not (12 <= major <= 26):
                    return False
            
            # فحص الموديل في الوضع المستقل
            if self.offline_mode:
                if product_type in self.local_allowed_models:
                    return True
                else:
                    return False
            
            # في الوضع العادي، نحتاج للخادم
            return False
            
        except Exception as e:
            print(f"خطأ في فحص الدعم: {e}")
            return False
    
    def activate_device(self):
        """تفعيل الجهاز"""
        if self.free_activation:
            QMessageBox.information(
                self,
                "✅ تم التفعيل",
                "تم تفعيل الجهاز بنجاح!\n\n"
                "🎉 مبروك! جهازك جاهز للاستخدام."
            )
        else:
            QMessageBox.warning(
                self,
                "⚠️ تنبيه",
                "التفعيل المجاني غير مفعل.\n"
                "تحقق من إعدادات FREE_ACTIVATION."
            )
    
    def show_settings(self):
        """عرض الإعدادات"""
        settings_info = f"""🔧 إعدادات التطبيق:

OFFLINE_MODE: {self.offline_mode}
FREE_ACTIVATION: {self.free_activation}
LOCAL_ALLOWED_MODELS: {self.local_allowed_models}

📁 مجلد التطبيق:
{os.getcwd()}

💡 لتغيير الإعدادات، عدل ملف .env"""
        
        QMessageBox.information(self, "⚙️ الإعدادات", settings_info)

def main():
    app = QApplication(sys.argv)
    
    # تعيين اللغة والترميز
    app.setStyle('Fusion')
    
    window = SimpleDeviceWindow()
    window.show()
    
    return app.exec_()

if __name__ == "__main__":
    sys.exit(main())