#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Gider Dialog
Gider ekleme/düzenleme için dialog penceresi.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QPushButton, QDateEdit, QComboBox,
    QDialogButtonBox, QGroupBox, QCheckBox, QDoubleSpinBox,
    QRadioButton, QButtonGroup, QFileDialog
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont

from datetime import datetime
import uuid
import os


class ExpenseDialog(QDialog):
    """Gider ekleme/düzenleme dialog penceresi"""
    
    def __init__(self, ledger, expense=None, parent=None):
        """Dialog başlatıcı
        
        Args:
            ledger: Muhasebe defteri nesnesi
            expense: Düzenlenecek gider (yeni gider için None)
            parent: Ebeveyn pencere
        """
        super().__init__(parent)
        
        self.ledger = ledger
        self.expense = expense
        self.receipt_file = None
        
        # Dialog ayarları
        self.setWindowTitle("Gider Ekle" if not expense else "Gider Düzenle")
        self.setMinimumWidth(500)
        
        # UI kurulumu
        self._setup_ui()
        
        # Gider düzenlemesi ise verileri doldur
        if self.expense:
            self._fill_expense_data()
    
    def _setup_ui(self):
        """UI kurulumu"""
        # Ana düzen
        main_layout = QVBoxLayout(self)
        
        # Temel bilgiler grubu
        basic_group = QGroupBox("Temel Bilgiler")
        basic_layout = QFormLayout(basic_group)
        
        # Tarih
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        basic_layout.addRow("Tarih:", self.date_edit)
        
        # Kategori
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Ofis Giderleri", "Seyahat ve Konaklama", "Pazarlama ve Reklam", 
            "Kira", "Faturalar", "Yazılım ve Abonelikler", "Profesyonel Hizmetler",
            "Maaşlar", "Banka ve Finansman Giderleri", "Diğer"
        ])
        basic_layout.addRow("Kategori:", self.category_combo)
        
        # Açıklama
        self.description_edit = QLineEdit()
        basic_layout.addRow("Açıklama:", self.description_edit)
        
        # Tedarikçi
        self.supplier_edit = QLineEdit()
        basic_layout.addRow("Tedarikçi:", self.supplier_edit)
        
        main_layout.addWidget(basic_group)
        
        # Ödeme bilgileri grubu
        payment_group = QGroupBox("Ödeme Bilgileri")
        payment_layout = QFormLayout(payment_group)
        
        # Tutar
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setDecimals(2)
        self.amount_spin.setMinimum(0)
        self.amount_spin.setMaximum(999999.99)
        self.amount_spin.setValue(0)
        self.amount_spin.valueChanged.connect(self._update_vat)
        payment_layout.addRow("Tutar:", self.amount_spin)
        
        # KDV oranı
        self.vat_rate_combo = QComboBox()
        self.vat_rate_combo.addItem("Standart Oran (%20)", 20)
        self.vat_rate_combo.addItem("İndirilmiş Oran (%5)", 5)
        self.vat_rate_combo.addItem("Sıfır Oran (%0)", 0)
        self.vat_rate_combo.currentIndexChanged.connect(self._update_vat)
        payment_layout.addRow("KDV Oranı:", self.vat_rate_combo)
        
        # KDV tutarı
        self.vat_amount_spin = QDoubleSpinBox()
        self.vat_amount_spin.setDecimals(2)
        self.vat_amount_spin.setMinimum(0)
        self.vat_amount_spin.setMaximum(999999.99)
        self.vat_amount_spin.setValue(0)
        payment_layout.addRow("KDV Tutarı:", self.vat_amount_spin)
        
        # Toplam tutar
        self.total_label = QLabel("0.00")
        self.total_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        payment_layout.addRow("Toplam:", self.total_label)
        
        # Ödeme yöntemi
        self.payment_method_combo = QComboBox()
        self.payment_method_combo.addItems(["Nakit", "Banka", "Kredi Kartı", "Diğer"])
        payment_layout.addRow("Ödeme Yöntemi:", self.payment_method_combo)
        
        # Fiş/Fatura no
        self.receipt_number_edit = QLineEdit()
        self.receipt_number_edit.setPlaceholderText("Otomatik oluşturulacak")
        payment_layout.addRow("Fiş/Fatura No:", self.receipt_number_edit)
        
        # Fiş/Fatura durumu
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Ödenmiş", "Ödenmemiş"])
        payment_layout.addRow("Durum:", self.status_combo)
        
        main_layout.addWidget(payment_group)
        
        # Vergi bilgileri grubu
        tax_group = QGroupBox("Vergi Bilgileri")
        tax_layout = QFormLayout(tax_group)
        
        # KDV'den düşülebilir
        self.vat_deductible_checkbox = QCheckBox("KDV indirilecek")
        self.vat_deductible_checkbox.setChecked(True)
        tax_layout.addRow("", self.vat_deductible_checkbox)
        
        # Gelir vergisinden düşülebilir
        self.tax_deductible_checkbox = QCheckBox("Gelir vergisinden düşülebilir")
        self.tax_deductible_checkbox.setChecked(True)
        tax_layout.addRow("", self.tax_deductible_checkbox)
        
        # Otomatik muhasebeleştirme
        self.auto_post_checkbox = QCheckBox("Otomatik Muhasebeleştir")
        self.auto_post_checkbox.setChecked(True)
        tax_layout.addRow("", self.auto_post_checkbox)
        
        main_layout.addWidget(tax_group)
        
        # Fiş/Fatura dosyası grubu
        receipt_group = QGroupBox("Fiş/Fatura Dosyası")
        receipt_layout = QHBoxLayout(receipt_group)
        
        # Seçili dosya etiketi
        self.receipt_file_label = QLabel("Seçili dosya: Yok")
        receipt_layout.addWidget(self.receipt_file_label)
        
        # Dosya seç butonu
        self.select_file_button = QPushButton("Dosya Seç")
        self.select_file_button.clicked.connect(self._select_receipt_file)
        receipt_layout.addWidget(self.select_file_button)
        
        main_layout.addWidget(receipt_group)
        
        # Notlar
        notes_group = QGroupBox("Notlar")
        notes_layout = QVBoxLayout(notes_group)
        
        self.notes_edit = QLineEdit()
        notes_layout.addWidget(self.notes_edit)
        
        main_layout.addWidget(notes_group)
        
        # Dialog butonları
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        main_layout.addWidget(button_box)
    
    def _update_vat(self):
        """KDV tutarını güncelle"""
        amount = self.amount_spin.value()
        vat_rate = self.vat_rate_combo.currentData()
        
        # KDV hesapla
        vat_amount = amount * (vat_rate / 100)
        self.vat_amount_spin.setValue(vat_amount)
        
        # Toplam hesapla
        total = amount + vat_amount
        self.total_label.setText(f"{total:.2f}")
    
    def _select_receipt_file(self):
        """Fiş/Fatura dosyası seç"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Fiş/Fatura Dosyası Seç", "", 
            "Tüm Dosyalar (*);;PDF Dosyaları (*.pdf);;Resim Dosyaları (*.jpg *.jpeg *.png)"
        )
        
        if file_path:
            self.receipt_file = file_path
            self.receipt_file_label.setText(f"Seçili dosya: {os.path.basename(file_path)}")
    
    def _fill_expense_data(self):
        """Düzenlenen gider verilerini forma doldur"""
        # Temel bilgiler
        try:
            date = QDate.fromString(self.expense["date"], "yyyy-MM-dd")
            if date.isValid():
                self.date_edit.setDate(date)
        except KeyError:
            pass
        
        # Kategori
        category_map = {
            "office": "Ofis Giderleri",
            "travel": "Seyahat ve Konaklama",
            "marketing": "Pazarlama ve Reklam",
            "rent": "Kira",
            "utilities": "Faturalar",
            "software": "Yazılım ve Abonelikler",
            "professional": "Profesyonel Hizmetler",
            "salary": "Maaşlar",
            "bank": "Banka ve Finansman Giderleri",
            "other": "Diğer"
        }
        
        category = category_map.get(self.expense.get("category"), "Diğer")
        index = self.category_combo.findText(category)
        if index >= 0:
            self.category_combo.setCurrentIndex(index)
        
        # Açıklama
        self.description_edit.setText(self.expense.get("description", ""))
        
        # Tedarikçi
        self.supplier_edit.setText(self.expense.get("supplier", ""))
        
        # Tutar
        self.amount_spin.setValue(self.expense.get("amount", 0))
        
        # KDV oranı
        vat_rate = self.expense.get("vat_rate", 20)
        index = self.vat_rate_combo.findData(vat_rate)
        if index >= 0:
            self.vat_rate_combo.setCurrentIndex(index)
        
        # KDV tutarı
        self.vat_amount_spin.setValue(self.expense.get("vat", 0))
        
        # Ödeme yöntemi
        payment_method_map = {
            "cash": "Nakit",
            "bank": "Banka",
            "credit_card": "Kredi Kartı",
            "other": "Diğer"
        }
        
        payment_method = payment_method_map.get(self.expense.get("payment_method"), "Diğer")
        index = self.payment_method_combo.findText(payment_method)
        if index >= 0:
            self.payment_method_combo.setCurrentIndex(index)
        
        # Fiş/Fatura no
        self.receipt_number_edit.setText(self.expense.get("receipt_number", ""))
        
        # Durum
        status_map = {
            "paid": "Ödenmiş",
            "unpaid": "Ödenmemiş"
        }
        
        status = status_map.get(self.expense.get("status"), "Ödenmiş")
        index = self.status_combo.findText(status)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        
        # Vergi bilgileri
        self.vat_deductible_checkbox.setChecked(self.expense.get("vat_deductible", True))
        self.tax_deductible_checkbox.setChecked(self.expense.get("tax_deductible", True))
        self.auto_post_checkbox.setChecked(self.expense.get("auto_post", True))
        
        # Fiş/Fatura dosyası
        receipt_file = self.expense.get("receipt_file")
        if receipt_file:
            self.receipt_file = receipt_file
            self.receipt_file_label.setText(f"Seçili dosya: {os.path.basename(receipt_file)}")
        
        # Notlar
        self.notes_edit.setText(self.expense.get("notes", ""))
        
        # Toplamı güncelle
        self._update_vat()
    
    def get_expense(self):
        """Girilen gider bilgilerinden gider dict nesnesi oluştur"""
        # Fiş/Fatura numarası (boşsa otomatik oluştur)
        receipt_number = self.receipt_number_edit.text()
        if not receipt_number:
            receipt_number = f"EXP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        
        # Kategori
        category_map = {
            "Ofis Giderleri": "office",
            "Seyahat ve Konaklama": "travel",
            "Pazarlama ve Reklam": "marketing",
            "Kira": "rent",
            "Faturalar": "utilities",
            "Yazılım ve Abonelikler": "software",
            "Profesyonel Hizmetler": "professional",
            "Maaşlar": "salary",
            "Banka ve Finansman Giderleri": "bank",
            "Diğer": "other"
        }
        
        category = category_map.get(self.category_combo.currentText(), "other")
        
        # Ödeme yöntemi
        payment_method_map = {
            "Nakit": "cash",
            "Banka": "bank",
            "Kredi Kartı": "credit_card",
            "Diğer": "other"
        }
        
        payment_method = payment_method_map.get(self.payment_method_combo.currentText(), "other")
        
        # Durum
        status_map = {
            "Ödenmiş": "paid",
            "Ödenmemiş": "unpaid"
        }
        
        status = status_map.get(self.status_combo.currentText(), "paid")
        
        # Gider verisi
        expense = {
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "category": category,
            "description": self.description_edit.text(),
            "supplier": self.supplier_edit.text(),
            "amount": self.amount_spin.value(),
            "vat_rate": self.vat_rate_combo.currentData(),
            "vat": self.vat_amount_spin.value(),
            "payment_method": payment_method,
            "receipt_number": receipt_number,
            "status": status,
            "vat_deductible": self.vat_deductible_checkbox.isChecked(),
            "tax_deductible": self.tax_deductible_checkbox.isChecked(),
            "auto_post": self.auto_post_checkbox.isChecked(),
            "receipt_file": self.receipt_file,
            "notes": self.notes_edit.text()
        }
        
        # Düzenlenen gider ise ID'yi koru
        if self.expense and "id" in self.expense:
            expense["id"] = self.expense["id"]
        
        return expense
