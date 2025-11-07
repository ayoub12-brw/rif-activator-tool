#!/usr/bin/env python3
"""
تشخيص شامل لمشكلة الموديل
"""

from dotenv import load_dotenv
import os

load_dotenv()

device_model = "iPhone14,2"
local_models = os.getenv('LOCAL_ALLOWED_MODELS', '')

print(f"🔍 تشخيص شامل:")
print(f"device_model: '{device_model}' (length: {len(device_model)})")
print(f"local_models: '{local_models}' (length: {len(local_models)})")
print(f"Exact match: {device_model == local_models}")
print()

# اختبار طرق مختلفة للتقسيم
print("🧪 اختبار طرق التقسيم:")

# طريقة 1: بدون تقسيم (مطابقة مباشرة)
direct_match = device_model == local_models
print(f"1. مطابقة مباشرة: {direct_match}")

# طريقة 2: التقسيم بـ comma
comma_split = local_models.split(',')
comma_match = device_model in [m.strip() for m in comma_split]
print(f"2. تقسيم بـ comma: {comma_split} -> {comma_match}")

# طريقة 3: التقسيم بـ |
pipe_split = local_models.split('|')  
pipe_match = device_model in [m.strip() for m in pipe_split]
print(f"3. تقسيم بـ |: {pipe_split} -> {pipe_match}")

# طريقة 4: التحقق من وجود النص
contains_match = device_model in local_models
print(f"4. يحتوي على: {contains_match}")

print()
print("🎯 الحل:")
if direct_match:
    print("✅ استخدم المطابقة المباشرة")
elif contains_match:
    print("✅ استخدم فحص الاحتواء")
else:
    print("❌ يحتاج إصلاح في التكوين")
    print("💡 اقتراح: استخدم قيمة واحدة في LOCAL_ALLOWED_MODELS")