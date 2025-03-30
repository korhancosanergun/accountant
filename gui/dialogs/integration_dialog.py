#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Entegrasyon Arayüzü
Wise ve Stripe entegrasyonları için kullanıcı arayüzü.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QTabWidget, QWidget, QGroupBox,
    QCheckBox, QComboBox, QDateEdit, QSpinBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QFont, QColor

from datetime import datetime, timedelta
import os

class IntegrationDialog(QDialog):
    """Entegrasyon arayüzü dialog penceresi"""
    
    def __init__(self, integration_manager, parent=None):
        """Dialog başlatıcı
        
        Args:
            integration_manager: Entegrasyon yöneticisi nesnesi
            parent: Ebeveyn pencere
        """
        super().__init__(parent)
        
        self.integration_manager = integration_manager
        
        # Dialog ayarları
        self.setWindowTitle("Banka ve Ödeme Entegrasyonları")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # UI kurulumu
        self._setup_ui()
        
        # Durumu güncelle
        self._update_status()
        
        # Otomatik yenileme için timer
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._update_status)
        self.status_timer.start(10000)  # 10 saniyede bir güncelle
    
    def _setup_ui(self):
        """UI kurulumu"""
        # Ana düzen
        main_layout = QVBoxLayout(self)
        
        # Sekme penceresi
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Gösterge Paneli Sekmesi
        dashboard_tab = QWidget()
        tab_widget.addTab(dashboard_tab, "Gösterge Paneli")
        
        # Wise Sekmesi
        wise_tab = QWidget()
        tab_widget.addTab(wise_tab, "Wise Entegrasyonu")
        
        # Stripe Sekmesi
        stripe_tab = QWidget()
        tab_widget.addTab(stripe_tab, "Stripe Entegrasyonu")
        
        # Senkronizasyon Sekmesi
        sync_tab = QWidget()
        tab_widget.addTab(sync_tab, "Senkronizasyon")
        
        # Gösterge Paneli Sekmesi Düzeni
        dashboard_layout = QVBoxLayout(dashboard_tab)
        
        # Durumlar
        status_group = QGroupBox("Entegrasyon Durumları")
        status_layout = QGridLayout(status_group)
        
        # Wise durumu
        status_layout.addWidget(QLabel("Wise Entegrasyonu:"), 0, 0)
        self.wise_status_label = QLabel("Devre Dışı")
        self.wise_status_label.setStyleSheet("color: #e74c3c;")
        status_layout.addWidget(self.wise_status_label, 0, 1)
        
        # Stripe durumu
        status_layout.addWidget(QLabel("Stripe Entegrasyonu:"), 1, 0)
        self.stripe_status_label = QLabel("Devre Dışı")
        self.stripe_status_label.setStyleSheet("color: #e74c3c;")
        status_layout.addWidget(self.stripe_status_label, 1, 1)
        
        # Senkronizasyon durumu
        status_layout.addWidget(QLabel("Otomatik Senkronizasyon:"), 2, 0)
        self.sync_status_label = QLabel("Devre Dışı")
        self.sync_status_label.setStyleSheet("color: #e74c3c;")
        status_layout.addWidget(self.sync_status_label, 2, 1)
        
        # Son senkronizasyon zamanı
        status_layout.addWidget(QLabel("Son Senkronizasyon:"), 3, 0)
        self.last_sync_label = QLabel("-")
        status_layout.addWidget(self.last_sync_label, 3, 1)
        
        # Manuel senkronizasyon butonu
        sync_button = QPushButton("Şimdi Senkronize Et")
        sync_button.clicked.connect(self._run_sync_all)
        status_layout.addWidget(sync_button, 4, 0, 1, 2)
        
        dashboard_layout.addWidget(status_group)
        
        # Wise hesapları
        wise_accounts_group = QGroupBox("Wise Hesapları")
        wise_accounts_layout = QVBoxLayout(wise_accounts_group)
        
        self.wise_accounts_table = QTableWidget()
        self.wise_accounts_table.setColumnCount(3)
        self.wise_accounts_table.setHorizontalHeaderLabels([
            "Hesap", "Para Birimi", "Bakiye"
        ])
        
        self.wise_accounts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.wise_accounts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        wise_accounts_layout.addWidget(self.wise_accounts_table)
        
        dashboard_layout.addWidget(wise_accounts_group)
        
        # Stripe bakiyeleri
        stripe_balances_group = QGroupBox("Stripe Bakiyeleri")
        stripe_balances_layout = QVBoxLayout(stripe_balances_group)
        
        self.stripe_balances_table = QTableWidget()
        self.stripe_balances_table.setColumnCount(2)
        self.stripe_balances_table.setHorizontalHeaderLabels([
            "Para Birimi", "Bakiye"
        ])
        
        self.stripe_balances_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stripe_balances_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        stripe_balances_layout.addWidget(self.stripe_balances_table)
        
        dashboard_layout.addWidget(stripe_balances_group)
        
        # Wise Sekmesi Düzeni
        wise_layout = QVBoxLayout(wise_tab)
        
        # Wise API ayarları
        wise_api_group = QGroupBox("Wise API Ayarları")
        wise_api_layout = QFormLayout(wise_api_group)
        
        # API Token
        self.wise_token_edit = QLineEdit()
        self.wise_token_edit.setEchoMode(QLineEdit.Password)
        self.wise_token_edit.setPlaceholderText("Wise API token'ı girin")
        wise_api_layout.addRow("API Token:", self.wise_token_edit)
        
        # Profil ID
        self.wise_profile_edit = QLineEdit()
        self.wise_profile_edit.setPlaceholderText("Opsiyonel, otomatik algılanabilir")
        wise_api_layout.addRow("Profil ID:", self.wise_profile_edit)
        
        # Sandbox mod
        self.wise_sandbox_check = QCheckBox("Sandbox (Test) Modunu Kullan")
        wise_api_layout.addRow("", self.wise_sandbox_check)
        
        # Kaydet butonu
        wise_save_button = QPushButton("Kaydet ve Test Et")
        wise_save_button.clicked.connect(self._save_wise_settings)
        wise_api_layout.addRow("", wise_save_button)
        
        wise_layout.addWidget(wise_api_group)
        
        # Manuel senkronizasyon
        wise_sync_group = QGroupBox("Manuel Senkronizasyon")
        wise_sync_layout = QFormLayout(wise_sync_group)
        
        # Başlangıç tarihi
        self.wise_start_date = QDateEdit()
        self.wise_start_date.setCalendarPopup(True)
        self.wise_start_date.setDate(QDate.currentDate().addDays(-30))
        wise_sync_layout.addRow("Başlangıç Tarihi:", self.wise_start_date)
        
        # Bitiş tarihi
        self.wise_end_date = QDateEdit()
        self.wise_end_date.setCalendarPopup(True)
        self.wise_end_date.setDate(QDate.currentDate())
        wise_sync_layout.addRow("Bitiş Tarihi:", self.wise_end_date)
        
        # Senkronizasyon butonu
        wise_sync_button = QPushButton("Wise İşlemlerini Senkronize Et")
        wise_sync_button.clicked.connect(self._sync_wise_transactions)
        wise_sync_layout.addRow("", wise_sync_button)
        
        wise_layout.addWidget(wise_sync_group)
        
        # Stripe Sekmesi Düzeni
        stripe_layout = QVBoxLayout(stripe_tab)
        
        # Stripe API ayarları
        stripe_api_group = QGroupBox("Stripe API Ayarları")
        stripe_api_layout = QFormLayout(stripe_api_group)
        
        # API Key
        self.stripe_key_edit = QLineEdit()
        self.stripe_key_edit.setEchoMode(QLineEdit.Password)
        self.stripe_key_edit.setPlaceholderText("Stripe API anahtarını girin")
        stripe_api_layout.addRow("API Key:", self.stripe_key_edit)
        
        # Webhook Secret
        self.stripe_webhook_edit = QLineEdit()
        self.stripe_webhook_edit.setEchoMode(QLineEdit.Password)
        self.stripe_webhook_edit.setPlaceholderText("Opsiyonel, webhook kullanmak için")
        stripe_api_layout.addRow("Webhook Secret:", self.stripe_webhook_edit)
        
        # Kaydet butonu
        stripe_save_button = QPushButton("Kaydet ve Test Et")
        stripe_save_button.clicked.connect(self._save_stripe_settings)
        stripe_api_layout.addRow("", stripe_save_button)
        
        stripe_layout.addWidget(stripe_api_group)
        
        # Manuel senkronizasyon
        stripe_sync_group = QGroupBox("Manuel Senkronizasyon")
        stripe_sync_layout = QFormLayout(stripe_sync_group)
        
        # Başlangıç tarihi
        self.stripe_start_date = QDateEdit()
        self.stripe_start_date.setCalendarPopup(True)
        self.stripe_start_date.setDate(QDate.currentDate().addDays(-30))
        stripe_sync_layout.addRow("Başlangıç Tarihi:", self.stripe_start_date)
        
        # Bitiş tarihi
        self.stripe_end_date = QDateEdit()
        self.stripe_end_date.setCalendarPopup(True)
        self.stripe_end_date.setDate(QDate.currentDate())
        stripe_sync_layout.addRow("Bitiş Tarihi:", self.stripe_end_date)
        
        # İşlem limiti
        self.stripe_limit_spin = QSpinBox()
        self.stripe_limit_spin.setMinimum(10)
        self.stripe_limit_spin.setMaximum(100)
        self.stripe_limit_spin.setValue(50)
        stripe_sync_layout.addRow("Maksimum İşlem:", self.stripe_limit_spin)
        
        # Senkronizasyon butonları
        stripe_sync_layout.addRow("", QLabel(""))
        
        stripe_payments_button = QPushButton("Ödemeleri Senkronize Et")
        stripe_payments_button.clicked.connect(self._sync_stripe_payments)
        stripe_sync_layout.addRow("", stripe_payments_button)
        
        stripe_invoices_button = QPushButton("Faturaları Senkronize Et")
        stripe_invoices_button.clicked.connect(self._sync_stripe_invoices)
        stripe_sync_layout.addRow("", stripe_invoices_button)
        
        stripe_layout.addWidget(stripe_sync_group)
        
        # Senkronizasyon Sekmesi Düzeni
        sync_layout = QVBoxLayout(sync_tab)
        
        # Otomatik senkronizasyon ayarları
        auto_sync_group = QGroupBox("Otomatik Senkronizasyon Ayarları")
        auto_sync_layout = QFormLayout(auto_sync_group)
        
        # Otomatik senkronizasyon
        self.auto_sync_check = QCheckBox("Otomatik Senkronizasyonu Etkinleştir")
        auto_sync_layout.addRow("", self.auto_sync_check)
        
        # Senkronizasyon aralığı
        self.sync_interval_spin = QSpinBox()
        self.sync_interval_spin.setMinimum(1)
        self.sync_interval_spin.setMaximum(24)
        self.sync_interval_spin.setValue(6)
        auto_sync_layout.addRow("Senkronizasyon Aralığı (saat):", self.sync_interval_spin)
        
        # Kaydet butonu
        sync_save_button = QPushButton("Ayarları Kaydet")
        sync_save_button.clicked.connect(self._save_sync_settings)
        auto_sync_layout.addRow("", sync_save_button)
        
        sync_layout.addWidget(auto_sync_group)
        
        # Senkronizasyon günlüğü
        sync_log_group = QGroupBox("Senkronizasyon Günlüğü")
        sync_log_layout = QVBoxLayout(sync_log_group)
        
        self.sync_log_table = QTableWidget()
        self.sync_log_table.setColumnCount(4)
        self.sync_log_table.setHorizontalHeaderLabels([
            "Tarih", "Hizmet", "İşlem", "Durum"
        ])
        
        self.sync_log_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.sync_log_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sync_log_table.setAlternatingRowColors(True)
        
        sync_log_layout.addWidget(self.sync_log_table)
        
        sync_layout.addWidget(sync_log_group)
        
        # İlerleme çubuğu
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Mevcut ayarları yükle
        self._load_current_settings()
    
    def _load_current_settings(self):
        """Mevcut entegrasyon ayarlarını yükle"""
        # Wise ayarları
        wise_config = self.integration_manager.config.get("wise", {})
        
        # API Token'ı gösterme
        if wise_config.get("api_token"):
            self.wise_token_edit.setText("●●●●●●●●●●●●")
        
        # Profil ID
        if wise_config.get("profile_id"):
            self.wise_profile_edit.setText(wise_config.get("profile_id"))
        
        # Sandbox modu
        self.wise_sandbox_check.setChecked(wise_config.get("sandbox", False))
        
        # Stripe ayarları
        stripe_config = self.integration_manager.config.get("stripe", {})
        
        # API Key'i gösterme
        if stripe_config.get("api_key"):
            self.stripe_key_edit.setText("●●●●●●●●●●●●")
        
        # Webhook Secret
        if stripe_config.get("webhook_secret"):
            self.stripe_webhook_edit.setText("●●●●●●●●●●●●")
        
        # Senkronizasyon ayarları
        sync_config = self.integration_manager.config.get("sync_schedule", {})
        
        # Otomatik senkronizasyon
        self.auto_sync_check.setChecked(sync_config.get("enabled", False))
        
        # Senkronizasyon aralığı
        if sync_config.get("interval_hours"):
            self.sync_interval_spin.setValue(sync_config.get("interval_hours"))
    
    def _update_status(self):
        """Entegrasyon durumlarını güncelle"""
        try:
            # Entegrasyon durumlarını al
            status = self.integration_manager.get_integration_status()
            
            # Wise durumu
            if status["wise"]["enabled"]:
                self.wise_status_label.setText("Aktif")
                self.wise_status_label.setStyleSheet("color: #2ecc71;")
            else:
                self.wise_status_label.setText("Devre Dışı")
                self.wise_status_label.setStyleSheet("color: #e74c3c;")
            
            # Stripe durumu
            if status["stripe"]["enabled"]:
                self.stripe_status_label.setText("Aktif")
                self.stripe_status_label.setStyleSheet("color: #2ecc71;")
            else:
                self.stripe_status_label.setText("Devre Dışı")
                self.stripe_status_label.setStyleSheet("color: #e74c3c;")
            
            # Senkronizasyon durumu
            if status["sync_schedule"]["enabled"]:
                self.sync_status_label.setText("Aktif")
                self.sync_status_label.setStyleSheet("color: #2ecc71;")
            else:
                self.sync_status_label.setText("Devre Dışı")
                self.sync_status_label.setStyleSheet("color: #e74c3c;")
            
            # Son senkronizasyon zamanı
            last_sync = status["sync_schedule"].get("last_sync")
            if last_sync:
                try:
                    last_sync_date = datetime.fromisoformat(last_sync)
                    self.last_sync_label.setText(last_sync_date.strftime("%d.%m.%Y %H:%M"))
                except ValueError:
                    self.last_sync_label.setText(last_sync)
            else:
                self.last_sync_label.setText("-")
            
            # Wise hesaplarını güncelle
            if status["wise"]["enabled"] and "balances" in status["wise"]:
                self._update_wise_accounts_table(status["wise"]["balances"])
            
            # Stripe bakiyelerini güncelle
            if status["stripe"]["enabled"] and "balances" in status["stripe"]:
                self._update_stripe_balances_table(status["stripe"]["balances"])
            
        except Exception as e:
            print(f"Durum güncellenirken hata: {e}")
    
    def _update_wise_accounts_table(self, balances):
        """Wise hesapları tablosunu güncelle"""
        # Tabloyu temizle
        self.wise_accounts_table.setRowCount(0)
        
        # Hesapları ekle
        for i, balance in enumerate(balances):
            self.wise_accounts_table.insertRow(i)
            
            # Hesap adı (uygunsa)
            account_item = QTableWidgetItem("Wise Hesabı")
            self.wise_accounts_table.setItem(i, 0, account_item)
            
            # Para birimi
            currency_item = QTableWidgetItem(balance.get("currency", ""))
            self.wise_accounts_table.setItem(i, 1, currency_item)
            
            # Bakiye
            amount = balance.get("amount", 0)
            amount_item = QTableWidgetItem(f"{amount:.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.wise_accounts_table.setItem(i, 2, amount_item)
    
    def _update_stripe_balances_table(self, balances):
        """Stripe bakiyeleri tablosunu güncelle"""
        # Tabloyu temizle
        self.stripe_balances_table.setRowCount(0)
        
        # Bakiyeleri ekle
        for i, balance in enumerate(balances):
            self.stripe_balances_table.insertRow(i)
            
            # Para birimi
            currency_item = QTableWidgetItem(balance.get("currency", ""))
            self.stripe_balances_table.setItem(i, 0, currency_item)
            
            # Bakiye
            amount = balance.get("amount", 0)
            amount_item = QTableWidgetItem(f"{amount:.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.stripe_balances_table.setItem(i, 1, amount_item)
    
    def _save_wise_settings(self):
        """Wise API ayarlarını kaydet"""
        # İlerleme çubuğunu göster
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        
        # Ayarları al
        api_token = self.wise_token_edit.text()
        profile_id = self.wise_profile_edit.text() or None
        is_sandbox = self.wise_sandbox_check.isChecked()
        
        # Mevcut ayarı kontrol et (şifrelenmiş gösterim)
        if api_token == "●●●●●●●●●●●●":
            # Değişmemişse, mevcut ayarı kullan
            api_token = self.integration_manager.config.get("wise", {}).get("api_token", "")
        
        self.progress_bar.setValue(30)
        
        # Ayarları kaydet
        success = self.integration_manager.setup_wise(api_token, profile_id, is_sandbox)
        
        self.progress_bar.setValue(70)
        
        if success:
            # Ayarları güncelle
            self._update_status()
            QMessageBox.information(
                self, "Başarılı", 
                "Wise API ayarları başarıyla kaydedildi ve test edildi."
            )
        else:
            QMessageBox.warning(
                self, "Hata", 
                "Wise API ayarları kaydedilirken veya test edilirken bir hata oluştu."
            )
        
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
    
    def _save_stripe_settings(self):
        """Stripe API ayarlarını kaydet"""
        # İlerleme çubuğunu göster
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        
        # Ayarları al
        api_key = self.stripe_key_edit.text()
        webhook_secret = self.stripe_webhook_edit.text() or None
        
        # Mevcut ayarı kontrol et (şifrelenmiş gösterim)
        if api_key == "●●●●●●●●●●●●":
            # Değişmemişse, mevcut ayarı kullan
            api_key = self.integration_manager.config.get("stripe", {}).get("api_key", "")
        
        if webhook_secret == "●●●●●●●●●●●●":
            # Değişmemişse, mevcut ayarı kullan
            webhook_secret = self.integration_manager.config.get("stripe", {}).get("webhook_secret")
        
        self.progress_bar.setValue(30)
        
        # Ayarları kaydet
        success = self.integration_manager.setup_stripe(api_key, webhook_secret)
        
        self.progress_bar.setValue(70)
        
        if success:
            # Ayarları güncelle
            self._update_status()
            QMessageBox.information(
                self, "Başarılı", 
                "Stripe API ayarları başarıyla kaydedildi ve test edildi."
            )
        else:
            QMessageBox.warning(
                self, "Hata", 
                "Stripe API ayarları kaydedilirken veya test edilirken bir hata oluştu."
            )
        
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
    
    def _save_sync_settings(self):
        """Senkronizasyon ayarlarını kaydet"""
        # İlerleme çubuğunu göster
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(30)
        
        # Ayarları al
        enabled = self.auto_sync_check.isChecked()
        interval_hours = self.sync_interval_spin.value()
        
        # Ayarları kaydet
        success = self.integration_manager.schedule_sync(interval_hours)
        
        self.progress_bar.setValue(70)
        
        if success:
            # Ayarları güncelle
            self._update_status()
            QMessageBox.information(
                self, "Başarılı", 
                f"Otomatik senkronizasyon ayarları kaydedildi. "
                f"Senkronizasyon {interval_hours} saat aralıkla yapılacak."
            )
        else:
            QMessageBox.warning(
                self, "Hata", 
                "Senkronizasyon ayarları kaydedilirken bir hata oluştu."
            )
        
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
    
    def _run_sync_all(self):
        """Tüm entegrasyonları senkronize et"""
        # İlerleme çubuğunu göster
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(10)
        
        try:
            # Senkronizasyonu başlat
            QMessageBox.information(
                self, "Senkronizasyon", 
                "Senkronizasyon başlatıldı. Bu işlem biraz zaman alabilir."
            )
            
            # Senkronizasyonu yap
            results = self.integration_manager.sync_all()
            
            self.progress_bar.setValue(70)
            
            # Sonuçları kontrol et
            success_count = 0
            total_count = 0
            
            for service, service_results in results.items():
                for operation, result in service_results.items():
                    total_count += 1
                    if result:
                        success_count += 1
                        self._add_sync_log(service, operation, "Başarılı")
                    else:
                        self._add_sync_log(service, operation, "Başarısız")
            
            # Son senkronizasyon zamanını güncelle
            self.integration_manager.update_last_sync_time()
            
            # Durumu güncelle
            self._update_status()
            
            if success_count == total_count:
                QMessageBox.information(
                    self, "Senkronizasyon Tamamlandı", 
                    f"Tüm senkronizasyon işlemleri başarıyla tamamlandı."
                )
            else:
                QMessageBox.warning(
                    self, "Senkronizasyon Tamamlandı", 
                    f"Senkronizasyon tamamlandı, ancak bazı işlemler başarısız oldu. "
                    f"Başarılı: {success_count}/{total_count}"
                )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Senkronizasyon Hatası", 
                f"Senkronizasyon işlemi sırasında bir hata oluştu:\n{str(e)}"
            )
        finally:
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
    
    def _sync_wise_transactions(self):
        """Wise işlemlerini senkronize et"""
        # İlerleme çubuğunu göster
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(20)
        
        # Tarihleri al
        start_date = self.wise_start_date.date().toString("yyyy-MM-dd")
        end_date = self.wise_end_date.date().toString("yyyy-MM-dd")
        
        try:
            # Senkronizasyonu başlat
            QMessageBox.information(
                self, "Wise Senkronizasyonu", 
                f"Wise işlemleri senkronizasyonu başlatıldı.\n"
                f"Tarih Aralığı: {start_date} - {end_date}"
            )
            
            # Senkronizasyonu yap
            success = self.integration_manager.sync_wise_transactions(start_date, end_date)
            
            self.progress_bar.setValue(70)
            
            if success:
                self._add_sync_log("wise", "transactions", "Başarılı")
                QMessageBox.information(
                    self, "Senkronizasyon Tamamlandı", 
                    "Wise işlemleri başarıyla senkronize edildi."
                )
            else:
                self._add_sync_log("wise", "transactions", "Başarısız")
                QMessageBox.warning(
                    self, "Senkronizasyon Hatası", 
                    "Wise işlemleri senkronize edilirken bir hata oluştu."
                )
            
            # Durumu güncelle
            self._update_status()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Senkronizasyon Hatası", 
                f"Wise senkronizasyonu sırasında bir hata oluştu:\n{str(e)}"
            )
        finally:
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
    
    def _sync_stripe_payments(self):
        """Stripe ödemelerini senkronize et"""
        # İlerleme çubuğunu göster
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(20)
        
        # Tarihleri ve limiti al
        start_date = self.stripe_start_date.date().toString("yyyy-MM-dd")
        end_date = self.stripe_end_date.date().toString("yyyy-MM-dd")
        limit = self.stripe_limit_spin.value()
        
        try:
            # Senkronizasyonu başlat
            QMessageBox.information(
                self, "Stripe Senkronizasyonu", 
                f"Stripe ödemeleri senkronizasyonu başlatıldı.\n"
                f"Tarih Aralığı: {start_date} - {end_date}\n"
                f"Maksimum İşlem: {limit}"
            )
            
            # Senkronizasyonu yap
            success = self.integration_manager.sync_stripe_payments(start_date, end_date, limit)
            
            self.progress_bar.setValue(70)
            
            if success:
                self._add_sync_log("stripe", "payments", "Başarılı")
                QMessageBox.information(
                    self, "Senkronizasyon Tamamlandı", 
                    "Stripe ödemeleri başarıyla senkronize edildi."
                )
            else:
                self._add_sync_log("stripe", "payments", "Başarısız")
                QMessageBox.warning(
                    self, "Senkronizasyon Hatası", 
                    "Stripe ödemeleri senkronize edilirken bir hata oluştu."
                )
            
            # Durumu güncelle
            self._update_status()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Senkronizasyon Hatası", 
                f"Stripe senkronizasyonu sırasında bir hata oluştu:\n{str(e)}"
            )
        finally:
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
    
    def _sync_stripe_invoices(self):
        """Stripe faturalarını senkronize et"""
        # İlerleme çubuğunu göster
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(20)
        
        # Limiti al
        limit = self.stripe_limit_spin.value()
        
        try:
            # Senkronizasyonu başlat
            QMessageBox.information(
                self, "Stripe Senkronizasyonu", 
                f"Stripe faturaları senkronizasyonu başlatıldı.\n"
                f"Maksimum Fatura: {limit}"
            )
            
            # Senkronizasyonu yap
            success = self.integration_manager.sync_stripe_invoices(limit)
            
            self.progress_bar.setValue(70)
            
            if success:
                self._add_sync_log("stripe", "invoices", "Başarılı")
                QMessageBox.information(
                    self, "Senkronizasyon Tamamlandı", 
                    "Stripe faturaları başarıyla senkronize edildi."
                )
            else:
                self._add_sync_log("stripe", "invoices", "Başarısız")
                QMessageBox.warning(
                    self, "Senkronizasyon Hatası", 
                    "Stripe faturaları senkronize edilirken bir hata oluştu."
                )
            
            # Durumu güncelle
            self._update_status()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Senkronizasyon Hatası", 
                f"Stripe senkronizasyonu sırasında bir hata oluştu:\n{str(e)}"
            )
        finally:
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
    
    def _add_sync_log(self, service, operation, status):
        """Senkronizasyon günlüğüne kayıt ekle"""
        # Günlük tarihini oluştur
        now = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        # Günlüğü tabloya ekle
        row = self.sync_log_table.rowCount()
        self.sync_log_table.insertRow(row)
        
        # Tarih
        date_item = QTableWidgetItem(now)
        self.sync_log_table.setItem(row, 0, date_item)
        
        # Hizmet
        service_item = QTableWidgetItem(service.title())
        self.sync_log_table.setItem(row, 1, service_item)
        
        # İşlem
        operation_map = {
            "accounts": "Hesaplar",
            "transactions": "İşlemler",
            "balance": "Bakiye",
            "payments": "Ödemeler",
            "invoices": "Faturalar"
        }
        operation_text = operation_map.get(operation, operation)
        operation_item = QTableWidgetItem(operation_text)
        self.sync_log_table.setItem(row, 2, operation_item)
        
        # Durum
        status_item = QTableWidgetItem(status)
        
        # Duruma göre renklendirme
        if status == "Başarılı":
            status_item.setForeground(QColor(46, 204, 113))  # Yeşil
        else:
            status_item.setForeground(QColor(231, 76, 60))  # Kırmızı
            
        self.sync_log_table.setItem(row, 3, status_item)
        
        # Son eklenen satıra kaydır
        self.sync_log_table.scrollToBottom()
    
    def closeEvent(self, event):
        """Dialog kapatılırken yapılacak işlemler"""
        # Timer'ı durdur
        self.status_timer.stop()
        event.accept()