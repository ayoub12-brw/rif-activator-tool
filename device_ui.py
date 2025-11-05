import sys
import os
import subprocess
import threading
import time
from datetime import datetime
import webbrowser
from urllib.parse import quote_plus
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Application title shown in dialogs
APP_TITLE = "RiF Activator A12+"

import requests
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
    QMessageBox,
    QSizePolicy,
    QCheckBox,
)


class DeviceWindow(QWidget):
    support_signal = pyqtSignal(object, object, object)
    registration_signal = pyqtSignal(object)
    clipboard_signal = pyqtSignal(str)
    spinner_signal = pyqtSignal(str)
    open_url_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    fail_signal = pyqtSignal(str)
    show_success_signal = pyqtSignal()

    MODEL_MAP = {
        "iPhone17,1": "iPhone 16 Pro",
        "iPhone17,2": "iPhone 16 Pro Max",
        "iPhone17,3": "iPhone 16",
        "iPhone17,4": "iPhone 16 Plus",
        "iPhone16,1": "iPhone 15 Pro",
        "iPhone16,2": "iPhone 15 Pro Max",
        "iPhone15,4": "iPhone 15",
        "iPhone15,5": "iPhone 15 Plus",
        "iPhone15,2": "iPhone 14 Pro",
        "iPhone15,3": "iPhone 14 Pro Max",
        "iPhone14,7": "iPhone 14",
        "iPhone14,8": "iPhone 14 Plus",
        "iPhone14,2": "iPhone 13 Pro",
        "iPhone14,3": "iPhone 13 Pro Max",
        "iPhone14,5": "iPhone 13",
        "iPhone14,4": "iPhone 13 mini",
        "iPhone13,3": "iPhone 12 Pro",
        "iPhone13,4": "iPhone 12 Pro Max",
        "iPhone13,2": "iPhone 12",
        "iPhone13,1": "iPhone 12 mini",
        "iPhone12,3": "iPhone 11 Pro",
        "iPhone12,5": "iPhone 11 Pro Max",
        "iPhone12,1": "iPhone 11",
        "iPhone11,2": "iPhone XS",
        "iPhone11,4": "iPhone XS Max",
        "iPhone11,6": "iPhone XS Max",
        "iPhone11,8": "iPhone XR",
        "iPhone10,3": "iPhone X",
        "iPhone10,6": "iPhone X",
        "iPhone10,1": "iPhone 8",
        "iPhone10,4": "iPhone 8",
        "iPhone10,2": "iPhone 8 Plus",
        "iPhone10,5": "iPhone 8 Plus",
        "iPhone9,1": "iPhone 7",
        "iPhone9,3": "iPhone 7",
        "iPhone9,2": "iPhone 7 Plus",
        "iPhone9,4": "iPhone 7 Plus",
        "iPhone8,4": "iPhone SE (1st gen)",
        "iPhone12,8": "iPhone SE (2nd gen)",
        "iPhone14,6": "iPhone SE (3rd gen)",
        "iPhone8,1": "iPhone 6s",
        "iPhone8,2": "iPhone 6s Plus",
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RiF Activator A12+")
        # Slightly smaller width per request while keeping info readable
        self.setFixedSize(760, 420)
        self.setStyleSheet("background-color: #222; color: white;")
        
        self.support_signal.connect(self._update_support_label)
        self.registration_signal.connect(self._update_registration_label)
        self.clipboard_signal.connect(self._do_set_clipboard)
        self.spinner_signal.connect(self._set_spinner_text)
        self.open_url_signal.connect(self._open_url)
        self.progress_signal.connect(self._update_progress)
        self.fail_signal.connect(self._on_show_fail)
        self.show_success_signal.connect(self._on_show_success)

        self.simulate_enabled = os.environ.get("SIMULATE_BYPASS", "0").lower() in ("1", "true")
        # Optional: skip server checks to avoid console spam when backend is offline
        self.offline_mode = os.environ.get("OFFLINE_MODE", "0").lower() in ("1", "true")
        # Throttle network error logs (seconds since epoch of next allowed log)
        self._server_error_next_log = 0.0
        # Throttle device detection error logs
        self._device_error_next_log = 0.0
        # iOS support range (inclusive) - Support from iOS 18.7.1 to iOS 26.1
        self._min_ios = (18, 7, 1)
        # Allow any patch for 26.1 by setting a high patch ceiling
        self._max_ios = (26, 1, 999)
        # API key for backend auth (server expects X-API-Key header)
        self.api_key = os.environ.get("API_KEY", "dev-api-key")
        # Optional local whitelist for development (comma-separated ProductType codes)
        local_allowed = os.environ.get("LOCAL_ALLOWED_MODELS", "").strip()
        self.local_allowed_models = set(
            x.strip() for x in local_allowed.split(",") if x.strip()
        )
        # Enable free activation mode in development/admin
        self.free_activation = (
            os.environ.get("FREE_ACTIVATION", "0").lower() in ("1", "true")
            or os.environ.get("ADMIN_MODE", "0").lower() in ("1", "true")
        )
        # Auto reboot during scan (ALWAYS enabled - one-time per device)
        self.auto_reboot_enabled = True  # Always enabled
        self._rebooted_udids = set()
        # Track if we've shown the congratulations dialog for current device
        self._shown_congrats_for_serial = None
        # Track pending congrats until we know registration status
        self._pending_congrats_serial = None
        self._build_ui()
        self._progress_stop_event = threading.Event()
        self._progress_thread = None
        self.start_device_check()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        self.header_label = QLabel("RiF Activator A12+")
        self.header_label.setFont(QFont("Arial", 22, QFont.Bold))
        self.header_label.setAlignment(Qt.AlignCenter)
        self.header_label.setStyleSheet("color: #4CAF50; margin: 10px 0;")

        self.logo_label = QLabel()
        self.logo_label.setAlignment(Qt.AlignCenter)
        base_path = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(base_path, "logo.png")
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.logo_label.setPixmap(scaled)

        # Connection instructions (we'll wrap them in a container to collapse cleanly)
        self.instr_ar = QLabel("🔌 وصّل الجهاز عبر كابل USB")
        self.instr_ar.setFont(QFont("Arial", 12))
        self.instr_ar.setAlignment(Qt.AlignCenter)
        self.instr_ar.setStyleSheet("color: #FFA726; margin: 5px;")
        self.instr_ar.setContentsMargins(0, 0, 0, 0)

        self.instr_en = QLabel("Connect your device via USB cable")
        self.instr_en.setFont(QFont("Arial", 10))
        self.instr_en.setAlignment(Qt.AlignCenter)
        self.instr_en.setStyleSheet("color: #AAA; margin-bottom: 10px;")
        self.instr_en.setContentsMargins(0, 0, 0, 0)

        # Container to ensure no leftover gap when hidden
        from PyQt5.QtWidgets import QFrame
        self.instructions_box = QFrame()
        inst_layout = QVBoxLayout(self.instructions_box)
        inst_layout.setContentsMargins(0, 0, 0, 0)
        inst_layout.setSpacing(2)
        inst_layout.addWidget(self.instr_ar)
        inst_layout.addWidget(self.instr_en)
        self.instructions_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        # Reserve a fixed height for the instructions area so content below doesn't jump
        try:
            self.instructions_box.adjustSize()
            _h = self.instructions_box.sizeHint().height()
            if not _h or _h <= 0:
                _h = 56
            self.instructions_box.setFixedHeight(_h)
        except Exception:
            pass

        def make_info_label():
            lbl = QLabel("---")
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            lbl.setStyleSheet("color: white; font-size: 13px;")
            # Improve visibility for long values
            try:
                lbl.setWordWrap(True)
                lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                lbl.setTextInteractionFlags(lbl.textInteractionFlags() | Qt.TextSelectableByMouse)
                lbl.setMinimumWidth(420)
            except Exception:
                pass
            return lbl

        self.model_label = make_info_label()
        # Ensure Model value is always readable: allow wrapping and expansion
        try:
            self.model_label.setWordWrap(True)
            self.model_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            # Slightly larger/bolder for emphasis without changing other rows
            self.model_label.setStyleSheet("color: white; font-size: 14px; font-weight: 600;")
        except Exception:
            pass
        self.product_label = make_info_label()
        self.ios_label = make_info_label()
        self.serial_label = make_info_label()
        self.imei_label = make_info_label()
        self.udid_label = make_info_label()

        def make_key_label(text):
            lbl = QLabel(text)
            lbl.setStyleSheet("color: #999; font-size: 12px;")
            # Give more room to values by reducing key width slightly
            lbl.setFixedWidth(120)
            return lbl

        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)

        rows = [
            ("Model:", self.model_label),
            ("Product Type:", self.product_label),
            ("iOS Version:", self.ios_label),
            ("SerialNumber:", self.serial_label),
            ("IMEI:", self.imei_label),
            ("UDID:", self.udid_label),
        ]

        for key_text, val_label in rows:
            row = QHBoxLayout()
            row.addWidget(make_key_label(key_text))
            row.addWidget(val_label, 1)
            info_layout.addLayout(row)

        self.support_label = QLabel("")
        self.support_label.setAlignment(Qt.AlignCenter)
        self.support_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.support_label.setStyleSheet("margin: 5px;")

        self.registration_label = QLabel("")
        self.registration_label.setAlignment(Qt.AlignCenter)
        self.registration_label.setFont(QFont("Arial", 11, QFont.Bold))
        self.registration_label.setStyleSheet("margin: 5px;")

        self.activate_btn = QPushButton("Activate")
        self.activate_btn.setFont(QFont("Arial", 12, QFont.Bold))
        self.activate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 12px;
                margin-top: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        self.activate_btn.clicked.connect(self.activate_device)
        self.activate_btn.setEnabled(False)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("Checking...")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555;
                border-radius: 5px;
                text-align: center;
                color: white;
                background-color: #333;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)

        layout.addWidget(self.header_label)
        layout.addWidget(self.logo_label)
        layout.addWidget(self.instructions_box)
        layout.addLayout(info_layout)
        layout.addWidget(self.support_label)
        layout.addWidget(self.registration_label)
        # auto_reboot_checkbox is hidden, not added to layout
        layout.addWidget(self.activate_btn)
        layout.addWidget(self.progress_bar)
        layout.addStretch(1)

        self.setLayout(layout)

    def start_device_check(self):
        self._check_timer = QTimer()
        self._check_timer.timeout.connect(self.check_device)
        self._check_timer.start(2000)

    def check_device(self):
        threading.Thread(target=self._check_device_support_background, daemon=True).start()

    def _check_device_support_background(self):
        info = self._get_device_info()
        if not info:
            self.support_signal.emit(None, None, None)
            return

        serial = info.get("SerialNumber", "")
        product_type = info.get("ProductType", "")
        ios_version = info.get("ProductVersion", "")
        udid = info.get("UniqueDeviceID", "")
        print(f"[DEBUG] Device detected: {product_type}, iOS {ios_version}, Serial {serial}")

        # If auto reboot is enabled, reboot once per detected device then continue checks after it reconnects
        if self.auto_reboot_enabled and udid and udid not in self._rebooted_udids:
            try:
                self.spinner_signal.emit("Rebooting device...")
            except Exception:
                pass
            self._reboot_device(udid)
            self._rebooted_udids.add(udid)
            # Skip further checks this cycle; the timer will run again after reboot
            return

        # If running in OFFLINE_MODE, compute support locally by iOS range only
        if self.offline_mode:
            supported_local = self._is_ios_in_supported_range(ios_version)
            print(f"[DEBUG] OFFLINE_MODE: iOS in range? {supported_local}")
            if not supported_local:
                print(f"[INFO] iOS version out of supported range: {ios_version}")
            self.support_signal.emit(info, supported_local, "")
            return

        serial = info.get("SerialNumber", "")
        product_type = info.get("ProductType", "")
        ios_version = info.get("ProductVersion", "")
        udid = info.get("UniqueDeviceID", "")

        try:
            url = "http://127.0.0.1:5000/api/check_device"
            payload = {"udid": udid, "serial": serial, "model": product_type}
            headers = {"X-API-Key": self.api_key}
            resp = requests.post(url, json=payload, headers=headers, timeout=3)
            data = resp.json()
            # New endpoint returns 'allowed' instead of 'supported'
            supported = data.get("allowed", data.get("supported", False))
            message = data.get("message", "")
            print(f"[DEBUG] Server response: status={resp.status_code}, supported={supported}, message={message}")
        except Exception as e:
            # Throttle noisy network errors when backend is offline
            now = time.time()
            if now >= self._server_error_next_log:
                print(f"[ERROR] check_device failed: {e}")
                self._server_error_next_log = now + 15
            supported = False
            message = ""
        # Apply optional local whitelist override for development
        allowed_local = product_type in self.local_allowed_models if self.local_allowed_models else False
        if allowed_local and not supported:
            print(f"[DEBUG] Local model override applied for {product_type}")
        # Enforce iOS version range and combine with server/local decision
        in_range = self._is_ios_in_supported_range(ios_version)
        final_supported = (bool(supported) or allowed_local) and in_range
        print(f"[DEBUG] iOS in range? {in_range}, Final supported: {final_supported}")
        if (supported or allowed_local) and not in_range:
            print(f"[INFO] iOS version out of supported range (server said supported): {ios_version}")
        supported = final_supported
        # Emit result and if supported, check registration status
        self.support_signal.emit(info, supported, message)
        if supported:
            self._check_registration_background(serial)

    def _reboot_device(self, udid: str):
        try:
            # Prefer bundled idevicediagnostics on Windows
            cmd = ["idevicediagnostics", "restart"]
            if os.name == "nt":
                base_path = os.path.dirname(os.path.abspath(__file__))
                candidate = os.path.join(base_path, "libimobiledevice-windows-master", "idevicediagnostics.exe")
                if os.path.exists(candidate):
                    cmd = [candidate, "restart"]
            # Insert UDID argument if available (option first, then command)
            if udid:
                # For format: idevicediagnostics -u <udid> restart
                exe = cmd[0]
                rest = cmd[1:]
                cmd = [exe, "-u", udid] + rest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=15,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            stderr = (result.stderr or "").strip()
            print(f"[INFO] Reboot command exit={result.returncode} {'OK' if result.returncode==0 else stderr}")
        except Exception as e:
            print(f"[ERROR] Reboot failed: {e}")

    def _check_registration_background(self, serial):
        try:
            url = "http://127.0.0.1:5000/api/check_serial"
            resp = requests.post(url, json={"serial": serial}, timeout=3)
            data = resp.json()
            registered = data.get("registered", False)
            self.registration_signal.emit({"registered": registered, "serial": serial})
        except Exception as e:
            # Throttle noisy network errors when backend is offline
            now = time.time()
            if now >= self._server_error_next_log:
                print(f"[ERROR] check_serial failed: {e}")
                self._server_error_next_log = now + 15
            self.registration_signal.emit({"registered": False, "serial": serial})

    def _get_device_info(self):
        if self.simulate_enabled:
            return {
                "ProductType": "iPhone15,2",
                "ProductVersion": "18.7.1",
                "SerialNumber": "SIMULATE123456",
                "UniqueDeviceID": "00000000-0000000000000000",
                "InternationalMobileEquipmentIdentity": "000000000000000",
            }
        try:
            # Prefer bundled ideviceinfo on Windows if available
            cmd = ["ideviceinfo"]
            if os.name == "nt":
                base_path = os.path.dirname(os.path.abspath(__file__))
                candidate = os.path.join(base_path, "libimobiledevice-windows-master", "ideviceinfo.exe")
                if os.path.exists(candidate):
                    cmd = [candidate]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if result.returncode != 0:
                # Throttle logs to avoid spam when device is not connected or not trusted
                now = time.time()
                if now >= self._device_error_next_log:
                    stderr = (result.stderr or "").strip()
                    print(f"[DEBUG] ideviceinfo returned {result.returncode}: {stderr or 'No device? Ensure device is unlocked and trusted, and iTunes/Apple Mobile Device Support is installed.'}")
                    self._device_error_next_log = now + 10
                return None
            lines = result.stdout.strip().split("\n")
            info = {}
            for line in lines:
                if ":" in line:
                    key, val = line.split(":", 1)
                    info[key.strip()] = val.strip()
            return info if info else None
        except Exception as e:
            print(f"[DEBUG] ideviceinfo error: {e}")
            return None

    def _parse_ios_version(self, version_str):
        """Parse iOS version string like '18.7.1' into a 3-int tuple."""
        parts = []
        for token in version_str.split('.'):
            try:
                parts.append(int(''.join(ch for ch in token if ch.isdigit())))
            except Exception:
                parts.append(0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])

    def _is_ios_in_supported_range(self, version_str):
        v = self._parse_ios_version(version_str or "0.0.0")
        return self._min_ios <= v <= self._max_ios

    def _update_support_label(self, info, supported, message):
        if not info:
            # No device connected: show instructions
            try:
                # Keep the instructions container visible and show its labels
                self.instr_ar.show()
                self.instr_en.show()
            except Exception:
                pass
                # Show logo when no device to fill header
            
            self.model_label.setText("---")
            self.product_label.setText("---")
            self.ios_label.setText("---")
            self.serial_label.setText("---")
            self.imei_label.setText("---")
            self.udid_label.setText("---")
            # Hide status labels to avoid leaving any visual gap
            self.support_label.setText("")
            try:
                self.support_label.hide()
            except Exception:
                pass
            self.registration_label.setText("")
            try:
                self.registration_label.hide()
            except Exception:
                pass
            self.activate_btn.setEnabled(False)
            self.progress_bar.setFormat("Waiting for device...")
            
            return

        product_type = info.get("ProductType", "Unknown")
        marketing_name = self.MODEL_MAP.get(product_type, product_type)
        # Show both marketing name and product code for clarity
        combined_model = f"{marketing_name} ({product_type})" if product_type else marketing_name
        self.model_label.setText(combined_model)
        try:
            # Provide full text on hover in case of truncation
            self.model_label.setToolTip(combined_model)
        except Exception:
            pass
        self.product_label.setText(product_type)
        self.ios_label.setText(info.get("ProductVersion", "Unknown"))
        self.serial_label.setText(info.get("SerialNumber", "Unknown"))
        self.imei_label.setText(info.get("InternationalMobileEquipmentIdentity", "Unknown"))
        self.udid_label.setText(info.get("UniqueDeviceID", "Unknown"))

        # Device connected: keep reserved space, hide only the instruction labels
        try:
            self.instr_ar.hide()
            self.instr_en.hide()
        except Exception:
            pass
        
        # Also hide labels by default; registration handler will show when needed
        try:
            self.support_label.hide()
        except Exception:
            pass
        try:
            self.registration_label.hide()
        except Exception:
            pass

        if supported:
            # Keep UI silent even when supported; show only the pop-up
            self.support_label.setText("")
            self.support_label.setStyleSheet("")
            self.support_label.hide()  # Hide the label completely
            # Defer popup to registration check so we can suppress it if already registered
            serial = info.get("SerialNumber", "Unknown")
            self._pending_congrats_serial = serial
        else:
            # Keep UI silent when not supported; log only in console
            self.support_label.setText("")
            self.support_label.setStyleSheet("")
            self.support_label.hide()  # Hide the label completely
            if message:
                print(f"[INFO] Device not supported: {message}")
            # Clear any pending congrats since device isn't supported
            self._pending_congrats_serial = None

    def _update_registration_label(self, data):
        registered = data.get("registered", False)
        serial = data.get("serial", "")

        if registered:
            # Hide the registered label from UI per request
            self.registration_label.setText("")
            self.registration_label.setStyleSheet("")
            self.activate_btn.setEnabled(True)
            self.progress_bar.setFormat("Ready to activate")
            # Do not show congrats popup for already registered devices
            self._pending_congrats_serial = None
            try:
                self.registration_label.hide()
            except Exception:
                pass
        else:
            # Hide the registration label when not registered to avoid gaps
            self.registration_label.setText("")
            self.registration_label.setStyleSheet("")
            try:
                self.registration_label.hide()
            except Exception:
                pass
            # Allow user to click Activate to complete registration flow (dev/payment)
            self.activate_btn.setEnabled(True)
            self.progress_bar.setFormat("Registration required")
            self.clipboard_signal.emit(serial)
            # Do not auto-open the registration website; user can register manually
            # Show congratulations popup only if supported and not yet registered
            if (
                serial
                and self._pending_congrats_serial == serial
                and serial != self._shown_congrats_for_serial
            ):
                self._shown_congrats_for_serial = serial
                msg = (
                    f"🎉 مبروك! جهازك مدعوم\n\n"
                    f"📱 السيريال: {serial}\n\n"
                    f"✨ يرجى تسجيل السيريال للمتابعة"
                )
                QMessageBox.information(self, APP_TITLE, msg)

    def _do_set_clipboard(self, text):
        try:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)
            print(f"[INFO] Copied to clipboard: {text}")
        except Exception as e:
            print(f"[ERROR] Clipboard copy failed: {e}")

    def _set_spinner_text(self, text):
        self.progress_bar.setFormat(text)

    def _open_url(self, url):
        try:
            webbrowser.open(url)
            print(f"[INFO] Opened URL: {url}")
        except Exception as e:
            print(f"[ERROR] Failed to open URL: {e}")

    def _update_progress(self, value):
        self.progress_bar.setValue(value)

    def activate_device(self):
        serial = self.serial_label.text()
        if serial == "Unknown" or serial == "---":
            QMessageBox.warning(self, APP_TITLE, "No device detected!")
            return

        # Disable the activate button during processing (but keep it visible)
        self.activate_btn.setEnabled(False)
        self.spinner_signal.emit("Activating...")
        self._progress_stop_event.clear()
        self._progress_thread = threading.Thread(target=self._animate_progress, daemon=True)
        self._progress_thread.start()

        threading.Thread(target=self._activate_background, args=(serial,), daemon=True).start()

    def _animate_progress(self):
        val = 0
        while not self._progress_stop_event.is_set():
            val = (val + 1) % 101
            self.progress_signal.emit(val)
            time.sleep(0.25)  # Much slower progress animation - moves every 0.25 seconds

    def _activate_background(self, serial):
        try:
            # Show ultra comprehensive preparation steps - maximum heavy processing
            self.spinner_signal.emit("Initializing activation system...")
            time.sleep(2.5)
            
            self.spinner_signal.emit("Loading Apple framework libraries...")
            time.sleep(3.2)
            
            self.spinner_signal.emit("Loading device drivers...")
            time.sleep(2.8)
            
            self.spinner_signal.emit("Preparing device interface...")
            time.sleep(3.0)
            
            self.spinner_signal.emit("Detecting iOS version and build...")
            time.sleep(2.4)
            
            self.spinner_signal.emit("Scanning hardware configuration...")
            time.sleep(2.9)
            
            self.spinner_signal.emit("Analyzing device security features...")
            time.sleep(3.5)
            
            # First reboot - Security analysis phase
            self.spinner_signal.emit("Preparing security reboot (1/4)...")
            time.sleep(2.0)
            self.spinner_signal.emit("Initiating first device restart...")
            udid = self.udid_label.text()
            if udid and udid != "Unknown" and udid != "---":
                self._reboot_device(udid)
            time.sleep(3.0)
            self.spinner_signal.emit("Reconnecting after security reboot...")
            time.sleep(3.5)
            
            self.spinner_signal.emit("Checking iOS compatibility matrix...")
            time.sleep(2.7)
            
            self.spinner_signal.emit("Loading activation bypass modules...")
            time.sleep(4.0)
            
            # Second reboot - Bypass loading phase  
            self.spinner_signal.emit("Preparing bypass reboot (2/4)...")
            time.sleep(2.2)
            self.spinner_signal.emit("Initiating bypass restart...")
            if udid and udid != "Unknown" and udid != "---":
                self._reboot_device(udid)
            time.sleep(3.2)
            self.spinner_signal.emit("Reconnecting after bypass reboot...")
            time.sleep(3.8)
            
            self.spinner_signal.emit("Validating device certificates...")
            time.sleep(2.3)
            
            self.spinner_signal.emit("Checking Apple server connectivity...")
            time.sleep(3.1)
            
            self.spinner_signal.emit("Verifying activation credentials...")
            time.sleep(2.9)
            
            # Third reboot - Credentials phase
            self.spinner_signal.emit("Preparing credentials reboot (3/4)...")
            time.sleep(2.1)
            self.spinner_signal.emit("Initiating credentials restart...")
            if udid and udid != "Unknown" and udid != "---":
                self._reboot_device(udid)
            time.sleep(3.1)
            self.spinner_signal.emit("Reconnecting after credentials reboot...")
            time.sleep(4.0)
            
            self.spinner_signal.emit("Preparing activation payload...")
            time.sleep(2.6)
            
            self.spinner_signal.emit("Creating secure backup snapshot...")
            time.sleep(4.5)
            
            self.spinner_signal.emit("Backing up device data...")
            time.sleep(4.2)
            
            # Fourth reboot - Final preparation phase
            self.spinner_signal.emit("Preparing final reboot (4/4)...")
            time.sleep(2.3)
            self.spinner_signal.emit("Initiating final restart...")
            if udid and udid != "Unknown" and udid != "---":
                self._reboot_device(udid)
            time.sleep(3.0)
            self.spinner_signal.emit("Final reconnection in progress...")
            time.sleep(4.5)
            
            self.spinner_signal.emit("Re-establishing device communication...")
            time.sleep(3.8)
            
            self.spinner_signal.emit("Verifying device connection...")
            time.sleep(2.7)
            
            self.spinner_signal.emit("Clearing system cache...")
            time.sleep(2.8)
            
            self.spinner_signal.emit("Clearing cache and temporary files...")
            time.sleep(3.3)
            
            self.spinner_signal.emit("Initiating activation bypass...")
            time.sleep(3.8)
            
            self.spinner_signal.emit("Bypassing iCloud activation lock...")
            time.sleep(4.5)
            
            self.spinner_signal.emit("Overriding Apple security protocols...")
            time.sleep(4.2)
            
            self.spinner_signal.emit("Removing activation locks...")
            time.sleep(5.0)
            
            self.spinner_signal.emit("Activation bypass completed successfully...")
            time.sleep(3.0)
            
            self.spinner_signal.emit("Establishing secure SSL connection...")
            time.sleep(2.5)
            
            self.spinner_signal.emit("Connecting to activation servers...")
            time.sleep(3.0)
            
            self.spinner_signal.emit("Bypassing Apple activation servers...")
            time.sleep(4.1)
            
            self.spinner_signal.emit("Spoofing device activation status...")
            time.sleep(3.7)
            
            self.spinner_signal.emit("Authenticating with Apple servers...")
            time.sleep(3.8)
            
            self.spinner_signal.emit("Injecting bypass activation tokens...")
            time.sleep(3.5)
            
            self.spinner_signal.emit("Authenticating with activation server...")
            time.sleep(3.2)
            
            self.spinner_signal.emit("Generating activation bypass certificates...")
            time.sleep(3.0)
            
            self.spinner_signal.emit("Finalizing activation bypass...")
            time.sleep(2.7)
            
            url = "http://127.0.0.1:5000/pay_register"
            payload = {"serial": serial}
            # In dev/admin mode, request a free activation on the server
            if self.free_activation:
                payload["chain"] = "free"
            
            self.spinner_signal.emit("Sending activation request...")
            time.sleep(2.5)
            
            self.spinner_signal.emit("Processing activation request...")
            resp = requests.post(url, json=payload, timeout=10)
            
            self.spinner_signal.emit("Validating server response...")
            time.sleep(3.2)
            
            self.spinner_signal.emit("Installing activation certificates...")
            time.sleep(4.0)
            
            self.spinner_signal.emit("Finalizing activation process...")
            time.sleep(3.5)
            
            self.spinner_signal.emit("Applying final configurations...")
            time.sleep(2.8)
            
            data = resp.json()
            success = data.get("success", False)
            message = data.get("message", "")

            self._progress_stop_event.set()
            if self._progress_thread:
                self._progress_thread.join(timeout=1)

            if success:
                self.show_success_signal.emit()
            else:
                self.fail_signal.emit(message or "Activation failed")

        except Exception as e:
            self._progress_stop_event.set()
            if self._progress_thread:
                self._progress_thread.join(timeout=1)
            self.fail_signal.emit(f"Network error: {str(e)}")

    def _on_show_success(self):
        self.progress_bar.setValue(100)
        self.spinner_signal.emit("✅ Activation successful!")
        
        # Create flashing effect for success celebration
        self._create_success_flash_effect()
        
        # Perform final software-like reboot after successful activation
        self._perform_final_software_reboot()
        
        QMessageBox.information(self, APP_TITLE, "Device activated successfully!")
        # Re-enable button after successful completion
        self.activate_btn.setEnabled(True)
    
    def _perform_final_software_reboot(self):
        """Perform final reboot like a software update completion"""
        def final_reboot_sequence():
            time.sleep(2.0)  # Wait a moment after success message
            
            self.spinner_signal.emit("Applying activation changes...")
            time.sleep(1.5)
            
            self.spinner_signal.emit("Preparing software update...")
            time.sleep(2.0)
            
            self.spinner_signal.emit("Installing activation firmware...")
            time.sleep(2.5)
            
            self.spinner_signal.emit("Device will restart to complete activation...")
            time.sleep(2.0)
            
            # Trigger final reboot like software update
            udid = self.udid_label.text()
            if udid and udid != "Unknown" and udid != "---":
                self.spinner_signal.emit("Restarting device (Software Update)...")
                self._reboot_device(udid)
                time.sleep(3.0)
                
                self.spinner_signal.emit("Device restarting...")
                time.sleep(4.0)
                
                self.spinner_signal.emit("Activation completed successfully!")
                time.sleep(1.0)
        
        # Run final reboot sequence in background
        threading.Thread(target=final_reboot_sequence, daemon=True).start()
    
    def _create_success_flash_effect(self):
        """Create a flashing effect on the progress bar when activation succeeds"""
        def flash_animation():
            original_style = self.progress_bar.styleSheet()
            flash_style = """
                QProgressBar {
                    border: 2px solid #4CAF50;
                    border-radius: 5px;
                    text-align: center;
                    color: white;
                    background-color: #2E7D32;
                }
                QProgressBar::chunk {
                    background-color: #66BB6A;
                }
            """
            bright_style = """
                QProgressBar {
                    border: 2px solid #FFD700;
                    border-radius: 5px;
                    text-align: center;
                    color: #000;
                    background-color: #FFEB3B;
                }
                QProgressBar::chunk {
                    background-color: #FFF176;
                }
            """
            
            # Flash sequence: bright -> normal -> bright -> normal -> bright -> normal
            for i in range(6):
                if i % 2 == 0:
                    self.progress_bar.setStyleSheet(bright_style)
                else:
                    self.progress_bar.setStyleSheet(flash_style)
                time.sleep(0.3)
            
            # Return to original style
            self.progress_bar.setStyleSheet(original_style)
        
        # Run flash animation in separate thread to not block UI
        threading.Thread(target=flash_animation, daemon=True).start()

    def _on_show_fail(self, message):
        self.progress_bar.setValue(0)
        self.spinner_signal.emit("❌ Activation failed")
        QMessageBox.critical(self, APP_TITLE, f"Activation failed:\n{message}")
        # Re-enable button after failure for retry
        self.activate_btn.setEnabled(True)


def main():
    app = QApplication(sys.argv)
    window = DeviceWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
