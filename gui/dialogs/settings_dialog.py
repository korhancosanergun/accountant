#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Ayarlar Dialog
Uygulama ve şirket ayarlarını düzenleme arayüzü.
"""


from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QFormLayout, QLabel, QLineEdit, QPushButton, QComboBox, 
    QCheckBox, QFileDialog, QMessageBox, QGroupBox, 
    QTextEdit, QDialogButtonBox, QSpinBox, QFrame
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

import json
import os
import copy


class SettingsDialog(QDialog):
    """Ayarlar dialog penceresi"""
    
    def __init__(self, config, new_company=False, parent=None):
        """Dialog başlatıcı
        
        Args:
            config: Mevcut yapılandırma
            new_company: Yeni şirket oluşturuluyor mu
            parent: Ebeveyn pencere
        """
        super().__init__(parent)
        
        self.config = copy.deepcopy(config)  # Orijinal yapılandırmayı değiştirmemek için kopya
        self.new_company = new_company
        
        # Dialog ayarları
        self.setWindowTitle("Ayarlar")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        # UI kurulumu
        self._setup_ui()
        
        # Yapılandırma verilerini yükle
        self._load_config()
    
    def _setup_ui(self):
        """UI kurulumu"""
        # Ana düzen
        main_layout = QVBoxLayout(self)
        
        # Sekme penceresi
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # Şirket Bilgileri Sekmesi
        company_tab = QWidget()
        self.tab_widget.addTab(company_tab, "Şirket Bilgileri")
        
        # HMRC API Sekmesi
        hmrc_tab = QWidget()
        self.tab_widget.addTab(hmrc_tab, "HMRC API")
        
        # Genel Ayarlar Sekmesi
        general_tab = QWidget()
        self.tab_widget.addTab(general_tab, "Genel Ayarlar")
        
        # Yedekleme Sekmesi
        backup_tab = QWidget()
        self.tab_widget.addTab(backup_tab, "Yedekleme")
        
        # Şirket Bilgileri Sekmesi Düzeni
        company_layout = QVBoxLayout(company_tab)
        
        # Temel Şirket Bilgileri
        basic_group = QGroupBox("Temel Şirket Bilgileri")
        basic_layout = QFormLayout(basic_group)
        
        # Şirket adı
        self.company_name_edit = QLineEdit()
        basic_layout.addRow("Şirket Adı:", self.company_name_edit)
        
        # VAT numarası
        self.company_vat_edit = QLineEdit()
        basic_layout.addRow("VAT Numarası:", self.company_vat_edit)
        
        # UTR numarası
        self.company_utr_edit = QLineEdit()
        basic_layout.addRow("UTR Numarası:", self.company_utr_edit)
        
        # Şirket adresi
        self.company_address_edit = QTextEdit()
        self.company_address_edit.setMaximumHeight(80)
        basic_layout.addRow("Şirket Adresi:", self.company_address_edit)
        
        # Telefon
        self.company_phone_edit = QLineEdit()
        basic_layout.addRow("Telefon:", self.company_phone_edit)
        
        # E-posta
        self.company_email_edit = QLineEdit()
        basic_layout.addRow("E-posta:", self.company_email_edit)
        
        # Web sitesi
        self.company_website_edit = QLineEdit()
        basic_layout.addRow("Web Sitesi:", self.company_website_edit)
        
        company_layout.addWidget(basic_group)
        
        # Vergi Bilgileri
        tax_group = QGroupBox("Vergi Bilgileri")
        tax_layout = QFormLayout(tax_group)
        
        # Vergi yılı başlangıcı
        self.tax_year_start_edit = QLineEdit()
        self.tax_year_start_edit.setPlaceholderText("MM-DD (örn: 04-06)")
        tax_layout.addRow("Vergi Yılı Başlangıcı:", self.tax_year_start_edit)
        
        # Şirket faaliyeti
        self.company_activity_edit = QLineEdit()
        tax_layout.addRow("Şirket Faaliyeti:", self.company_activity_edit)
        
        # VAT kayıtlı mı
        self.vat_registered_checkbox = QCheckBox("VAT Kayıtlı")
        tax_layout.addRow("", self.vat_registered_checkbox)
        
        # VAT kayıt tarihi
        self.vat_registration_date_edit = QLineEdit()
        self.vat_registration_date_edit.setPlaceholderText("YYYY-MM-DD")
        tax_layout.addRow("VAT Kayıt Tarihi:", self.vat_registration_date_edit)
        
        company_layout.addWidget(tax_group)
        
        # Banka Bilgileri
        bank_group = QGroupBox("Banka Bilgileri")
        bank_layout = QFormLayout(bank_group)
        
        # Banka adı
        self.bank_name_edit = QLineEdit()
        bank_layout.addRow("Banka Adı:", self.bank_name_edit)
        
        # Hesap adı
        self.bank_account_name_edit = QLineEdit()
        bank_layout.addRow("Hesap Adı:", self.bank_account_name_edit)
        
        # Hesap numarası
        self.bank_account_number_edit = QLineEdit()
        bank_layout.addRow("Hesap Numarası:", self.bank_account_number_edit)
        
        # Sort kodu
        self.bank_sort_code_edit = QLineEdit()
        bank_layout.addRow("Sort Kodu:", self.bank_sort_code_edit)
        
        company_layout.addWidget(bank_group)
        
        # HMRC API Sekmesi Düzeni
        hmrc_layout = QVBoxLayout(hmrc_tab)
        
        # API Ayarları
        api_group = QGroupBox("HMRC API Ayarları")
        api_layout = QFormLayout(api_group)
        
        # Client ID
        self.api_client_id_edit = QLineEdit()
        api_layout.addRow("Client ID:", self.api_client_id_edit)
        
        # Client Secret
        self.api_client_secret_edit = QLineEdit()
        api_layout.addRow("Client Secret:", self.api_client_secret_edit)
        
        # API Ortamı
        self.api_environment_combo = QComboBox()
        self.api_environment_combo.addItems(["Test Ortamı", "Üretim Ortamı"])
        self.api_environment_combo.currentIndexChanged.connect(self._update_api_endpoint)
        api_layout.addRow("API Ortamı:", self.api_environment_combo)
        
        # API Endpoint
        self.api_endpoint_edit = QLineEdit()
        self.api_endpoint_edit.setReadOnly(True)
        api_layout.addRow("API Endpoint:", self.api_endpoint_edit)
        
        # Yönlendirme URI'si
        self.api_redirect_uri_edit = QLineEdit()
        api_layout.addRow("Redirect URI:", self.api_redirect_uri_edit)
        
        hmrc_layout.addWidget(api_group)
        
        # API Bilgi
        info_group = QGroupBox("HMRC API Bilgileri")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel(
            "HMRC API kullanımı için Making Tax Digital (MTD) portalından "
            "uygulama kaydı yapmanız gerekmektedir. Test ortamı için Sandbox "
            "hesabı oluşturabilirsiniz. Daha fazla bilgi için HMRC Developer Hub'ı ziyaret edin."
        )
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        
        # HMRC Developer Hub linki
        link_layout = QHBoxLayout()
        link_layout.addWidget(QLabel("HMRC Developer Hub:"))
        
        hmrc_link = QLabel('<a href="https://developer.service.hmrc.gov.uk/">developer.service.hmrc.gov.uk</a>')
        hmrc_link.setOpenExternalLinks(True)
        link_layout.addWidget(hmrc_link)
        link_layout.addStretch()
        
        info_layout.addLayout(link_layout)
        
        hmrc_layout.addWidget(info_group)
        hmrc_layout.addStretch()
        
        # Genel Ayarlar Sekmesi Düzeni
        general_layout = QVBoxLayout(general_tab)
        
        # Arayüz Ayarları
        ui_group = QGroupBox("Arayüz Ayarları")
        ui_layout = QFormLayout(ui_group)
        
        # Dil seçimi
        self.language_combo = QComboBox()
        self.language_combo.addItems(["Türkçe", "İngilizce"])
        ui_layout.addRow("Dil:", self.language_combo)
        
        # Tema seçimi
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Açık", "Koyu", "Sistem"])
        ui_layout.addRow("Tema:", self.theme_combo)
        
        general_layout.addWidget(ui_group)
        
        # Para Birimi Ayarları
        currency_group = QGroupBox("Para Birimi Ayarları")
        currency_layout = QFormLayout(currency_group)
        
        # Para birimi
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["GBP (£)", "EUR (€)", "USD ($)"])
        currency_layout.addRow("Para Birimi:", self.currency_combo)
        
        # Ondalık ayırıcı
        self.decimal_separator_combo = QComboBox()
        self.decimal_separator_combo.addItems(["Nokta (.)", "Virgül (,)"])
        currency_layout.addRow("Ondalık Ayırıcı:", self.decimal_separator_combo)
        
        # Binlik ayırıcı
        self.thousands_separator_combo = QComboBox()
        self.thousands_separator_combo.addItems(["Virgül (,)", "Nokta (.)", "Boşluk ( )", "Hiçbiri"])
        currency_layout.addRow("Binlik Ayırıcı:", self.thousands_separator_combo)
        
        general_layout.addWidget(currency_group)
        
        # Diğer Ayarlar
        other_group = QGroupBox("Diğer Ayarlar")
        other_layout = QFormLayout(other_group)
        
        # Log seviyesi
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        other_layout.addRow("Log Seviyesi:", self.log_level_combo)
        
        general_layout.addWidget(other_group)
        general_layout.addStretch()
        
        # Yedekleme Sekmesi Düzeni
        backup_layout = QVBoxLayout(backup_tab)
        
        # Otomatik Yedekleme
        auto_backup_group = QGroupBox("Otomatik Yedekleme")
        auto_backup_layout = QFormLayout(auto_backup_group)
        
        # Otomatik yedekleme yapılsın mı
        self.auto_backup_checkbox = QCheckBox("Otomatik Yedekleme Yap")
        auto_backup_layout.addRow("", self.auto_backup_checkbox)
        
        # Yedekleme aralığı
        self.backup_interval_spin = QSpinBox()
        self.backup_interval_spin.setMinimum(1)
        self.backup_interval_spin.setMaximum(168)  # 1 hafta (saat cinsinden)
        auto_backup_layout.addRow("Yedekleme Aralığı (saat):", self.backup_interval_spin)
        
        # Tutulacak yedek sayısı
        self.keep_backups_spin = QSpinBox()
        self.keep_backups_spin.setMinimum(1)
        self.keep_backups_spin.setMaximum(100)
        auto_backup_layout.addRow("Tutulacak Yedek Sayısı:", self.keep_backups_spin)
        
        backup_layout.addWidget(auto_backup_group)
        
        # Manuel Yedekleme
        manual_backup_group = QGroupBox("Manuel Yedekleme")
        manual_backup_layout = QFormLayout(manual_backup_group)
        
        # Yedekleme dizini
        backup_path_layout = QHBoxLayout()
        self.backup_path_edit = QLineEdit()
        self.backup_path_edit.setReadOnly(True)
        backup_path_layout.addWidget(self.backup_path_edit)
        
        self.browse_backup_button = QPushButton("Gözat...")
        self.browse_backup_button.clicked.connect(self._browse_backup_directory)
        backup_path_layout.addWidget(self.browse_backup_button)
        
        manual_backup_layout.addRow("Yedekleme Dizini:", backup_path_layout)
        
        # Yedek oluştur butonu
        self.create_backup_button = QPushButton("Şimdi Yedek Oluştur")
        self.create_backup_button.clicked.connect(self._create_backup_now)
        manual_backup_layout.addRow("", self.create_backup_button)
        
        backup_layout.addWidget(manual_backup_group)
        backup_layout.addStretch()
        
        # Dialog butonları
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        main_layout.addWidget(button_box)
        
        # Yeni şirket oluşturuluyorsa, ilk sekmeye odaklan
        if self.new_company:
            self.tab_widget.setCurrentIndex(0)
    
    def _update_api_endpoint(self):
        """API ortamı değiştiğinde endpoint'i güncelle"""
        if self.api_environment_combo.currentIndex() == 0:
            # Test ortamı
            self.api_endpoint_edit.setText("https://test.api.service.hmrc.gov.uk/")
        else:
            # Üretim ortamı
            self.api_endpoint_edit.setText("https://api.service.hmrc.gov.uk/")
    
    def _browse_backup_directory(self):
        """Yedekleme dizini seç"""
        directory = QFileDialog.getExistingDirectory(
            self, "Yedekleme Dizini Seç", 
            self.backup_path_edit.text() or os.path.expanduser("~")
        )
        
        if directory:
            self.backup_path_edit.setText(directory)
    
    def _create_backup_now(self):
        """Manuel yedek oluştur"""
        # Bu metod sadece bilgi verir, gerçek yedekleme ana pencereden yapılmalıdır
        QMessageBox.information(
            self, "Yedekleme", 
            "Yedekleme işlemi için önce ayarları kaydedin, ardından ana pencereden "
            "'Dosya > Yedekle' menüsünü kullanabilirsiniz."
        )
    
    def _load_config(self):
        """Yapılandırma verilerini forma yükle"""
        # Şirket Bilgileri
        self.company_name_edit.setText(self.config.get("company_name", ""))
        self.company_vat_edit.setText(self.config.get("company_vat", ""))
        
        # Vergi bilgileri
        self.tax_year_start_edit.setText(self.config.get("tax_year_start", "04-06"))
        
        # Şirket bilgileri alanlarını doldur (company_info içindekiler)
        company_info = self.config.get("company_info", {})
        self.company_utr_edit.setText(company_info.get("utr", ""))
        self.company_address_edit.setText(company_info.get("address", ""))
        self.company_phone_edit.setText(company_info.get("phone", ""))
        self.company_email_edit.setText(company_info.get("email", ""))
        self.company_website_edit.setText(company_info.get("website", ""))
        self.company_activity_edit.setText(company_info.get("activity", ""))
        self.vat_registered_checkbox.setChecked(company_info.get("vat_registered", False))
        self.vat_registration_date_edit.setText(company_info.get("vat_registration_date", ""))
        
        # Banka bilgileri
        bank_info = company_info.get("bank", {})
        self.bank_name_edit.setText(bank_info.get("name", ""))
        self.bank_account_name_edit.setText(bank_info.get("account_name", ""))
        self.bank_account_number_edit.setText(bank_info.get("account_number", ""))
        self.bank_sort_code_edit.setText(bank_info.get("sort_code", ""))
        
        # HMRC API ayarları
        hmrc_api = self.config.get("hmrc_api", {})
        self.api_client_id_edit.setText(hmrc_api.get("client_id", ""))
        self.api_client_secret_edit.setText(hmrc_api.get("client_secret", ""))
        
        # API ortamı
        endpoint = hmrc_api.get("endpoint", "https://test.api.service.hmrc.gov.uk/")
        self.api_environment_combo.setCurrentIndex(0 if "test" in endpoint else 1)
        self.api_endpoint_edit.setText(endpoint)
        
        self.api_redirect_uri_edit.setText(hmrc_api.get("redirect_uri", "http://localhost:8080/callback"))
        
        # Genel ayarlar
        # Dil
        language = self.config.get("language", "tr")
        self.language_combo.setCurrentIndex(0 if language == "tr" else 1)
        
        # Tema
        theme = self.config.get("theme", "light")
        theme_index = {"light": 0, "dark": 1, "system": 2}.get(theme, 0)
        self.theme_combo.setCurrentIndex(theme_index)
        
        # Para birimi
        currency = self.config.get("currency", "GBP")
        currency_index = {"GBP": 0, "EUR": 1, "USD": 2}.get(currency, 0)
        self.currency_combo.setCurrentIndex(currency_index)
        
        # Ayırıcılar
        decimal_separator = self.config.get("decimal_separator", ".")
        self.decimal_separator_combo.setCurrentIndex(0 if decimal_separator == "." else 1)
        
        thousands_separator = self.config.get("thousands_separator", ",")
        thousands_index = {",": 0, ".": 1, " ": 2, "": 3}.get(thousands_separator, 0)
        self.thousands_separator_combo.setCurrentIndex(thousands_index)
        
        # Log seviyesi
        log_level = self.config.get("log_level", "INFO")
        log_level_index = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3, "CRITICAL": 4}.get(log_level, 1)
        self.log_level_combo.setCurrentIndex(log_level_index)
        
        # Yedekleme ayarları
        backup = self.config.get("backup", {})
        self.auto_backup_checkbox.setChecked(backup.get("auto_backup", True))
        self.backup_interval_spin.setValue(backup.get("backup_interval", 24))
        self.keep_backups_spin.setValue(backup.get("keep_backups", 30))
        
        # Yedekleme dizini
        backup_dir = self.config.get("backup_dir", "")
        self.backup_path_edit.setText(backup_dir)
    
    def get_updated_config(self):
        """Güncellenmiş yapılandırma verilerini döndür"""
        # Şirket bilgilerini güncelle
        self.config["company_name"] = self.company_name_edit.text()
        self.config["company_vat"] = self.company_vat_edit.text()
        self.config["tax_year_start"] = self.tax_year_start_edit.text()
        
        # Detaylı şirket bilgileri
        company_info = self.config.get("company_info", {})
        company_info.update({
            "utr": self.company_utr_edit.text(),
            "address": self.company_address_edit.toPlainText(),
            "phone": self.company_phone_edit.text(),
            "email": self.company_email_edit.text(),
            "website": self.company_website_edit.text(),
            "activity": self.company_activity_edit.text(),
            "vat_registered": self.vat_registered_checkbox.isChecked(),
            "vat_registration_date": self.vat_registration_date_edit.text()
        })
        
        # Banka bilgileri
        bank_info = {
            "name": self.bank_name_edit.text(),
            "account_name": self.bank_account_name_edit.text(),
            "account_number": self.bank_account_number_edit.text(),
            "sort_code": self.bank_sort_code_edit.text()
        }
        company_info["bank"] = bank_info
        
        self.config["company_info"] = company_info
        
        # HMRC API ayarları
        hmrc_api = {
            "client_id": self.api_client_id_edit.text(),
            "client_secret": self.api_client_secret_edit.text(),
            "endpoint": self.api_endpoint_edit.text(),
            "redirect_uri": self.api_redirect_uri_edit.text()
        }
        self.config["hmrc_api"] = hmrc_api
        
        # Genel ayarlar
        # Dil
        self.config["language"] = "tr" if self.language_combo.currentIndex() == 0 else "en"
        
        # Tema
        theme_map = {0: "light", 1: "dark", 2: "system"}
        self.config["theme"] = theme_map.get(self.theme_combo.currentIndex(), "light")
        
        # Para birimi
        currency_map = {0: "GBP", 1: "EUR", 2: "USD"}
        self.config["currency"] = currency_map.get(self.currency_combo.currentIndex(), "GBP")
        
        # Ayırıcılar
        self.config["decimal_separator"] = "." if self.decimal_separator_combo.currentIndex() == 0 else ","
        
        thousands_map = {0: ",", 1: ".", 2: " ", 3: ""}
        self.config["thousands_separator"] = thousands_map.get(self.thousands_separator_combo.currentIndex(), ",")
        
        # Log seviyesi
        log_level_map = {0: "DEBUG", 1: "INFO", 2: "WARNING", 3: "ERROR", 4: "CRITICAL"}
        self.config["log_level"] = log_level_map.get(self.log_level_combo.currentIndex(), "INFO")
        
        # Yedekleme ayarları
        backup = {
            "auto_backup": self.auto_backup_checkbox.isChecked(),
            "backup_interval": self.backup_interval_spin.value(),
            "keep_backups": self.keep_backups_spin.value()
        }
        self.config["backup"] = backup
        
        # Yedekleme dizini
        self.config["backup_dir"] = self.backup_path_edit.text()
        
        return self.config
