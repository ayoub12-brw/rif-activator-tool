#!/usr/bin/env python3
"""
تشخيص مشكلة المقارنة
"""

from dotenv import load_dotenv
import os

load_dotenv()

device_model = "iPhone14,2"
local_models = os.getenv('LOCAL_ALLOWED_MODELS', '')

print(f"device_model: '{device_model}'")
print(f"local_models: '{local_models}'")
print(f"split result: {local_models.split(',')}")
print(f"device_model in split: {device_model in local_models.split(',')}")
print(f"Stripped comparison:")
for model in local_models.split(','):
    print(f"  '{model.strip()}' == '{device_model}': {model.strip() == device_model}")
    
print(f"\nFixed check: {device_model in [m.strip() for m in local_models.split(',')]}")