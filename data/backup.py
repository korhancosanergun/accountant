#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Yedekleme Modülü
Veritabanı yedekleme ve geri yükleme işlemleri
"""

import os
import json
import shutil
import logging
from datetime import datetime
import zipfile
import glob
from pathlib import Path
import threading
import time

# Modül için logger
logger = logging.getLogger(__name__)


class BackupManager:
    """Yedekleme yöneticisi"""
    
    def __init__(self, database, config):
        """Yönetici başlatıcı
        
        Args:
            database: Veritabanı nesnesi
            config: Uygulama yapılandırması
        """
        self.db = database
        self.config = config
        
        # Yedekleme dizini
        backup_dir = config.get("backup_dir", "backups")
        
        # Tam yol olup olmadığını kontrol et
        if os.path.isabs(backup_dir):
            self.backup_dir = Path(backup_dir)
        else:
            # Uygulama dizinine göre yol
            app_dir = Path(os.path.dirname(os.path.abspath(database.db_file)))
            self.backup_dir = app_dir / backup_dir
        
        # Dizinin var olduğundan emin ol
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Otomatik yedekleme ayarları
        self.auto_backup = config.get("backup", {}).get("auto_backup", True)
        self.backup_interval = config.get("backup", {}).get("backup_interval", 24)  # Saat cinsinden
        self.keep_backups = config.get("backup", {}).get("keep_backups", 30)  # Tutulan yedek sayısı
        
        # Otomatik yedekleme için son yedekleme zamanı
        self.last_backup_time = datetime.now()
        
        # Otomatik yedekleme izleme
        self.auto_backup_thread = None
        self.auto_backup_running = False
    
    def create_backup(self, comment=None):
        """Yedek oluştur
        
        Args:
            comment: Yedek için açıklama
            
        Returns:
            str: Oluşturulan yedek dosyasının yolu
        """
        try:
            # Zaman damgalı dosya adı oluştur
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_filename = f"backup_{timestamp}.json"
            backup_path = self.backup_dir / backup_filename
            
            # Veritabanının bir kopyasını oluştur
            with open(self.db.db_file, 'r', encoding='utf-8') as src:
                db_content = json.load(src)
            
            # Meta bilgileri ekle
            db_content["_backup_info"] = {
                "timestamp": datetime.now().isoformat(),
                "comment": comment,
                "version": self.config.get("metadata", {}).get("version", "1.0.0")
            }
            
            # Yedek dosyasını oluştur
            with open(backup_path, 'w', encoding='utf-8') as dest:
                json.dump(db_content, dest, indent=2, ensure_ascii=False)
            
            logger.info(f"Yedekleme oluşturuldu: {backup_path}")
            
            # Eski yedekleri temizle
            self._clean_old_backups()
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Yedekleme oluşturulurken hata: {e}")
            raise
    
    def create_zip_backup(self, comment=None):
        """Sıkıştırılmış yedek oluştur
        
        Args:
            comment: Yedek için açıklama
            
        Returns:
            str: Oluşturulan yedek dosyasının yolu
        """
        try:
            # Zaman damgalı dosya adı oluştur
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_filename = f"backup_{timestamp}.zip"
            backup_path = self.backup_dir / backup_filename
            
            # Geçici yedek dosyası oluştur
            temp_backup = self.create_backup(comment)
            
            # Zip dosyası oluştur
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Yedek veritabanını ekle
                zipf.write(temp_backup, os.path.basename(temp_backup))
                
                # Varsa ek dosyaları ekle (örn: loglar, yapılandırma, vb.)
                config_file = Path(os.path.dirname(self.db.db_file)) / "config.json"
                if os.path.exists(config_file):
                    zipf.write(config_file, "config.json")
            
            # Geçici dosyayı sil
            os.remove(temp_backup)
            
            logger.info(f"Sıkıştırılmış yedekleme oluşturuldu: {backup_path}")
            
            # Eski yedekleri temizle
            self._clean_old_backups()
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Sıkıştırılmış yedekleme oluşturulurken hata: {e}")
            raise
    
    def restore_backup(self, backup_file):
        """Yedekten geri yükle
        
        Args:
            backup_file: Yedek dosyası yolu
            
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            backup_path = Path(backup_file)
            
            # Zip dosyası mı kontrol et
            if backup_path.suffix.lower() == ".zip":
                return self._restore_zip_backup(backup_path)
            
            # Mevcut veritabanını yedekle
            self.db.create_backup()
            
            # Yedek dosyasını yükle
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Yedek meta bilgilerini temizle
            if "_backup_info" in backup_data:
                del backup_data["_backup_info"]
            
            # Veritabanını güncelle
            with open(self.db.db_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Yedekten geri yükleme yapıldı: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Yedekten geri yükleme yapılırken hata: {e}")
            return False
    
    def _restore_zip_backup(self, zip_path):
        """Zip yedekten geri yükle
        
        Args:
            zip_path: Zip yedek dosyası yolu
            
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            # Geçici dizin oluştur
            temp_dir = self.backup_dir / "temp_restore"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Zip dosyasını geçici dizine aç
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Yedek veritabanı dosyasını bul
            backup_files = list(temp_dir.glob("backup_*.json"))
            if not backup_files:
                raise FileNotFoundError("Zip dosyasında yedek veritabanı bulunamadı")
            
            # En yeni yedek dosyasını kullan
            backup_file = sorted(backup_files)[-1]
            
            # Yedek dosyasından geri yükle
            success = self.restore_backup(backup_file)
            
            # Geçici dizini temizle
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            return success
            
        except Exception as e:
            logger.error(f"Zip yedekten geri yükleme yapılırken hata: {e}")
            # Temizlik
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            return False
    
    def list_backups(self):
        """Tüm yedekleri listele
        
        Returns:
            list: Yedek bilgileri listesi
        """
        backups = []
        
        # JSON yedekler
        json_files = sorted(self.backup_dir.glob("backup_*.json"))
        for file_path in json_files:
            try:
                # Dosya bilgilerini al
                file_stat = os.stat(file_path)
                file_time = datetime.fromtimestamp(file_stat.st_mtime)
                
                # Yedek meta bilgilerini al
                comment = None
                version = None
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if "_backup_info" in data:
                            comment = data["_backup_info"].get("comment")
                            version = data["_backup_info"].get("version")
                except:
                    pass
                
                backups.append({
                    "path": str(file_path),
                    "filename": file_path.name,
                    "date": file_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "size": file_stat.st_size,
                    "type": "json",
                    "comment": comment,
                    "version": version
                })
            except Exception as e:
                logger.warning(f"Yedek bilgisi alınırken hata: {e}")
        
        # Zip yedekler
        zip_files = sorted(self.backup_dir.glob("backup_*.zip"))
        for file_path in zip_files:
            try:
                # Dosya bilgilerini al
                file_stat = os.stat(file_path)
                file_time = datetime.fromtimestamp(file_stat.st_mtime)
                
                backups.append({
                    "path": str(file_path),
                    "filename": file_path.name,
                    "date": file_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "size": file_stat.st_size,
                    "type": "zip",
                    "comment": None,
                    "version": None
                })
            except Exception as e:
                logger.warning(f"Yedek bilgisi alınırken hata: {e}")
        
        # Yenilik sırasına göre sırala
        backups.sort(key=lambda x: x["date"], reverse=True)
        
        return backups
    
    def _clean_old_backups(self):
        """Eski yedekleri temizle
        
        Yapılandırmada belirtilen sayıdan fazla yedek varsa, en eski yedekleri siler.
        """
        try:
            if self.keep_backups <= 0:
                # Yedek temizleme devre dışı
                return
            
            # Tüm yedekleri listele
            backups = self.list_backups()
            
            # Tutulacak yedek sayısından fazla varsa
            if len(backups) > self.keep_backups:
                # Eski yedekleri sil
                for i in range(self.keep_backups, len(backups)):
                    try:
                        os.remove(backups[i]["path"])
                        logger.info(f"Eski yedek silindi: {backups[i]['filename']}")
                    except Exception as e:
                        logger.warning(f"Eski yedek silinirken hata: {e}")
                        
        except Exception as e:
            logger.error(f"Eski yedekler temizlenirken hata: {e}")
    
    def start_auto_backup(self):
        """Otomatik yedekleme izleyicisini başlat"""
        if not self.auto_backup:
            logger.info("Otomatik yedekleme devre dışı")
            return
        
        if self.auto_backup_running:
            logger.info("Otomatik yedekleme zaten çalışıyor")
            return
        
        self.auto_backup_running = True
        self.auto_backup_thread = threading.Thread(target=self._auto_backup_monitor, daemon=True)
        self.auto_backup_thread.start()
        
        logger.info(f"Otomatik yedekleme başlatıldı (interval: {self.backup_interval} saat)")
    
    def stop_auto_backup(self):
        """Otomatik yedekleme izleyicisini durdur"""
        if not self.auto_backup_running:
            return
        
        self.auto_backup_running = False
        
        # Thread'in durmasını bekle
        if self.auto_backup_thread:
            self.auto_backup_thread.join(timeout=1.0)
            self.auto_backup_thread = None
        
        logger.info("Otomatik yedekleme durduruldu")
    
    def _auto_backup_monitor(self):
        """Otomatik yedekleme izleyici fonksiyonu
        
        Bu fonksiyon bir thread olarak çalışır ve belirli aralıklarla yedekleme yapar.
        """
        while self.auto_backup_running:
            try:
                # Son yedekten beri geçen süreyi kontrol et
                now = datetime.now()
                time_diff = now - self.last_backup_time
                
                # Yedekleme zamanı gelmiş mi
                if time_diff.total_seconds() >= self.backup_interval * 3600:
                    # Yedek oluştur
                    self.create_backup("Otomatik yedekleme")
                    self.last_backup_time = now
            except Exception as e:
                logger.error(f"Otomatik yedeklemede hata: {e}")
            
            # Bir süre bekle
            time.sleep(60 * 5)  # 5 dakika
    
    def update_config(self, config):
        """Yapılandırmayı güncelle
        
        Args:
            config: Yeni yapılandırma
        """
        self.config = config
        
        # Yedekleme dizini
        backup_dir = config.get("backup_dir", "backups")
        
        # Tam yol olup olmadığını kontrol et
        if os.path.isabs(backup_dir):
            self.backup_dir = Path(backup_dir)
        else:
            # Uygulama dizinine göre yol
            app_dir = Path(os.path.dirname(os.path.abspath(self.db.db_file)))
            self.backup_dir = app_dir / backup_dir
        
        # Dizinin var olduğundan emin ol
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Otomatik yedekleme ayarları
        self.auto_backup = config.get("backup", {}).get("auto_backup", True)
        self.backup_interval = config.get("backup", {}).get("backup_interval", 24)
        self.keep_backups = config.get("backup", {}).get("keep_backups", 30)
        
        # Otomatik yedekleme durumunu güncelle
        if self.auto_backup and not self.auto_backup_running:
            self.start_auto_backup()
        elif not self.auto_backup and self.auto_backup_running:
            self.stop_auto_backup()


def backup_database(db_file, backup_dir=None, comment=None):
    """Hızlı yedekleme fonksiyonu
    
    Args:
        db_file: Veritabanı dosyası yolu
        backup_dir: Yedekleme dizini (None ise veritabanı dizininde "backups" klasörü kullanılır)
        comment: Yedek için açıklama
        
    Returns:
        str: Oluşturulan yedek dosyasının yolu
    """
    try:
        # Yedekleme dizini
        if backup_dir is None:
            backup_dir = os.path.join(os.path.dirname(db_file), "backups")
        
        # Dizinin var olduğundan emin ol
        os.makedirs(backup_dir, exist_ok=True)
        
        # Zaman damgalı dosya adı oluştur
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_filename = f"backup_{timestamp}.json"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Veritabanının bir kopyasını oluştur
        with open(db_file, 'r', encoding='utf-8') as src:
            db_content = json.load(src)
        
        # Meta bilgileri ekle
        db_content["_backup_info"] = {
            "timestamp": datetime.now().isoformat(),
            "comment": comment
        }
        
        # Yedek dosyasını oluştur
        with open(backup_path, 'w', encoding='utf-8') as dest:
            json.dump(db_content, dest, indent=2, ensure_ascii=False)
        
        logger.info(f"Hızlı yedekleme oluşturuldu: {backup_path}")
        return backup_path
        
    except Exception as e:
        logger.error(f"Hızlı yedekleme oluşturulurken hata: {e}")
        raise


def restore_database(db_file, backup_file):
    """Hızlı geri yükleme fonksiyonu
    
    Args:
        db_file: Veritabanı dosyası yolu
        backup_file: Yedek dosyası yolu
        
    Returns:
        bool: İşlem başarılı mı
    """
    try:
        # Mevcut veritabanını yedekle
        backup_before_restore = os.path.join(
            os.path.dirname(backup_file), 
            f"pre_restore_{os.path.basename(db_file)}"
        )
        shutil.copy2(db_file, backup_before_restore)
        
        # Yedek dosyasını yükle
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        # Yedek meta bilgilerini temizle
        if "_backup_info" in backup_data:
            del backup_data["_backup_info"]
        
        # Veritabanını güncelle
        with open(db_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Hızlı geri yükleme yapıldı: {backup_file}")
        return True
        
    except Exception as e:
        logger.error(f"Hızlı geri yükleme yapılırken hata: {e}")
        return False
