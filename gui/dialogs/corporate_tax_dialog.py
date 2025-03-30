#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Kurumlar Vergisi Dialog
Kurumlar vergisi hesaplama ve raporlama arayüzü.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QDateEdit, QComboBox,
    QTabWidget, QWidget, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QCheckBox, QDialogButtonBox, QFileDialog,
    QTextEdit, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QFont, QColor

from datetime import datetime, timedelta
import json
from hmrc.corporate_tax import CorporateTaxCalculator


class CorporateTaxDialog(QDialog):
    """Kurumlar vergisi dialog penceresi"""
    
    def __init__(self, ledger, company_info, parent=None):
        """Dialog başlatıcı
        
        Args:
            ledger: Muhasebe defteri nesnesi
            company_info: Şirket bilgileri
            parent: Ebeveyn pencere
        """
        super().__init__(parent)
        
        self.ledger = ledger
        self.company_info = company_info
        self.calculator = CorporateTaxCalculator(ledger)
        
        # Dialog ayarları
        self.setWindowTitle("Kurumlar Vergisi")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        
        # UI kurulumu
        self._setup_ui()
        
        # Varsayılan hesap dönemini ayarla
        self._set_default_accounting_period()
    
    def _setup_ui(self):
        """UI kurulumu"""
        # Ana düzen
        main_layout = QVBoxLayout(self)
        
        # Sekme penceresi
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Hesaplama Sekmesi
        calculation_tab = QWidget()
        tab_widget.addTab(calculation_tab, "Hesaplama")
        
        # Raporlar Sekmesi
        reports_tab = QWidget()
        tab_widget.addTab(reports_tab, "Raporlar")
        
        # Beyanname Sekmesi
        return_tab = QWidget()
        tab_widget.addTab(return_tab, "Beyanname")
        
        # Hesaplama Sekmesi Düzeni
        calculation_layout = QVBoxLayout(calculation_tab)
        
        # Hesap Dönemi Grubu
        period_group = QGroupBox("Hesap Dönemi")
        period_layout = QFormLayout(period_group)
        
        # Başlangıç Tarihi
        self.start_date_edit = QDateEdit()
        self.start_date_edit.setCalendarPopup(True)
        self.start_date_edit.setDisplayFormat("dd.MM.yyyy")
        period_layout.addRow("Başlangıç Tarihi:", self.start_date_edit)
        
        # Bitiş Tarihi
        self.end_date_edit = QDateEdit()
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("dd.MM.yyyy")
        period_layout.addRow("Bitiş Tarihi:", self.end_date_edit)
        
        # Hesaplama butonu
        self.calculate_button = QPushButton("Hesapla")
        self.calculate_button.clicked.connect(self._calculate_tax)
        period_layout.addRow("", self.calculate_button)
        
        calculation_layout.addWidget(period_group)
        
        # Sonuçlar Grubu
        results_group = QGroupBox("Sonuçlar")
        results_layout = QGridLayout(results_group)
        
        # Toplam Gelir ve Gider
        results_layout.addWidget(QLabel("Toplam Gelir:"), 0, 0)
        self.total_income_label = QLabel("£0.00")
        self.total_income_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_income_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(self.total_income_label, 0, 1)
        
        results_layout.addWidget(QLabel("Toplam Gider:"), 1, 0)
        self.total_expenses_label = QLabel("£0.00")
        self.total_expenses_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_expenses_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(self.total_expenses_label, 1, 1)
        
        results_layout.addWidget(QLabel("Vergilendirilebilir Kâr:"), 2, 0)
        self.taxable_profit_label = QLabel("£0.00")
        self.taxable_profit_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.taxable_profit_label.setStyleSheet("font-weight: bold;")
        results_layout.addWidget(self.taxable_profit_label, 2, 1)
        
        # Ayırıcı çizgi
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        results_layout.addWidget(separator, 3, 0, 1, 2)
        
        # Vergi bilgileri
        results_layout.addWidget(QLabel("Vergi Oranı:"), 4, 0)
        self.tax_rate_label = QLabel("0%")
        self.tax_rate_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        results_layout.addWidget(self.tax_rate_label, 4, 1)
        
        results_layout.addWidget(QLabel("Ödenmesi Gereken Vergi:"), 5, 0)
        self.tax_due_label = QLabel("£0.00")
        self.tax_due_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.tax_due_label.setStyleSheet("font-weight: bold; color: #e74c3c;")
        results_layout.addWidget(self.tax_due_label, 5, 1)
        
        results_layout.addWidget(QLabel("Efektif Vergi Oranı:"), 6, 0)
        self.effective_rate_label = QLabel("0%")
        self.effective_rate_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        results_layout.addWidget(self.effective_rate_label, 6, 1)
        
        calculation_layout.addWidget(results_group)
        
        # Gelir ve Gider Detayları
        details_group = QGroupBox("Gelir ve Gider Detayları")
        details_layout = QGridLayout(details_group)
        
        # Ticari gelir
        details_layout.addWidget(QLabel("Ticari Gelir:"), 0, 0)
        self.trading_income_label = QLabel("£0.00")
        self.trading_income_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        details_layout.addWidget(self.trading_income_label, 0, 1)
        
        # Ticari olmayan gelir
        details_layout.addWidget(QLabel("Ticari Olmayan Gelir:"), 1, 0)
        self.non_trading_income_label = QLabel("£0.00")
        self.non_trading_income_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        details_layout.addWidget(self.non_trading_income_label, 1, 1)
        
        # Ticari gider
        details_layout.addWidget(QLabel("Ticari Gider:"), 2, 0)
        self.trading_expenses_label = QLabel("£0.00")
        self.trading_expenses_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        details_layout.addWidget(self.trading_expenses_label, 2, 1)
        
        # Ticari olmayan gider
        details_layout.addWidget(QLabel("Ticari Olmayan Gider:"), 3, 0)
        self.non_trading_expenses_label = QLabel("£0.00")
        self.non_trading_expenses_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        details_layout.addWidget(self.non_trading_expenses_label, 3, 1)
        
        calculation_layout.addWidget(details_group)
        
        # Rapor kaydetme ve HMRC gönderimi
        action_layout = QHBoxLayout()
        
        self.save_report_button = QPushButton("Raporu Kaydet")
        self.save_report_button.clicked.connect(self._save_tax_report)
        self.save_report_button.setEnabled(False)
        action_layout.addWidget(self.save_report_button)
        
        self.save_to_file_button = QPushButton("Dosyaya Kaydet")
        self.save_to_file_button.clicked.connect(self._save_to_file)
        self.save_to_file_button.setEnabled(False)
        action_layout.addWidget(self.save_to_file_button)
        
        self.submit_to_hmrc_button = QPushButton("HMRC'ye Gönder")
        self.submit_to_hmrc_button.clicked.connect(self._submit_to_hmrc)
        self.submit_to_hmrc_button.setEnabled(False)
        action_layout.addWidget(self.submit_to_hmrc_button)
        
        calculation_layout.addLayout(action_layout)
        
        # Raporlar Sekmesi Düzeni
        reports_layout = QVBoxLayout(reports_tab)
        
        # Kaydedilmiş raporlar tablosu
        self.reports_table = QTableWidget()
        self.reports_table.setColumnCount(5)
        self.reports_table.setHorizontalHeaderLabels([
            "Hesap Dönemi", "Oluşturulma Tarihi", "Vergilendirilebilir Kâr", "Vergi Tutarı", "Durum"
        ])
        
        self.reports_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.reports_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.reports_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.reports_table.setAlternatingRowColors(True)
        self.reports_table.doubleClicked.connect(self._view_report_details)
        
        reports_layout.addWidget(self.reports_table)
        
        # Rapor işlemleri
        report_actions_layout = QHBoxLayout()
        
        self.view_report_button = QPushButton("Raporu Görüntüle")
        self.view_report_button.clicked.connect(self._view_selected_report)
        report_actions_layout.addWidget(self.view_report_button)
        
        self.delete_report_button = QPushButton("Raporu Sil")
        self.delete_report_button.clicked.connect(self._delete_selected_report)
        report_actions_layout.addWidget(self.delete_report_button)
        
        reports_layout.addLayout(report_actions_layout)
        
        # Beyanname Sekmesi Düzeni
        return_layout = QVBoxLayout(return_tab)
        
        # Beyanname hazırlama grupları
        company_group = QGroupBox("Şirket Bilgileri")
        company_form = QFormLayout(company_group)
        
        # Şirket adı
        self.company_name_edit = QLineEdit()
        self.company_name_edit.setText(self.company_info.get("company_name", ""))
        company_form.addRow("Şirket Adı:", self.company_name_edit)
        
        # Şirket sicil numarası (CRN)
        self.company_crn_edit = QLineEdit()
        self.company_crn_edit.setText(self.company_info.get("crn", ""))
        company_form.addRow("Şirket Sicil No (CRN):", self.company_crn_edit)
        
        # Şirket vergi referans numarası (UTR)
        self.company_utr_edit = QLineEdit()
        self.company_utr_edit.setText(self.company_info.get("utr", ""))
        company_form.addRow("Vergi Referans No (UTR):", self.company_utr_edit)
        
        return_layout.addWidget(company_group)
        
        # Beyanname seçimi
        return_selection_group = QGroupBox("Beyanname Hazırlama")
        return_selection_layout = QFormLayout(return_selection_group)
        
        # Mevcut hesap dönemi seçimi
        self.period_combo = QComboBox()
        self._load_saved_periods()
        return_selection_layout.addRow("Hesap Dönemi:", self.period_combo)
        
        # Beyanname hazırlama butonu
        prepare_return_button = QPushButton("Beyannameyi Hazırla")
        prepare_return_button.clicked.connect(self._prepare_tax_return)
        return_selection_layout.addRow("", prepare_return_button)
        
        return_layout.addWidget(return_selection_group)
        
        # Beyanname önizleme
        preview_group = QGroupBox("Beyanname Önizleme")
        preview_layout = QVBoxLayout(preview_group)
        
        self.return_preview = QTextEdit()
        self.return_preview.setReadOnly(True)
        preview_layout.addWidget(self.return_preview)
        
        return_layout.addWidget(preview_group)
        
        # Beyanname onay ve gönderim
        return_action_layout = QHBoxLayout()
        
        self.finalize_return_checkbox = QCheckBox("Beyannameyi Onaylıyorum")
        return_action_layout.addWidget(self.finalize_return_checkbox)
        
        return_action_layout.addStretch()
        
        self.submit_return_button = QPushButton("Beyannameyi Gönder")
        self.submit_return_button.clicked.connect(self._submit_tax_return)
        self.submit_return_button.setEnabled(False)
        return_action_layout.addWidget(self.submit_return_button)
        
        return_layout.addLayout(return_action_layout)
        
        # Onay kutusu durumu değişikliğini izle
        self.finalize_return_checkbox.stateChanged.connect(self._update_submit_button)
        
        # Dialog butonları
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        
        main_layout.addWidget(button_box)
        
        # Kaydedilmiş raporları yükle
        self._load_saved_reports()
    
    def _set_default_accounting_period(self):
        """Varsayılan hesap dönemini ayarla"""
        # Şirket bilgilerinden hesap dönemini al
        # Yoksa, şu anki yılı kullan
        current_date = QDate.currentDate()
        
        # Varsayılan olarak 1 Nisan - 31 Mart dönemini kullan
        if current_date.month() < 4:
            # Önceki yıl 1 Nisan - Bu yıl 31 Mart
            start_date = QDate(current_date.year() - 1, 4, 1)
            end_date = QDate(current_date.year(), 3, 31)
        else:
            # Bu yıl 1 Nisan - Sonraki yıl 31 Mart
            start_date = QDate(current_date.year(), 4, 1)
            end_date = QDate(current_date.year() + 1, 3, 31)
        
        # Şirket bilgilerinden dönem varsa kullan
        accounting_period_start = self.company_info.get("accounting_period_start")
        accounting_period_end = self.company_info.get("accounting_period_end")
        
        if accounting_period_start and accounting_period_end:
            try:
                start_date = QDate.fromString(accounting_period_start, "yyyy-MM-dd")
                end_date = QDate.fromString(accounting_period_end, "yyyy-MM-dd")
            except:
                # Hata durumunda varsayılan değerleri kullan
                pass
        
        # Tarih editörlerini ayarla
        self.start_date_edit.setDate(start_date)
        self.end_date_edit.setDate(end_date)
    
    def _calculate_tax(self):
        """Kurumlar vergisini hesapla"""
        # Tarihleri al
        start_date = self.start_date_edit.date().toString("yyyy-MM-dd")
        end_date = self.end_date_edit.date().toString("yyyy-MM-dd")
        
        # Tarihleri doğrula
        if self.start_date_edit.date() >= self.end_date_edit.date():
            QMessageBox.warning(
                self, "Hatalı Tarih Aralığı", 
                "Başlangıç tarihi, bitiş tarihinden önce olmalıdır."
            )
            return
        
        try:
            # Vergi hesaplamasını yap
            self.tax_calculation = self.calculator.calculate_corporation_tax(
                start_date, end_date
            )
            
            # Sonuçları göster
            self._update_results_display()
            
            # Butonları aktifleştir
            self.save_report_button.setEnabled(True)
            self.save_to_file_button.setEnabled(True)
            self.submit_to_hmrc_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(
                self, "Hesaplama Hatası", 
                f"Kurumlar vergisi hesaplanırken bir hata oluştu:\n{str(e)}"
            )
    
    def _update_results_display(self):
        """Hesaplama sonuçlarını ekranda göster"""
        if not hasattr(self, 'tax_calculation'):
            return
        
        calc = self.tax_calculation
        
        # Gelir ve gider toplamları
        self.total_income_label.setText(f"£{calc['income']['total_income']:,.2f}")
        self.total_expenses_label.setText(f"£{calc['expenses']['total_expenses']:,.2f}")
        self.taxable_profit_label.setText(f"£{calc['taxable_profit']:,.2f}")
        
        # Detaylar
        self.trading_income_label.setText(f"£{calc['income']['trading_income']:,.2f}")
        self.non_trading_income_label.setText(f"£{calc['income']['non_trading_income']:,.2f}")
        self.trading_expenses_label.setText(f"£{calc['expenses']['trading_expenses']:,.2f}")
        self.non_trading_expenses_label.setText(f"£{calc['expenses']['non_trading_expenses']:,.2f}")
        
        # Vergi bilgileri
        if calc['taxable_profit'] <= calc['tax_rates']['lower_limit']:
            rate = calc['tax_rates']['small_profits_rate'] * 100
            self.tax_rate_label.setText(f"{rate:.1f}% (Küçük Kârlar Oranı)")
        elif calc['taxable_profit'] >= calc['tax_rates']['upper_limit']:
            rate = calc['tax_rates']['main_rate'] * 100
            self.tax_rate_label.setText(f"{rate:.1f}% (Ana Oran)")
        else:
            # Karışık oran (marjinal hafifletme)
            self.tax_rate_label.setText("Karışık Oran (Marjinal Hafifletme)")
        
        self.tax_due_label.setText(f"£{calc['tax_due']:,.2f}")
        self.effective_rate_label.setText(f"{calc['effective_rate']:.2f}%")
    
    def _save_tax_report(self):
        """Vergi raporunu veritabanına kaydet"""
        if not hasattr(self, 'tax_calculation'):
            return
        
        try:
            # Hesap dönemi bilgilerini al
            period_start = self.start_date_edit.date().toString("yyyy-MM-dd")
            period_end = self.end_date_edit.date().toString("yyyy-MM-dd")
            
            # Raporu veritabanına kaydet
            report_id = self.calculator.save_corporation_tax_return(
                period_start,
                period_end,
                self.tax_calculation
            )
            
            if report_id:
                QMessageBox.information(
                    self, "Başarılı", 
                    f"Kurumlar vergisi raporu başarıyla kaydedildi.\nRapor ID: {report_id}"
                )
                
                # Raporlar listesini güncelle
                self._load_saved_reports()
                
                # Dönem listesini güncelle
                self._load_saved_periods()
            else:
                QMessageBox.warning(
                    self, "Hata", 
                    "Rapor kaydedilirken bir hata oluştu."
                )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Kaydetme Hatası", 
                f"Rapor kaydedilirken bir hata oluştu:\n{str(e)}"
            )
    
    def _save_to_file(self):
        """Vergi raporunu dosyaya kaydet"""
        if not hasattr(self, 'tax_calculation'):
            return
        
        try:
            # Dosya adı iste
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Raporu Kaydet", "", 
                "JSON Dosyaları (*.json);;Tüm Dosyalar (*)"
            )
            
            if not file_path:
                return
            
            # JSON formatına dönüştür
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.tax_calculation, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(
                self, "Başarılı", 
                f"Rapor dosyaya başarıyla kaydedildi:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Dosya Kaydetme Hatası", 
                f"Rapor dosyaya kaydedilirken bir hata oluştu:\n{str(e)}"
            )
    
    def _submit_to_hmrc(self):
        """Kurumlar vergisi hesaplamasını HMRC'ye gönder"""
        if not hasattr(self, 'tax_calculation'):
            return
        
        # Basitleştirilmiş gösterim için sadece bilgi mesajı
        QMessageBox.information(
            self, "HMRC Gönderimi", 
            "Bu fonksiyon, gerçek bir HMRC API entegrasyonu gerektirir.\n\n"
            "Gerçek bir gönderim için, hesaplama sonuçlarını önce kaydedin, "
            "ardından 'Beyanname' sekmesinden ilgili dönemi seçip beyanname "
            "hazırlayarak HMRC'ye gönderebilirsiniz."
        )
    
    def _load_saved_reports(self):
        """Kaydedilmiş raporları yükle"""
        try:
            # Kurumlar vergisi raporlarını veritabanından al
            # Gerçek veritabanı yapısına göre ayarlanmalı
            all_tax_returns = self.ledger.get_tax_returns()
            corp_tax_reports = [
                report for report in all_tax_returns 
                if report.get("type") == "corporation_tax"
            ]
            
            # Tabloyu temizle
            self.reports_table.setRowCount(0)
            
            # Raporları tabloya ekle
            for i, report in enumerate(corp_tax_reports):
                self.reports_table.insertRow(i)
                
                # Hesap dönemi
                period_start = report.get("period_start", "")
                period_end = report.get("period_end", "")
                period_text = f"{period_start} - {period_end}"
                period_item = QTableWidgetItem(period_text)
                self.reports_table.setItem(i, 0, period_item)
                
                # Oluşturulma tarihi
                created_at = report.get("created_at", "")
                try:
                    # ISO formatını tarihe dönüştür
                    created_date = datetime.fromisoformat(created_at)
                    created_text = created_date.strftime("%d.%m.%Y %H:%M")
                except:
                    created_text = created_at
                
                created_item = QTableWidgetItem(created_text)
                self.reports_table.setItem(i, 1, created_item)
                
                # Vergilendirilebilir kâr
                data = report.get("data", {})
                taxable_profit = data.get("taxable_profit", 0)
                profit_item = QTableWidgetItem(f"£{taxable_profit:,.2f}")
                profit_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.reports_table.setItem(i, 2, profit_item)
                
                # Vergi tutarı
                tax_due = data.get("tax_due", 0)
                tax_item = QTableWidgetItem(f"£{tax_due:,.2f}")
                tax_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.reports_table.setItem(i, 3, tax_item)
                
                # Durum
                status = report.get("status", "")
                status_map = {
                    "draft": "Taslak",
                    "submitted": "Gönderildi",
                    "accepted": "Kabul Edildi"
                }
                status_text = status_map.get(status, status)
                status_item = QTableWidgetItem(status_text)
                
                # Duruma göre renklendirme
                if status == "submitted" or status == "accepted":
                    status_item.setBackground(QColor(200, 255, 200))  # Açık yeşil
                
                self.reports_table.setItem(i, 4, status_item)
                
                # Rapor ID'sini gizli veri olarak sakla
                report_id = report.get("id")
                period_item.setData(Qt.UserRole, report_id)
            
        except Exception as e:
            QMessageBox.warning(
                self, "Raporları Yükleme Hatası", 
                f"Kaydedilmiş raporlar yüklenirken bir hata oluştu:\n{str(e)}"
            )
    
    def _load_saved_periods(self):
        """Kaydedilmiş hesap dönemlerini yükle"""
        try:
            # Kurumlar vergisi raporlarını veritabanından al
            all_tax_returns = self.ledger.get_tax_returns()
            corp_tax_reports = [
                report for report in all_tax_returns 
                if report.get("type") == "corporation_tax"
            ]
            
            # Combo box'ı temizle
            self.period_combo.clear()
            
            # Dönemleri ekle
            for report in corp_tax_reports:
                period_start = report.get("period_start", "")
                period_end = report.get("period_end", "")
                period_text = f"{period_start} - {period_end}"
                
                self.period_combo.addItem(period_text, report.get("id"))
            
        except Exception as e:
            print(f"Hesap dönemleri yüklenirken hata: {e}")
    
    def _view_report_details(self, index):
        """Rapor detaylarını görüntüle"""
        # Seçili satırın raporunu al
        row = index.row()
        report_id = self.reports_table.item(row, 0).data(Qt.UserRole)
        
        # Bu noktada, rapor detaylarını görüntüleyen bir dialog açılabilir
        # Basitlik için sadece bir mesaj kutusu gösterelim
        try:
            # Veritabanından raporu al
            report = self.ledger.get_tax_return_by_id(report_id)
            
            # Rapor verilerini formatla
            report_text = f"Rapor ID: {report.get('id')}\n"
            report_text += f"Hesap Dönemi: {report.get('period_start')} - {report.get('period_end')}\n"
            report_text += f"Durum: {report.get('status')}\n"
            report_text += f"Oluşturulma Tarihi: {report.get('created_at')}\n\n"
            
            data = report.get("data", {})
            report_text += f"Toplam Gelir: £{data.get('income', {}).get('total_income', 0):,.2f}\n"
            report_text += f"Toplam Gider: £{data.get('expenses', {}).get('total_expenses', 0):,.2f}\n"
            report_text += f"Vergilendirilebilir Kâr: £{data.get('taxable_profit', 0):,.2f}\n"
            report_text += f"Ödenmesi Gereken Vergi: £{data.get('tax_due', 0):,.2f}\n"
            report_text += f"Efektif Vergi Oranı: {data.get('effective_rate', 0):.2f}%\n"
            
            QMessageBox.information(
                self, "Rapor Detayları", report_text
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Hata", 
                f"Rapor detayları alınırken bir hata oluştu:\n{str(e)}"
            )
    
    def _view_selected_report(self):
        """Seçili raporu görüntüle"""
        # Seçili satırı al
        selected_items = self.reports_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir rapor seçin.")
            return
        
        # Seçili satırın raporunu al
        row = selected_items[0].row()
        report_id = self.reports_table.item(row, 0).data(Qt.UserRole)
        
        # Rapor detaylarını görüntüle
        try:
            report = self.ledger.get_tax_return_by_id(report_id)
            
            # Burada detaylı bir rapor görüntüleme dialog'u açılabilir
            # Basitlik için aynı mesaj kutusunu kullanıyoruz
            self._view_report_details(self.reports_table.model().index(row, 0))
            
        except Exception as e:
            QMessageBox.critical(
                self, "Hata", 
                f"Rapor detayları alınırken bir hata oluştu:\n{str(e)}"
            )
    
    def _delete_selected_report(self):
        """Seçili raporu sil"""
        # Seçili satırı al
        selected_items = self.reports_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Uyarı", "Lütfen bir rapor seçin.")
            return
        
        # Seçili satırın raporunu al
        row = selected_items[0].row()
        report_id = self.reports_table.item(row, 0).data(Qt.UserRole)
        
        # Silme onayı al
        reply = QMessageBox.question(
            self, "Raporu Sil", 
            "Seçili raporu silmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Raporu sil (veritabanı yapısına göre ayarlanmalı)
                success = self.ledger.delete_tax_return(report_id)
                
                if success:
                    # Tablodan satırı kaldır
                    self.reports_table.removeRow(row)
                    # Dönem listesini güncelle
                    self._load_saved_periods()
                    
                    QMessageBox.information(
                        self, "Başarılı", 
                        "Rapor başarıyla silindi."
                    )
                else:
                    QMessageBox.warning(
                        self, "Hata", 
                        "Rapor silinirken bir hata oluştu."
                    )
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Silme Hatası", 
                    f"Rapor silinirken bir hata oluştu:\n{str(e)}"
                )
    
    def _prepare_tax_return(self):
        """Kurumlar vergisi beyannamesi hazırla"""
        # Seçili dönem ID'sini al
        selected_index = self.period_combo.currentIndex()
        if selected_index < 0:
            QMessageBox.warning(
                self, "Uyarı", 
                "Lütfen bir hesap dönemi seçin."
            )
            return
        
        report_id = self.period_combo.itemData(selected_index)
        
        try:
            # Raporu veritabanından al
            report = self.ledger.get_tax_return_by_id(report_id)
            
            if not report:
                raise ValueError(f"Rapor bulunamadı: {report_id}")
            
            # Şirket bilgilerini al
            company_name = self.company_name_edit.text()
            company_crn = self.company_crn_edit.text()
            company_utr = self.company_utr_edit.text()
            
            # Beyanname verilerini hazırla
            period_start = report.get("period_start")
            period_end = report.get("period_end")
            data = report.get("data", {})
            
            tax_return = {
                "companyName": company_name,
                "companyRegistrationNumber": company_crn,
                "uniqueTaxpayerReference": company_utr,
                "accountingPeriod": {
                    "startDate": period_start,
                    "endDate": period_end
                },
                "income": {
                    "tradingIncome": data.get("income", {}).get("trading_income", 0),
                    "nonTradingIncome": data.get("income", {}).get("non_trading_income", 0),
                    "totalIncome": data.get("income", {}).get("total_income", 0)
                },
                "expenses": {
                    "tradingExpenses": data.get("expenses", {}).get("trading_expenses", 0),
                    "nonTradingExpenses": data.get("expenses", {}).get("non_trading_expenses", 0),
                    "totalExpenses": data.get("expenses", {}).get("total_expenses", 0)
                },
                "taxableProfit": data.get("taxable_profit", 0),
                "taxDue": data.get("tax_due", 0),
                "declaration": False  # İlk olarak onay işaretli değil
            }
            
            # Beyannameyi önizleme alanında göster
            self.return_preview.setPlainText(json.dumps(tax_return, indent=2))
            
            # Beyanname hazır, onay kutusu ve buton kontrolü
            self.finalize_return_checkbox.setEnabled(True)
            self._update_submit_button()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Beyanname Hazırlama Hatası", 
                f"Beyanname hazırlanırken bir hata oluştu:\n{str(e)}"
            )
    
    def _update_submit_button(self):
        """Onay kutusu durumuna göre gönder butonunu güncelle"""
        self.submit_return_button.setEnabled(self.finalize_return_checkbox.isChecked())
    
    def _submit_tax_return(self):
        """Beyannameyi HMRC'ye gönder"""
        if not self.finalize_return_checkbox.isChecked():
            return
        
        # Beyanname verilerini al
        try:
            tax_return_json = self.return_preview.toPlainText()
            tax_return = json.loads(tax_return_json)
            
            # Onay durumunu güncelle
            tax_return["declaration"] = True
            
            # Basitleştirilmiş gösterim için bilgi mesajı
            QMessageBox.information(
                self, "HMRC Beyanname Gönderimi", 
                "Bu fonksiyon, gerçek bir HMRC API entegrasyonu gerektirir.\n\n"
                "Gerçek bir uygulama, bu beyannameyi HMRC API'sine gönderecek ve "
                "onay referansı alacaktır.\n\n"
                "Gönderilecek beyanname içeriği önizlemede gösterilmektedir."
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Beyanname Gönderme Hatası", 
                f"Beyanname gönderilirken bir hata oluştu:\n{str(e)}"
            )
