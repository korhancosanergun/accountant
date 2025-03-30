#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Fatura Dialog
Fatura ekleme/düzenleme için dialog penceresi.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, 
    QLabel, QLineEdit, QPushButton, QDateEdit, QComboBox,
    QDialogButtonBox, QGroupBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView,
    QSpinBox, QDoubleSpinBox, QMessageBox
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont

from datetime import datetime, timedelta
import uuid


class InvoiceDialog(QDialog):
    """Fatura ekleme/düzenleme dialog penceresi"""
    
    def __init__(self, ledger, invoice=None, parent=None):
        """Dialog başlatıcı
        
        Args:
            ledger: Muhasebe defteri nesnesi
            invoice: Düzenlenecek fatura (yeni fatura için None)
            parent: Ebeveyn pencere
        """
        super().__init__(parent)
        
        self.ledger = ledger
        self.invoice = invoice
        self.invoice_items = []
        
        # Dialog ayarları
        self.setWindowTitle("Fatura Ekle" if not invoice else "Fatura Düzenle")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # UI kurulumu
        self._setup_ui()
        
        # Fatura düzenlemesi ise verileri doldur
        if self.invoice:
            self._fill_invoice_data()
    
    def _setup_ui(self):
        """UI kurulumu"""
        # Ana düzen
        main_layout = QVBoxLayout(self)
        
        # Fatura bilgileri grubu
        invoice_group = QGroupBox("Fatura Bilgileri")
        invoice_layout = QFormLayout(invoice_group)
        
        # Fatura numarası
        self.invoice_number_edit = QLineEdit()
        self.invoice_number_edit.setPlaceholderText("Otomatik oluşturulacak")
        invoice_layout.addRow("Fatura No:", self.invoice_number_edit)
        
        # Fatura tipi
        self.invoice_type_combo = QComboBox()
        self.invoice_type_combo.addItem("Satış Faturası", "sales")
        self.invoice_type_combo.addItem("Alış Faturası", "purchase")
        self.invoice_type_combo.currentIndexChanged.connect(self._update_entity_label)
        invoice_layout.addRow("Fatura Tipi:", self.invoice_type_combo)
        
        # Tarih
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        invoice_layout.addRow("Tarih:", self.date_edit)
        
        # Vade tarihi
        self.due_date_edit = QDateEdit()
        self.due_date_edit.setCalendarPopup(True)
        self.due_date_edit.setDate(QDate.currentDate().addDays(30))  # Varsayılan 30 gün
        invoice_layout.addRow("Vade Tarihi:", self.due_date_edit)
        
        # Müşteri/Tedarikçi
        self.entity_label = QLabel("Müşteri:")
        self.entity_edit = QLineEdit()
        invoice_layout.addRow(self.entity_label, self.entity_edit)
        
        # KDV oranı
        self.vat_rate_combo = QComboBox()
        self.vat_rate_combo.addItem("Standart Oran (%20)", 20)
        self.vat_rate_combo.addItem("İndirilmiş Oran (%5)", 5)
        self.vat_rate_combo.addItem("Sıfır Oran (%0)", 0)
        self.vat_rate_combo.currentIndexChanged.connect(self._update_totals)
        invoice_layout.addRow("KDV Oranı:", self.vat_rate_combo)
        
        # Referans
        self.reference_edit = QLineEdit()
        invoice_layout.addRow("Referans:", self.reference_edit)
        
        # Otomatik muhasebeleştirme
        self.auto_post_checkbox = QCheckBox("Otomatik Muhasebeleştir")
        self.auto_post_checkbox.setChecked(True)
        invoice_layout.addRow("", self.auto_post_checkbox)
        
        main_layout.addWidget(invoice_group)
        
        # Fatura kalemleri grubu
        items_group = QGroupBox("Fatura Kalemleri")
        items_layout = QVBoxLayout(items_group)
        
        # Fatura kalemleri tablosu
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels([
            "Açıklama", "Miktar", "Birim Fiyat", "KDV", "Toplam"
        ])
        
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.items_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.items_table.setAlternatingRowColors(True)
        
        items_layout.addWidget(self.items_table)
        
        # Kalem ekle/sil butonları
        buttons_layout = QHBoxLayout()
        
        self.add_item_button = QPushButton("Kalem Ekle")
        self.add_item_button.clicked.connect(self._add_item)
        buttons_layout.addWidget(self.add_item_button)
        
        self.remove_item_button = QPushButton("Kalem Sil")
        self.remove_item_button.clicked.connect(self._remove_item)
        buttons_layout.addWidget(self.remove_item_button)
        
        items_layout.addLayout(buttons_layout)
        
        main_layout.addWidget(items_group)
        
        # Toplam bilgileri grubu
        totals_group = QGroupBox("Toplam Bilgileri")
        totals_layout = QFormLayout(totals_group)
        
        self.subtotal_label = QLabel("0.00")
        self.subtotal_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        totals_layout.addRow("Ara Toplam:", self.subtotal_label)
        
        self.vat_amount_label = QLabel("0.00")
        self.vat_amount_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        totals_layout.addRow("KDV:", self.vat_amount_label)
        
        self.total_label = QLabel("0.00")
        self.total_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        totals_layout.addRow("Genel Toplam:", self.total_label)
        
        main_layout.addWidget(totals_group)
        
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
    
    def _update_entity_label(self):
        """Müşteri/Tedarikçi etiketini güncelle"""
        invoice_type = self.invoice_type_combo.currentData()
        if invoice_type == "sales":
            self.entity_label.setText("Müşteri:")
        else:
            self.entity_label.setText("Tedarikçi:")
    
    def _add_item(self):
        """Fatura kalemi ekle"""
        # İç içe dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Fatura Kalemi Ekle")
        dialog.setMinimumWidth(400)
        
        # Dialog düzeni
        layout = QFormLayout(dialog)
        
        # Kalem alanları
        description_edit = QLineEdit()
        layout.addRow("Açıklama:", description_edit)
        
        quantity_spin = QSpinBox()
        quantity_spin.setMinimum(1)
        quantity_spin.setMaximum(9999)
        quantity_spin.setValue(1)
        layout.addRow("Miktar:", quantity_spin)
        
        unit_price_spin = QDoubleSpinBox()
        unit_price_spin.setDecimals(2)
        unit_price_spin.setMinimum(0)
        unit_price_spin.setMaximum(999999.99)
        unit_price_spin.setValue(0)
        layout.addRow("Birim Fiyat:", unit_price_spin)
        
        # Dialog butonları
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addRow(button_box)
        
        # Dialog'u göster
        if dialog.exec_() == QDialog.Accepted:
            # Kalem bilgilerini al
            description = description_edit.text()
            quantity = quantity_spin.value()
            unit_price = unit_price_spin.value()
            
            # Boş açıklama kontrolü
            if not description:
                QMessageBox.warning(self, "Eksik Bilgi", "Açıklama alanı boş olamaz.")
                return
            
            # KDV hesapla
            vat_rate = self.vat_rate_combo.currentData()
            vat_amount = (quantity * unit_price) * (vat_rate / 100)
            total = (quantity * unit_price) + vat_amount
            
            # Kalem listesine ekle
            self.invoice_items.append({
                "description": description,
                "quantity": quantity,
                "unit_price": unit_price,
                "vat_rate": vat_rate,
                "vat_amount": vat_amount,
                "total": total
            })
            
            # Tabloyu güncelle
            self._update_items_table()
            
            # Toplamları güncelle
            self._update_totals()
    
    def _remove_item(self):
        """Seçili fatura kalemini sil"""
        selected_rows = self.items_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Seçim Yapılmadı", "Silmek için bir kalem seçin.")
            return
        
        # Seçili satırı al (tekrarlanan satır indekslerini ele almak için set kullanıyoruz)
        rows = set()
        for index in selected_rows:
            rows.add(index.row())
        
        # Her satırı sondan başa doğru sil (indeks kayması olmaması için)
        for row in sorted(rows, reverse=True):
            del self.invoice_items[row]
        
        # Tabloyu güncelle
        self._update_items_table()
        
        # Toplamları güncelle
        self._update_totals()
    
    def _update_items_table(self):
        """Fatura kalemleri tablosunu güncelle"""
        # Tabloyu temizle
        self.items_table.setRowCount(0)
        
        # Kalemleri ekle
        for i, item in enumerate(self.invoice_items):
            self.items_table.insertRow(i)
            
            # Açıklama
            self.items_table.setItem(i, 0, QTableWidgetItem(item["description"]))
            
            # Miktar
            quantity_item = QTableWidgetItem(str(item["quantity"]))
            quantity_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(i, 1, quantity_item)
            
            # Birim Fiyat
            unit_price_item = QTableWidgetItem(f"{item['unit_price']:.2f}")
            unit_price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(i, 2, unit_price_item)
            
            # KDV
            vat_item = QTableWidgetItem(f"{item['vat_amount']:.2f}")
            vat_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(i, 3, vat_item)
            
            # Toplam
            total_item = QTableWidgetItem(f"{item['total']:.2f}")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.items_table.setItem(i, 4, total_item)
    
    def _update_totals(self):
        """Toplam bilgilerini güncelle"""
        # Ara toplam (KDV hariç)
        subtotal = sum(item["quantity"] * item["unit_price"] for item in self.invoice_items)
        
        # KDV oranını al ve uygula
        vat_rate = self.vat_rate_combo.currentData()
        
        # KDV tutarı ve genel toplam
        vat_amount = sum(item["vat_amount"] for item in self.invoice_items)
        total = subtotal + vat_amount
        
        # Etiketleri güncelle
        self.subtotal_label.setText(f"{subtotal:.2f}")
        self.vat_amount_label.setText(f"{vat_amount:.2f}")
        self.total_label.setText(f"{total:.2f}")
        
        # KDV oranı değiştirildiğinde, tüm kalemlerin KDV oranlarını güncelle
        for item in self.invoice_items:
            item["vat_rate"] = vat_rate
            item["vat_amount"] = (item["quantity"] * item["unit_price"]) * (vat_rate / 100)
            item["total"] = (item["quantity"] * item["unit_price"]) + item["vat_amount"]
        
        # Tabloyu güncelle
        self._update_items_table()
    
    def _fill_invoice_data(self):
        """Düzenlenen fatura verilerini forma doldur"""
        # Temel fatura bilgileri
        self.invoice_number_edit.setText(self.invoice["invoice_number"])
        
        # Fatura tipi
        index = self.invoice_type_combo.findData(self.invoice["type"])
        if index >= 0:
            self.invoice_type_combo.setCurrentIndex(index)
        
        # Tarihler
        try:
            date = QDate.fromString(self.invoice["date"], "yyyy-MM-dd")
            if date.isValid():
                self.date_edit.setDate(date)
            
            due_date = QDate.fromString(self.invoice["due_date"], "yyyy-MM-dd")
            if due_date.isValid():
                self.due_date_edit.setDate(due_date)
        except KeyError:
            pass
        
        # Müşteri/Tedarikçi
        self.entity_edit.setText(self.invoice.get("entity_name", ""))
        
        # KDV oranı
        vat_rate = self.invoice.get("vat_rate", 20)
        index = self.vat_rate_combo.findData(vat_rate)
        if index >= 0:
            self.vat_rate_combo.setCurrentIndex(index)
        
        # Referans
        self.reference_edit.setText(self.invoice.get("reference", ""))
        
        # Otomatik muhasebeleştirme
        self.auto_post_checkbox.setChecked(self.invoice.get("auto_post", True))
        
        # Notlar
        self.notes_edit.setText(self.invoice.get("notes", ""))
        
        # Fatura kalemleri (varsa)
        self.invoice_items = self.invoice.get("items", [])
        self._update_items_table()
        self._update_totals()
    
    def get_invoice(self):
        """Girilen fatura bilgilerinden fatura dict nesnesi oluştur"""
        # Fatura numarası (boşsa otomatik oluştur)
        invoice_number = self.invoice_number_edit.text()
        if not invoice_number:
            invoice_type = self.invoice_type_combo.currentData()
            prefix = "INV" if invoice_type == "sales" else "PUR"
            invoice_number = f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        
        # Fatura bilgileri
        invoice = {
            "invoice_number": invoice_number,
            "type": self.invoice_type_combo.currentData(),
            "date": self.date_edit.date().toString("yyyy-MM-dd"),
            "due_date": self.due_date_edit.date().toString("yyyy-MM-dd"),
            "entity_name": self.entity_edit.text(),
            "vat_rate": self.vat_rate_combo.currentData(),
            "reference": self.reference_edit.text(),
            "auto_post": self.auto_post_checkbox.isChecked(),
            "notes": self.notes_edit.text(),
            "items": self.invoice_items
        }
        
        # Toplam tutarlar
        invoice["amount"] = float(self.subtotal_label.text())
        invoice["vat"] = float(self.vat_amount_label.text())
        
        # Ödeme durumu
        invoice["payment_status"] = "unpaid"
        
        # Düzenlenen fatura ise ID'yi koru
        if self.invoice and "id" in self.invoice:
            invoice["id"] = self.invoice["id"]
        
        return invoice
