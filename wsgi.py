#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WSGI Configuration for RiF Activator A12+
إعداد WSGI لـ RiF Activator A12+

This module contains the WSGI callable used by WSGI servers to serve
the RiF Activator A12+ application.
"""

import os
import sys

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_dir)

# Import the Flask application
from app_simple import app

# WSGI callable
application = app

if __name__ == "__main__":
    application.run()