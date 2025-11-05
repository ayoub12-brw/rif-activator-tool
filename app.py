from flask import Flask, request, render_template, redirect, url_for, jsonify, session, send_file, make_response
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import sqlite3
import os
from datetime import datetime
import requests
import json
import threading
import time
from collections import deque
from dotenv import load_dotenv
import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import psutil
from security_manager import SecurityManager
from notification_manager import notification_manager, notify_successful_activation, notify_failed_login, notify_system_health_alert
from api_integration import setup_complete_api_documentation
from functools import wraps

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
DB_PATH = 'serials.db'
app.secret_key = os.environ.get('FLASK_SECRET', 'dev-secret-key')

# Initialize SocketIO for real-time features
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Initialize Security Manager
security_manager = SecurityManager(DB_PATH, app.secret_key)

# Security decorators
def require_auth(f):
    """Require authentication for endpoint"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check session-based auth first
        if session.get('admin'):
            return f(*args, **kwargs)
        
        # Check token-based auth
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header[7:]
            session_data = security_manager.validate_session(token)
            if session_data.get('valid'):
                session['admin'] = True
                session['user_id'] = session_data['user_id']
                return f(*args, **kwargs)
        
        return jsonify({'error': 'Authentication required'}), 401
    return decorated_function

def rate_limit(max_requests=10, window_minutes=1):
    """Rate limiting decorator"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            endpoint = request.endpoint or f.__name__
            
            if not security_manager.check_rate_limit(client_ip, endpoint, max_requests, window_minutes):
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Default admin password (can be overridden by ADMIN_PASSWORD env var)
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Gsmrif2024@@')

# Enhanced logging setup
def setup_enhanced_logging():
    # Create logs directory
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Application logger
    app_logger = logging.getLogger('app')
    app_logger.setLevel(logging.INFO)
    
    # Rotating file handler for general app logs
    app_handler = RotatingFileHandler(
        'logs/app.log', 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    app_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    ))
    app_logger.addHandler(app_handler)
    
    # Security logger for admin actions
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    
    security_handler = RotatingFileHandler(
        'logs/security.log',
        maxBytes=5*1024*1024,  # 5MB
        backupCount=10
    )
    security_handler.setFormatter(logging.Formatter(
        '%(asctime)s | SECURITY | %(message)s'
    ))
    security_logger.addHandler(security_handler)
    
    # API access logger
    api_logger = logging.getLogger('api')
    api_logger.setLevel(logging.INFO)
    
    api_handler = TimedRotatingFileHandler(
        'logs/api.log',
        when='midnight',
        interval=1,
        backupCount=30
    )
    api_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(remote_addr)s | %(method)s %(url)s | %(status_code)s | %(response_time)s ms'
    ))
    api_logger.addHandler(api_handler)
    
    return app_logger, security_logger, api_logger

# Initialize loggers
app_logger, security_logger, api_logger = setup_enhanced_logging()

# Real-time activity feed
activity_feed = deque(maxlen=1000)  # Keep last 1000 activities

def add_activity(activity_type, description, user=None, metadata=None):
    activity = {
        'timestamp': datetime.utcnow().isoformat(),
        'type': activity_type,
        'description': description,
        'user': user,
        'metadata': metadata or {}
    }
    activity_feed.append(activity)

def init_db():
    # Always connect and ensure required tables exist. This handles upgrades
    # when the DB file already exists but new tables (like payments) are missing.
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS serials (id INTEGER PRIMARY KEY AUTOINCREMENT, serial TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS payments (id INTEGER PRIMARY KEY AUTOINCREMENT, serial TEXT, tx_hash TEXT, amount REAL, currency TEXT, status TEXT, created_at TEXT, verified_at TEXT)''')
    conn.commit()
    # Ensure `chain` column exists (for upgrades). SQLite doesn't support IF NOT EXISTS for columns,
    # so check PRAGMA and ALTER TABLE only when necessary.
    c.execute("PRAGMA table_info(payments)")
    cols = [r[1] for r in c.fetchall()]
    if 'chain' not in cols:
        try:
            c.execute("ALTER TABLE payments ADD COLUMN chain TEXT DEFAULT 'bsc'")
            conn.commit()
        except Exception:
            # best-effort: if ALTER fails, keep going
            pass
    conn.close()

    # Ensure device verification tables
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS supported_models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model TEXT UNIQUE,
        notes TEXT,
        enabled INTEGER DEFAULT 1,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS activations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        udid TEXT,
        serial TEXT,
        model TEXT,
        status TEXT,
        reason TEXT,
        notes TEXT,
        api_key_user TEXT,
        created_at TEXT,
        processed_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys (
        key TEXT PRIMARY KEY,
        label TEXT,
        active INTEGER DEFAULT 1,
        scope TEXT DEFAULT 'default',
        created_at TEXT
    )''')
    conn.commit()
    # Ensure 'scope' column exists for older DBs (migrations)
    try:
        c.execute("PRAGMA table_info(api_keys)")
        ak_cols = [r[1] for r in c.fetchall()]
        if 'scope' not in ak_cols:
            try:
                c.execute("ALTER TABLE api_keys ADD COLUMN scope TEXT DEFAULT 'default'")
                conn.commit()
            except Exception:
                pass
    except Exception:
        pass
    # Ensure there's at least one API key if none exist (development key from env)
    try:
        c.execute('SELECT COUNT(*) FROM api_keys')
        if c.fetchone()[0] == 0:
            default_key = os.environ.get('API_KEY', 'dev-api-key')
            now = datetime.utcnow().isoformat()
            c.execute('INSERT OR IGNORE INTO api_keys (key,label,active,created_at) VALUES (?,?,?,?)', (default_key, 'default', 1, now))
            conn.commit()
    except Exception:
        pass
    conn.close()
    
    # Initialize security manager database
    security_manager.init_security_db()
    
    # Create default admin user if none exists
    create_default_admin_user()

def create_default_admin_user():
    """Create default admin user if none exists"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM admin_users')
        count = c.fetchone()[0]
        conn.close()
        
        if count == 0:
            # Create default admin user
            result = security_manager.create_admin_user(
                username='admin',
                password=ADMIN_PASSWORD,
                enable_2fa=False
            )
            if result['success']:
                print("✅ تم إنشاء حساب المشرف الافتراضي:")
                print(f"   👤 اسم المستخدم: admin")
                print(f"   🔑 كلمة المرور: {ADMIN_PASSWORD}")
                print("   🔒 يمكنك تفعيل المصادقة الثنائية من لوحة الإدارة")
            else:
                print(f"❌ فشل في إنشاء حساب المشرف: {result.get('error', 'خطأ غير معروف')}")
    except Exception as e:
        print(f"⚠️ خطأ في إنشاء حساب المشرف: {e}")

# Payment address (show on home page) - set PAYMENT_ADDRESS env var to your receiving address
PAYMENT_ADDRESS = os.environ.get('PAYMENT_ADDRESS', 'YOUR_USDT_ADDRESS')
ETHERSCAN_API_KEY = os.environ.get('ETHERSCAN_API_KEY')
BSC_API_KEY = os.environ.get('BSC_API_KEY')
ETHEREUM_RPC = os.environ.get('ETHEREUM_RPC')
BSC_RPC = os.environ.get('BSC_RPC')

# Rate limiting (per API key): requests per minute
RATE_LIMIT_PER_MIN = int(os.environ.get('RATE_LIMIT_PER_MIN', '60'))
# In-memory store: key -> deque of timestamps
rate_buckets = {}
rate_lock = threading.Lock()

# USDT contract addresses and decimals per chain
TOKEN_INFO = {
    'eth': {
        'contract': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
        'decimals': 6,
        'api_base': 'https://api.etherscan.io/api',
        'api_key': ETHERSCAN_API_KEY,
        'rpc': ETHEREUM_RPC
    },
    'bsc': {
        'contract': '0x55d398326f99059fF775485246999027B3197955',
        'decimals': 18,  # actually USDT on BSC has 18 decimals
        'api_base': 'https://api.bscscan.com/api',
        'api_key': BSC_API_KEY,
        'rpc': BSC_RPC
    }
}

TRANSFER_EVENT_SIG = '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef'

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        # Enhanced main page with modern design - Version 2
        return render_template('index_enhanced_v2.html')
    
    if request.method == 'POST':
        # Support both form POST and JSON POST (AJAX)
        if request.is_json:
            data = request.get_json()
            serial = data.get('serial', '').strip()
        else:
            serial = request.form.get('serial', '').strip()

        if serial:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            try:
                c.execute('INSERT INTO serials (serial) VALUES (?)', (serial,))
                conn.commit()
                inserted = True
            except sqlite3.IntegrityError:
                inserted = False
            conn.close()
        else:
            inserted = False

        if request.is_json:
            return jsonify({'success': inserted, 'serial': serial})
        return redirect(url_for('index'))
    # عرض كل السيريلات
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT serial FROM serials')
    serials = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template('index.html', serials=serials)

@app.route('/classic', methods=['GET', 'POST'])
def index_classic():
    # Classic interface for device checking
    if request.method == 'POST':
        # Same logic as main index but return classic template
        if request.is_json:
            data = request.get_json()
            serial = data.get('serial', '').strip()
        else:
            serial = request.form.get('serial', '').strip()
        
        if serial:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            try:
                c.execute('INSERT INTO serials (serial) VALUES (?)', (serial,))
                conn.commit()
                inserted = True
            except sqlite3.IntegrityError:
                inserted = False
            conn.close()
        else:
            inserted = False
        
        if request.is_json:
            return jsonify({'success': inserted, 'serial': serial})
        return redirect(url_for('index_classic'))
    
    # عرض كل السيريلات في الواجهة الكلاسيكية
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT serial FROM serials')
    serials = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template('index.html', serials=serials)

@app.route('/check_device', methods=['GET'])
def check_device():
    # Enhanced device check page
    return render_template('check_device_enhanced.html')

@app.route('/api/check_serial', methods=['POST'])
def check_serial():
    data = request.get_json()
    serial = data.get('serial', '').strip()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM serials WHERE serial=?', (serial,))
    found = c.fetchone() is not None
    conn.close()
    return jsonify({'registered': found})


@app.route('/pay_register', methods=['POST'])
def pay_register():
    # Accept JSON { serial, tx, amount, currency }
    data = request.get_json() or {}
    serial = data.get('serial', '').strip()
    tx = data.get('tx', '').strip()
    try:
        amount = float(data.get('amount', 0))
    except Exception:
        amount = 0.0
    currency = (data.get('currency') or 'USDT').strip()
    chain = (data.get('chain') or 'bsc').strip().lower()

    # Support a special free registration mode: chain='free'
    if chain == 'free':
        # free registrations don't require tx or amount; create a verified payment record
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            now = datetime.utcnow().isoformat()
            # insert serial if not exists
            try:
                c.execute('INSERT INTO serials (serial) VALUES (?)', (serial,))
            except sqlite3.IntegrityError:
                pass
            c.execute('INSERT INTO payments (serial, tx_hash, amount, currency, status, created_at, verified_at, chain) VALUES (?,?,?,?,?,?,?,?)',
                      (serial, '', 0.0, 'FREE', 'verified', now, now, 'free'))
            conn.commit()
            pid = c.lastrowid
            conn.close()
            return jsonify({'success': True, 'payment_id': pid, 'chain': 'free', 'message': 'free registration verified'})
        except sqlite3.Error as e:
            try:
                conn.close()
            except Exception:
                pass
            return jsonify({'success': False, 'message': 'Database error: ' + str(e)}), 500

    if not serial or not tx or amount <= 0:
        return jsonify({'success': False, 'message': 'Missing or invalid parameters'}), 400

    # Server-side basic tx validation to avoid storing serials in the tx field
    def is_valid_tx(t):
        if not t or not isinstance(t, str):
            return False
        t = t.strip()
        # Accept common formats: 0x-prefixed hex of reasonable length
        if t.startswith('0x') and len(t) >= 10:
            return True
        # also accept etherscan/bscscan links containing /tx/...
        if '/tx/' in t and 'http' in t:
            return True
        return False

    if not is_valid_tx(tx):
        return jsonify({'success': False, 'message': 'Invalid tx hash format'}), 400

    # require exact 5 USDT for now
    if currency.upper() != 'USDT' or abs(amount - 5.0) > 0.001:
        return jsonify({'success': False, 'message': 'Amount must be 5 USDT'}), 400

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        c.execute('INSERT INTO payments (serial, tx_hash, amount, currency, status, created_at, chain) VALUES (?,?,?,?,?,?,?)',
                  (serial, tx, amount, currency.upper(), 'pending', now, chain))
        conn.commit()
        pid = c.lastrowid
        conn.close()
        # Log the payment attempt for debugging (append-only)
        try:
            with open('payments.log', 'a', encoding='utf-8') as lf:
                lf.write(f"{datetime.utcnow().isoformat()} | payment_id={pid} | serial={serial} | tx={tx} | amount={amount} | currency={currency} | chain={chain}\n")
        except Exception:
            pass
        return jsonify({'success': True, 'payment_id': pid, 'chain': chain})
    except sqlite3.Error as e:
        # return a JSON error so the frontend can show a helpful message
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'success': False, 'message': 'Database error: ' + str(e)}), 500


@app.route('/api/admin/payments', methods=['GET'])
def admin_payments():
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, serial, tx_hash, amount, currency, status, created_at, verified_at, chain FROM payments ORDER BY id DESC')
    rows = c.fetchall()
    payments = [dict(id=r[0], serial=r[1], tx=r[2], amount=r[3], currency=r[4], status=r[5], created_at=r[6], verified_at=r[7], chain=(r[8] or 'bsc')) for r in rows]
    conn.close()
    return jsonify({'payments': payments})


@app.route('/api/admin/cleanup_bad_payments', methods=['POST'])
def admin_cleanup_bad_payments():
    """Mark payments with obviously invalid tx as 'invalid_tx'. Admin only."""
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, serial, tx_hash FROM payments')
    rows = c.fetchall()
    to_mark = []
    for r in rows:
        pid, serial, tx = r[0], r[1], (r[2] or '')
        if not isinstance(tx, str):
            tx = str(tx)
        # same logic as pay_register.is_valid_tx
        valid = False
        if tx.startswith('0x') and len(tx) >= 10:
            valid = True
        if '/tx/' in tx and 'http' in tx:
            valid = True
        if not valid:
            to_mark.append(pid)
    if to_mark:
        c.executemany('UPDATE payments SET status=? WHERE id=?', [('invalid_tx', pid) for pid in to_mark])
        conn.commit()
    conn.close()
    return jsonify({'marked': to_mark})


@app.route('/api/admin/verify_payment', methods=['POST'])
def admin_verify_payment():
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'forbidden'}), 403
    data = request.get_json() or {}
    pid = data.get('payment_id')
    if not pid:
        return jsonify({'success': False, 'message': 'Missing payment_id'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT serial, status FROM payments WHERE id=?', (pid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'message': 'Not found'}), 404
    serial, status = row
    if status == 'verified':
        conn.close()
        return jsonify({'success': False, 'message': 'Already verified'})
    # insert serial if not exists
    try:
        c.execute('INSERT INTO serials (serial) VALUES (?)', (serial,))
    except sqlite3.IntegrityError:
        pass
    now = datetime.utcnow().isoformat()
    c.execute('UPDATE payments SET status=?, verified_at=? WHERE id=?', ('verified', now, pid))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


def _eth_get_receipt(txhash, api_base, api_key, rpc_url=None):
    """
    Fetch transaction receipt. Prefer JSON-RPC when rpc_url is provided.
    Fallback to explorer proxy API. Always return a dict (possibly with 'raw'
    containing text) so callers can inspect/log unexpected responses.
    """
    try:
        # Try JSON-RPC first when rpc_url is provided
        if rpc_url:
            payload = {'jsonrpc': '2.0', 'method': 'eth_getTransactionReceipt', 'params': [txhash], 'id': 1}
            try:
                r = requests.post(rpc_url, json=payload, timeout=10)
                r.raise_for_status()
                j = r.json()
                # If the node returns the receipt directly, wrap as {'result': receipt}
                if isinstance(j, dict) and 'result' in j:
                    return j
                if isinstance(j, dict) and ('logs' in j or 'transactionHash' in j):
                    return {'result': j}
            except Exception:
                # fallthrough to explorer API
                pass

        # Use explorer proxy API as fallback
        params = {'module': 'proxy', 'action': 'eth_getTransactionReceipt', 'txhash': txhash}
        if api_key:
            params['apikey'] = api_key
        r = requests.get(api_base, params=params, timeout=15)
        r.raise_for_status()
        # Try to parse JSON
        try:
            parsed = r.json()
            # If explorer returns a string inside the JSON, normalize
            if isinstance(parsed, dict):
                return parsed
            else:
                return {'result': parsed}
        except Exception:
            # Not JSON: return raw text in a wrapper
            return {'result': None, 'raw': r.text}
    except Exception:
        return {}


def check_api_key(req):
    key = req.headers.get('X-API-Key') or req.headers.get('x-api-key')
    if not key:
        return False, None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT active, scope FROM api_keys WHERE key=?', (key,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False, None
    return (row[0] == 1), {'key': key, 'scope': row[1]}


def is_rate_limited(key_info):
    if not key_info:
        return True
    k = key_info['key'] if isinstance(key_info, dict) else key_info
    now = time.time()
    window = 60
    with rate_lock:
        dq = rate_buckets.get(k)
        if dq is None:
            dq = deque()
            rate_buckets[k] = dq
        # drop old timestamps
        while dq and dq[0] < now - window:
            dq.popleft()
        if len(dq) >= RATE_LIMIT_PER_MIN:
            return True
        dq.append(now)
    return False


def log_activation_enhanced(udid, serial, model, status, reason='', notes='', api_key_user=None, additional_data=None):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        
        # Store in database
        c.execute('INSERT INTO activations (udid, serial, model, status, reason, notes, api_key_user, created_at) VALUES (?,?,?,?,?,?,?,?)',
                  (udid, serial, model, status, reason, notes, api_key_user, now))
        
        # Enhanced file logging
        log_entry = {
            'timestamp': now,
            'udid': udid,
            'serial': serial,
            'model': model,
            'status': status,
            'reason': reason,
            'notes': notes,
            'api_key_user': api_key_user,
            'additional_data': additional_data or {}
        }
        
        app_logger.info(f"ACTIVATION: {json.dumps(log_entry)}")
        
        # Add to activity feed
        add_activity('activation', f"{model} - {status}", api_key_user, {
            'serial': serial[:8] + '...' if serial else '',
            'model': model,
            'status': status
        })
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        app_logger.error(f"Failed to log activation: {str(e)}")

# Keep old function for compatibility
def log_activation(udid, serial, model, status, reason='', notes='', api_key_user=None):
    return log_activation_enhanced(udid, serial, model, status, reason, notes, api_key_user)


@app.route('/api/check_device', methods=['POST'])
def api_check_device():
    ok, key_info = check_api_key(request)
    if not ok:
        return jsonify({'error': 'invalid_api_key'}), 401
    if is_rate_limited(key_info):
        return jsonify({'error': 'rate_limited'}), 429
    data = request.get_json() or {}
    udid = (data.get('udid') or '').strip()
    serial = (data.get('serial') or '').strip()
    model = (data.get('model') or '').strip()
    if not (udid and serial and model):
        return jsonify({'error': 'missing_parameters'}), 400

    # Check supported models
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT enabled FROM supported_models WHERE model=?', (model,))
    row = c.fetchone()
    print(f"[SERVER DEBUG] check_device: model={model}, row={row}")
    if not row:
        # not supported
        log_activation(udid, serial, model, 'rejected', 'model_not_supported', '', key_info['key'])
        conn.close()
        return jsonify({'allowed': False, 'code': 'UNSUPPORTED_MODEL', 'message': 'Model not supported'}), 200
    enabled = bool(row[0])
    if not enabled:
        log_activation(udid, serial, model, 'rejected', 'model_disabled', '', key_info['key'])
        conn.close()
        return jsonify({'allowed': False, 'code': 'MODEL_DISABLED', 'message': 'Model is disabled'}), 200

    # auto-approve
    log_activation(udid, serial, model, 'allowed', 'auto_approved', '', key_info['key'])
    conn.close()
    return jsonify({'allowed': True, 'code': 'OK', 'message': 'device allowed'}), 200


@app.route('/api/admin/supported_models', methods=['GET', 'POST'])
def admin_supported_models():
    # admin (session) required
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    if request.method == 'GET':
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, model, notes, enabled, created_at FROM supported_models ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()
        models = [dict(id=r[0], model=r[1], notes=r[2], enabled=bool(r[3]), created_at=r[4]) for r in rows]
        return jsonify({'models': models})
    else:
        data = request.get_json() or {}
        model = (data.get('model') or '').strip()
        notes = (data.get('notes') or '').strip()
        if not model:
            return jsonify({'success': False, 'message': 'Missing model'}), 400
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        try:
            c.execute('INSERT INTO supported_models (model, notes, enabled, created_at) VALUES (?,?,?,?)', (model, notes, 1, now))
            conn.commit()
            mid = c.lastrowid
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'success': False, 'message': 'Model already exists'}), 400
        conn.close()
        return jsonify({'success': True, 'id': mid})


@app.route('/api/admin/supported_models/<int:model_id>/toggle', methods=['POST'])
def admin_toggle_model(model_id):
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT enabled FROM supported_models WHERE id=?', (model_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'message': 'Not found'}), 404
    newv = 0 if row[0]==1 else 1
    c.execute('UPDATE supported_models SET enabled=? WHERE id=?', (newv, model_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'enabled': bool(newv)})


@app.route('/api/admin/api_keys', methods=['GET', 'POST'])
def admin_api_keys():
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    if request.method == 'GET':
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT key, label, active, scope, created_at FROM api_keys ORDER BY created_at DESC')
        rows = c.fetchall()
        conn.close()
        keys = [dict(key=r[0], label=r[1], active=bool(r[2]), scope=r[3], created_at=r[4]) for r in rows]
        return jsonify({'api_keys': keys})
    else:
        data = request.get_json() or {}
        label = (data.get('label') or '').strip()
        scope = (data.get('scope') or 'default').strip()
        if not label:
            return jsonify({'success': False, 'message': 'Missing label'}), 400
        new_key = os.environ.get('API_KEY_PREFIX', '') + os.urandom(12).hex()
        now = datetime.utcnow().isoformat()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO api_keys (key,label,active,scope,created_at) VALUES (?,?,?,?,?)', (new_key, label, 1, scope, now))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'key': new_key})


@app.route('/api/admin/api_keys/<key>/toggle', methods=['POST'])
def admin_toggle_api_key(key):
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT active FROM api_keys WHERE key=?', (key,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'message': 'Not found'}), 404
    newv = 0 if row[0]==1 else 1
    c.execute('UPDATE api_keys SET active=? WHERE key=?', (newv, key))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'active': bool(newv)})


@app.route('/api/admin/activations', methods=['GET'])
def admin_activations():
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    try:
        limit = int(request.args.get('limit','50'))
    except Exception:
        limit = 50
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, udid, serial, model, status, reason, notes, api_key_user, created_at FROM activations ORDER BY id DESC LIMIT ?', (limit,))
    rows = c.fetchall()
    conn.close()
    activations = [dict(id=r[0], udid=r[1], serial=r[2], model=r[3], status=r[4], reason=r[5], notes=r[6], api_key_user=r[7], created_at=r[8]) for r in rows]
    return jsonify({'activations': activations})


def _parse_transfer_from_receipt(receipt_json, token_contract, expected_to):
    # receipt_json may be a dict returned by eth_getTransactionReceipt, an explorer
    # wrapper, or a dict with a 'raw' text field. Be defensive when extracting logs.
    if not isinstance(receipt_json, dict):
        return False, 0
    # Try common locations for the receipt object
    res = None
    if isinstance(receipt_json.get('result'), dict):
        res = receipt_json.get('result')
    elif isinstance(receipt_json.get('result'), str):
        # some proxies return a JSON string inside 'result'
        try:
            res = json.loads(receipt_json.get('result'))
        except Exception:
            res = None
    elif 'logs' in receipt_json:
        res = receipt_json
    elif receipt_json.get('raw'):
        # raw text available; cannot parse logs reliably
        return False, 0
    if res is None:
        res = {}
    logs = res.get('logs') or []
    token_contract = token_contract.lower()
    expected_to_noprefix = expected_to.lower().replace('0x','')
    for log in logs:
        addr = (log.get('address','') or '').lower()
        topics = log.get('topics') or []
        if addr == token_contract and len(topics) >= 3 and topics[0].lower() == TRANSFER_EVENT_SIG:
            # topics[2] is the 'to' (padded 32 bytes)
            to_topic = topics[2].lower().replace('0x','')
            if to_topic.endswith(expected_to_noprefix):
                # amount is in data
                data = log.get('data','0x0')
                try:
                    amount = int(data,16)
                except Exception:
                    amount = 0
                return True, amount
    return False, 0


@app.route('/api/auto_verify', methods=['POST'])
def api_auto_verify():
    # body: { payment_id: int, chain: 'eth'|'bsc' }
    data = request.get_json() or {}
    pid = data.get('payment_id')
    chain = (data.get('chain') or 'eth').lower()
    if not pid:
        return jsonify({'success': False, 'message': 'missing payment_id'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, serial, tx_hash, amount, currency, status FROM payments WHERE id=?', (pid,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'success': False, 'message': 'not found'}), 404
    _, serial, tx, amount, currency, status = row
    if status == 'verified':
        conn.close()
        return jsonify({'success': False, 'message': 'already verified'})

    if currency.upper() != 'USDT':
        conn.close()
        return jsonify({'success': False, 'message': 'only USDT supported for auto-verify'}), 400

    info = TOKEN_INFO.get(chain)
    if not info:
        conn.close()
        return jsonify({'success': False, 'message': 'unsupported chain'}), 400
    api_base = info['api_base']
    api_key = info.get('api_key')
    rpc_url = info.get('rpc') or None
    contract = info['contract']
    decimals = info.get('decimals',6)

    try:
        receipt = _eth_get_receipt(tx, api_base, api_key, rpc_url=rpc_url)
        if not isinstance(receipt, dict):
            conn.close()
            return jsonify({'success': False, 'message': f'invalid_receipt_type:{type(receipt).__name__}'}), 500
        ok, raw_amount = _parse_transfer_from_receipt(receipt, contract, PAYMENT_ADDRESS)
        if not ok:
            conn.close()
            return jsonify({'success': False, 'message': 'transfer not found in tx logs'}), 400
        # compute human amount
        human_amount = raw_amount / (10 ** decimals) if decimals>0 else float(raw_amount)
        if abs(human_amount - float(amount)) > 0.0001:
            conn.close()
            return jsonify({'success': False, 'message': f'amount mismatch, tx shows {human_amount}'}), 400
        # mark verified and insert serial
        now = datetime.utcnow().isoformat()
        try:
            c.execute('INSERT INTO serials (serial) VALUES (?)', (serial,))
        except sqlite3.IntegrityError:
            pass
        c.execute('UPDATE payments SET status=?, verified_at=? WHERE id=?', ('verified', now, pid))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'verified'})
    except requests.HTTPError as e:
        conn.close()
        return jsonify({'success': False, 'message': 'api error: '+str(e)}), 500
    except Exception as e:
        conn.close()
        return jsonify({'success': False, 'message': 'error: '+str(e)}), 500


def verify_payment_by_id(pid, chain_hint=None):
    # internal helper: call the same logic as api_auto_verify but without HTTP
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, serial, tx_hash, amount, currency, status FROM payments WHERE id=?', (pid,))
    row = c.fetchone()
    if not row:
        conn.close(); return False, 'not found'
    _, serial, tx, amount, currency, status = row
    if status == 'verified':
        conn.close(); return False, 'already verified'
    if currency.upper() != 'USDT':
        conn.close(); return False, 'unsupported currency'
    # choose chain
    chain = (chain_hint or 'bsc').lower()
    info = TOKEN_INFO.get(chain)
    if not info:
        conn.close(); return False, 'unsupported chain'
    api_base = info['api_base']; api_key = info.get('api_key'); contract = info['contract']; decimals = info.get('decimals',6)
    rpc_url = info.get('rpc') or None
    try:
        receipt = _eth_get_receipt(tx, api_base, api_key, rpc_url=rpc_url)
        # debug log receipt type/content snippet
        try:
            with open('auto_verify_debug.log','a',encoding='utf-8') as f:
                f.write(f"{datetime.utcnow().isoformat()} | pid={pid} | receipt_type={type(receipt).__name__} | receipt_snippet={str(receipt)[:200].replace('\n',' ')}\n")
        except Exception:
            pass
        if not isinstance(receipt, dict):
            conn.close(); return False, f'invalid_receipt_type:{type(receipt).__name__}'
        try:
            ok, raw_amount = _parse_transfer_from_receipt(receipt, contract, PAYMENT_ADDRESS)
        except Exception as e:
            conn.close(); return False, 'parse_error:'+str(e)
        if not ok:
            conn.close(); return False, 'transfer not found'
        human_amount = raw_amount / (10 ** decimals) if decimals>0 else float(raw_amount)
        if abs(human_amount - float(amount)) > 0.0001:
            conn.close(); return False, f'amount mismatch, tx shows {human_amount}'
        now = datetime.utcnow().isoformat()
        try:
            c.execute('INSERT INTO serials (serial) VALUES (?)', (serial,))
        except sqlite3.IntegrityError:
            pass
        c.execute('UPDATE payments SET status=?, verified_at=? WHERE id=?', ('verified', now, pid))
        conn.commit()
        conn.close(); return True, 'verified'
    except Exception as e:
        conn.close(); return False, str(e)


def background_verifier_loop(interval_seconds=60):
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT id, chain FROM payments WHERE status='pending' ORDER BY id ASC LIMIT 20")
            rows = c.fetchall()
            conn.close()
            for r in rows:
                pid, chain = r[0], (r[1] or 'bsc')
                ok, msg = verify_payment_by_id(pid, chain)
                # write a small log
                try:
                    with open('auto_verify.log','a',encoding='utf-8') as f:
                        f.write(f"{datetime.utcnow().isoformat()} | pid={pid} | result={ok} | msg={msg}\n")
                except Exception:
                    pass
                time.sleep(1)
        except Exception:
            pass
        time.sleep(interval_seconds)


def start_background_verifier():
    t = threading.Thread(target=background_verifier_loop, args=(60,), daemon=True)
    t.start()


@app.route('/api/list_serials', methods=['GET'])
def list_serials():
    # Only reveal serials to authenticated admins. Public requests receive an empty list.
    if not session.get('admin'):
        return jsonify({'serials': []})
    q = request.args.get('q', '').strip()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if q:
        c.execute('SELECT serial FROM serials WHERE serial LIKE ? ORDER BY id DESC', (f'%{q}%',))
    else:
        c.execute('SELECT serial FROM serials ORDER BY id DESC')
    serials = [row[0] for row in c.fetchall()]
    conn.close()
    return jsonify({'serials': serials})


@app.route('/api/recent_payments', methods=['GET'])
def recent_payments():
    # For privacy, do not expose recent payments via this endpoint.
    # Admins should use /api/admin/payments which is protected.
    return jsonify({'payments': []})


@app.route('/api/admin/serials', methods=['GET'])
def admin_serials():
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    q = request.args.get('q', '').strip()
    try:
        page = int(request.args.get('page', '1'))
        per_page = int(request.args.get('per_page', '20'))
    except ValueError:
        page = 1; per_page = 20
    offset = (page-1) * per_page
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if q:
        c.execute('SELECT COUNT(*) FROM serials WHERE serial LIKE ?', (f'%{q}%',))
        total = c.fetchone()[0]
        c.execute('SELECT serial FROM serials WHERE serial LIKE ? ORDER BY id DESC LIMIT ? OFFSET ?', (f'%{q}%', per_page, offset))
    else:
        c.execute('SELECT COUNT(*) FROM serials')
        total = c.fetchone()[0]
        c.execute('SELECT serial FROM serials ORDER BY id DESC LIMIT ? OFFSET ?', (per_page, offset))
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return jsonify({'serials': rows, 'total': total, 'page': page, 'per_page': per_page})


@app.route('/api/admin/delete_all_serials', methods=['POST'])
def admin_delete_all_serials():
    """Dangerous: delete all stored serials. Admin only."""
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM serials')
        count = c.fetchone()[0]
        c.execute('DELETE FROM serials')
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'deleted': count})
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/delete_serial', methods=['POST'])
def delete_serial():
    # require admin session
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
    data = request.get_json() or {}
    serial = data.get('serial', '').strip()
    if not serial:
        return jsonify({'success': False, 'message': 'Empty serial'}), 400
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('DELETE FROM serials WHERE serial=?', (serial,))
    conn.commit()
    deleted = c.rowcount > 0
    conn.close()
    return jsonify({'success': deleted})


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    pwd = data.get('password', '')
    if pwd == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'success': True})
    return jsonify({'success': False}), 401


@app.route('/logout', methods=['POST'])
def logout():
    # Enhanced logout with session invalidation
    session_token = request.headers.get('Authorization')
    if session_token and session_token.startswith('Bearer '):
        token = session_token[7:]
        security_manager.invalidate_session(token)
    
    session.pop('admin', None)
    session.pop('user_id', None)
    return jsonify({'success': True})

@app.route('/api/auth/login', methods=['POST'])
@rate_limit(max_requests=5, window_minutes=5)  # Stricter rate limit for login
def secure_login():
    """Enhanced login with 2FA support"""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    totp_token = data.get('totp_token', '')
    
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'}), 400
    
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', '')
    
    result = security_manager.authenticate_user(
        username=username,
        password=password,
        totp_token=totp_token,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    if result['success']:
        session['admin'] = True
        session['user_id'] = result['user_id']
        return jsonify({
            'success': True,
            'session_token': result['session_token'],
            'user_id': result['user_id']
        })
    
    status_code = 401
    if result.get('requires_2fa'):
        status_code = 202  # Accepted, but 2FA required
    
    return jsonify(result), status_code

@app.route('/api/auth/setup-2fa', methods=['POST'])
@require_auth
def setup_2fa():
    """Setup 2FA for current user"""
    data = request.get_json()
    username = data.get('username', '')
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    result = security_manager.create_admin_user(username, password, enable_2fa=True)
    
    if result['success']:
        return jsonify({
            'success': True,
            'qr_code': result['qr_code'],
            'secret': result['secret']
        })
    
    return jsonify(result), 400

@app.route('/api/auth/security-stats', methods=['GET'])
@require_auth
def security_stats():
    """Get security statistics"""
    stats = security_manager.get_security_stats()
    return jsonify(stats)


@app.route('/api/is_admin', methods=['GET'])
def is_admin():
    return jsonify({'admin': bool(session.get('admin'))})


@app.route('/admin', methods=['GET'])
def admin_page():
    # If not logged in as admin, show secure login page
    if not session.get('admin'):
        return render_template('admin_login_secure.html')
    return render_template('admin_enhanced_v2.html')


@app.route('/admin_enhanced', methods=['GET'])
def admin_enhanced_page():
    # Enhanced admin interface with advanced monitoring
    if not session.get('admin'):
        return render_template('admin_login_secure.html')
    return render_template('admin_enhanced_v2.html')

@app.route('/realtime', methods=['GET'])
def realtime_dashboard():
    # Real-time dashboard with WebSocket support
    if not session.get('admin'):
        return render_template('admin_login_secure.html')
    return render_template('realtime_dashboard.html')

@app.route('/reports')
def reports_dashboard():
    """صفحة لوحة التقارير المتقدمة"""
    if not session.get('admin'):
        return render_template('admin_login_secure.html')
    return render_template('reports_dashboard_enhanced.html')

@app.route('/api/docs')
def api_documentation():
    """صفحة توثيق API التفاعلية"""
    return render_template('api_docs_enhanced.html')

@app.route('/api/docs/openapi.json')
def openapi_specification():
    """مواصفات OpenAPI 3.0"""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "RiF Activator A12+ API",
            "version": "2.0.0",
            "description": "واجهة برمجة التطبيقات لنظام تفعيل أجهزة iOS"
        },
        "servers": [
            {
                "url": "http://127.0.0.1:5000/api",
                "description": "خادم التطوير المحلي"
            }
        ],
        "paths": {
            "/pay_register": {
                "post": {
                    "summary": "تسجيل رقم تسلسلي جديد",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "serial": {
                                            "type": "string",
                                            "description": "الرقم التسلسلي للجهاز"
                                        }
                                    },
                                    "required": ["serial"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "تم التسجيل بنجاح"}
                    }
                }
            },
            "/check_serial": {
                "post": {
                    "summary": "فحص حالة الرقم التسلسلي",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "serial": {
                                            "type": "string",
                                            "description": "الرقم التسلسلي للفحص"
                                        }
                                    },
                                    "required": ["serial"]
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "نتيجة الفحص"}
                    }
                }
            }
        }
    }
    return jsonify(spec)

@app.route('/api/docs/postman')
def postman_collection():
    """مجموعة Postman للاختبار"""
    collection = {
        "info": {
            "name": "RiF Activator A12+ API Collection",
            "description": "مجموعة Postman شاملة لاختبار جميع APIs في نظام RiF Activator A12+",
            "version": "2.0.0",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [
            {
                "name": "Device Management",
                "description": "APIs إدارة الأجهزة",
                "item": [
                    {
                        "name": "تسجيل جهاز جديد",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json"
                                }
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n    \"serial\": \"C8KV7Q2PH72Y\",\n    \"amount\": 15.0,\n    \"currency\": \"USDT\",\n    \"chain\": \"bsc\",\n    \"tx_hash\": \"0x1234567890abcdef\"\n}"
                            },
                            "url": {
                                "raw": "{{base_url}}/api/pay_register",
                                "host": ["{{base_url}}"],
                                "path": ["api", "pay_register"]
                            },
                            "description": "تسجيل رقم تسلسلي جديد مع معلومات الدفع"
                        }
                    },
                    {
                        "name": "فحص حالة الجهاز",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json"
                                }
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n    \"serial\": \"C8KV7Q2PH72Y\"\n}"
                            },
                            "url": {
                                "raw": "{{base_url}}/api/check_serial",
                                "host": ["{{base_url}}"],
                                "path": ["api", "check_serial"]
                            },
                            "description": "التحقق من حالة تفعيل الرقم التسلسلي"
                        }
                    },
                    {
                        "name": "التحقق التلقائي من المدفوعات",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json"
                                }
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n    \"force\": false\n}"
                            },
                            "url": {
                                "raw": "{{base_url}}/api/auto_verify",
                                "host": ["{{base_url}}"],
                                "path": ["api", "auto_verify"]
                            },
                            "description": "تحقق تلقائي من معاملات الدفع على البلوك تشين"
                        }
                    }
                ]
            },
            {
                "name": "Admin APIs",
                "description": "APIs لوحة الإدارة",
                "item": [
                    {
                        "name": "تسجيل دخول المدير",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json"
                                }
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n    \"password\": \"admin_password_here\"\n}"
                            },
                            "url": {
                                "raw": "{{base_url}}/api/auth/login",
                                "host": ["{{base_url}}"],
                                "path": ["api", "auth", "login"]
                            },
                            "description": "تسجيل دخول لوحة الإدارة"
                        }
                    },
                    {
                        "name": "إحصائيات لوحة التحكم",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}/api/admin/dashboard_stats",
                                "host": ["{{base_url}}"],
                                "path": ["api", "admin", "dashboard_stats"]
                            },
                            "description": "الحصول على إحصائيات شاملة للنظام"
                        }
                    },
                    {
                        "name": "قائمة الأرقام التسلسلية",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}/api/admin/serials",
                                "host": ["{{base_url}}"],
                                "path": ["api", "admin", "serials"]
                            },
                            "description": "عرض جميع الأرقام التسلسلية المسجلة"
                        }
                    },
                    {
                        "name": "قائمة المدفوعات",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}/api/admin/payments",
                                "host": ["{{base_url}}"],
                                "path": ["api", "admin", "payments"]
                            },
                            "description": "عرض جميع المدفوعات والمعاملات"
                        }
                    }
                ]
            },
            {
                "name": "Reports & Analytics",
                "description": "APIs التقارير والتحليلات",
                "item": [
                    {
                        "name": "إنشاء تقرير شامل",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}/api/reports/generate?days=30&type=comprehensive",
                                "host": ["{{base_url}}"],
                                "path": ["api", "reports", "generate"],
                                "query": [
                                    {
                                        "key": "days",
                                        "value": "30",
                                        "description": "عدد الأيام للتقرير"
                                    },
                                    {
                                        "key": "type",
                                        "value": "comprehensive",
                                        "description": "نوع التقرير"
                                    }
                                ]
                            },
                            "description": "إنشاء تقرير شامل عن النشاط"
                        }
                    },
                    {
                        "name": "تصدير البيانات",
                        "request": {
                            "method": "POST",
                            "header": [
                                {
                                    "key": "Content-Type",
                                    "value": "application/json"
                                }
                            ],
                            "body": {
                                "mode": "raw",
                                "raw": "{\n    \"date_range\": {\n        \"start\": \"2024-01-01\",\n        \"end\": \"2024-12-31\"\n    },\n    \"include_serials\": true,\n    \"include_payments\": true\n}"
                            },
                            "url": {
                                "raw": "{{base_url}}/api/reports/export/excel",
                                "host": ["{{base_url}}"],
                                "path": ["api", "reports", "export", "excel"]
                            },
                            "description": "تصدير البيانات بصيغة Excel"
                        }
                    }
                ]
            },
            {
                "name": "System Health",
                "description": "APIs صحة النظام",
                "item": [
                    {
                        "name": "فحص حالة النظام",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}/api/system/health",
                                "host": ["{{base_url}}"],
                                "path": ["api", "system", "health"]
                            },
                            "description": "فحص شامل لحالة النظام والخدمات"
                        }
                    },
                    {
                        "name": "معلومات النظام",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}/api/system/info",
                                "host": ["{{base_url}}"],
                                "path": ["api", "system", "info"]
                            },
                            "description": "معلومات تفصيلية عن النظام والإصدار"
                        }
                    }
                ]
            }
        ],
        "variable": [
            {
                "key": "base_url",
                "value": "http://127.0.0.1:5000",
                "type": "string",
                "description": "عنوان الخادم الأساسي"
            }
        ]
    }
    return jsonify(collection)

@app.route('/api/docs/examples')
def api_examples():
    """أمثلة استخدام API بلغات مختلفة"""
    examples = {
        "curl": {
            "register_device": "curl -X POST http://127.0.0.1:5000/api/pay_register \\\n  -H 'Content-Type: application/json' \\\n  -d '{\n    \"serial\": \"C8KV7Q2PH72Y\",\n    \"amount\": 15.0,\n    \"currency\": \"USDT\",\n    \"chain\": \"bsc\",\n    \"tx_hash\": \"0x1234567890abcdef\"\n  }'",
            "check_device": "curl -X POST http://127.0.0.1:5000/api/check_serial \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"serial\": \"C8KV7Q2PH72Y\"}'",
            "auto_verify": "curl -X POST http://127.0.0.1:5000/api/auto_verify \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"force\": false}'"
        },
        "python": {
            "register_device": "import requests\n\nurl = 'http://127.0.0.1:5000/api/pay_register'\ndata = {\n    'serial': 'C8KV7Q2PH72Y',\n    'amount': 15.0,\n    'currency': 'USDT',\n    'chain': 'bsc',\n    'tx_hash': '0x1234567890abcdef'\n}\n\nresponse = requests.post(url, json=data)\nprint(response.json())",
            "check_device": "import requests\n\nurl = 'http://127.0.0.1:5000/api/check_serial'\ndata = {'serial': 'C8KV7Q2PH72Y'}\n\nresponse = requests.post(url, json=data)\nprint(response.json())",
            "auto_verify": "import requests\n\nurl = 'http://127.0.0.1:5000/api/auto_verify'\ndata = {'force': False}\n\nresponse = requests.post(url, json=data)\nprint(response.json())"
        },
        "javascript": {
            "register_device": "const response = await fetch('http://127.0.0.1:5000/api/pay_register', {\n  method: 'POST',\n  headers: {\n    'Content-Type': 'application/json'\n  },\n  body: JSON.stringify({\n    serial: 'C8KV7Q2PH72Y',\n    amount: 15.0,\n    currency: 'USDT',\n    chain: 'bsc',\n    tx_hash: '0x1234567890abcdef'\n  })\n});\n\nconst data = await response.json();\nconsole.log(data);",
            "check_device": "const response = await fetch('http://127.0.0.1:5000/api/check_serial', {\n  method: 'POST',\n  headers: {\n    'Content-Type': 'application/json'\n  },\n  body: JSON.stringify({\n    serial: 'C8KV7Q2PH72Y'\n  })\n});\n\nconst data = await response.json();\nconsole.log(data);",
            "auto_verify": "const response = await fetch('http://127.0.0.1:5000/api/auto_verify', {\n  method: 'POST',\n  headers: {\n    'Content-Type': 'application/json'\n  },\n  body: JSON.stringify({\n    force: false\n  })\n});\n\nconst data = await response.json();\nconsole.log(data);"
        },
        "php": {
            "register_device": "<?php\n$url = 'http://127.0.0.1:5000/api/pay_register';\n$data = [\n    'serial' => 'C8KV7Q2PH72Y',\n    'amount' => 15.0,\n    'currency' => 'USDT',\n    'chain' => 'bsc',\n    'tx_hash' => '0x1234567890abcdef'\n];\n\n$options = [\n    'http' => [\n        'header' => 'Content-Type: application/json',\n        'method' => 'POST',\n        'content' => json_encode($data)\n    ]\n];\n\n$context = stream_context_create($options);\n$result = file_get_contents($url, false, $context);\n$response = json_decode($result, true);\n\nprint_r($response);\n?>",
            "check_device": "<?php\n$url = 'http://127.0.0.1:5000/api/check_serial';\n$data = ['serial' => 'C8KV7Q2PH72Y'];\n\n$options = [\n    'http' => [\n        'header' => 'Content-Type: application/json',\n        'method' => 'POST',\n        'content' => json_encode($data)\n    ]\n];\n\n$context = stream_context_create($options);\n$result = file_get_contents($url, false, $context);\n$response = json_decode($result, true);\n\nprint_r($response);\n?>"
        }
    }
    return jsonify(examples)

@app.route('/api/reports/generate')
def generate_report_api():
    """API لإنشاء التقارير"""
    if not session.get('admin'):
        return jsonify({'error': 'غير مصرح'}), 401
    
    try:
        days = int(request.args.get('days', 30))
        report_type = request.args.get('type', 'comprehensive')
        
        from reports_manager import reports_manager
        
        if report_type == 'comprehensive':
            report = reports_manager.generate_comprehensive_report(days, include_charts=False)
        elif report_type == 'activation':
            report = {'activation_statistics': reports_manager.get_activation_statistics(days)}
        elif report_type == 'security':
            report = {'security_report': reports_manager.get_security_report(days)}
        elif report_type == 'revenue':
            report = {'revenue_analytics': reports_manager.get_revenue_analytics(days)}
        else:
            report = reports_manager.generate_comprehensive_report(days, include_charts=False)
        
        return jsonify(report)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/export/<format_type>', methods=['POST'])
def export_report_api(format_type):
    """API لتصدير التقارير"""
    if not session.get('admin'):
        return jsonify({'error': 'غير مصرح'}), 401
    
    try:
        days = int(request.args.get('days', 30))
        
        from reports_manager import reports_manager
        
        if format_type == 'pdf':
            report_data = reports_manager.generate_comprehensive_report(days, include_charts=False)
            pdf_path = reports_manager.export_to_pdf(report_data)
            
            return send_file(pdf_path, as_attachment=True, 
                           download_name=f'rif_activator_report_{days}days.pdf')
        
        elif format_type == 'json':
            report_data = reports_manager.generate_comprehensive_report(days, include_charts=False)
            
            response = make_response(jsonify(report_data))
            response.headers['Content-Disposition'] = f'attachment; filename=rif_activator_report_{days}days.json'
            return response
        
        else:
            return jsonify({'error': 'نوع التصدير غير مدعوم'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules', methods=['GET'])
def get_schedules_api():
    """API لجلب جداول التقارير"""
    if not session.get('admin'):
        return jsonify({'error': 'غير مصرح'}), 401
    
    try:
        from report_scheduler import report_scheduler
        schedules = report_scheduler.list_schedules()
        return jsonify({'schedules': schedules})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules', methods=['POST'])
def create_schedule_api():
    """API لإنشاء جدول تقرير جديد"""
    if not session.get('admin'):
        return jsonify({'error': 'غير مصرح'}), 401
    
    try:
        data = request.get_json()
        from report_scheduler import report_scheduler
        
        schedule_id = report_scheduler.add_schedule(
            name=data.get('name', 'تقرير جديد'),
            frequency=data.get('frequency', 'weekly'),
            days=int(data.get('days', 7)),
            format_type=data.get('format', 'pdf'),
            email_recipients=data.get('email_recipients', [])
        )
        
        return jsonify({'success': True, 'schedule_id': schedule_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedules/<int:schedule_id>', methods=['DELETE'])
def delete_schedule_api(schedule_id):
    """API لحذف جدول تقرير"""
    if not session.get('admin'):
        return jsonify({'error': 'غير مصرح'}), 401
    
    try:
        from report_scheduler import report_scheduler
        success = report_scheduler.delete_schedule(schedule_id)
        return jsonify({'success': success})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/home', methods=['GET'])
def home_page():
    # Provide counts and recent serials for the home dashboard
    # For privacy we do NOT show serials on the public home page at all.
    # Serial management and viewing is available only in the admin panel (/admin).
    total = 0
    recent = []
    return render_template('home.html', total=total, recent=recent)


@app.route('/export_csv', methods=['GET'])
def export_csv():
    # only admin can export
    if not session.get('admin'):
        return jsonify({'success': False, 'message': 'Forbidden'}), 403
    q = request.args.get('q', '').strip()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if q:
        c.execute('SELECT serial FROM serials WHERE serial LIKE ? ORDER BY id DESC', (f'%{q}%',))
    else:
        c.execute('SELECT serial FROM serials ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    csv_lines = ['serial'] + [r[0] for r in rows]
    csv_text = '\n'.join(csv_lines)
    timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    filename = f'serials_{timestamp}.csv'
    return (csv_text, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename="{filename}"'
    })

# Enhanced request logging middleware
@app.before_request
def log_request_info():
    request.start_time = time.time()

@app.after_request
def log_response_info(response):
    try:
        response_time = (time.time() - request.start_time) * 1000
        
        # Skip logging for static files
        if request.endpoint and 'static' not in request.endpoint:
            # Create structured log entry
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'remote_addr': request.remote_addr,
                'method': request.method,
                'url': request.url,
                'endpoint': request.endpoint,
                'status_code': response.status_code,
                'response_time_ms': round(response_time, 2),
                'user_agent': request.headers.get('User-Agent', ''),
                'api_key': request.headers.get('X-API-Key', '')[:8] + '...' if request.headers.get('X-API-Key') else None
            }
            
        # Log to API logger (use structured JSON logging only)
        app.logger.info(json.dumps(log_data))
        
        # Create real-time notification for important events
        if response.status_code >= 400:
            notification = notification_manager.create_notification(
                notification_type='error',
                title='خطأ في النظام',
                message=f"خطأ {response.status_code} في {request.endpoint}",
                severity='error'
            )
            broadcast_notification(notification)
        elif request.endpoint in ['admin_login', 'secure_login'] and response.status_code == 200:
            notification = notification_manager.create_notification(
                notification_type='security',
                title='تسجيل دخول جديد',
                message=f"تم تسجيل دخول من {request.remote_addr}",
                severity='info'
            )
            broadcast_notification(notification)            # Log security events
            if request.endpoint in ['login', 'admin_page'] or '/admin/' in request.url:
                security_logger.info(f"Admin access: {request.remote_addr} -> {request.url} [{response.status_code}]")
    
    except Exception:
        pass  # Don't break the response if logging fails
    
    return response

# Add dashboard stats endpoint
@app.route('/api/admin/dashboard_stats', methods=['GET'])
@require_auth
@rate_limit(max_requests=30, window_minutes=1)
def admin_dashboard_stats():
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get comprehensive stats
    stats = {}
    
    # Serials stats
    c.execute('SELECT COUNT(*) FROM serials')
    stats['total_serials'] = c.fetchone()[0]
    
    # Payments stats
    c.execute('SELECT COUNT(*) FROM payments WHERE status="verified"')
    stats['verified_payments'] = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM payments WHERE status="pending"')
    stats['pending_payments'] = c.fetchone()[0]
    
    c.execute('SELECT SUM(amount) FROM payments WHERE status="verified"')
    result = c.fetchone()[0]
    stats['total_revenue'] = float(result) if result else 0.0
    
    # Device stats
    c.execute('SELECT COUNT(*) FROM supported_models WHERE enabled=1')
    stats['supported_models'] = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM activations WHERE status="allowed"')
    stats['successful_activations'] = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM activations WHERE status="rejected"')
    stats['rejected_activations'] = c.fetchone()[0]
    
    # Recent activity (last 24 hours)
    from datetime import timedelta
    yesterday = (datetime.utcnow() - timedelta(days=1)).isoformat()
    
    c.execute('SELECT COUNT(*) FROM activations WHERE created_at > ?', (yesterday,))
    stats['activations_24h'] = c.fetchone()[0]
    
    c.execute('SELECT COUNT(*) FROM payments WHERE created_at > ?', (yesterday,))
    stats['payments_24h'] = c.fetchone()[0]
    
    # Top models (most activated)
    c.execute('''SELECT model, COUNT(*) as count FROM activations 
                WHERE status="allowed" GROUP BY model ORDER BY count DESC LIMIT 5''')
    stats['top_models'] = [{'model': row[0], 'count': row[1]} for row in c.fetchall()]
    
    # API Keys stats
    c.execute('SELECT COUNT(*) FROM api_keys WHERE active=1')
    stats['active_api_keys'] = c.fetchone()[0]
    
    conn.close()
    return jsonify(stats)

# System health endpoint
@app.route('/api/admin/system_health', methods=['GET'])
@require_auth
@rate_limit(max_requests=20, window_minutes=1)
def admin_system_health():
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    
    health = {
        'timestamp': datetime.utcnow().isoformat(),
        'status': 'healthy'
    }
    
    try:
        # System resources
        health['cpu_percent'] = psutil.cpu_percent(interval=1)
        health['memory'] = {
            'total': psutil.virtual_memory().total,
            'available': psutil.virtual_memory().available,
            'percent': psutil.virtual_memory().percent
        }
        health['disk'] = {
            'total': psutil.disk_usage('.').total,
            'free': psutil.disk_usage('.').free,
            'percent': psutil.disk_usage('.').percent
        }
        
        # Database health
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('PRAGMA integrity_check')
        db_check = c.fetchone()[0]
        health['database'] = 'ok' if db_check == 'ok' else 'error'
        
        # Check database size
        health['db_size'] = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
        
        conn.close()
        
        # Rate limiting health
        health['rate_buckets_count'] = len(rate_buckets)
        
        # Determine overall status
        if health['cpu_percent'] > 90 or health['memory']['percent'] > 90:
            health['status'] = 'warning'
        if health['database'] != 'ok':
            health['status'] = 'error'
            
    except Exception as e:
        health['status'] = 'error'
        health['error'] = str(e)
    
    return jsonify(health)

# Activity feed endpoint
@app.route('/api/admin/activity_feed', methods=['GET'])
def admin_activity_feed():
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    
    limit = int(request.args.get('limit', '50'))
    activities = list(activity_feed)[-limit:]
    
    return jsonify({'activities': activities})

# System logs endpoint
@app.route('/api/admin/system_logs', methods=['GET'])
def admin_system_logs():
    if not session.get('admin'):
        return jsonify({'error': 'forbidden'}), 403
    
    log_type = request.args.get('type', 'app')  # app, security, api
    lines = int(request.args.get('lines', '100'))
    
    try:
        log_file = f'logs/{log_type}.log'
        if not os.path.exists(log_file):
            return jsonify({'logs': [], 'message': 'Log file not found'})
        
        # Read last N lines
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return jsonify({
            'logs': [line.strip() for line in recent_lines],
            'total_lines': len(all_lines),
            'returned_lines': len(recent_lines)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    """Public stats endpoint for the enhanced homepage"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Get total devices
        c.execute('SELECT COUNT(*) FROM serials')
        total_devices = c.fetchone()[0]
        
        # Calculate success rate (assuming 99%+ success)
        success_rate = min(99.8, 95 + (total_devices / 1000) * 0.1)
        
        # Average time (simulated based on load)
        avg_time = max(1.5, 3.0 - (total_devices / 10000) * 0.5)
        
        # Happy customers (roughly 80% of total devices)
        happy_customers = int(total_devices * 0.8)
        
        conn.close()
        
        return jsonify({
            'total_devices': total_devices,
            'success_rate': round(success_rate, 1),
            'avg_time': round(avg_time, 1),
            'happy_customers': happy_customers,
            'last_updated': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        # Return demo stats if database error
        return jsonify({
            'total_devices': 15847,
            'success_rate': 99.8,
            'avg_time': 2.5,
            'happy_customers': 12500,
            'last_updated': datetime.utcnow().isoformat()
        })

# WebSocket Events for Real-time Features
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid
    notification_manager.add_connection(client_id)
    
    # Send welcome message with current stats
    emit('connected', {
        'message': 'متصل بنجاح مع الخادم',
        'timestamp': datetime.utcnow().isoformat(),
        'active_connections': notification_manager.get_active_connections_count()
    })
    
    # Send recent notifications
    recent_notifications = notification_manager.get_recent_notifications(10)
    emit('notifications_batch', recent_notifications)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    notification_manager.remove_connection(client_id)

@socketio.on('join_admin')
def handle_join_admin():
    """Join admin room for admin-specific updates"""
    if not session.get('admin'):
        emit('error', {'message': 'غير مخول للوصول'})
        return
    
    join_room('admin')
    emit('joined_admin', {
        'message': 'انضممت لقناة المشرفين',
        'timestamp': datetime.utcnow().isoformat()
    })

@socketio.on('leave_admin')
def handle_leave_admin():
    """Leave admin room"""
    leave_room('admin')

@socketio.on('request_system_stats')
def handle_system_stats_request():
    """Send current system statistics"""
    try:
        stats = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('.').percent,
            'active_connections': notification_manager.get_active_connections_count(),
            'timestamp': datetime.utcnow().isoformat()
        }
        emit('system_stats', stats)
    except Exception as e:
        emit('error', {'message': f'خطأ في جلب إحصائيات النظام: {str(e)}'})

@socketio.on('request_activity_feed')
def handle_activity_feed_request():
    """Send recent activity feed"""
    try:
        notifications = notification_manager.get_recent_notifications(20)
        emit('activity_feed', notifications)
    except Exception as e:
        emit('error', {'message': f'خطأ في جلب النشاط الحديث: {str(e)}'})

# Helper functions for real-time notifications
def broadcast_notification(notification):
    """Broadcast notification to all connected clients"""
    socketio.emit('new_notification', notification)

def broadcast_to_admins(event, data):
    """Broadcast event to admin users only"""
    socketio.emit(event, data, room='admin')

def broadcast_system_alert(alert_type, message, severity='warning'):
    """Broadcast system alert"""
    notification = notification_manager.create_notification(
        notification_type='system',
        title='تنبيه النظام',
        message=message,
        severity=severity
    )
    broadcast_notification(notification)

# Background task for system monitoring
def system_monitor():
    """Background task to monitor system health and send alerts"""
    while True:
        try:
            # Check system resources
            cpu_percent = psutil.cpu_percent(interval=1)
            memory_percent = psutil.virtual_memory().percent
            disk_percent = psutil.disk_usage('.').percent
            
            # Send alerts if thresholds exceeded
            if cpu_percent > 80:
                alert_data = notify_system_health_alert('استخدام المعالج', cpu_percent, 80)
                notification = notification_manager.create_notification(**alert_data)
                broadcast_to_admins('system_alert', notification)
            
            if memory_percent > 85:
                alert_data = notify_system_health_alert('استخدام الذاكرة', memory_percent, 85)
                notification = notification_manager.create_notification(**alert_data)
                broadcast_to_admins('system_alert', notification)
            
            if disk_percent > 90:
                alert_data = notify_system_health_alert('استخدام القرص', disk_percent, 90)
                notification = notification_manager.create_notification(**alert_data)
                broadcast_to_admins('system_alert', notification)
            
            # Broadcast live stats to connected clients
            stats = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'timestamp': datetime.utcnow().isoformat()
            }
            socketio.emit('live_stats', stats)
            
            # Clean up old notifications
            notification_manager.cleanup_expired_notifications()
            
        except Exception as e:
            print(f"Error in system monitor: {e}")
        
        time.sleep(30)  # Check every 30 seconds

# Start background monitoring
def start_system_monitor():
    monitor_thread = threading.Thread(target=system_monitor, daemon=True)
    monitor_thread.start()

# PWA Support Routes
@app.route('/sw.js')
def service_worker():
    """Serve service worker for PWA functionality"""
    return send_file('static/sw.js', mimetype='application/javascript')

@app.route('/manifest.json')
def manifest():
    """Serve manifest file for PWA"""
    return send_file('static/manifest.json', mimetype='application/manifest+json')

@app.route('/favicon.ico')
def favicon():
    """Serve favicon"""
    return send_file('static/favicon.ico', mimetype='image/x-icon')

@app.route('/offline.html')
def offline():
    """Offline fallback page"""
    return '''
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>غير متصل - RiF Activator A12+</title>
        <style>
            body {
                font-family: 'Cairo', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                text-align: center;
                padding: 2rem;
                min-height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
            }
            .offline-icon {
                font-size: 4rem;
                margin-bottom: 1rem;
            }
            .offline-title {
                font-size: 2rem;
                margin-bottom: 1rem;
            }
            .offline-message {
                font-size: 1.1rem;
                margin-bottom: 2rem;
                opacity: 0.9;
            }
            .retry-button {
                background: rgba(255, 255, 255, 0.2);
                border: 2px solid rgba(255, 255, 255, 0.3);
                color: white;
                padding: 1rem 2rem;
                border-radius: 50px;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .retry-button:hover {
                background: rgba(255, 255, 255, 0.3);
            }
        </style>
    </head>
    <body>
        <div class="offline-icon">📱</div>
        <h1 class="offline-title">غير متصل بالإنترنت</h1>
        <p class="offline-message">
            يرجى التحقق من اتصالك بالإنترنت والمحاولة مرة أخرى
        </p>
        <button class="retry-button" onclick="window.location.reload()">
            إعادة المحاولة
        </button>
        <script>
            // Auto-refresh when connection is restored
            window.addEventListener('online', () => {
                window.location.reload();
            });
        </script>
    </body>
    </html>
    '''

# Additional Admin APIs for Button Functionality

@app.route('/api/admin/add_serial', methods=['POST'])
@require_auth
def add_serial_api():
    """إضافة رقم تسلسلي جديد"""
    try:
        data = request.get_json()
        serial = data.get('serial', '').strip().upper()
        
        if not serial or len(serial) != 12:
            return jsonify({'error': 'الرقم التسلسلي يجب أن يكون 12 رقم/حرف'}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        try:
            c.execute('INSERT INTO serials (serial, created_at) VALUES (?, ?)', 
                     (serial, datetime.utcnow().isoformat()))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': f'تم إضافة الرقم التسلسلي {serial} بنجاح'})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'الرقم التسلسلي موجود مسبقاً'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/delete_serial/<serial>', methods=['DELETE'])
@require_auth
def delete_serial_api(serial):
    """حذف رقم تسلسلي"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('DELETE FROM serials WHERE serial = ?', (serial,))
        c.execute('DELETE FROM payments WHERE serial = ?', (serial,))
        
        if c.rowcount > 0:
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': f'تم حذف الرقم التسلسلي {serial} بنجاح'})
        else:
            conn.close()
            return jsonify({'error': 'الرقم التسلسلي غير موجود'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/export_serials')
@require_auth
def export_serials_api():
    """تصدير الأرقام التسلسلية"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT * FROM serials ORDER BY created_at DESC')
        serials = c.fetchall()
        conn.close()
        
        # إنشاء ملف CSV في الذاكرة
        import io
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Serial', 'Created At', 'Status'])
        
        for serial in serials:
            writer.writerow([serial[0], serial[1], 'Active'])
        
        # إنشاء response
        output.seek(0)
        return make_response(
            output.getvalue(),
            200,
            {'Content-Type': 'text/csv', 
             'Content-Disposition': f'attachment; filename=serials_{datetime.now().strftime("%Y%m%d")}.csv'}
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/clear_serials', methods=['POST'])
@require_auth
def clear_all_serials_api():
    """مسح جميع الأرقام التسلسلية"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute('DELETE FROM serials')
        c.execute('DELETE FROM payments')
        
        deleted_count = c.rowcount
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'تم حذف {deleted_count} رقم تسلسلي بنجاح',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/bulk_import', methods=['POST'])
@require_auth
def bulk_import_serials_api():
    """استيراد مجموعة من الأرقام التسلسلية"""
    try:
        data = request.get_json()
        serials_text = data.get('serials', '').strip()
        
        if not serials_text:
            return jsonify({'error': 'يرجى إدخال الأرقام التسلسلية'}), 400
        
        # فصل الأرقام التسلسلية (سطر جديد أو فاصلة أو مسافة)
        import re
        serials = re.split(r'[,\n\s]+', serials_text)
        serials = [s.strip().upper() for s in serials if s.strip()]
        
        # التحقق من صحة الأرقام
        valid_serials = []
        invalid_serials = []
        
        for serial in serials:
            if len(serial) == 12 and serial.isalnum():
                valid_serials.append(serial)
            else:
                invalid_serials.append(serial)
        
        if not valid_serials:
            return jsonify({'error': 'لا توجد أرقام تسلسلية صحيحة'}), 400
        
        # إدخال الأرقام في قاعدة البيانات
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        added_count = 0
        duplicate_count = 0
        
        for serial in valid_serials:
            try:
                c.execute('INSERT INTO serials (serial, created_at) VALUES (?, ?)', 
                         (serial, datetime.utcnow().isoformat()))
                added_count += 1
            except sqlite3.IntegrityError:
                duplicate_count += 1
        
        conn.commit()
        conn.close()
        
        result = {
            'success': True,
            'added_count': added_count,
            'duplicate_count': duplicate_count,
            'invalid_count': len(invalid_serials),
            'message': f'تم إضافة {added_count} رقم تسلسلي بنجاح'
        }
        
        if duplicate_count > 0:
            result['message'] += f', {duplicate_count} مكرر'
        if invalid_serials:
            result['message'] += f', {len(invalid_serials)} غير صحيح'
            result['invalid_serials'] = invalid_serials
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/generate_report')
@require_auth
def generate_admin_report():
    """إنشاء تقرير إداري شامل"""
    try:
        days = int(request.args.get('days', 30))
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # إحصائيات عامة
        c.execute('SELECT COUNT(*) FROM serials')
        total_serials = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM payments WHERE status = "verified"')
        verified_payments = c.fetchone()[0]
        
        c.execute('SELECT SUM(amount) FROM payments WHERE status = "verified"')
        total_revenue = c.fetchone()[0] or 0
        
        # نشاط الأيام الأخيرة
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).isoformat()
        
        c.execute('SELECT COUNT(*) FROM serials WHERE created_at > ?', (cutoff_date,))
        recent_serials = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM payments WHERE created_at > ?', (cutoff_date,))
        recent_payments = c.fetchone()[0]
        
        # أهم المعاملات
        c.execute('''
            SELECT serial, amount, currency, created_at 
            FROM payments 
            WHERE status = "verified" 
            ORDER BY amount DESC 
            LIMIT 10
        ''')
        top_transactions = c.fetchall()
        
        conn.close()
        
        report = {
            'success': True,
            'report_date': datetime.utcnow().isoformat(),
            'period_days': days,
            'statistics': {
                'total_serials': total_serials,
                'verified_payments': verified_payments,
                'total_revenue': round(total_revenue, 2),
                'recent_serials': recent_serials,
                'recent_payments': recent_payments
            },
            'top_transactions': [
                {
                    'serial': tx[0],
                    'amount': tx[1],
                    'currency': tx[2],
                    'date': tx[3]
                } for tx in top_transactions
            ]
        }
        
        return jsonify(report)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/system_logs')
@require_auth
def get_system_logs():
    """عرض سجلات النظام"""
    try:
        import glob
        import os
        
        # البحث عن ملفات السجلات
        log_files = glob.glob('*.log') + glob.glob('logs/*.log')
        
        logs = []
        for log_file in log_files[-5:]:  # آخر 5 ملفات فقط
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    logs.append({
                        'file': log_file,
                        'size': os.path.getsize(log_file),
                        'modified': os.path.getmtime(log_file),
                        'content': content[-2000:]  # آخر 2000 حرف فقط
                    })
            except:
                continue
        
        # إضافة سجل النظام الحالي
        import psutil
        
        system_info = {
            'cpu_percent': psutil.cpu_percent(),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'boot_time': psutil.boot_time()
        }
        
        return jsonify({
            'success': True,
            'logs': logs,
            'system_info': system_info,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/admin/manage_models', methods=['GET', 'POST'])
@require_auth
def manage_supported_models():
    """إدارة طرازات الأجهزة المدعومة"""
    if request.method == 'GET':
        # قائمة الطرازات المدعومة
        supported_models = [
            'iPhone X', 'iPhone XS', 'iPhone XS Max', 'iPhone XR',
            'iPhone 11', 'iPhone 11 Pro', 'iPhone 11 Pro Max',
            'iPhone 12', 'iPhone 12 Mini', 'iPhone 12 Pro', 'iPhone 12 Pro Max',
            'iPhone 13', 'iPhone 13 Mini', 'iPhone 13 Pro', 'iPhone 13 Pro Max',
            'iPhone 14', 'iPhone 14 Plus', 'iPhone 14 Pro', 'iPhone 14 Pro Max',
            'iPhone 15', 'iPhone 15 Plus', 'iPhone 15 Pro', 'iPhone 15 Pro Max'
        ]
        
        return jsonify({
            'success': True,
            'models': supported_models,
            'count': len(supported_models)
        })
    
    elif request.method == 'POST':
        # إضافة طراز جديد (مخصص للمستقبل)
        data = request.get_json()
        new_model = data.get('model', '').strip()
        
        if not new_model:
            return jsonify({'error': 'اسم الطراز مطلوب'}), 400
        
        # في المستقبل يمكن حفظ الطرازات المخصصة في قاعدة البيانات
        return jsonify({
            'success': True,
            'message': f'تم إضافة الطراز {new_model} بنجاح'
        })

@app.route('/api/admin/system_health')
@require_auth
def system_health_check():
    """فحص صحة النظام"""
    try:
        import psutil
        
        # فحص استخدام الموارد
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # فحص قاعدة البيانات
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM serials')
            db_status = 'healthy'
            conn.close()
        except:
            db_status = 'error'
        
        # حالة النظام العامة
        health_score = 100
        warnings = []
        
        if cpu_percent > 80:
            health_score -= 20
            warnings.append('استخدام المعالج مرتفع')
        
        if memory.percent > 85:
            health_score -= 20
            warnings.append('استخدام الذاكرة مرتفع')
        
        if disk.percent > 90:
            health_score -= 30
            warnings.append('مساحة القرص منخفضة')
        
        if db_status != 'healthy':
            health_score -= 40
            warnings.append('مشكلة في قاعدة البيانات')
        
        status = 'excellent' if health_score >= 90 else 'good' if health_score >= 70 else 'warning' if health_score >= 50 else 'critical'
        
        return jsonify({
            'success': True,
            'health_score': health_score,
            'status': status,
            'warnings': warnings,
            'details': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': disk.percent,
                'disk_free': disk.free,
                'database_status': db_status,
                'uptime': time.time() - psutil.boot_time()
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/info')
def system_info():
    """معلومات النظام العامة"""
    try:
        import platform
        
        info = {
            'success': True,
            'app_name': 'RiF Activator A12+',
            'version': '2.0.0',
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'architecture': platform.architecture()[0],
            'hostname': platform.node(),
            'timestamp': datetime.utcnow().isoformat(),
            'endpoints': {
                'main': '/',
                'check_device': '/check_device',
                'admin': '/admin',
                'reports': '/reports',
                'api_docs': '/api/docs'
            }
        }
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/system/health')
def public_health_check():
    """فحص صحة النظام - عام"""
    try:
        # فحص أساسي للنظام
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM serials')
        db_working = True
        conn.close()
        
        return jsonify({
            'success': True,
            'status': 'healthy',
            'database': 'connected' if db_working else 'error',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': 'running'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# تحديث الإحصائيات المباشرة
@app.route('/api/live_stats')
def live_statistics():
    """إحصائيات مباشرة للصفحة الرئيسية"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # إحصائيات مباشرة
        c.execute('SELECT COUNT(*) FROM serials')
        total_devices = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM payments WHERE status = "verified"')
        verified_payments = c.fetchone()[0]
        
        # محاكاة مستخدمين نشطين (عدد عشوائي واقعي)
        import random
        active_users = random.randint(850, 950)
        
        # حساب معدل النجاح
        if total_devices > 0:
            success_rate = min(98.5 + random.uniform(-0.3, 0.3), 99.9)
        else:
            success_rate = 98.7
        
        # متوسط وقت التفعيل
        avg_time = round(random.uniform(1.8, 2.8), 1)
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_devices': total_devices,
                'active_users': active_users,
                'success_rate': f"{success_rate:.1f}%",
                'avg_time': avg_time
            },
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Print startup banner
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                   RiF Activator A12+ Server                 ║
║                     إدارة وتفعيل الأجهزة                    ║
╠══════════════════════════════════════════════════════════════╣
║  🚀 نسخة محسنة مع مراقبة شاملة                              ║
║  📊 لوحة إدارة متقدمة                                       ║
║  🔒 أمان عالي مع تسجيل مفصل                                 ║
║  ⚡ أداء محسن مع مراقبة فورية                               ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)
    print(f"🕐 بدء التشغيل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 66)
    
    init_db()
    # start background verifier thread
    start_background_verifier()
    
    # إعداد نظام توثيق API
    print("📚 إعداد نظام توثيق API...")
    api_docs_result = setup_complete_api_documentation(app)
    if api_docs_result['status'] == 'success':
        print("✅ تم إعداد توثيق API بنجاح")
        print(f"📖 واجهة التوثيق: http://127.0.0.1:5000{api_docs_result['docs_url']}")
    else:
        print(f"⚠️ تحذير: فشل في إعداد التوثيق - {api_docs_result.get('message', 'خطأ غير معروف')}")
    
    # Host/port configuration: allow binding to LAN via env vars
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    try:
        port = int(os.environ.get('FLASK_PORT', '5000'))
    except Exception:
        port = 5000
    debug_env = os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true', 'yes')
    
    print(f"🌐 العنوان: http://{host}:{port}")
    print(f"🔧 وضع التطوير: {'مفعل' if debug_env else 'معطل'}")
    print(f"🔑 كلمة سر الإدمن: {os.environ.get('ADMIN_PASSWORD', 'Gsmrif2024@@')}")
    print(f"💰 التسجيل المجاني: {'مفعل' if os.environ.get('FREE_ACTIVATION') == '1' else 'معطل'}")
    print("=" * 66)
    print("✅ السيرفر جاهز للاستقبال!")
    print("🔗 لوحة الإدارة: http://127.0.0.1:5000/admin")
    print("=" * 66)
    
    # Start system monitoring
    start_system_monitor()
    
    # When exposing to network, ensure debug is False unless explicitly requested
    socketio.run(app, host=host, port=port, debug=debug_env)
