#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Gösterge Paneli Modülü
Muhasebe verilerinin özet görünümü ve grafiksel sunumu.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
    QLabel, QFrame, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QGroupBox
)
from PyQt5.QtCore import Qt, QSize, QDate
from PyQt5.QtGui import QFont, QColor, QPainter, QBrush, QPen, QPixmap
from PyQt5.QtChart import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis, QValueAxis

from datetime import datetime, timedelta


class SummaryCard(QFrame):
    """Özet kart bileşeni"""
    
    def __init__(self, title, value, unit="£", change=None, color="#3498db", icon=None):
        """Kart başlatıcı
        
        Args:
            title: Kart başlığı
            value: Gösterilecek değer
            unit: Birim (£, %, vb.)
            change: Değişim yüzdesi
            color: Tema rengi
            icon: İkon (QPixmap nesnesi)
        """
        super().__init__()
        
        self.title = title
        self.value = value
        self.unit = unit
        self.change = change
        self.color = color
        self.icon = icon
        
        # Kart tasarımı
        self.setFrameShape(QFrame.StyledPanel)
        self.setStyleSheet(f"""
            SummaryCard {{
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
            }}
        """)
        
        # Ana Layout'u bir kez oluştur
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Başlık ve değer etiketlerini oluştur
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("color: #7f8c8d; font-size: 14px;")
        
        self.value_layout = QHBoxLayout()
        self.value_label = QLabel()
        self.value_label.setStyleSheet(f"color: {self.color}; font-size: 24px; font-weight: bold;")
        
        self.change_label = None
        if self.change is not None:
            self.change_label = QLabel()
            self.value_layout.addWidget(self.change_label)
        
        self.value_layout.addWidget(self.value_label)
        self.value_layout.addStretch()
        
        # İkon varsa ekle
        self.icon_label = None
        if self.icon:
            self.icon_label = QLabel()
            self.icon_label.setPixmap(self.icon.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.value_layout.addWidget(self.icon_label)
        
        # Widget'ları layout'a ekle
        self.main_layout.addWidget(self.title_label)
        self.main_layout.addLayout(self.value_layout)
        
        # Değerleri güncelle
        self.update_value(self.value)
    
    def update_value(self, new_value):
        """Kart değerini güncelle"""
        self.value = new_value
        self.value_label.setText(f"{self.unit}{self.value:,.2f}")
        
        # Değişim etiketi varsa güncelle
        if self.change_label and self.change is not None:
            change_color = "#2ecc71" if self.change >= 0 else "#e74c3c"
            change_prefix = "+" if self.change > 0 else ""
            self.change_label.setText(f"({change_prefix}{self.change:.1f}%)")
            self.change_label.setStyleSheet(f"color: {change_color}; font-size: 14px;")
        
        # İkon varsa güncelle
        if self.icon_label and self.icon:
            self.icon_label.setPixmap(self.icon.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))


class Dashboard(QWidget):
    """Gösterge paneli bileşeni"""
    
    def __init__(self, ledger, config):
        """Gösterge paneli başlatıcı
        
        Args:
            ledger: Muhasebe defteri nesnesi
            config: Uygulama yapılandırması
        """
        super().__init__()
        
        self.ledger = ledger
        self.config = config
        
        # UI kurulumu
        self._setup_ui()
        
        # İlk yükleme
        self.refresh()
    
    def _setup_ui(self):
        """UI kurulumu"""
        # Ana düzen
        main_layout = QVBoxLayout(self)
        
        # Özet kartları bölümü
        summary_layout = QHBoxLayout()
        
        # Gelir kartı
        self.income_card = SummaryCard("Toplam Gelir", 0, "£", None, "#3498db")
        summary_layout.addWidget(self.income_card)
        
        # Gider kartı
        self.expense_card = SummaryCard("Toplam Gider", 0, "£", None, "#e74c3c")
        summary_layout.addWidget(self.expense_card)
        
        # Kâr kartı
        self.profit_card = SummaryCard("Net Kâr", 0, "£", None, "#2ecc71")
        summary_layout.addWidget(self.profit_card)
        
        # KDV kartı
        self.vat_card = SummaryCard("Net KDV", 0, "£", None, "#9b59b6")
        summary_layout.addWidget(self.vat_card)
        
        # Banka kartı
        self.bank_card = SummaryCard("Banka Bakiyesi", 0, "£", None, "#f1c40f")
        summary_layout.addWidget(self.bank_card)
        
        main_layout.addLayout(summary_layout)
        
        # Grafik ve tablo bölümü
        content_layout = QHBoxLayout()
        
        # Sol taraf (grafikler)
        charts_layout = QVBoxLayout()
        
        # Gelir/Gider grafiği
        income_expense_group = QGroupBox("Gelir ve Gider Dağılımı")
        income_expense_layout = QVBoxLayout(income_expense_group)
        
        self.income_expense_chart = QChartView()
        self.income_expense_chart.setRenderHint(QPainter.Antialiasing)
        income_expense_layout.addWidget(self.income_expense_chart)
        
        charts_layout.addWidget(income_expense_group)
        
        # Aylık trend grafiği
        trend_group = QGroupBox("Aylık Trend")
        trend_layout = QVBoxLayout(trend_group)
        
        self.trend_chart = QChartView()
        self.trend_chart.setRenderHint(QPainter.Antialiasing)
        trend_layout.addWidget(self.trend_chart)
        
        charts_layout.addWidget(trend_group)
        
        content_layout.addLayout(charts_layout, 2)  # Ağırlık: 2
        
        # Sağ taraf (tablolar)
        tables_layout = QVBoxLayout()
        
        # Son işlemler tablosu
        transactions_group = QGroupBox("Son İşlemler")
        transactions_layout = QVBoxLayout(transactions_group)
        
        self.transactions_table = QTableWidget()
        self.transactions_table.setColumnCount(5)
        self.transactions_table.setHorizontalHeaderLabels([
            "Tarih", "Açıklama", "Gelir", "Gider", "Hesap"
        ])
        
        self.transactions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.transactions_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.transactions_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.transactions_table.setAlternatingRowColors(True)
        
        transactions_layout.addWidget(self.transactions_table)
        
        # Vadesi yaklaşan faturalar
        upcoming_group = QGroupBox("Vadesi Yaklaşan Faturalar")
        upcoming_layout = QVBoxLayout(upcoming_group)
        
        self.upcoming_table = QTableWidget()
        self.upcoming_table.setColumnCount(5)
        self.upcoming_table.setHorizontalHeaderLabels([
            "Vade Tarihi", "Fatura No", "Müşteri/Tedarikçi", "Tutar", "Durum"
        ])
        
        self.upcoming_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.upcoming_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.upcoming_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.upcoming_table.setAlternatingRowColors(True)
        
        upcoming_layout.addWidget(self.upcoming_table)
        
        tables_layout.addWidget(transactions_group)
        tables_layout.addWidget(upcoming_group)
        
        content_layout.addLayout(tables_layout, 1)  # Ağırlık: 1
        
        main_layout.addLayout(content_layout)
        
        # Alt kısım (KDV ve vergi hatırlatıcıları)
        self.reminders_layout = QHBoxLayout()
        
        # KDV hatırlatıcı
        self.vat_reminder = QLabel()
        self.vat_reminder.setStyleSheet("""
            background-color: #ecf0f1;
            border-radius: 5px;
            padding: 10px;
            color: #2c3e50;
        """)
        self.reminders_layout.addWidget(self.vat_reminder)
        
        # Vergi hatırlatıcı
        self.tax_reminder = QLabel()
        self.tax_reminder.setStyleSheet("""
            background-color: #ecf0f1;
            border-radius: 5px;
            padding: 10px;
            color: #2c3e50;
        """)
        self.reminders_layout.addWidget(self.tax_reminder)
        
        # Kurumlar vergisi hatırlatıcısı için yer tutucu
        self.corp_tax_reminder = QLabel()
        self.corp_tax_reminder.setStyleSheet("""
            background-color: #ecf0f1;
            border-radius: 5px;
            padding: 10px;
            color: #2c3e50;
        """)
        self.reminders_layout.addWidget(self.corp_tax_reminder)
        
        main_layout.addLayout(self.reminders_layout)
    
    def refresh(self):
        """Gösterge panelini yenile"""
        try:
            # Özet verileri al
            summary = self.ledger.get_summary_data()
            
            # Özet kartları güncelle
            self.income_card.update_value(summary["total_income"])
            self.expense_card.update_value(summary["total_expense"])
            self.profit_card.update_value(summary["total_profit"])
            self.vat_card.update_value(summary["net_vat"])
            self.bank_card.update_value(summary["bank_balance"])
            
            # Gelir/Gider grafiğini güncelle
            self._update_income_expense_chart(summary)
            
            # Aylık trend grafiğini güncelle
            self._update_trend_chart()
            
            # Son işlemler tablosunu güncelle
            self._update_recent_transactions()
            
            # Vadesi yaklaşan faturaları güncelle
            self._update_upcoming_invoices()
            
            # Hatırlatıcıları güncelle
            self._update_reminders()
            
        except Exception as e:
            print(f"Gösterge paneli yenilenirken hata oluştu: {e}")
    
    def _update_income_expense_chart(self, summary):
        """Gelir/Gider dağılım grafiğini güncelle"""
        # Pie chart oluştur
        series = QPieSeries()
        
        # Gelir ekle
        if summary["total_income"] > 0:
            income_slice = series.append("Gelir", summary["total_income"])
            income_slice.setBrush(QColor("#3498db"))
        
        # Gider ekle
        if summary["total_expense"] > 0:
            expense_slice = series.append("Gider", summary["total_expense"])
            expense_slice.setBrush(QColor("#e74c3c"))
        
        # Dilimlere etiket ekle
        for slice in series.slices():
            slice.setLabelVisible(True)
            percent = slice.percentage() * 100
            slice.setLabel(f"{slice.label()}: £{slice.value():,.2f} ({percent:.1f}%)")
        
        # Chart oluştur
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Gelir/Gider Dağılımı")
        chart.legend().setAlignment(Qt.AlignBottom)
        
        # Animate
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # Chart view güncelle
        self.income_expense_chart.setChart(chart)
    
    def _update_trend_chart(self):
        """Aylık trend grafiğini güncelle"""
        # Son 6 ayın verilerini al
        income_expense = self.ledger.get_income_expenses()
        
        # Son 6 ay için tarih aralıkları oluştur
        today = datetime.now()
        months = []
        month_data = {}
        
        for i in range(5, -1, -1):
            dt = today.replace(day=1) - timedelta(days=i*30)
            month_str = dt.strftime("%Y-%m")
            month_label = dt.strftime("%b %y")
            months.append(month_label)
            month_data[month_str] = {"income": 0, "expense": 0}
        
        # Gelirleri ve giderleri aylara göre grupla
        for item in income_expense:
            try:
                date = datetime.strptime(item["date"], "%Y-%m-%d")
                month_str = date.strftime("%Y-%m")
                
                if month_str in month_data:
                    month_data[month_str]["income"] += item["income"]
                    month_data[month_str]["expense"] += item["expense"]
            except ValueError:
                # Geçersiz tarih formatı, öğeyi atla
                pass
        
        # Bar chart için veri setleri oluştur
        income_set = QBarSet("Gelir")
        expense_set = QBarSet("Gider")
        
        income_set.setColor(QColor("#3498db"))
        expense_set.setColor(QColor("#e74c3c"))
        
        # Son 6 ay için verileri ekle
        month_keys = sorted(month_data.keys())[-6:]
        for month in month_keys:
            income_set.append(month_data[month]["income"])
            expense_set.append(month_data[month]["expense"])
        
        # Bar series oluştur
        series = QBarSeries()
        series.append(income_set)
        series.append(expense_set)
        
        # Chart oluştur
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Aylık Gelir/Gider Trendi")
        
        # Eksenler
        categories = QBarCategoryAxis()
        categories.append(months)
        chart.addAxis(categories, Qt.AlignBottom)
        series.attachAxis(categories)
        
        value_axis = QValueAxis()
        value_axis.setRange(0, max([max(income_set), max(expense_set)]) * 1.1)
        chart.addAxis(value_axis, Qt.AlignLeft)
        series.attachAxis(value_axis)
        
        # Animate
        chart.setAnimationOptions(QChart.SeriesAnimations)
        
        # Legend
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        
        # Chart view güncelle
        self.trend_chart.setChart(chart)
    
    def _update_recent_transactions(self):
        """Son işlemler tablosunu güncelle"""
        # Son 10 işlemi al
        transactions = self.ledger.get_all_transactions()
        transactions.sort(key=lambda x: x.get("date", ""), reverse=True)
        recent_transactions = transactions[:10]
        
        # Tabloyu temizle
        self.transactions_table.setRowCount(0)
        
        # İşlemleri tabloya ekle
        for i, trans in enumerate(recent_transactions):
            self.transactions_table.insertRow(i)
            
            # Tarih
            date_item = QTableWidgetItem(trans.get("date", ""))
            date_item.setTextAlignment(Qt.AlignCenter)
            self.transactions_table.setItem(i, 0, date_item)
            
            # Açıklama
            desc_item = QTableWidgetItem(trans.get("description", ""))
            self.transactions_table.setItem(i, 1, desc_item)
            
            # Gelir
            debit = trans.get("debit", 0)
            income_item = QTableWidgetItem(f"{debit:.2f}" if debit else "")
            income_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if debit:
                income_item.setForeground(QColor("#2ecc71"))
            self.transactions_table.setItem(i, 2, income_item)
            
            # Gider
            credit = trans.get("credit", 0)
            expense_item = QTableWidgetItem(f"{credit:.2f}" if credit else "")
            expense_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            if credit:
                expense_item.setForeground(QColor("#e74c3c"))
            self.transactions_table.setItem(i, 3, expense_item)
            
            # Hesap
            account_code = trans.get("account", "")
            account = self.ledger.get_account_by_code(account_code)
            account_name = account.get("name", "") if account else account_code
            account_item = QTableWidgetItem(account_name)
            self.transactions_table.setItem(i, 4, account_item)
    
    def _update_upcoming_invoices(self):
        """Vadesi yaklaşan faturaları güncelle"""
        # Tüm faturaları al
        invoices = self.ledger.get_all_invoices()
        
        # Ödenmemiş faturaları filtrele
        unpaid_invoices = [inv for inv in invoices if inv.get("payment_status", "") == "unpaid"]
        
        # Vade tarihine göre sırala
        try:
            unpaid_invoices.sort(key=lambda x: datetime.strptime(x.get("due_date", "9999-12-31"), "%Y-%m-%d"))
        except ValueError:
            # Geçersiz tarih formatı
            pass
        
        # Yaklaşan faturaları al (ilk 10)
        upcoming_invoices = unpaid_invoices[:10]
        
        # Tabloyu temizle
        self.upcoming_table.setRowCount(0)
        
        # Faturaları tabloya ekle
        for i, inv in enumerate(upcoming_invoices):
            self.upcoming_table.insertRow(i)
            
            # Vade tarihi
            due_date = inv.get("due_date", "")
            due_item = QTableWidgetItem(due_date)
            due_item.setTextAlignment(Qt.AlignCenter)
            
            # Vade tarihini kontrol et ve renklendirme yap
            try:
                due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
                today = datetime.now()
                
                if due_date_obj < today:
                    # Vadesi geçmiş
                    due_item.setBackground(QColor(255, 200, 200))
                elif (due_date_obj - today).days <= 7:
                    # Son 7 gün
                    due_item.setBackground(QColor(255, 235, 200))
            except ValueError:
                # Geçersiz tarih formatı
                pass
            
            self.upcoming_table.setItem(i, 0, due_item)
            
            # Fatura No
            invoice_no_item = QTableWidgetItem(inv.get("invoice_number", ""))
            self.upcoming_table.setItem(i, 1, invoice_no_item)
            
            # Müşteri/Tedarikçi
            entity_item = QTableWidgetItem(inv.get("entity_name", ""))
            self.upcoming_table.setItem(i, 2, entity_item)
            
            # Tutar
            amount = inv.get("amount", 0) + inv.get("vat", 0)
            amount_item = QTableWidgetItem(f"{amount:.2f}")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            # Fatura tipine göre renklendirme
            if inv.get("type") == "sales":
                amount_item.setForeground(QColor("#2ecc71"))
            else:
                amount_item.setForeground(QColor("#e74c3c"))
            
            self.upcoming_table.setItem(i, 3, amount_item)
            
            # Durum
            status_item = QTableWidgetItem(inv.get("payment_status", ""))
            status_item.setTextAlignment(Qt.AlignCenter)
            self.upcoming_table.setItem(i, 4, status_item)
    
    def _update_reminders(self):
        """Hatırlatıcıları güncelle"""
        # KDV hatırlatıcısı (varsayılan olarak her 3 ayda bir)
        current_date = datetime.now()
        last_day_of_quarter = QDate(current_date.year, ((current_date.month - 1) // 3) * 3 + 3, 1)
        last_day_of_quarter = last_day_of_quarter.addDays(last_day_of_quarter.daysInMonth() - 1)
        
        days_to_vat = (last_day_of_quarter.toPyDate() - current_date.date()).days + 7  # 7 gün ek süre
        
        if days_to_vat <= 14:
            self.vat_reminder.setText(f"<b>KDV Hatırlatma:</b> KDV beyannamesinin gönderilmesine {days_to_vat} gün kaldı.")
            self.vat_reminder.setStyleSheet("""
                background-color: #fadbd8;
                border-radius: 5px;
                padding: 10px;
                color: #c0392b;
            """)
        else:
            self.vat_reminder.setText(f"<b>KDV Hatırlatma:</b> KDV beyannamesinin gönderilmesine {days_to_vat} gün var.")
            self.vat_reminder.setStyleSheet("""
                background-color: #ecf0f1;
                border-radius: 5px;
                padding: 10px;
                color: #2c3e50;
            """)
        
        # Gelir vergisi hatırlatıcısı (İngiltere'de vergi beyannamesi 31 Ocak'ta son bulur)
        tax_deadline = QDate(current_date.year, 1, 31)
        
        if current_date.month > 1:
            tax_deadline = tax_deadline.addYears(1)
        
        days_to_tax = (tax_deadline.toPyDate() - current_date.date()).days
        
        if days_to_tax <= 31:
            self.tax_reminder.setText(f"<b>Vergi Hatırlatma:</b> Gelir vergisi beyannamesinin gönderilmesine {days_to_tax} gün kaldı.")
            self.tax_reminder.setStyleSheet("""
                background-color: #fadbd8;
                border-radius: 5px;
                padding: 10px;
                color: #c0392b;
            """)
        else:
            self.tax_reminder.setText(f"<b>Vergi Hatırlatma:</b> Gelir vergisi beyannamesinin gönderilmesine {days_to_tax} gün var.")
            self.tax_reminder.setStyleSheet("""
                background-color: #ecf0f1;
                border-radius: 5px;
                padding: 10px;
                color: #2c3e50;
            """)
        
        # Kurumlar vergisi hatırlatıcısı
        try:
            # Şirket bilgilerini al
            company_info = self.ledger.get_company_info()
            
            # Kurumlar vergisi hesaplayıcısı oluştur
            from hmrc.corporate_tax import CorporateTaxCalculator
            corp_tax_calc = CorporateTaxCalculator(self.ledger)
            
            # Sonraki beyanname son tarihini al
            filing_deadline, days_remaining = corp_tax_calc.get_next_filing_deadline(company_info)
            
            if filing_deadline and days_remaining is not None:
                # Hatırlatıcıyı güncelle
                if days_remaining <= 60:
                    self.corp_tax_reminder.setText(f"<b>Kurumlar Vergisi Hatırlatma:</b> Beyanname son tarihi: {filing_deadline} ({days_remaining} gün kaldı).")
                    self.corp_tax_reminder.setStyleSheet("""
                        background-color: #fadbd8;
                        border-radius: 5px;
                        padding: 10px;
                        color: #c0392b;
                    """)
                else:
                    self.corp_tax_reminder.setText(f"<b>Kurumlar Vergisi Hatırlatma:</b> Beyanname son tarihi: {filing_deadline} ({days_remaining} gün kaldı).")
                    self.corp_tax_reminder.setStyleSheet("""
                        background-color: #ecf0f1;
                        border-radius: 5px;
                        padding: 10px;
                        color: #2c3e50;
                    """)
                self.corp_tax_reminder.setVisible(True)
            else:
                # Bilgi yoksa hatırlatıcıyı gizle
                self.corp_tax_reminder.setVisible(False)
        except Exception as e:
            # Hata durumunda hatırlatıcıyı gizle
            self.corp_tax_reminder.setVisible(False)
            print(f"Kurumlar vergisi hatırlatıcısı oluşturulurken hata: {e}")
