#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os

# Read the contents of README file
this_directory = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Read requirements
with open('requirements.txt') as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="rif-activator-a12plus",
    version="2.0.0",
    author="RiF Development Team",
    author_email="dev@rifactivator.com",
    description="Advanced iOS Device Activation System for A12+ Devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ayoub12-brw/rif-activator-tool",
    project_urls={
        "Bug Reports": "https://github.com/ayoub12-brw/rif-activator-tool/issues",
        "Source": "https://github.com/ayoub12-brw/rif-activator-tool",
        "Documentation": "https://github.com/ayoub12-brw/rif-activator-tool/wiki",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: System :: Hardware",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Environment :: Web Environment",
        "Framework :: Flask",
    ],
    keywords=[
        "ios", "iphone", "activation", "a12", "device-management", 
        "flask", "pyqt", "mobile", "tools", "arabic"
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'black>=23.0.0',
            'flake8>=6.0.0',
            'bandit>=1.7.0',
            'sphinx>=5.0.0',
        ],
        'gui': [
            'PyQt5>=5.15.0',
        ],
        'analysis': [
            'pandas>=2.1.0',
            'matplotlib>=3.8.0',
            'seaborn>=0.13.0',
            'plotly>=5.15.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'rif-activator=app_simple:main',
            'rif-gui=device_ui:main',
        ],
    },
    include_package_data=True,
    package_data={
        '': ['templates/*.html', 'static/*', '*.md', '*.txt', '*.bat'],
    },
    zip_safe=False,
    platforms=['any'],
    license='MIT',
    
    # Arabic metadata
    metadata={
        'name_ar': 'مفعل الآيفون A12+',
        'description_ar': 'نظام متقدم لتفعيل أجهزة iOS المدعومة بمعالجات A12 وأحدث',
        'author_ar': 'فريق تطوير RiF',
    }
)