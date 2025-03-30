#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Loglama Modülü
Uygulama genelinde loglama işlemlerini yönetir.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime


def setup_logger(log_level="INFO", log_file=None, console=True, max_size=5*1024*1024, backup_count=5):
    """Logger kurulumu
    
    Args:
        log_level: Log seviyesi (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Log dosyası yolu (None ise konsola yazdırır)
        console: Konsola log yazdırılsın mı
        max_size: Maksimum log dosyası boyutu (byte)
        backup_count: Tutulacak eski log dosyası sayısı
        
    Returns:
        logging.Logger: Yapılandırılmış logger nesnesi
    """
    # Ana logger nesnesi
    logger = logging.getLogger("uk_muhasebe")
    
    # Log seviyesi ayarı
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Önceki handler'ları temizle
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Formatter
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Konsol handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Dosya handler
    if log_file:
        # Log dizini oluştur
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Logger nesnesini döndür
    return logger


def get_logger(name=None):
    """Mevcut logger nesnesini al veya alt logger oluştur
    
    Args:
        name: Alt logger adı (None ise ana logger döndürülür)
        
    Returns:
        logging.Logger: Logger nesnesi
    """
    if name:
        return logging.getLogger(f"uk_muhasebe.{name}")
    return logging.getLogger("uk_muhasebe")


def log_uncaught_exceptions(ex_cls, ex, tb):
    """Yakalanmamış hataları logla
    
    Args:
        ex_cls: Hata sınıfı
        ex: Hata nesnesi
        tb: Traceback nesnesi
    """
    logger = get_logger("uncaught")
    logger.critical(f"Uncaught exception: {ex_cls.__name__}: {ex}", exc_info=(ex_cls, ex, tb))


def create_app_logger(app_dir, log_level="INFO"):
    """Uygulama başlangıcında logger oluştur
    
    Args:
        app_dir: Uygulama dizini
        log_level: Log seviyesi
        
    Returns:
        logging.Logger: Yapılandırılmış logger nesnesi
    """
    # Log dizini oluştur
    log_dir = Path(app_dir) / "logs"
    if not log_dir.exists():
        os.makedirs(log_dir)
    
    # Tarih bazlı log dosyası
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_dir / f"app_{today}.log"
    
    # Logger kurulumu
    logger = setup_logger(
        log_level=log_level,
        log_file=log_file,
        console=True  # Geliştirme aşamasında konsola da yazdır
    )
    
    # Yakalanmamış hataları logla
    sys.excepthook = log_uncaught_exceptions
    
    # Başlangıç mesajı
    logger.info("=" * 60)
    logger.info("Uygulama başlatılıyor")
    logger.info(f"Log seviyesi: {log_level}")
    logger.info(f"Log dosyası: {log_file}")
    logger.info("-" * 60)
    
    return logger


def get_logger_with_context(module_name):
    """Modül adı bağlamında logger oluştur
    
    Modül içinde kullanımı:
    ```
    from utils.logger import get_logger_with_context
    logger = get_logger_with_context(__name__)
    ```
    
    Args:
        module_name: Modül adı (__name__)
        
    Returns:
        logging.Logger: Logger nesnesi
    """
    # Ana modül adını çıkar
    if module_name.startswith("uk_muhasebe."):
        context = module_name[len("uk_muhasebe."):]
    else:
        context = module_name
    
    return get_logger(context)
