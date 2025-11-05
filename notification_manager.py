"""# Real-time notification system for RiF Activator A12+

Notification Manager for RiF Activatorimport json

إدارة الإشعارات لـ RiF Activatorimport time

"""from datetime import datetime

from threading import Lock

import jsonfrom collections import deque

from datetime import datetimeimport sqlite3



class NotificationManager:class NotificationManager:

    def __init__(self):    """Manage real-time notifications and events"""

        self.notifications = []    

            def __init__(self, db_path='activator.db'):

    def add_notification(self, title, message, type="info"):        self.db_path = db_path

        """إضافة إشعار جديد"""        self.active_connections = set()

        notification = {        self.notification_queue = deque(maxlen=1000)  # Keep last 1000 notifications

            'id': len(self.notifications) + 1,        self.lock = Lock()

            'title': title,        self.init_notifications_db()

            'message': message,    

            'type': type,    def init_notifications_db(self):

            'timestamp': datetime.now().isoformat(),        """Initialize notifications database table"""

            'read': False        conn = sqlite3.connect(self.db_path)

        }        c = conn.cursor()

        self.notifications.append(notification)        

        return notification        c.execute('''

                    CREATE TABLE IF NOT EXISTS notifications (

    def get_notifications(self):                id INTEGER PRIMARY KEY AUTOINCREMENT,

        """الحصول على جميع الإشعارات"""                type TEXT NOT NULL,

        return self.notifications                title TEXT NOT NULL,

                        message TEXT NOT NULL,

    def mark_as_read(self, notification_id):                severity TEXT DEFAULT 'info',

        """تحديد الإشعار كمقروء"""                metadata TEXT,

        for notification in self.notifications:                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            if notification['id'] == notification_id:                read_by TEXT DEFAULT '[]',

                notification['read'] = True                expires_at TIMESTAMP

                return True            )

        return False        ''')

        

# إنشاء مثيل عام        # Real-time events table

notification_manager = NotificationManager()        c.execute('''

            CREATE TABLE IF NOT EXISTS realtime_events (

def notify_successful_activation(device_model, serial):                id INTEGER PRIMARY KEY AUTOINCREMENT,

    """إشعار نجاح التفعيل"""                event_type TEXT NOT NULL,

    title = "🎉 تم التفعيل بنجاح"                source TEXT NOT NULL,

    message = f"تم تفعيل {device_model} - السيريال: {serial}"                data TEXT NOT NULL,

    return notification_manager.add_notification(title, message, "success")                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                processed BOOLEAN DEFAULT FALSE

def notify_failed_login(ip_address):            )

    """إشعار فشل تسجيل الدخول"""        ''')

    title = "⚠️ محاولة دخول مشبوهة"        

    message = f"محاولة دخول فاشلة من IP: {ip_address}"        conn.commit()

    return notification_manager.add_notification(title, message, "warning")        conn.close()

    

def notify_system_health_alert(message):    def add_connection(self, connection_id):

    """إشعار تنبيه صحة النظام"""        """Add new WebSocket connection"""

    title = "🔧 تنبيه النظام"        with self.lock:

    return notification_manager.add_notification(title, message, "error")            self.active_connections.add(connection_id)
    
    def remove_connection(self, connection_id):
        """Remove WebSocket connection"""
        with self.lock:
            self.active_connections.discard(connection_id)
    
    def get_active_connections_count(self):
        """Get number of active connections"""
        with self.lock:
            return len(self.active_connections)
    
    def create_notification(self, notification_type, title, message, 
                          severity='info', metadata=None, expires_in_hours=24):
        """Create and store a new notification"""
        
        notification = {
            'id': int(time.time() * 1000),  # Unique ID based on timestamp
            'type': notification_type,
            'title': title,
            'message': message,
            'severity': severity,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat(),
            'read': False
        }
        
        # Store in memory queue
        with self.lock:
            self.notification_queue.append(notification)
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        expires_at = None
        if expires_in_hours:
            from datetime import timedelta
            expires_at = (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat()
        
        c.execute('''
            INSERT INTO notifications (type, title, message, severity, metadata, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            notification_type, title, message, severity,
            json.dumps(metadata) if metadata else None,
            expires_at
        ))
        
        conn.commit()
        conn.close()
        
        return notification
    
    def log_realtime_event(self, event_type, source, data):
        """Log real-time event for processing"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO realtime_events (event_type, source, data)
            VALUES (?, ?, ?)
        ''', (event_type, source, json.dumps(data)))
        
        conn.commit()
        conn.close()
    
    def get_recent_notifications(self, limit=50):
        """Get recent notifications"""
        with self.lock:
            recent = list(self.notification_queue)[-limit:]
            return recent
    
    def get_notifications_by_type(self, notification_type, limit=20):
        """Get notifications by type from database"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''
            SELECT id, type, title, message, severity, metadata, created_at
            FROM notifications
            WHERE type = ? AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
            LIMIT ?
        ''', (notification_type, datetime.utcnow().isoformat(), limit))
        
        notifications = []
        for row in c.fetchall():
            notification = {
                'id': row[0],
                'type': row[1],
                'title': row[2],
                'message': row[3],
                'severity': row[4],
                'metadata': json.loads(row[5]) if row[5] else {},
                'timestamp': row[6]
            }
            notifications.append(notification)
        
        conn.close()
        return notifications
    
    def cleanup_expired_notifications(self):
        """Clean up expired notifications"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Delete expired notifications
        c.execute('''
            DELETE FROM notifications
            WHERE expires_at IS NOT NULL AND expires_at < ?
        ''', (datetime.utcnow().isoformat(),))
        
        # Delete old realtime events (older than 7 days)
        from datetime import timedelta
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        c.execute('''
            DELETE FROM realtime_events
            WHERE timestamp < ?
        ''', (week_ago,))
        
        conn.commit()
        conn.close()
    
    def get_dashboard_alerts(self):
        """Get critical alerts for dashboard"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Get recent critical and warning notifications
        c.execute('''
            SELECT type, title, message, severity, created_at
            FROM notifications
            WHERE severity IN ('critical', 'warning', 'error')
            AND (expires_at IS NULL OR expires_at > ?)
            ORDER BY created_at DESC
            LIMIT 10
        ''', (datetime.utcnow().isoformat(),))
        
        alerts = []
        for row in c.fetchall():
            alerts.append({
                'type': row[0],
                'title': row[1], 
                'message': row[2],
                'severity': row[3],
                'timestamp': row[4]
            })
        
        conn.close()
        return alerts

# Predefined notification types and templates
NOTIFICATION_TYPES = {
    'system': {
        'icon': 'bi-cpu',
        'color': 'primary',
        'title_template': 'System Event'
    },
    'security': {
        'icon': 'bi-shield-exclamation',
        'color': 'warning', 
        'title_template': 'Security Alert'
    },
    'activation': {
        'icon': 'bi-check-circle',
        'color': 'success',
        'title_template': 'Activation Event'
    },
    'error': {
        'icon': 'bi-exclamation-triangle',
        'color': 'danger',
        'title_template': 'Error Occurred'
    },
    'admin': {
        'icon': 'bi-person-gear',
        'color': 'info',
        'title_template': 'Admin Action'
    }
}

# Helper functions for common notifications
def notify_successful_activation(device_info, activation_time):
    """Notify successful device activation"""
    return {
        'notification_type': 'activation',
        'title': 'تفعيل ناجح',
        'message': f"تم تفعيل الجهاز {device_info.get('model', 'غير معروف')} بنجاح",
        'severity': 'success',
        'metadata': {
            'device_info': device_info,
            'activation_time': activation_time
        }
    }

def notify_failed_login(ip_address, username):
    """Notify failed login attempt"""
    return {
        'notification_type': 'security',
        'title': 'محاولة دخول مرفوضة',
        'message': f"محاولة دخول فاشلة من {ip_address} للمستخدم {username}",
        'severity': 'warning',
        'metadata': {
            'ip_address': ip_address,
            'username': username
        }
    }

def notify_system_health_alert(metric, value, threshold):
    """Notify system health alert"""
    return {
        'notification_type': 'system',
        'title': 'تحذير صحة النظام',
        'message': f"{metric} وصل إلى {value}% (الحد الأقصى: {threshold}%)",
        'severity': 'warning',
        'metadata': {
            'metric': metric,
            'value': value,
            'threshold': threshold
        }
    }

def notify_database_backup(success, file_path=None, error=None):
    """Notify database backup result"""
    if success:
        return {
            'notification_type': 'system',
            'title': 'نسخ احتياطي ناجح',
            'message': f"تم إنشاء نسخة احتياطية بنجاح: {file_path}",
            'severity': 'info',
            'metadata': {'file_path': file_path}
        }
    else:
        return {
            'notification_type': 'error',
            'title': 'فشل النسخ الاحتياطي',
            'message': f"فشل في إنشاء النسخة الاحتياطية: {error}",
            'severity': 'error',
            'metadata': {'error': error}
        }

# Global notification manager instance
notification_manager = NotificationManager()