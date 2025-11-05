# -*- coding: utf-8 -*-
"""
Security Manager for RiF Activator
إدارة الأمان لـ RiF Activator
"""

import hashlib
import secrets
from datetime import datetime, timedelta

class SecurityManager:
    def __init__(self, secret_key="default-secret"):
        self.secret_key = secret_key
        self.failed_attempts = {}
        self.blocked_ips = {}
        
    def hash_password(self, password):
        """تشفير كلمة المرور"""
        return hashlib.sha256(password.encode()).hexdigest()
        
    def verify_password(self, password, hashed):
        """التحقق من كلمة المرور"""
        return self.hash_password(password) == hashed
        
    def generate_token(self, user_id):
        """إنشاء رمز مميز"""
        try:
            import jwt
            payload = {
                'user_id': user_id,
                'exp': datetime.utcnow() + timedelta(hours=24)
            }
            return jwt.encode(payload, self.secret_key, algorithm='HS256')
        except ImportError:
            # إذا لم يكن JWT متاح، استخدم رمز بسيط
            return hashlib.sha256(f"{user_id}{self.secret_key}".encode()).hexdigest()
        
    def verify_token(self, token):
        """التحقق من الرمز المميز"""
        try:
            import jwt
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload['user_id']
        except ImportError:
            return None
        except Exception:
            return None
            
    def is_safe_request(self, ip_address):
        """التحقق من سلامة الطلب"""
        if ip_address in self.blocked_ips:
            block_time = self.blocked_ips[ip_address]
            if datetime.now() < block_time:
                return False
            else:
                del self.blocked_ips[ip_address]
        return True
        
    def record_failed_attempt(self, ip_address):
        """تسجيل محاولة فاشلة"""
        if ip_address not in self.failed_attempts:
            self.failed_attempts[ip_address] = 0
            
        self.failed_attempts[ip_address] += 1
        
        if self.failed_attempts[ip_address] >= 5:
            self.blocked_ips[ip_address] = datetime.now() + timedelta(minutes=15)