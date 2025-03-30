#!/usr/bin/env python3
"""
UK Muhasebe Yazılımı
HMRC ile entegre, Excel benzeri arayüze sahip masaüstü muhasebe yazılımı.
"""

from setuptools import setup, find_packages
import os

# Uzun açıklama için README dosyasını oku
here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Gerekli paketleri requirements.txt'den oku
with open('requirements.txt') as f:
    required = f.read().splitlines()
    # Yorum satırlarını ve boş satırları temizle
    required = [line for line in required if line and not line.startswith('#')]

setup(
    name="uk_muhasebe",
    version="1.0.0",
    description="İngiltere vergi sistemi ile entegre çalışan masaüstü muhasebe yazılımı",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/kullanici/uk-muhasebe",
    author="HMRC Muhasebe Projesi",
    author_email="ornek@email.com",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Office/Business :: Financial :: Accounting",
        "Operating System :: OS Independent",
    ],
    keywords="muhasebe, vergi, hmrc, ingiltere, accounting, tax, uk",
    packages=find_packages(),
    install_requires=required,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "uk_muhasebe=uk_muhasebe.main:main",
        ],
    },
    # Veri dosyaları ekle
    include_package_data=True,
    package_data={
        "uk_muhasebe": [
            "resources/icons/*.png",
            "resources/templates/*.html",
            "resources/localization/*.json",
        ],
    },
    # Dağıtım için ek dosyalar
    data_files=[
        ("", ["LICENSE", "README.md"]),
    ],
    # Zip dağıtımı yapmayı devre dışı bırak
    zip_safe=False,
)
