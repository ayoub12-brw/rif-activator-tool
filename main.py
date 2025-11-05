#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RiF Activator A12+ - Main Server Entry Point
نقطة الدخول الرئيسية لخادم RiF Activator A12+

This file serves as the main entry point for the RiF Activator A12+ server.
It imports and runs the Flask application from app.py with all enhanced features.
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path
current_dir = Path(__file__).parent.absolute()
sys.path.insert(0, str(current_dir))

try:
    # Import the Flask application
    from app import app, socketio
    
    print("🚀 RiF Activator A12+ Server Starting...")
    print("=" * 50)
    print("📱 RiF Activator A12+ - Enhanced Edition")
    print("🛡️  Secure iOS Device Activation System")
    print("=" * 50)
    
    # Get configuration from environment or use defaults
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('FLASK_ENV', 'production') == 'development'
    
    print(f"🌐 Server URL: http://{HOST}:{PORT}")
    print(f"🔧 Debug Mode: {'Enabled' if DEBUG else 'Disabled'}")
    print("=" * 50)
    print("📚 Available Endpoints:")
    print(f"   🏠 Main Page: http://{HOST}:{PORT}/")
    print(f"   🔍 Device Check: http://{HOST}:{PORT}/check_device")
    print(f"   🛡️  Admin Panel: http://{HOST}:{PORT}/admin")
    print(f"   📊 Reports: http://{HOST}:{PORT}/reports")
    print(f"   📖 API Docs: http://{HOST}:{PORT}/api/docs")
    print("=" * 50)
    print("🚀 Starting server...")
    
    # Run the application with SocketIO support
    socketio.run(
        app,
        host=HOST,
        port=PORT,
        debug=DEBUG,
        use_reloader=DEBUG,
        log_output=True
    )
    
except ImportError as e:
    print("❌ Error importing Flask application:")
    print(f"   {e}")
    print("\n💡 Make sure all required packages are installed:")
    print("   pip install -r requirements.txt")
    sys.exit(1)
    
except KeyboardInterrupt:
    print("\n🛑 Server stopped by user")
    sys.exit(0)
    
except Exception as e:
    print(f"❌ Unexpected error starting server: {e}")
    sys.exit(1)
