#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MobileGestalt.plist Parser
تحليل ملف معلومات الجهاز iOS

هذا الملف يقرأ ويحلل بيانات MobileGestalt لاستخراج معلومات الجهاز المهمة
"""

import plistlib
import json
import os
from pathlib import Path

class MobileGestaltParser:
    """
    قارئ ومحلل ملف MobileGestalt.plist
    """
    
    def __init__(self, plist_path="com.apple.MobileGestalt.plist"):
        self.plist_path = plist_path
        self.data = None
        self.device_info = {}
        
    def load_plist(self):
        """تحميل ملف plist"""
        try:
            with open(self.plist_path, 'rb') as f:
                self.data = plistlib.load(f)
            return True
        except Exception as e:
            print(f"❌ خطأ في تحميل الملف: {e}")
            return False
    
    def extract_device_info(self):
        """استخراج معلومات الجهاز المهمة"""
        if not self.data:
            return None
            
        cache_extra = self.data.get('CacheExtra', {})
        
        # معلومات الجهاز الأساسية
        self.device_info = {
            # الموديل والاسم
            'product_type': cache_extra.get('h9jDsbgj7xIVeIQ8S3/X3Q', 'Unknown'),  # iPhone11,2
            'marketing_name': cache_extra.get('Z/dqyWS6OZTRy10UcmUAhw', 'Unknown'),  # iPhone XS
            'device_class': cache_extra.get('+3Uf0Pm5F8Xy7Onyvko0vA', 'Unknown'),  # iPhone
            'model_number': cache_extra.get('97JDvERpVwO+GHtthIh7hA', 'Unknown'),   # A2098
            
            # نظام التشغيل
            'ios_version': cache_extra.get('qNNddlUK+B/YlooNoymwgA', 'Unknown'),    # 18.7.1
            'build_version': cache_extra.get('mZfUC7qo4pURNhyMHZ62RQ', 'Unknown'),  # 22H31
            'system_name': cache_extra.get('ivIu8YTDnBSrYv/SN4G8Ag', 'Unknown'),   # iPhone OS
            'ui_kit_name': cache_extra.get('yjP8DgByZmLk04Ta6f6DWQ', 'Unknown'),   # iOS
            
            # المعالج والأداء
            'chip_id': cache_extra.get('5pYKlGnYYBzGvAlIU8RjEQ', 'Unknown'),       # t8020 (A12)
            'cpu_architecture': cache_extra.get('k7QIBwZJJOVw+Sej/8h8VA', 'Unknown'), # arm64e
            'bootloader': cache_extra.get('LeSRsiLoJCMhjn6nd6GWbQ', 'Unknown'),     # iBoot version
            
            # الشاشة والرسومات
            'artwork_info': cache_extra.get('oPeik/9e8lQWMszEjbPzng', {}),
            'display_gamut': cache_extra.get('LTI8wHvEYKy8zR1IXBW1uQ', 'Unknown'),  # P3
            
            # معلومات إضافية
            'device_uuid': cache_extra.get('4qfpxrvLtWillIHpIsVgMA', 'Unknown'),
            'platform_uuid': cache_extra.get('qwXfFvH5jPXPxrny0XuGtQ', 'Unknown'),
            'region_code': cache_extra.get('zHeENZu+wbg7PUprwNwBWg', 'Unknown'),   # J/A
            'baseband_version': cache_extra.get('96GRvvjxBKkU4HzNsYcHPA', 'Unknown')
        }
        
        return self.device_info
    
    def get_compatibility_info(self):
        """معلومات التوافق مع التفعيل"""
        if not self.device_info:
            return None
            
        # تحليل التوافق
        compatibility = {
            'supported_device': self.is_supported_device(),
            'ios_in_range': self.is_ios_supported(),
            'bypass_compatible': self.is_bypass_compatible(),
            'activation_ready': False
        }
        
        # تحديد الجاهزية للتفعيل
        compatibility['activation_ready'] = all([
            compatibility['supported_device'],
            compatibility['ios_in_range'],
            compatibility['bypass_compatible']
        ])
        
        return compatibility
    
    def is_supported_device(self):
        """فحص إذا كان الجهاز مدعوم"""
        supported_models = [
            'iPhone11,2', 'iPhone11,4', 'iPhone11,6', 'iPhone11,8',  # iPhone XS/XR
            'iPhone12,1', 'iPhone12,3', 'iPhone12,5',                # iPhone 11
            'iPhone13,1', 'iPhone13,2', 'iPhone13,3', 'iPhone13,4',  # iPhone 12
            'iPhone14,2', 'iPhone14,3', 'iPhone14,4', 'iPhone14,5',  # iPhone 13
            'iPhone14,7', 'iPhone14,8',                              # iPhone 14
            'iPhone15,2', 'iPhone15,3', 'iPhone15,4', 'iPhone15,5',  # iPhone 14 Pro/15
            'iPhone16,1', 'iPhone16,2'                               # iPhone 15 Pro
        ]
        
        return self.device_info.get('product_type') in supported_models
    
    def is_ios_supported(self):
        """فحص نطاق iOS المدعوم"""
        ios_version = self.device_info.get('ios_version', '0.0.0')
        try:
            # تحويل النسخة لأرقام للمقارنة
            version_parts = [int(x) for x in ios_version.split('.')]
            while len(version_parts) < 3:
                version_parts.append(0)
                
            version_tuple = tuple(version_parts[:3])
            
            # النطاق المدعوم: iOS 18.7.1 - 26.1.999
            min_version = (18, 7, 1)
            max_version = (26, 1, 999)
            
            return min_version <= version_tuple <= max_version
            
        except Exception:
            return False
    
    def is_bypass_compatible(self):
        """فحص توافق bypass"""
        # فحص المعالج (A12+)
        chip_id = self.device_info.get('chip_id', '')
        supported_chips = ['t8020', 't8027', 't8030', 't8101', 't8103', 't8110', 't8120']
        
        # فحص المعمارية
        architecture = self.device_info.get('cpu_architecture', '')
        supported_arch = ['arm64e', 'arm64']
        
        return (chip_id in supported_chips and 
                architecture in supported_arch)
    
    def print_analysis(self):
        """طباعة تحليل شامل للجهاز"""
        if not self.device_info:
            print("❌ لم يتم تحميل بيانات الجهاز")
            return
            
        print("\n" + "="*60)
        print("🔍 تحليل معلومات جهاز iOS")
        print("="*60)
        
        # معلومات الجهاز
        print(f"\n📱 معلومات الجهاز:")
        print(f"   الموديل: {self.device_info['product_type']}")
        print(f"   الاسم التسويقي: {self.device_info['marketing_name']}")
        print(f"   رقم الطراز: {self.device_info['model_number']}")
        print(f"   نوع الجهاز: {self.device_info['device_class']}")
        
        # نظام التشغيل
        print(f"\n🍎 نظام التشغيل:")
        print(f"   إصدار iOS: {self.device_info['ios_version']}")
        print(f"   البناء: {self.device_info['build_version']}")
        print(f"   اسم النظام: {self.device_info['system_name']}")
        
        # المعالج
        print(f"\n⚡ المعالج:")
        print(f"   معرف الشريحة: {self.device_info['chip_id']}")
        print(f"   المعمارية: {self.device_info['cpu_architecture']}")
        print(f"   البوتلودر: {self.device_info['bootloader']}")
        
        # الشاشة
        artwork = self.device_info.get('artwork_info', {})
        if artwork:
            print(f"\n🖥️ الشاشة:")
            print(f"   نوع الجهاز: {artwork.get('ArtworkDeviceIdiom', 'Unknown')}")
            print(f"   معامل التكبير: {artwork.get('ArtworkDeviceScaleFactor', 'Unknown')}x")
            print(f"   نوع الشاشة: {artwork.get('ArtworkDeviceSubType', 'Unknown')}")
            print(f"   نطاق الألوان: {artwork.get('ArtworkDisplayGamut', 'Unknown')}")
        
        # تحليل التوافق
        compatibility = self.get_compatibility_info()
        print(f"\n🛡️ تحليل التوافق:")
        print(f"   جهاز مدعوم: {'✅ نعم' if compatibility['supported_device'] else '❌ لا'}")
        print(f"   iOS مدعوم: {'✅ نعم' if compatibility['ios_in_range'] else '❌ لا'}")
        print(f"   Bypass متوافق: {'✅ نعم' if compatibility['bypass_compatible'] else '❌ لا'}")
        print(f"   جاهز للتفعيل: {'🚀 نعم' if compatibility['activation_ready'] else '⚠️ لا'}")
        
        print("\n" + "="*60)
    
    def save_analysis(self, output_file="device_analysis.json"):
        """حفظ التحليل في ملف JSON"""
        if not self.device_info:
            return False
            
        analysis_data = {
            'device_info': self.device_info,
            'compatibility': self.get_compatibility_info(),
            'analysis_timestamp': os.path.getctime(self.plist_path) if os.path.exists(self.plist_path) else None
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            print(f"💾 تم حفظ التحليل في: {output_file}")
            return True
        except Exception as e:
            print(f"❌ خطأ في حفظ التحليل: {e}")
            return False

def main():
    """الدالة الرئيسية"""
    print("🚀 محلل MobileGestalt.plist")
    print("="*40)
    
    parser = MobileGestaltParser()
    
    # تحميل الملف
    if not parser.load_plist():
        print("❌ فشل في تحميل ملف MobileGestalt.plist")
        return
    
    # استخراج المعلومات
    device_info = parser.extract_device_info()
    if not device_info:
        print("❌ فشل في استخراج معلومات الجهاز")
        return
    
    # طباعة التحليل
    parser.print_analysis()
    
    # حفظ التحليل
    parser.save_analysis()
    
    print("\n✅ تم الانتهاء من التحليل بنجاح!")

if __name__ == "__main__":
    main()