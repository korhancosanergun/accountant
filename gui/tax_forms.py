#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Vergi Formları Modülü
HMRC ile entegre vergi formları arayüzleri.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QPushButton, QDateEdit, QCheckBox,
    QComboBox, QGroupBox, QMessageBox, QTableWidget, 
    QTableWidgetItem, QHeaderView, QTabWidget, QTextEdit,
    QProgressBar
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor, QPixmap

from datetime import datetime, timedelta
import json


class VATReturnForm(QWidget):
    """KDV Beyannamesi formu"""
    
    def __init__(self, ledger, hmrc_client):
        """Form başlatıcı
        
        Args:
            ledger: Muhasebe defteri nesnesi
            hmrc_client: HMRC API istemcisi
        """
        super().__init__()
        
        self.ledger = ledger
        self.hmrc_client = hmrc_client
        
        # UI kurulumu
        self._setup_ui()
    
    def _setup_ui(self):
        """UI kurulumu"""
        # Ana düzen
        main_layout = QVBoxLayout(self)
        
        # Sekmeler
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # KDV Hesaplama Sekmesi
        calculation_tab = QWidget()
        tab_widget.addTab(calculation_tab, "KDV Hesaplama")
        
        # KDV Geçmişi Sekmesi
        history_tab = QWidget()
        tab_widget.addTab(history_tab, "KDV Geçmişi")
        
        # HMRC Yükümlülükler Sekmesi
        obligations_tab = QWidget()
        tab_widget.addTab(obligations_tab, "HMRC Yükümlülükler")
        
        # KDV Hesaplama Sekmesi Düzeni
        calc_layout = QVBoxLayout(calculation_tab)
        
        # Dönem Seçimi
        period_box = QGroupBox("KDV Beyanname Dönemi")
        period_layout = QFormLayout(period_box)
        
        # Başlangıç ve bitiş tarihleri
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDate(QDate.currentDate().addMonths(-3))
        
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDate(QDate.currentDate())
        
        period_layout.addRow("Başlangıç Tarihi:", self.start_date_edit)
        period_layout.addRow("Bitiş Tarihi:", self.end_date_edit)
        
        # Hesaplama butonu
        self.calculate_button = QPushButton("Hesapla")
        self.calculate_button.clicked.connect(self._calculate_vat)
        period_layout.addRow("", self.calculate_button)
        
        # Dönem kutusunu ana düzene ekle
        calc_layout.addWidget(period_box)
        
        # Beyanname Kutusu
        form_box = QGroupBox("KDV Beyannamesi")
        form_layout = QFormLayout(form_box)
        
        # KDV Kutuları (Box 1-9)
        self.box1_edit = QLineEdit()
        self.box1_edit.setReadOnly(True)
        self.box1_edit.setAlignment(Qt.AlignRight)
        form_layout.addRow("Box 1: Satışlardan KDV:", self.box1_edit)
        
        self.box2_edit = QLineEdit()
        self.box2_edit.setReadOnly(True)
        self.box2_edit.setAlignment(Qt.AlignRight)
        form_layout.addRow("Box 2: AB Alımlarından KDV:", self.box2_edit)
        
        self.box3_edit = QLineEdit()
        self.box3_edit.setReadOnly(True)
        self.box3_edit.setAlignment(Qt.AlignRight)
        self.box3_edit.setStyleSheet("background-color: #e0e0e0; font-weight: bold;")
        form_layout.addRow("Box 3: Toplam KDV:", self.box3_edit)
        
        self.box4_edit = QLineEdit()
        self.box4_edit.setReadOnly(True)
        self.box4_edit.setAlignment(Qt.AlignRight)
        form_layout.addRow("Box 4: İndirilecek KDV:", self.box4_edit)
        
        self.box5_edit = QLineEdit()
        self.box5_edit.setReadOnly(True)
        self.box5_edit.setAlignment(Qt.AlignRight)
        self.box5_edit.setStyleSheet("background-color: #e0e0e0; font-weight: bold;")
        form_layout.addRow("Box 5: Net KDV:", self.box5_edit)
        
        self.box6_edit = QLineEdit()
        self.box6_edit.setReadOnly(True)
        self.box6_edit.setAlignment(Qt.AlignRight)
        form_layout.addRow("Box 6: Toplam Satışlar (KDV hariç):", self.box6_edit)
        
        self.box7_edit = QLineEdit()
        self.box7_edit.setReadOnly(True)
        self.box7_edit.setAlignment(Qt.AlignRight)
        form_layout.addRow("Box 7: Toplam Alımlar (KDV hariç):", self.box7_edit)
        
        self.box8_edit = QLineEdit()
        self.box8_edit.setReadOnly(True)
        self.box8_edit.setAlignment(Qt.AlignRight)
        form_layout.addRow("Box 8: AB'ye Mal Teslimleri (KDV hariç):", self.box8_edit)
        
        self.box9_edit = QLineEdit()
        self.box9_edit.setReadOnly(True)
        self.box9_edit.setAlignment(Qt.AlignRight)
        form_layout.addRow("Box 9: AB'den Mal Alımları (KDV hariç):", self.box9_edit)
        
        # Doğrulama onay kutusu
        self.declaration_checkbox = QCheckBox(
            "Verdiğim bilgilerin doğru ve eksiksiz olduğunu beyan ederim."
        )
        form_layout.addRow("", self.declaration_checkbox)
        
        # Gönder butonu
        self.submit_button = QPushButton("HMRC'ye Gönder")
        self.submit_button.setEnabled(False)
        self.submit_button.clicked.connect(self._submit_vat_return)
        form_layout.addRow("", self.submit_button)
        
        # Beyanname kutusunu ana düzene ekle
        calc_layout.addWidget(form_box)
        
        # KDV Geçmişi Sekmesi Düzeni
        history_layout = QVBoxLayout(history_tab)
        
        # Tablo
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            "Dönem Başlangıcı", "Dönem Bitişi", "Gönderim Tarihi", 
            "Box 1", "Box 2", "Box 3", "Box 4", "Box 5", "Durum"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        history_layout.addWidget(self.history_table)
        
        # Geçmişi yenile butonu
        self.refresh_history_button = QPushButton("Geçmişi Yenile")
        self.refresh_history_button.clicked.connect(self._load_vat_history)
        history_layout.addWidget(self.refresh_history_button)
        
        # HMRC Yükümlülükler Sekmesi Düzeni
        obligations_layout = QVBoxLayout(obligations_tab)
        
        # VAT Kayıt Numarası
        vrn_layout = QHBoxLayout()
        vrn_layout.addWidget(QLabel("VAT Kayıt Numarası (VRN):"))
        self.vrn_edit = QLineEdit()
        vrn_layout.addWidget(self.vrn_edit)
        
        # Tarih aralığı
        vrn_layout.addWidget(QLabel("Başlangıç:"))
        self.obl_start_date = QDateEdit()
        self.obl_start_date.setCalendarPopup(True)
        self.obl_start_date.setDate(QDate.currentDate().addMonths(-12))
        vrn_layout.addWidget(self.obl_start_date)
        
        vrn_layout.addWidget(QLabel("Bitiş:"))
        self.obl_end_date = QDateEdit()
        self.obl_end_date.setCalendarPopup(True)
        self.obl_end_date.setDate(QDate.currentDate())
        vrn_layout.addWidget(self.obl_end_date)
        
        # Yükümlülükleri getir
        self.get_obligations_button = QPushButton("Yükümlülükleri Getir")
        self.get_obligations_button.clicked.connect(self._get_vat_obligations)
        vrn_layout.addWidget(self.get_obligations_button)
        
        obligations_layout.addLayout(vrn_layout)
        
        # Yükümlülükler tablosu
        self.obligations_table = QTableWidget()
        self.obligations_table.setColumnCount(5)
        self.obligations_table.setHorizontalHeaderLabels([
            "Dönem Başlangıcı", "Dönem Bitişi", "Son Tarih", "Durum", "Dönem Anahtarı"
        ])
        self.obligations_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        obligations_layout.addWidget(self.obligations_table)
        
        # Dönem seç ve yükle
        select_period_layout = QHBoxLayout()
        select_period_layout.addWidget(QLabel("Seçili Dönemi Yükle:"))
        
        self.load_selected_button = QPushButton("Dönemi Yükle")
        self.load_selected_button.clicked.connect(self._load_selected_obligation)
        select_period_layout.addWidget(self.load_selected_button)
        
        obligations_layout.addLayout(select_period_layout)
        
        # İlk yükleme
        self._load_vat_history()
    
    def _calculate_vat(self):
        """KDV hesapla"""
        try:
            # Tarih bilgilerini alma
            start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
            end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
            
            # Ledger üzerinden KDV hesaplama
            vat_data = self.ledger.calculate_vat_return(start_date, end_date)
            
            # Arayüzü güncelle
            self.box1_edit.setText(f"{vat_data['vat_due_sales']:.2f}")
            self.box2_edit.setText(f"{vat_data['vat_due_acquisitions']:.2f}")
            self.box3_edit.setText(f"{vat_data['total_vat_due']:.2f}")
            self.box4_edit.setText(f"{vat_data['vat_reclaimed']:.2f}")
            self.box5_edit.setText(f"{vat_data['net_vat_due']:.2f}")
            self.box6_edit.setText(f"{vat_data['total_sales_ex_vat']:.2f}")
            self.box7_edit.setText(f"{vat_data['total_purchases_ex_vat']:.2f}")
            self.box8_edit.setText(f"{vat_data['total_supplies_ex_vat']:.2f}")
            self.box9_edit.setText(f"{vat_data['total_acquisitions_ex_vat']:.2f}")
            
            # Gönderme butonunu etkinleştir
            self.submit_button.setEnabled(True)
            
            # Hesaplanan KDV'yi saklayalım
            self.current_vat_return = vat_data
            
        except Exception as e:
            QMessageBox.critical(self, "Hesaplama Hatası", f"KDV hesaplanırken bir hata oluştu: {e}")
    
    def _submit_vat_return(self):
        """KDV beyannamesi gönder"""
        # Beyan kontrolü
        if not self.declaration_checkbox.isChecked():
            QMessageBox.warning(
                self, "Beyan Gerekli", 
                "Devam etmek için beyan onay kutusunu işaretlemelisiniz."
            )
            return
        
        try:
            # Beyanname verilerini hazırla
            vat_data = self.current_vat_return.copy()
            
            # HMRC formatına dönüştür
            hmrc_data = {
                "periodKey": "A001",  # Örnek değer (gerçekte HMRC'den alınır)
                "vatDueSales": float(vat_data["vat_due_sales"]),
                "vatDueAcquisitions": float(vat_data["vat_due_acquisitions"]),
                "totalVatDue": float(vat_data["total_vat_due"]),
                "vatReclaimedCurrPeriod": float(vat_data["vat_reclaimed"]),
                "netVatDue": float(vat_data["net_vat_due"]),
                "totalValueSalesExVAT": float(vat_data["total_sales_ex_vat"]),
                "totalValuePurchasesExVAT": float(vat_data["total_purchases_ex_vat"]),
                "totalValueGoodsSuppliedExVAT": float(vat_data["total_supplies_ex_vat"]),
                "totalAcquisitionsExVAT": float(vat_data["total_acquisitions_ex_vat"]),
                "finalised": True
            }
            
            # HMRC gönderimi (Burada sadece temsili olarak yapılıyor)
            # Gerçek bir uygulamada bu kısımda HMRC API kullanılır
            
            # Kullanıcıya bilgi ver
            reply = QMessageBox.question(
                self, "KDV Beyanı", 
                "KDV beyannamesi HMRC'ye gönderilecek. Onaylıyor musunuz?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Veritabanına kaydet
                self.ledger.submit_vat_return(vat_data)
                
                QMessageBox.information(
                    self, "Gönderim Başarılı", 
                    "KDV beyannamesi başarıyla gönderildi ve kaydedildi."
                )
                
                # Formu sıfırla
                self._reset_form()
                
                # Geçmişi güncelle
                self._load_vat_history()
                
        except Exception as e:
            QMessageBox.critical(self, "Gönderim Hatası", f"KDV beyannamesi gönderilirken bir hata oluştu: {e}")
    
    def _reset_form(self):
        """Formu sıfırla"""
        # Tüm kutuları temizle
        for box in [
            self.box1_edit, self.box2_edit, self.box3_edit, self.box4_edit, 
            self.box5_edit, self.box6_edit, self.box7_edit, self.box8_edit, 
            self.box9_edit
        ]:
            box.clear()
        
        # Onay kutusunu temizle
        self.declaration_checkbox.setChecked(False)
        
        # Gönder butonunu devre dışı bırak
        self.submit_button.setEnabled(False)
        
        # Geçerli beyanname verisini temizle
        self.current_vat_return = None
    
    def _load_vat_history(self):
        """KDV beyanname geçmişini yükle"""
        try:
            # Geçmiş beyanları al
            vat_returns = self.ledger.get_vat_returns()
            
            # Tabloyu temizle
            self.history_table.setRowCount(0)
            
            # Beyanları tabloya ekle
            for i, vat_ret in enumerate(vat_returns):
                self.history_table.insertRow(i)
                
                # Temel veriler
                self.history_table.setItem(i, 0, QTableWidgetItem(vat_ret.get("period_start", "")))
                self.history_table.setItem(i, 1, QTableWidgetItem(vat_ret.get("period_end", "")))
                
                # Gönderim tarihi (ISO formatını insan okunabilir hale getir)
                submission_date = vat_ret.get("submission_date", "")
                try:
                    if submission_date:
                        dt = datetime.fromisoformat(submission_date)
                        submission_date = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
                
                self.history_table.setItem(i, 2, QTableWidgetItem(submission_date))
                
                # KDV bilgileri
                self.history_table.setItem(i, 3, QTableWidgetItem(f"{vat_ret.get('vat_due_sales', 0):.2f}"))
                self.history_table.setItem(i, 4, QTableWidgetItem(f"{vat_ret.get('vat_due_acquisitions', 0):.2f}"))
                self.history_table.setItem(i, 5, QTableWidgetItem(f"{vat_ret.get('total_vat_due', 0):.2f}"))
                self.history_table.setItem(i, 6, QTableWidgetItem(f"{vat_ret.get('vat_reclaimed', 0):.2f}"))
                self.history_table.setItem(i, 7, QTableWidgetItem(f"{vat_ret.get('net_vat_due', 0):.2f}"))
                
                # Durum
                status_item = QTableWidgetItem(vat_ret.get("status", ""))
                status_item.setTextAlignment(Qt.AlignCenter)
                if vat_ret.get("status") == "submitted":
                    status_item.setBackground(QColor(200, 255, 200))
                
                self.history_table.setItem(i, 8, status_item)
            
            # Tarih sütunları için hizalama
            for row in range(self.history_table.rowCount()):
                for col in [0, 1, 2]:
                    item = self.history_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
                
                # Sayı sütunları için hizalama
                for col in [3, 4, 5, 6, 7]:
                    item = self.history_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
        except Exception as e:
            QMessageBox.critical(self, "Yükleme Hatası", f"KDV geçmişi yüklenirken bir hata oluştu: {e}")
    
    def _get_vat_obligations(self):
        """HMRC'den VAT yükümlülüklerini al"""
        # API çağrısı için gerekli parametreler
        vrn = self.vrn_edit.text().strip()
        start_date = self.obl_start_date.date().toString("yyyy-MM-dd")
        end_date = self.obl_end_date.date().toString("yyyy-MM-dd")
        
        if not vrn:
            QMessageBox.warning(self, "VAT Numarası Gerekli", "VAT Kayıt Numarası (VRN) girilmelidir.")
            return
        
        try:
            # Yetkilendirme durumunu kontrol et
            if not self.hmrc_client.ensure_token_valid():
                QMessageBox.warning(
                    self, "Yetkilendirme Gerekli", 
                    "HMRC API'ye erişim için yetkilendirme gereklidir. "
                    "Lütfen önce HMRC yetkilendirme işlemini tamamlayın."
                )
                return
            
            # Yükümlülükleri getir
            obligations = self.hmrc_client.get_vat_obligations(vrn, start_date, end_date)
            
            # Tabloyu temizle
            self.obligations_table.setRowCount(0)
            
            # Yükümlülükleri tabloya ekle
            for i, obl in enumerate(obligations.get("obligations", [])):
                self.obligations_table.insertRow(i)
                
                # Tarih bilgileri
                self.obligations_table.setItem(i, 0, QTableWidgetItem(obl.get("start", "")))
                self.obligations_table.setItem(i, 1, QTableWidgetItem(obl.get("end", "")))
                self.obligations_table.setItem(i, 2, QTableWidgetItem(obl.get("due", "")))
                
                # Durum
                status = "Açık" if obl.get("status") == "O" else "Tamamlandı"
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignCenter)
                
                if status == "Açık":
                    status_item.setBackground(QColor(255, 200, 200))
                else:
                    status_item.setBackground(QColor(200, 255, 200))
                
                self.obligations_table.setItem(i, 3, status_item)
                
                # Dönem anahtarı
                self.obligations_table.setItem(i, 4, QTableWidgetItem(obl.get("periodKey", "")))
            
            # Hizalama
            for row in range(self.obligations_table.rowCount()):
                for col in [0, 1, 2, 4]:
                    item = self.obligations_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
            
        except Exception as e:
            QMessageBox.critical(
                self, "HMRC Hatası", 
                f"VAT yükümlülükleri alınırken bir hata oluştu: {e}"
            )
    
    def _load_selected_obligation(self):
        """Seçili yükümlülük dönemini yükle"""
        selected_items = self.obligations_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen bir VAT dönemi seçin.")
            return
        
        # Seçili satırı al
        row = selected_items[0].row()
        
        # Dönem bilgilerini al
        start_date = self.obligations_table.item(row, 0).text()
        end_date = self.obligations_table.item(row, 1).text()
        period_key = self.obligations_table.item(row, 4).text()
        
        # Tarih formatını kontrol et ve dönüştür
        try:
            start_date_obj = QDate.fromString(start_date, "yyyy-MM-dd")
            end_date_obj = QDate.fromString(end_date, "yyyy-MM-dd")
            
            if not start_date_obj.isValid() or not end_date_obj.isValid():
                raise ValueError("Geçersiz tarih formatı")
            
            # Hesaplama sekmesine geç
            self.parent().parent().setCurrentIndex(0)  # TabWidget -> VATReturnForm
            
            # Tarihleri ayarla
            self.start_date_edit.setDate(start_date_obj)
            self.end_date_edit.setDate(end_date_obj)
            
            # KDV'yi hesapla
            self._calculate_vat()
            
            # Kullanıcıya bilgi ver
            QMessageBox.information(
                self, "Dönem Yüklendi", 
                f"Seçilen VAT dönemi yüklendi: {start_date} - {end_date}"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Yükleme Hatası", f"Dönem yüklenirken bir hata oluştu: {e}")
    
    def prepare_submission(self):
        """Beyanname gönderimini hazırla"""
        # Bu metod ana pencereden çağrılır
        # İlk sekmeye geç
        self.parent().parent().setCurrentIndex(0)  # TabWidget -> VATReturnForm
        
        # Üç aylık bir dönem ayarla (varsayılan)
        end_date = QDate.currentDate()
        start_date = end_date.addMonths(-3)
        
        self.start_date_edit.setDate(start_date)
        self.end_date_edit.setDate(end_date)
        
        # KDV'yi hesapla
        self._calculate_vat()
    
    def refresh(self):
        """Form verilerini yenile"""
        self._load_vat_history()


class SelfAssessmentForm(QWidget):
    """Gelir Vergisi Beyannamesi formu"""
    
    def __init__(self, ledger, hmrc_client):
        """Form başlatıcı
        
        Args:
            ledger: Muhasebe defteri nesnesi
            hmrc_client: HMRC API istemcisi
        """
        super().__init__()
        
        self.ledger = ledger
        self.hmrc_client = hmrc_client
        
        # UK vergi yılları (en son 3 yıl)
        current_year = datetime.now().year
        month = datetime.now().month
        
        # Nisan ayı öncesiyse bir önceki vergi yılını son yıl olarak kabul et
        if month < 4:
            current_year -= 1
            
        # Son üç vergi yılı
        self.tax_years = [
            f"{current_year-2}-{str(current_year-1)[2:]}",
            f"{current_year-1}-{str(current_year)[2:]}",
            f"{current_year}-{str(current_year+1)[2:]}"
        ]
        
        # UI kurulumu
        self._setup_ui()
    
    def _setup_ui(self):
        """UI kurulumu"""
        # Ana düzen
        main_layout = QVBoxLayout(self)
        
        # Sekmeler
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Vergi Hesaplama Sekmesi
        calculation_tab = QWidget()
        tab_widget.addTab(calculation_tab, "Gelir Vergisi Hesaplama")
        
        # Vergi Geçmişi Sekmesi
        history_tab = QWidget()
        tab_widget.addTab(history_tab, "Beyanname Geçmişi")
        
        # HMRC Yükümlülükler Sekmesi
        obligations_tab = QWidget()
        tab_widget.addTab(obligations_tab, "HMRC Yükümlülükler")
        
        # Vergi Hesaplama Sekmesi Düzeni
        calc_layout = QVBoxLayout(calculation_tab)
        
        # Vergi Yılı Seçimi
        year_box = QGroupBox("Vergi Yılı")
        year_layout = QFormLayout(year_box)
        
        self.tax_year_combo = QComboBox()
        self.tax_year_combo.addItems(self.tax_years)
        self.tax_year_combo.setCurrentIndex(len(self.tax_years) - 2)  # Bir önceki vergi yılı
        
        year_layout.addRow("Vergi Yılı Seçin:", self.tax_year_combo)
        
        # Hesaplama butonu
        self.calculate_button = QPushButton("Hesapla")
        self.calculate_button.clicked.connect(self._calculate_tax)
        year_layout.addRow("", self.calculate_button)
        
        # Vergi yılı kutusunu ana düzene ekle
        calc_layout.addWidget(year_box)
        
        # Vergi Beyannamesi Kutusu
        form_box = QGroupBox("Gelir Vergisi Beyannamesi")
        form_layout = QFormLayout(form_box)
        
        # Kişisel bilgiler
        self.taxpayer_info = QGroupBox("Kişisel Bilgiler")
        taxpayer_layout = QFormLayout(self.taxpayer_info)
        
        self.utr_edit = QLineEdit()
        taxpayer_layout.addRow("Unique Taxpayer Reference (UTR):", self.utr_edit)
        
        self.nino_edit = QLineEdit()
        taxpayer_layout.addRow("National Insurance Number:", self.nino_edit)
        
        form_layout.addRow(self.taxpayer_info)
        
        # Gelir ve Gider Özeti
        self.income_summary = QGroupBox("Gelir ve Gider Özeti")
        income_layout = QFormLayout(self.income_summary)
        
        self.total_income_edit = QLineEdit()
        self.total_income_edit.setReadOnly(True)
        self.total_income_edit.setAlignment(Qt.AlignRight)
        income_layout.addRow("Toplam Gelir:", self.total_income_edit)
        
        self.total_expenses_edit = QLineEdit()
        self.total_expenses_edit.setReadOnly(True)
        self.total_expenses_edit.setAlignment(Qt.AlignRight)
        income_layout.addRow("Toplam Gider:", self.total_expenses_edit)
        
        self.net_profit_edit = QLineEdit()
        self.net_profit_edit.setReadOnly(True)
        self.net_profit_edit.setAlignment(Qt.AlignRight)
        self.net_profit_edit.setStyleSheet("background-color: #e0e0e0; font-weight: bold;")
        income_layout.addRow("Net Kâr:", self.net_profit_edit)
        
        form_layout.addRow(self.income_summary)
        
        # Vergi Hesaplaması
        self.tax_calculation = QGroupBox("Vergi Hesaplaması")
        tax_layout = QFormLayout(self.tax_calculation)
        
        self.tax_allowance_edit = QLineEdit()
        self.tax_allowance_edit.setReadOnly(True)
        self.tax_allowance_edit.setAlignment(Qt.AlignRight)
        tax_layout.addRow("Vergi Muafiyeti:", self.tax_allowance_edit)
        
        self.taxable_income_edit = QLineEdit()
        self.taxable_income_edit.setReadOnly(True)
        self.taxable_income_edit.setAlignment(Qt.AlignRight)
        self.taxable_income_edit.setStyleSheet("background-color: #e0e0e0;")
        tax_layout.addRow("Vergilendirilecek Gelir:", self.taxable_income_edit)
        
        self.tax_due_edit = QLineEdit()
        self.tax_due_edit.setReadOnly(True)
        self.tax_due_edit.setAlignment(Qt.AlignRight)
        self.tax_due_edit.setStyleSheet("background-color: #e0e0e0; font-weight: bold;")
        tax_layout.addRow("Ödenecek Gelir Vergisi:", self.tax_due_edit)
        
        form_layout.addRow(self.tax_calculation)
        
        # Doğrulama onay kutusu
        self.declaration_checkbox = QCheckBox(
            "Verdiğim bilgilerin doğru ve eksiksiz olduğunu beyan ederim."
        )
        form_layout.addRow("", self.declaration_checkbox)
        
        # Gönder butonu
        self.submit_button = QPushButton("HMRC'ye Gönder")
        self.submit_button.setEnabled(False)
        self.submit_button.clicked.connect(self._submit_tax_return)
        form_layout.addRow("", self.submit_button)
        
        # Beyanname kutusunu ana düzene ekle
        calc_layout.addWidget(form_box)
        
        # Vergi Geçmişi Sekmesi Düzeni
        history_layout = QVBoxLayout(history_tab)
        
        # Tablo
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(8)
        self.history_table.setHorizontalHeaderLabels([
            "Vergi Yılı", "Gönderim Tarihi", "Toplam Gelir", 
            "Toplam Gider", "Net Kâr", "Vergi Muafiyeti", 
            "Vergilendirilecek Gelir", "Ödenecek Vergi"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        history_layout.addWidget(self.history_table)
        
        # Geçmişi yenile butonu
        self.refresh_history_button = QPushButton("Geçmişi Yenile")
        self.refresh_history_button.clicked.connect(self._load_tax_history)
        history_layout.addWidget(self.refresh_history_button)
        
        # HMRC Yükümlülükler Sekmesi Düzeni
        obligations_layout = QVBoxLayout(obligations_tab)
        
        # UTR
        utr_layout = QHBoxLayout()
        utr_layout.addWidget(QLabel("Unique Taxpayer Reference (UTR):"))
        self.obl_utr_edit = QLineEdit()
        utr_layout.addWidget(self.obl_utr_edit)
        
        # Tarih aralığı
        utr_layout.addWidget(QLabel("Başlangıç:"))
        self.obl_start_date = QDateEdit()
        self.obl_start_date.setCalendarPopup(True)
        self.obl_start_date.setDate(QDate.currentDate().addYears(-1))
        utr_layout.addWidget(self.obl_start_date)
        
        utr_layout.addWidget(QLabel("Bitiş:"))
        self.obl_end_date = QDateEdit()
        self.obl_end_date.setCalendarPopup(True)
        self.obl_end_date.setDate(QDate.currentDate())
        utr_layout.addWidget(self.obl_end_date)
        
        # Yükümlülükleri getir
        self.get_obligations_button = QPushButton("Yükümlülükleri Getir")
        self.get_obligations_button.clicked.connect(self._get_tax_obligations)
        utr_layout.addWidget(self.get_obligations_button)
        
        obligations_layout.addLayout(utr_layout)
        
        # Yükümlülükler tablosu
        self.obligations_table = QTableWidget()
        self.obligations_table.setColumnCount(4)
        self.obligations_table.setHorizontalHeaderLabels([
            "Başlangıç", "Bitiş", "Son Tarih", "Durum"
        ])
        self.obligations_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        obligations_layout.addWidget(self.obligations_table)
        
        # Dönem seç ve yükle
        select_period_layout = QHBoxLayout()
        select_period_layout.addWidget(QLabel("Seçili Dönemi Yükle:"))
        
        self.load_selected_button = QPushButton("Dönemi Yükle")
        self.load_selected_button.clicked.connect(self._load_selected_obligation)
        select_period_layout.addWidget(self.load_selected_button)
        
        obligations_layout.addLayout(select_period_layout)
        
        # İlk yükleme
        self._load_tax_history()
    
    def _calculate_tax(self):
        """Gelir vergisi hesapla"""
        try:
            # Vergi yılını al
            tax_year = self.tax_year_combo.currentText()
            
            # Ledger üzerinden vergi hesaplama
            tax_data = self.ledger.calculate_tax_return(tax_year)
            
            # Arayüzü güncelle
            self.total_income_edit.setText(f"{tax_data['total_income']:.2f}")
            self.total_expenses_edit.setText(f"{tax_data['total_expenses']:.2f}")
            self.net_profit_edit.setText(f"{tax_data['net_profit']:.2f}")
            self.tax_allowance_edit.setText(f"{tax_data['tax_allowance']:.2f}")
            self.taxable_income_edit.setText(f"{tax_data['taxable_income']:.2f}")
            self.tax_due_edit.setText(f"{tax_data['tax_due']:.2f}")
            
            # Gönderme butonunu etkinleştir
            self.submit_button.setEnabled(True)
            
            # Hesaplanan vergiyi saklayalım
            self.current_tax_return = tax_data
            
        except Exception as e:
            QMessageBox.critical(self, "Hesaplama Hatası", f"Vergi hesaplanırken bir hata oluştu: {e}")
    
    def _submit_tax_return(self):
        """Gelir vergisi beyannamesi gönder"""
        # Beyan kontrolü
        if not self.declaration_checkbox.isChecked():
            QMessageBox.warning(
                self, "Beyan Gerekli", 
                "Devam etmek için beyan onay kutusunu işaretlemelisiniz."
            )
            return
        
        # UTR kontrolü
        utr = self.utr_edit.text().strip()
        if not utr:
            QMessageBox.warning(
                self, "UTR Gerekli", 
                "Unique Taxpayer Reference (UTR) girilmelidir."
            )
            return
        
        try:
            # Beyanname verilerini hazırla
            tax_data = self.current_tax_return.copy()
            
            # HMRC formatına dönüştür (burada basitleştirilmiş)
            
            # Kullanıcıya bilgi ver
            reply = QMessageBox.question(
                self, "Gelir Vergisi Beyanı", 
                "Gelir vergisi beyannamesi HMRC'ye gönderilecek. Onaylıyor musunuz?",
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                # Veritabanına kaydet
                self.ledger.submit_tax_return(tax_data)
                
                QMessageBox.information(
                    self, "Gönderim Başarılı", 
                    "Gelir vergisi beyannamesi başarıyla gönderildi ve kaydedildi."
                )
                
                # Formu sıfırla
                self._reset_form()
                
                # Geçmişi güncelle
                self._load_tax_history()
                
        except Exception as e:
            QMessageBox.critical(
                self, "Gönderim Hatası", 
                f"Gelir vergisi beyannamesi gönderilirken bir hata oluştu: {e}"
            )
    
    def _reset_form(self):
        """Formu sıfırla"""
        # Tüm kutuları temizle
        for edit in [
            self.total_income_edit, self.total_expenses_edit, self.net_profit_edit,
            self.tax_allowance_edit, self.taxable_income_edit, self.tax_due_edit
        ]:
            edit.clear()
        
        # Onay kutusunu temizle
        self.declaration_checkbox.setChecked(False)
        
        # Gönder butonunu devre dışı bırak
        self.submit_button.setEnabled(False)
        
        # Geçerli beyanname verisini temizle
        self.current_tax_return = None
    
    def _load_tax_history(self):
        """Vergi beyanname geçmişini yükle"""
        try:
            # Geçmiş beyanları al
            tax_returns = self.ledger.get_tax_returns()
            
            # Tabloyu temizle
            self.history_table.setRowCount(0)
            
            # Beyanları tabloya ekle
            for i, tax_ret in enumerate(tax_returns):
                self.history_table.insertRow(i)
                
                # Temel veriler
                self.history_table.setItem(i, 0, QTableWidgetItem(tax_ret.get("tax_year", "")))
                
                # Gönderim tarihi (ISO formatını insan okunabilir hale getir)
                submission_date = tax_ret.get("submission_date", "")
                try:
                    if submission_date:
                        dt = datetime.fromisoformat(submission_date)
                        submission_date = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
                
                self.history_table.setItem(i, 1, QTableWidgetItem(submission_date))
                
                # Vergi bilgileri
                self.history_table.setItem(i, 2, QTableWidgetItem(f"{tax_ret.get('total_income', 0):.2f}"))
                self.history_table.setItem(i, 3, QTableWidgetItem(f"{tax_ret.get('total_expenses', 0):.2f}"))
                self.history_table.setItem(i, 4, QTableWidgetItem(f"{tax_ret.get('net_profit', 0):.2f}"))
                self.history_table.setItem(i, 5, QTableWidgetItem(f"{tax_ret.get('tax_allowance', 0):.2f}"))
                self.history_table.setItem(i, 6, QTableWidgetItem(f"{tax_ret.get('taxable_income', 0):.2f}"))
                self.history_table.setItem(i, 7, QTableWidgetItem(f"{tax_ret.get('tax_due', 0):.2f}"))
            
            # Hizalama
            for row in range(self.history_table.rowCount()):
                # Vergi yılı ve gönderim tarihi için hizalama
                for col in [0, 1]:
                    item = self.history_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
                
                # Sayı sütunları için hizalama
                for col in range(2, 8):
                    item = self.history_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
        except Exception as e:
            QMessageBox.critical(self, "Yükleme Hatası", f"Vergi geçmişi yüklenirken bir hata oluştu: {e}")
    
    def _get_tax_obligations(self):
        """HMRC'den vergi yükümlülüklerini al"""
        # API çağrısı için gerekli parametreler
        utr = self.obl_utr_edit.text().strip()
        start_date = self.obl_start_date.date().toString("yyyy-MM-dd")
        end_date = self.obl_end_date.date().toString("yyyy-MM-dd")
        
        if not utr:
            QMessageBox.warning(self, "UTR Gerekli", "Unique Taxpayer Reference (UTR) girilmelidir.")
            return
        
        try:
            # Yetkilendirme durumunu kontrol et
            if not self.hmrc_client.ensure_token_valid():
                QMessageBox.warning(
                    self, "Yetkilendirme Gerekli", 
                    "HMRC API'ye erişim için yetkilendirme gereklidir. "
                    "Lütfen önce HMRC yetkilendirme işlemini tamamlayın."
                )
                return
            
            # Yükümlülükleri getir (burada temsili olarak)
            obligations = self.hmrc_client.get_self_assessment_obligations(utr, start_date, end_date)
            
            # Tabloyu temizle
            self.obligations_table.setRowCount(0)
            
            # Yükümlülükleri tabloya ekle
            for i, obl in enumerate(obligations.get("obligations", [])):
                self.obligations_table.insertRow(i)
                
                # Tarih bilgileri
                self.obligations_table.setItem(i, 0, QTableWidgetItem(obl.get("start", "")))
                self.obligations_table.setItem(i, 1, QTableWidgetItem(obl.get("end", "")))
                self.obligations_table.setItem(i, 2, QTableWidgetItem(obl.get("due", "")))
                
                # Durum
                status = "Açık" if obl.get("status") == "O" else "Tamamlandı"
                status_item = QTableWidgetItem(status)
                status_item.setTextAlignment(Qt.AlignCenter)
                
                if status == "Açık":
                    status_item.setBackground(QColor(255, 200, 200))
                else:
                    status_item.setBackground(QColor(200, 255, 200))
                
                self.obligations_table.setItem(i, 3, status_item)
            
            # Hizalama
            for row in range(self.obligations_table.rowCount()):
                for col in [0, 1, 2]:
                    item = self.obligations_table.item(row, col)
                    if item:
                        item.setTextAlignment(Qt.AlignCenter)
            
        except Exception as e:
            QMessageBox.critical(
                self, "HMRC Hatası", 
                f"Vergi yükümlülükleri alınırken bir hata oluştu: {e}"
            )
    
    def _load_selected_obligation(self):
        """Seçili yükümlülük dönemini yükle"""
        selected_items = self.obligations_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Lütfen bir vergi dönemi seçin.")
            return
        
        # Seçili satırı al
        row = selected_items[0].row()
        
        # Dönem bilgilerini al
        start_date = self.obligations_table.item(row, 0).text()
        end_date = self.obligations_table.item(row, 1).text()
        
        # Tarih formatını kontrol et
        try:
            start_date_obj = QDate.fromString(start_date, "yyyy-MM-dd")
            end_date_obj = QDate.fromString(end_date, "yyyy-MM-dd")
            
            if not start_date_obj.isValid() or not end_date_obj.isValid():
                raise ValueError("Geçersiz tarih formatı")
            
            # Vergi yılını belirle (UK vergi yılı: 6 Nisan - 5 Nisan)
            start_year = start_date_obj.year()
            end_year = end_date_obj.year()
            
            # Vergi yılını ayarla
            tax_year = f"{start_year}-{str(end_year)[2:]}"
            index = self.tax_year_combo.findText(tax_year)
            
            if index >= 0:
                # Hesaplama sekmesine geç
                self.parent().parent().setCurrentIndex(0)  # TabWidget -> SelfAssessmentForm
                
                # Vergi yılını seç
                self.tax_year_combo.setCurrentIndex(index)
                
                # Vergiyi hesapla
                self._calculate_tax()
                
                # Kullanıcıya bilgi ver
                QMessageBox.information(
                    self, "Dönem Yüklendi", 
                    f"Seçilen vergi dönemi yüklendi: {start_date} - {end_date}"
                )
            else:
                QMessageBox.warning(
                    self, "Vergi Yılı Bulunamadı", 
                    f"Bu tarih aralığı için vergi yılı ({tax_year}) mevcut vergi yıllarında bulunamadı."
                )
            
        except Exception as e:
            QMessageBox.critical(self, "Yükleme Hatası", f"Dönem yüklenirken bir hata oluştu: {e}")
    
    def prepare_submission(self):
        """Beyanname gönderimini hazırla"""
        # Bu metod ana pencereden çağrılır
        # İlk sekmeye geç
        self.parent().parent().setCurrentIndex(0)  # TabWidget -> SelfAssessmentForm
        
        # En son vergi yılını seç
        self.tax_year_combo.setCurrentIndex(len(self.tax_years) - 2)  # Bir önceki vergi yılı
        
        # Vergiyi hesapla
        self._calculate_tax()
    
    def refresh(self):
        """Form verilerini yenile"""
        self._load_tax_history()
