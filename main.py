#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Ana Uygulama Modülü
HMRC ile entegre, Excel benzeri arayüze sahip masaüstü muhasebe yazılımı.
"""

import os
import sys
import json
import logging
from pathlib import Path

# GUI kütüphanesi import (PyQt5 kullanıyoruz)
from PyQt5.QtWidgets import QApplication

# Proje modülleri
from gui.main_window import MainWindow
from core.ledger import Ledger
from data.database import Database
from utils.logger import setup_logger

# HMRC modülleri
from hmrc import mtd, vat, income_tax, corporate_tax

# Entegrasyon modülleri
from integrations.integration import IntegrationsManager


class UKMuhasebe:
    """Ana uygulama sınıfı"""
    
    def __init__(self):
        """Uygulama başlatıcı"""
        self.app_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        self.config = self._load_config()
        
        # Loglama ayarları
        self.logger = setup_logger(
            log_level=self.config.get("log_level", "INFO"),
            log_file=self.app_dir / "logs" / "app.log"
        )
        self.logger.info("Uygulama başlatılıyor...")
        
        # Veritabanı bağlantısı
        self.db = Database(
            db_file=self.app_dir / "data" / "company_data.json",
            backup_dir=self.app_dir / "data" / "backups"
        )
        
        # Ana muhasebe defteri oluşturma
        self.ledger = Ledger(self.db)
        
        # Entegrasyon yöneticisini oluştur
        self.integration_manager = IntegrationsManager(self.ledger, self.config)
        
        # PyQt5 uygulaması oluşturma
        self.qt_app = QApplication(sys.argv)
        
        # Ana pencere oluşturma
        self.main_window = MainWindow(
            ledger=self.ledger,
            db=self.db,
            config=self.config,
            integration_manager=self.integration_manager
        )
        
        # Otomatik senkronizasyon kontrolü
        if self.integration_manager.should_sync():
            self.logger.info("Zamanlanmış otomatik senkronizasyon başlatılıyor...")
            self.integration_manager.sync_all()
            self.integration_manager.update_last_sync_time()
    
    def _load_config(self):
        """Yapılandırma dosyasını yükle"""
        config_path = self.app_dir / "config.json"
        
        # Varsayılan ayarlar
        default_config = {
            "company_name": "",
            "company_vat": "",
            "company_address": "",
            "company_type": "sole_trader",  # sole_trader, limited_company, partnership
            "currency": "GBP",
            "tax_year_start": "04-06",  # UK vergi yılı formatı: ay-gün
            "hmrc_api": {
                "client_id": "",
                "client_secret": "",
                "endpoint": "https://test.api.service.hmrc.gov.uk/",  # Test ortamı
                "redirect_uri": "http://localhost:8080/callback"
            },
            "company_info": {
                "crn": "",  # Company Registration Number (limited şirketler için)
                "utr": "",  # Unique Taxpayer Reference
                "accounting_period_start": "",  # Şirket mali yılı başlangıcı
                "accounting_period_end": ""     # Şirket mali yılı bitişi
            },
            "backup": {
                "auto_backup": True,
                "backup_interval": 24,  # Saat cinsinden
                "keep_backups": 30      # Tutulacak yedek sayısı
            },
            "wise": {
                "api_token": "",
                "profile_id": "",
                "sandbox": False,
                "account_mappings": {}
            },
            "stripe": {
                "api_key": "",
                "webhook_secret": "",
                "account_mappings": {}
            },
            "sync_schedule": {
                "enabled": False,
                "interval_hours": 6,
                "last_sync": ""
            },
            "log_level": "INFO",
            "language": "tr",
            "theme": "light"
        }
        
        # Eğer config dosyası yoksa oluştur
        if not config_path.exists():
            os.makedirs(config_path.parent, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4)
            return default_config
        
        # Config dosyasını oku
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            # Eksik ayarları varsayılan değerlerle tamamla
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value
                    
            # company_info alanını kontrol et ve eksik alt alanları tamamla
            if "company_info" not in config:
                config["company_info"] = default_config["company_info"]
            else:
                for sub_key, sub_value in default_config["company_info"].items():
                    if sub_key not in config["company_info"]:
                        config["company_info"][sub_key] = sub_value
                    
            # wise alanını kontrol et
            if "wise" not in config:
                config["wise"] = default_config["wise"]
                
            # stripe alanını kontrol et
            if "stripe" not in config:
                config["stripe"] = default_config["stripe"]
                
            # sync_schedule alanını kontrol et
            if "sync_schedule" not in config:
                config["sync_schedule"] = default_config["sync_schedule"]
                    
            return config
        except Exception as e:
            print(f"Yapılandırma dosyası yüklenirken hata oluştu: {e}")
            return default_config
    
    def run(self):
        """Uygulamayı çalıştır"""
        self.main_window.show()
        return self.qt_app.exec_()


if __name__ == "__main__":
    app = UKMuhasebe()
    sys.exit(app.run())
