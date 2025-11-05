#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RiF Activator Real Device Reader
قارئ الجهاز الحقيقي - بدون محاكاة
"""

import subprocess
import os
import json

def read_real_device():
    """قراءة معلومات الجهاز الحقيقي"""
    print("🔍 قراءة معلومات الجهاز الحقيقي...")
    
    try:
        # استخدام ideviceinfo للجهاز الحقيقي
        cmd = ["ideviceinfo.exe"]
        if not os.path.exists("ideviceinfo.exe"):
            cmd = ["ideviceinfo"]
            
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        
        if result.returncode != 0:
            print("❌ لم يتم العثور على جهاز")
            print("💡 تأكد من:")
            print("   • وصل الهاتف بكابل USB")
            print("   • فتح الهاتف واختيار Trust")
            print("   • تثبيت iTunes أو Apple Mobile Device Support")
            return None
            
        # تحليل المخرجات
        lines = result.stdout.strip().split("\n")
        device_info = {}
        
        for line in lines:
            if ":" in line:
                key, val = line.split(":", 1)
                device_info[key.strip()] = val.strip()
        
        if not device_info:
            print("❌ لا توجد معلومات جهاز")
            return None
            
        print("✅ تم قراءة معلومات الجهاز بنجاح!")
        return device_info
        
    except subprocess.TimeoutExpired:
        print("❌ انتهت مهلة الاتصال")
        return None
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return None

def display_device_info(device_info):
    """عرض معلومات الجهاز"""
    if not device_info:
        return
        
    print("\n📱 معلومات الجهاز الحقيقي:")
    print("="*40)
    
    # المعلومات المهمة
    important_keys = {
        "ProductType": "نوع المنتج",
        "ProductVersion": "إصدار iOS",
        "SerialNumber": "الرقم التسلسلي",
        "UniqueDeviceID": "معرف الجهاز",
        "DeviceName": "اسم الجهاز",
        "ModelNumber": "رقم الطراز",
        "RegionInfo": "معلومات المنطقة",
        "InternationalMobileEquipmentIdentity": "IMEI",
        "WiFiAddress": "عنوان WiFi",
        "BluetoothAddress": "عنوان Bluetooth"
    }
    
    for key, arabic_name in important_keys.items():
        value = device_info.get(key, "غير متوفر")
        print(f"🔹 {arabic_name}: {value}")
    
    # معلومات إضافية مفيدة
    print(f"\n🔧 معلومات تقنية:")
    tech_keys = {
        "BuildVersion": "رقم البناء",
        "HardwareModel": "موديل العتاد", 
        "CPUArchitecture": "معمارية المعالج",
        "ProductionSOC": "نوع المعالج",
        "SupportedDeviceFamilies": "العائلات المدعومة"
    }
    
    for key, arabic_name in tech_keys.items():
        value = device_info.get(key, "غير متوفر")
        print(f"⚡ {arabic_name}: {value}")

def test_with_server(device_info):
    """اختبار مع خادم RiF Activator"""
    if not device_info:
        return
        
    print(f"\n🌐 اختبار مع خادم RiF Activator...")
    
    try:
        import requests
        
        payload = {
            'udid': device_info.get('UniqueDeviceID', ''),
            'serial': device_info.get('SerialNumber', ''),
            'model': device_info.get('ProductType', '')
        }
        
        headers = {'X-API-Key': 'dev-api-key'}
        
        print(f"📡 إرسال البيانات:")
        print(f"   📱 الموديل: {payload['model']}")
        print(f"   🆔 السيريال: {payload['serial']}")
        
        response = requests.post(
            'http://127.0.0.1:5000/api/check_device',
            json=payload,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            supported = result.get('allowed', False)
            message = result.get('message', '')
            
            print(f"\n✅ استجابة الخادم:")
            print(f"   🎯 النتيجة: {'مدعوم' if supported else 'غير مدعوم'}")
            print(f"   💬 الرسالة: {message}")
            
            if supported:
                print(f"   🚀 الجهاز جاهز للتفعيل!")
            else:
                print(f"   ⚠️ الجهاز غير مدعوم أو يحتاج تحديث")
                
        else:
            print(f"❌ خطأ في الخادم: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ لا يمكن الاتصال بالخادم")
        print("💡 تأكد من تشغيل الخادم: python main.py")
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")

def save_device_info(device_info):
    """حفظ معلومات الجهاز"""
    if not device_info:
        return
        
    try:
        filename = f"real_device_info.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(device_info, f, indent=2, ensure_ascii=False)
        print(f"\n💾 تم حفظ معلومات الجهاز: {filename}")
    except Exception as e:
        print(f"❌ خطأ في الحفظ: {e}")

def main():
    """الدالة الرئيسية"""
    print("🚀 RiF Activator - قارئ الجهاز الحقيقي")
    print("="*50)
    print("⚠️ تأكد من وصل الهاتف واختيار Trust!")
    print()
    
    # قراءة الجهاز
    device_info = read_real_device()
    
    if device_info:
        # عرض المعلومات
        display_device_info(device_info)
        
        # حفظ المعلومات
        save_device_info(device_info)
        
        # اختبار مع الخادم
        test_with_server(device_info)
        
        print(f"\n🎉 تمت قراءة الجهاز الحقيقي بنجاح!")
    else:
        print(f"\n❌ فشل في قراءة الجهاز")
        
    print(f"\nللتشغيل مع الجهاز الحقيقي:")
    print(f"python device_ui.py  (بدون SIMULATE_BYPASS)")

if __name__ == "__main__":
    main()