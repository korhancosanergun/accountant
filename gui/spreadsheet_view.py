#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Excel Benzeri Tablo Görünümü
MS Excel benzeri kullanıcı arayüzü sunan tablo bileşeni.
"""

from PyQt5.QtWidgets import (
    QWidget, QTableView, QHeaderView, QAbstractItemView,
    QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QLineEdit, QMenu, QAction, QMessageBox
)
from PyQt5.QtCore import Qt, QSortFilterProxyModel, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor, QBrush, QFont

import datetime
import json


class SpreadsheetModel(QStandardItemModel):
    """Excel benzeri tablo veri modeli"""
    
    def __init__(self, ledger, view_type="ledger"):
        """Model başlatıcı
        
        Args:
            ledger: Muhasebe defteri nesnesi
            view_type: Görünüm tipi ('ledger', 'income_expense', 'invoices', 'accounts')
        """
        super().__init__()
        
        self.ledger = ledger
        self.view_type = view_type
        
        # Tablo içeriğini yükle
        self.load_data()
    
    def load_data(self):
        """Verileri modele yükle"""
        self.clear()
        
        if self.view_type == "ledger":
            self._load_ledger_data()
        elif self.view_type == "income_expense":
            self._load_income_expense_data()
        elif self.view_type == "invoices":
            self._load_invoice_data()
        elif self.view_type == "accounts":
            self._load_accounts_data()
    
    def _load_ledger_data(self):
        """Muhasebe defteri verilerini yükle"""
        # Sütun başlıklarını ayarla
        headers = [
            "Tarih", "Belge No", "Açıklama", "Hesap", "Borç", "Alacak", 
            "KDV", "Durumu", "İşlem Tipi", "Notlar"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Verileri yükle
        transactions = self.ledger.get_all_transactions()
        self.setRowCount(len(transactions))
        
        for row, trans in enumerate(transactions):
            # Tarih
            date_item = QStandardItem(trans.get("date", ""))
            self.setItem(row, 0, date_item)
            
            # Belge No
            doc_item = QStandardItem(trans.get("document_number", ""))
            self.setItem(row, 1, doc_item)
            
            # Açıklama
            desc_item = QStandardItem(trans.get("description", ""))
            self.setItem(row, 2, desc_item)
            
            # Hesap
            account_item = QStandardItem(trans.get("account", ""))
            self.setItem(row, 3, account_item)
            
            # Borç
            debit = trans.get("debit", 0)
            debit_item = QStandardItem(f"{debit:.2f}" if debit else "")
            debit_item.setData(debit, Qt.UserRole)
            debit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 4, debit_item)
            
            # Alacak
            credit = trans.get("credit", 0)
            credit_item = QStandardItem(f"{credit:.2f}" if credit else "")
            credit_item.setData(credit, Qt.UserRole)
            credit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 5, credit_item)
            
            # KDV
            vat = trans.get("vat", 0)
            vat_item = QStandardItem(f"{vat:.2f}" if vat else "")
            vat_item.setData(vat, Qt.UserRole)
            vat_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 6, vat_item)
            
            # Durumu
            status_item = QStandardItem(trans.get("status", ""))
            self.setItem(row, 7, status_item)
            
            # İşlem Tipi
            type_item = QStandardItem(trans.get("transaction_type", ""))
            self.setItem(row, 8, type_item)
            
            # Notlar
            notes_item = QStandardItem(trans.get("notes", ""))
            self.setItem(row, 9, notes_item)
            
            # Renklendirme
            if "reconciled" in trans.get("status", "").lower():
                for col in range(self.columnCount()):
                    item = self.item(row, col)
                    if item:
                        item.setBackground(QBrush(QColor(230, 255, 230)))  # Açık yeşil
    
    def _load_income_expense_data(self):
        """Gelir/Gider verilerini yükle"""
        # Sütun başlıklarını ayarla
        headers = [
            "Tarih", "Kategori", "Açıklama", "Gelir", "Gider", 
            "KDV", "Ödeme Yöntemi", "Fiş/Fatura No", "Durumu"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Verileri yükle
        items = self.ledger.get_income_expenses()
        self.setRowCount(len(items))
        
        for row, item in enumerate(items):
            # Tarih
            date_item = QStandardItem(item.get("date", ""))
            self.setItem(row, 0, date_item)
            
            # Kategori
            category_item = QStandardItem(item.get("category", ""))
            self.setItem(row, 1, category_item)
            
            # Açıklama
            desc_item = QStandardItem(item.get("description", ""))
            self.setItem(row, 2, desc_item)
            
            # Gelir
            income = item.get("income", 0)
            income_item = QStandardItem(f"{income:.2f}" if income else "")
            income_item.setData(income, Qt.UserRole)
            income_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if income:
                income_item.setForeground(QBrush(QColor(0, 128, 0)))  # Yeşil
            self.setItem(row, 3, income_item)
            
            # Gider
            expense = item.get("expense", 0)
            expense_item = QStandardItem(f"{expense:.2f}" if expense else "")
            expense_item.setData(expense, Qt.UserRole)
            expense_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if expense:
                expense_item.setForeground(QBrush(QColor(255, 0, 0)))  # Kırmızı
            self.setItem(row, 4, expense_item)
            
            # KDV
            vat = item.get("vat", 0)
            vat_item = QStandardItem(f"{vat:.2f}" if vat else "")
            vat_item.setData(vat, Qt.UserRole)
            vat_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 5, vat_item)
            
            # Ödeme Yöntemi
            payment_item = QStandardItem(item.get("payment_method", ""))
            self.setItem(row, 6, payment_item)
            
            # Fiş/Fatura No
            receipt_item = QStandardItem(item.get("receipt_number", ""))
            self.setItem(row, 7, receipt_item)
            
            # Durumu
            status_item = QStandardItem(item.get("status", ""))
            self.setItem(row, 8, status_item)
            
            # Renklendirme
            row_color = None
            if item.get("type") == "income":
                row_color = QColor(240, 255, 240)  # Açık yeşil
            elif item.get("type") == "expense":
                row_color = QColor(255, 240, 240)  # Açık kırmızı
                
            if row_color:
                for col in range(self.columnCount()):
                    item = self.item(row, col)
                    if item:
                        item.setBackground(QBrush(row_color))
    
    def _load_invoice_data(self):
        """Fatura verilerini yükle"""
        # Sütun başlıklarını ayarla
        headers = [
            "Fatura No", "Tarih", "Müşteri/Tedarikçi", "Tutar", "KDV", 
            "Toplam", "Vade Tarihi", "Ödeme Durumu", "Tipi"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Verileri yükle
        invoices = self.ledger.get_all_invoices()
        self.setRowCount(len(invoices))
        
        for row, inv in enumerate(invoices):
            # Fatura No
            inv_no_item = QStandardItem(inv.get("invoice_number", ""))
            self.setItem(row, 0, inv_no_item)
            
            # Tarih
            date_item = QStandardItem(inv.get("date", ""))
            self.setItem(row, 1, date_item)
            
            # Müşteri/Tedarikçi
            entity_item = QStandardItem(inv.get("entity_name", ""))
            self.setItem(row, 2, entity_item)
            
            # Tutar
            amount = inv.get("amount", 0)
            amount_item = QStandardItem(f"{amount:.2f}")
            amount_item.setData(amount, Qt.UserRole)
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 3, amount_item)
            
            # KDV
            vat = inv.get("vat", 0)
            vat_item = QStandardItem(f"{vat:.2f}")
            vat_item.setData(vat, Qt.UserRole)
            vat_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 4, vat_item)
            
            # Toplam
            total = amount + vat
            total_item = QStandardItem(f"{total:.2f}")
            total_item.setData(total, Qt.UserRole)
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 5, total_item)
            
            # Vade Tarihi
            due_date_item = QStandardItem(inv.get("due_date", ""))
            self.setItem(row, 6, due_date_item)
            
            # Ödeme Durumu
            status_item = QStandardItem(inv.get("payment_status", ""))
            self.setItem(row, 7, status_item)
            
            # Tipi (Satış/Alış)
            type_item = QStandardItem(inv.get("type", ""))
            self.setItem(row, 8, type_item)
            
            # Renklendirme
            row_color = None
            if inv.get("type") == "sales":
                row_color = QColor(240, 255, 240)  # Açık yeşil
            elif inv.get("type") == "purchase":
                row_color = QColor(255, 240, 240)  # Açık kırmızı
                
            # Gecikmişse kırmızı yap
            if inv.get("payment_status") == "unpaid":
                try:
                    due_date = datetime.datetime.strptime(inv.get("due_date", ""), "%Y-%m-%d")
                    if due_date < datetime.datetime.now():
                        row_color = QColor(255, 200, 200)  # Daha belirgin kırmızı
                except:
                    pass
                
            if row_color:
                for col in range(self.columnCount()):
                    item = self.item(row, col)
                    if item:
                        item.setBackground(QBrush(row_color))
    
    def _load_accounts_data(self):
        """Hesap planı verilerini yükle"""
        # Sütun başlıklarını ayarla
        headers = [
            "Hesap Kodu", "Hesap Adı", "Türü", "Kategori", "KDV Oranı", "Bakiye"
        ]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Verileri yükle
        accounts = self.ledger.get_chart_of_accounts()
        self.setRowCount(len(accounts))
        
        for row, acc in enumerate(accounts):
            # Hesap Kodu
            code_item = QStandardItem(acc.get("code", ""))
            self.setItem(row, 0, code_item)
            
            # Hesap Adı
            name_item = QStandardItem(acc.get("name", ""))
            self.setItem(row, 1, name_item)
            
            # Türü
            type_item = QStandardItem(acc.get("type", ""))
            self.setItem(row, 2, type_item)
            
            # Kategori
            category_item = QStandardItem(acc.get("category", ""))
            self.setItem(row, 3, category_item)
            
            # KDV Oranı
            vat_rate = acc.get("vat_rate", 0)
            vat_item = QStandardItem(f"{vat_rate}%" if vat_rate else "")
            vat_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.setItem(row, 4, vat_item)
            
            # Bakiye
            balance = acc.get("balance", 0)
            balance_item = QStandardItem(f"{balance:.2f}")
            balance_item.setData(balance, Qt.UserRole)
            balance_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Negatif bakiyeleri kırmızı yap
            if balance < 0:
                balance_item.setForeground(QBrush(QColor(255, 0, 0)))
            
            self.setItem(row, 5, balance_item)
            
            # Hesap tipine göre renklendirme
            row_color = None
            if acc.get("type") == "asset":
                row_color = QColor(230, 230, 255)  # Açık mavi
            elif acc.get("type") == "liability":
                row_color = QColor(255, 230, 230)  # Açık kırmızı
            elif acc.get("type") == "equity":
                row_color = QColor(255, 255, 200)  # Açık sarı
            elif acc.get("type") == "income":
                row_color = QColor(230, 255, 230)  # Açık yeşil
            elif acc.get("type") == "expense":
                row_color = QColor(255, 240, 220)  # Açık turuncu
                
            if row_color:
                for col in range(self.columnCount()):
                    item = self.item(row, col)
                    if item:
                        item.setBackground(QBrush(row_color))


class SpreadsheetView(QWidget):
    """Excel benzeri tablo görünümü"""
    
    def __init__(self, ledger, view_type="ledger"):
        """Görünüm başlatıcı
        
        Args:
            ledger: Muhasebe defteri nesnesi
            view_type: Görünüm tipi ('ledger', 'income_expense', 'invoices', 'accounts')
        """
        super().__init__()
        
        self.ledger = ledger
        self.view_type = view_type
        
        # UI oluşturma
        self._setup_ui()
    
    def _setup_ui(self):
        """UI kurulumu"""
        # Ana düzen
        main_layout = QVBoxLayout(self)
        
        # Üst filtre çubuğu
        filter_layout = QHBoxLayout()
        
        # Ara etiketi ve kutusu
        filter_layout.addWidget(QLabel("Ara:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Filtrelemek için yazın...")
        self.search_edit.textChanged.connect(self._filter_changed)
        filter_layout.addWidget(self.search_edit)
        
        # Filtre kombo kutusu
        filter_layout.addWidget(QLabel("Filtrele:"))
        self.filter_combo = QComboBox()
        
        # Görünüm tipine göre filtre seçeneklerini ayarlama
        if self.view_type == "ledger":
            self.filter_combo.addItems(["Tümü", "Bu Ay", "Geçen Ay", "Bu Çeyrek", "Bu Yıl"])
        elif self.view_type == "income_expense":
            self.filter_combo.addItems(["Tümü", "Gelirler", "Giderler", "Bu Ay", "Geçen Ay", "Bu Çeyrek", "Bu Yıl"])
        elif self.view_type == "invoices":
            self.filter_combo.addItems(["Tümü", "Satış Faturaları", "Alış Faturaları", "Ödenmemiş", "Ödenmiş", "Gecikmiş"])
        elif self.view_type == "accounts":
            self.filter_combo.addItems(["Tümü", "Varlıklar", "Borçlar", "Öz Sermaye", "Gelirler", "Giderler"])
        
        self.filter_combo.currentTextChanged.connect(self._filter_changed)
        filter_layout.addWidget(self.filter_combo)
        
        # Dışa aktar butonu
        self.export_button = QPushButton("Dışa Aktar")
        self.export_button.clicked.connect(self._export_data)
        filter_layout.addWidget(self.export_button)
        
        # Yenile butonu
        self.refresh_button = QPushButton("Yenile")
        self.refresh_button.clicked.connect(self.refresh)
        filter_layout.addWidget(self.refresh_button)
        
        # Ana düzene filtre çubuğunu ekle
        main_layout.addLayout(filter_layout)
        
        # Tablo görünümü
        self.table_view = QTableView()
        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._show_context_menu)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSortingEnabled(True)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.DoubleClicked)
        
        # Veri modeli
        self.model = SpreadsheetModel(self.ledger, self.view_type)
        
        # Filtre proxy modeli
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(-1)  # Tüm sütunlarda ara
        
        # Modeli tablo görünümüne bağlama
        self.table_view.setModel(self.proxy_model)
        
        # Sütun genişliklerini ayarlama
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Ana düzene tablo görünümünü ekle
        main_layout.addWidget(self.table_view)
        
        # İlk yükleme
        self.refresh()
    
    def refresh(self):
        """Tabloyu yenile"""
        # Veri modelini yenile
        self.model.load_data()
        
        # Filtre uygula
        self._apply_filter()
        
        # Sütun genişliklerini içeriğe göre ayarla
        self.table_view.resizeColumnsToContents()
        
        # Bazı sütunların minimum genişliklerini ayarla
        for col in range(self.model.columnCount()):
            header_text = self.model.headerData(col, Qt.Horizontal)
            if header_text in ["Açıklama", "Müşteri/Tedarikçi", "Hesap Adı"]:
                self.table_view.setColumnWidth(col, max(200, self.table_view.columnWidth(col)))
    
    def _filter_changed(self):
        """Filtre değiştiğinde"""
        self._apply_filter()
    
    def _apply_filter(self):
        """Filtre uygula"""
        # Metin filtresi
        search_text = self.search_edit.text()
        self.proxy_model.setFilterFixedString(search_text)
        
        # Kombo kutusu filtresi
        filter_text = self.filter_combo.currentText()
        
        # Bu filtre basitleştirilmiştir, gerçek uygulamada daha kapsamlı olmalıdır
        if filter_text != "Tümü":
            # Şu an için bir şey yapmıyoruz, daha gelişmiş filtreleme için
            # QSortFilterProxyModel sınıfından türetilmiş özel bir sınıf gerekebilir
            pass
    
    def _export_data(self):
        """Tabloyu dışa aktar"""
        # Dışa aktarım butonu tıklandığında
        # Bu fonksiyon basitleştirilmiştir, gerçek uygulamada daha kapsamlı olmalıdır
        QMessageBox.information(self, "Dışa Aktarım", "Dışa aktarım özelliği henüz uygulanmamıştır.")
    
    def _show_context_menu(self, position):
        """Sağ tık menüsü göster"""
        # Seçili satırı al
        indexes = self.table_view.selectedIndexes()
        if not indexes:
            return
        
        # Sağ tık menüsü oluştur
        menu = QMenu()
        
        # Görünüm tipine göre menü öğelerini ekle
        if self.view_type == "ledger":
            edit_action = QAction("Düzenle", self)
            edit_action.triggered.connect(self._edit_item)
            menu.addAction(edit_action)
            
            delete_action = QAction("Sil", self)
            delete_action.triggered.connect(self._delete_item)
            menu.addAction(delete_action)
            
            menu.addSeparator()
            
            reconcile_action = QAction("Mutabakat", self)
            reconcile_action.triggered.connect(self._reconcile_item)
            menu.addAction(reconcile_action)
            
        elif self.view_type == "income_expense":
            edit_action = QAction("Düzenle", self)
            edit_action.triggered.connect(self._edit_item)
            menu.addAction(edit_action)
            
            delete_action = QAction("Sil", self)
            delete_action.triggered.connect(self._delete_item)
            menu.addAction(delete_action)
            
            menu.addSeparator()
            
            mark_paid_action = QAction("Ödenmiş Olarak İşaretle", self)
            mark_paid_action.triggered.connect(self._mark_as_paid)
            menu.addAction(mark_paid_action)
            
        elif self.view_type == "invoices":
            view_action = QAction("Görüntüle", self)
            view_action.triggered.connect(self._view_invoice)
            menu.addAction(view_action)
            
            edit_action = QAction("Düzenle", self)
            edit_action.triggered.connect(self._edit_item)
            menu.addAction(edit_action)
            
            delete_action = QAction("Sil", self)
            delete_action.triggered.connect(self._delete_item)
            menu.addAction(delete_action)
            
            menu.addSeparator()
            
            mark_paid_action = QAction("Ödenmiş Olarak İşaretle", self)
            mark_paid_action.triggered.connect(self._mark_as_paid)
            menu.addAction(mark_paid_action)
            
            print_action = QAction("Yazdır", self)
            print_action.triggered.connect(self._print_invoice)
            menu.addAction(print_action)
            
        elif self.view_type == "accounts":
            edit_action = QAction("Düzenle", self)
            edit_action.triggered.connect(self._edit_item)
            menu.addAction(edit_action)
            
            view_transactions_action = QAction("İşlemleri Görüntüle", self)
            view_transactions_action.triggered.connect(self._view_account_transactions)
            menu.addAction(view_transactions_action)
            
            menu.addSeparator()
            
            new_account_action = QAction("Yeni Hesap", self)
            new_account_action.triggered.connect(self._new_account)
            menu.addAction(new_account_action)
        
        # Menüyü göster
        menu.exec_(self.table_view.viewport().mapToGlobal(position))
    
    def _edit_item(self):
        """Seçili öğeyi düzenle"""
        # Bu fonksiyon basitleştirilmiştir, gerçek uygulamada daha kapsamlı olmalıdır
        QMessageBox.information(self, "Düzenle", "Düzenleme özelliği henüz uygulanmamıştır.")
    
    def _delete_item(self):
        """Seçili öğeyi sil"""
        # Bu fonksiyon basitleştirilmiştir, gerçek uygulamada daha kapsamlı olmalıdır
        QMessageBox.information(self, "Sil", "Silme özelliği henüz uygulanmamıştır.")
    
    def _reconcile_item(self):
        """Seçili öğeyi mutabakat yap"""
        # Bu fonksiyon basitleştirilmiştir, gerçek uygulamada daha kapsamlı olmalıdır
        QMessageBox.information(self, "Mutabakat", "Mutabakat özelliği henüz uygulanmamıştır.")
    
    def _mark_as_paid(self):
        """Seçili öğeyi ödenmiş olarak işaretle"""
        # Bu fonksiyon basitleştirilmiştir, gerçek uygulamada daha kapsamlı olmalıdır
        QMessageBox.information(self, "Ödenmiş İşaretle", "Ödeme işaretleme özelliği henüz uygulanmamıştır.")
    
    def _view_invoice(self):
        """Seçili faturayı görüntüle"""
        # Bu fonksiyon basitleştirilmiştir, gerçek uygulamada daha kapsamlı olmalıdır
        QMessageBox.information(self, "Fatura Görüntüle", "Fatura görüntüleme özelliği henüz uygulanmamıştır.")
    
    def _print_invoice(self):
        """Seçili faturayı yazdır"""
        # Bu fonksiyon basitleştirilmiştir, gerçek uygulamada daha kapsamlı olmalıdır
        QMessageBox.information(self, "Fatura Yazdır", "Fatura yazdırma özelliği henüz uygulanmamıştır.")
    
    def _view_account_transactions(self):
        """Hesap işlemlerini görüntüle"""
        # Bu fonksiyon basitleştirilmiştir, gerçek uygulamada daha kapsamlı olmalıdır
        QMessageBox.information(self, "Hesap İşlemleri", "Hesap işlemleri görüntüleme özelliği henüz uygulanmamıştır.")
    
    def _new_account(self):
        """Yeni hesap oluştur"""
        # Bu fonksiyon basitleştirilmiştir, gerçek uygulamada daha kapsamlı olmalıdır
        QMessageBox.information(self, "Yeni Hesap", "Yeni hesap oluşturma özelliği henüz uygulanmamıştır.")
