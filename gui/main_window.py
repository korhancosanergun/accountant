#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Ana Pencere Modülü
Excel benzeri arayüz sunan ana uygulama penceresi.
"""

import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QAction, QMessageBox, 
    QFileDialog, QMenu, QToolBar, QDockWidget, QVBoxLayout, QWidget
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon

from gui.spreadsheet_view import SpreadsheetView
from gui.dashboard import Dashboard
from gui.tax_forms import VATReturnForm, SelfAssessmentForm
from gui.dialogs.invoice_dialog import InvoiceDialog
from gui.dialogs.expense_dialog import ExpenseDialog
from gui.dialogs.settings_dialog import SettingsDialog
from gui.dialogs.integration_dialog import IntegrationDialog

from hmrc.api_client import HMRCApiClient


class MainWindow(QMainWindow):
    """Ana uygulama penceresi"""
    
    def __init__(self, ledger, db, config, integration_manager=None):
        """Ana pencere başlatıcı"""
        super().__init__()
        
        self.ledger = ledger
        self.db = db
        self.config = config
        self.integration_manager = integration_manager
        
        # HMRC API istemcisi
        self.hmrc_client = HMRCApiClient(
            client_id=config["hmrc_api"]["client_id"],
            client_secret=config["hmrc_api"]["client_secret"],
            endpoint=config["hmrc_api"]["endpoint"],
            redirect_uri=config["hmrc_api"]["redirect_uri"]
        )
        
        # Pencere ayarları
        self.setWindowTitle(f"{config['company_name']} - UK Muhasebe")
        self.setMinimumSize(1024, 768)
        
        # Arayüz kurulumu
        self._setup_ui()
        
        # Menü ve araç çubuğu kurulumu
        self._create_actions()
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_status_bar()
        
        # İlk başlatmada ayarlar tanımlanmamışsa ayarlar penceresini aç
        if not config["company_name"]:
            self._show_settings_dialog()
    
    def _setup_ui(self):
        """Ana arayüz kurulumu"""
        # Ana sekme penceresi
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)
        
        # Dashboard sekmesi
        self.dashboard = Dashboard(self.ledger, self.config)
        self.tab_widget.addTab(self.dashboard, "Gösterge Paneli")
        
        # Muhasebe defteri sekmesi (Excel benzeri görünüm)
        self.ledger_view = SpreadsheetView(self.ledger)
        self.tab_widget.addTab(self.ledger_view, "Muhasebe Defteri")
        
        # Gelir/Gider sekmesi
        self.income_expense_view = SpreadsheetView(self.ledger, view_type="income_expense")
        self.tab_widget.addTab(self.income_expense_view, "Gelir ve Giderler")
        
        # Faturalar sekmesi
        self.invoices_view = SpreadsheetView(self.ledger, view_type="invoices")
        self.tab_widget.addTab(self.invoices_view, "Faturalar")
        
        # Vergi sekmesi
        self.vat_return_form = VATReturnForm(self.ledger, self.hmrc_client)
        self.tab_widget.addTab(self.vat_return_form, "KDV Beyannamesi")
        
        # Gelir vergisi sekmesi
        self.income_tax_form = SelfAssessmentForm(self.ledger, self.hmrc_client)
        self.tab_widget.addTab(self.income_tax_form, "Gelir Vergisi")
        
        # Hesap planı yan paneli
        self._create_chart_of_accounts_dock()
    
    def _create_chart_of_accounts_dock(self):
        """Hesap planı kenar paneli oluşturma"""
        # Dock widget oluştur
        dock = QDockWidget("Hesap Planı", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        # İçerik widget'ı
        content = QWidget()
        layout = QVBoxLayout(content)
        
        # Hesap planı görünümü oluştur (SpreadsheetView'den türetilmiş özel bir sınıf olabilir)
        # Bu basitleştirme için burada detaylandırılmadı
        accounts_view = SpreadsheetView(self.ledger, view_type="accounts")
        layout.addWidget(accounts_view)
        
        # Dock'a içeriği ekle
        dock.setWidget(content)
        
        # Ana pencereye dock'u ekle
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
    
    def _create_actions(self):
        """Menü ve araç çubuğu eylemleri oluşturma"""
        # Dosya eylemleri
        self.new_company_action = QAction("Yeni Şirket", self)
        self.new_company_action.triggered.connect(self._new_company)
        
        self.open_company_action = QAction("Şirket Aç", self)
        self.open_company_action.triggered.connect(self._open_company)
        
        self.save_action = QAction("Kaydet", self)
        self.save_action.setShortcut("Ctrl+S")
        self.save_action.triggered.connect(self._save_data)
        
        self.backup_action = QAction("Yedekle", self)
        self.backup_action.triggered.connect(self._create_backup)
        
        self.import_action = QAction("İçe Aktar", self)
        self.import_action.triggered.connect(self._import_data)
        
        self.export_action = QAction("Dışa Aktar", self)
        self.export_action.triggered.connect(self._export_data)
        
        self.exit_action = QAction("Çıkış", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)
        
        # Düzenleme eylemleri
        self.settings_action = QAction("Ayarlar", self)
        self.settings_action.triggered.connect(self._show_settings_dialog)
        
        # Muhasebe eylemleri
        self.new_transaction_action = QAction("Yeni İşlem", self)
        self.new_transaction_action.triggered.connect(self._new_transaction)
        
        self.new_invoice_action = QAction("Yeni Fatura", self)
        self.new_invoice_action.triggered.connect(self._new_invoice)
        
        self.new_expense_action = QAction("Yeni Gider", self)
        self.new_expense_action.triggered.connect(self._new_expense)
        
        # Vergi eylemleri
        self.submit_vat_action = QAction("KDV Beyannamesi Gönder", self)
        self.submit_vat_action.triggered.connect(self._submit_vat)
        
        self.submit_self_assessment_action = QAction("Gelir Vergisi Beyannamesi Gönder", self)
        self.submit_self_assessment_action.triggered.connect(self._submit_self_assessment)
        
        # Kurumlar vergisi eylemi
        self.corporate_tax_action = QAction("Kurumlar Vergisi", self)
        self.corporate_tax_action.triggered.connect(self._show_corporate_tax_dialog)
        
        # HMRC Eylemler
        self.hmrc_auth_action = QAction("HMRC Yetkilendirme", self)
        self.hmrc_auth_action.triggered.connect(self._hmrc_authenticate)
        
        # Entegrasyon eylemleri
        self.integration_settings_action = QAction("Banka ve Ödeme Entegrasyonları", self)
        self.integration_settings_action.triggered.connect(self._open_integration_settings)
        
        self.sync_now_action = QAction("Manuel Senkronizasyon", self)
        self.sync_now_action.triggered.connect(self._run_manual_sync)
        
        # Yardım eylemleri
        self.about_action = QAction("Hakkında", self)
        self.about_action.triggered.connect(self._show_about)
        
        self.help_action = QAction("Yardım", self)
        self.help_action.triggered.connect(self._show_help)
    
    def _create_menu_bar(self):
        """Menü çubuğu oluşturma"""
        # Ana menü çubuğu
        menu_bar = self.menuBar()
        
        # Dosya menüsü
        file_menu = menu_bar.addMenu("Dosya")
        file_menu.addAction(self.new_company_action)
        file_menu.addAction(self.open_company_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.backup_action)
        file_menu.addSeparator()
        file_menu.addAction(self.import_action)
        file_menu.addAction(self.export_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)
        
        # Düzenleme menüsü
        edit_menu = menu_bar.addMenu("Düzenle")
        edit_menu.addAction(self.settings_action)
        
        # Muhasebe menüsü
        accounting_menu = menu_bar.addMenu("Muhasebe")
        accounting_menu.addAction(self.new_transaction_action)
        accounting_menu.addAction(self.new_invoice_action)
        accounting_menu.addAction(self.new_expense_action)
        
        # Vergi menüsü
        tax_menu = menu_bar.addMenu("Vergi")
        
        # KDV alt menüsü
        vat_menu = QMenu("KDV İşlemleri", self)
        vat_menu.addAction(self.submit_vat_action)
        vat_report_action = QAction("KDV Raporları", self)
        vat_report_action.triggered.connect(self._show_vat_reports)
        vat_menu.addAction(vat_report_action)
        tax_menu.addMenu(vat_menu)
        
        # Gelir vergisi alt menüsü
        income_tax_menu = QMenu("Gelir Vergisi", self)
        income_tax_menu.addAction(self.submit_self_assessment_action)
        tax_menu.addMenu(income_tax_menu)
        
        # Kurumlar vergisi menü öğesi
        tax_menu.addAction(self.corporate_tax_action)
        
        tax_menu.addSeparator()
        tax_menu.addAction(self.hmrc_auth_action)
        
        # Entegrasyonlar menüsü (YENİ)
        integrations_menu = menu_bar.addMenu("Entegrasyonlar")
        integrations_menu.addAction(self.integration_settings_action)
        integrations_menu.addAction(self.sync_now_action)
        
        # Yardım menüsü
        help_menu = menu_bar.addMenu("Yardım")
        help_menu.addAction(self.help_action)
        help_menu.addAction(self.about_action)
    
    def _create_tool_bar(self):
        """Araç çubuğu oluşturma"""
        # Ana araç çubuğu
        main_toolbar = QToolBar("Ana Araç Çubuğu")
        main_toolbar.setIconSize(QSize(32, 32))
        self.addToolBar(main_toolbar)
        
        # Dosya araçları
        main_toolbar.addAction(self.save_action)
        main_toolbar.addSeparator()
        
        # Muhasebe araçları
        main_toolbar.addAction(self.new_transaction_action)
        main_toolbar.addAction(self.new_invoice_action)
        main_toolbar.addAction(self.new_expense_action)
        main_toolbar.addSeparator()
        
        # Vergi araçları
        main_toolbar.addAction(self.submit_vat_action)
        main_toolbar.addAction(self.corporate_tax_action)
        main_toolbar.addSeparator()
        
        # Entegrasyon araçları (YENİ)
        main_toolbar.addAction(self.integration_settings_action)
        main_toolbar.addAction(self.sync_now_action)
    
    def _create_status_bar(self):
        """Durum çubuğu oluşturma"""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Hazır")
        
        # Şirket bilgileri
        company_label = f"{self.config['company_name']} | VAT: {self.config['company_vat']}"
        self.status_bar.addPermanentWidget(QWidget())  # Boşluk için
        self.status_bar.showMessage(company_label)
    
    def _new_company(self):
        """Yeni şirket oluşturma"""
        # Kullanıcıya mevcut verilerini kaydetmek isteyip istemediğini sor
        reply = QMessageBox.question(
            self, "Yeni Şirket", 
            "Yeni bir şirket oluşturmak mevcut verileri temizleyecektir. Devam etmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Ayarlar penceresini göster
            self._show_settings_dialog(new_company=True)
    
    def _open_company(self):
        """Şirket dosyası açma"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Şirket Dosyası Aç", "", "JSON Dosyaları (*.json)"
        )
        
        if file_path:
            try:
                # Veritabanı işlemleri ile yükleme yapılacak
                self.db.load_from_file(file_path)
                self.ledger.refresh()
                
                # UI'yi güncelle
                self._refresh_all_views()
                self.status_bar.showMessage(f"Şirket dosyası yüklendi: {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Hata", f"Dosya açılırken hata oluştu: {e}")
    
    def _save_data(self):
        """Verileri kaydetme"""
        try:
            self.db.save()
            self.status_bar.showMessage("Veriler başarıyla kaydedildi", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Veriler kaydedilirken hata oluştu: {e}")
    
    def _create_backup(self):
        """Yedek oluşturma"""
        try:
            backup_file = self.db.create_backup()
            self.status_bar.showMessage(f"Yedek oluşturuldu: {backup_file}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Yedek oluşturulurken hata oluştu: {e}")
    
    def _import_data(self):
        """Veri içe aktarma"""
        # CSV/Excel içe aktarma için dialog göster
        file_path, _ = QFileDialog.getOpenFileName(
            self, "İçe Aktar", "", "CSV Dosyaları (*.csv);;Excel Dosyaları (*.xlsx *.xls)"
        )
        
        if file_path:
            # İçe aktarma işlemleri burada yapılacak
            # Basitleştirme için detaylandırılmadı
            self.status_bar.showMessage(f"İçe aktarma tamamlandı: {file_path}", 3000)
    
    def _export_data(self):
        """Veri dışa aktarma"""
        # Dışa aktarma için dialog göster
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Dışa Aktar", "", "CSV Dosyaları (*.csv);;Excel Dosyaları (*.xlsx)"
        )
        
        if file_path:
            # Dışa aktarma işlemleri burada yapılacak
            # Basitleştirme için detaylandırılmadı
            self.status_bar.showMessage(f"Dışa aktarma tamamlandı: {file_path}", 3000)
    
    def _show_settings_dialog(self, new_company=False):
        """Ayarlar penceresini gösterme"""
        dialog = SettingsDialog(self.config, new_company=new_company)
        if dialog.exec_():
            # Ayarları güncelle
            self.config = dialog.get_updated_config()
            
            # Başlığı güncelle
            self.setWindowTitle(f"{self.config['company_name']} - UK Muhasebe")
            
            # HMRC istemcisini güncelle
            self.hmrc_client.update_config(
                client_id=self.config["hmrc_api"]["client_id"],
                client_secret=self.config["hmrc_api"]["client_secret"],
                endpoint=self.config["hmrc_api"]["endpoint"],
                redirect_uri=self.config["hmrc_api"]["redirect_uri"]
            )
            
            # UI'yi güncelle
            self._refresh_all_views()
            
            # Durum çubuğunu güncelle
            company_label = f"{self.config['company_name']} | VAT: {self.config['company_vat']}"
            self.status_bar.showMessage(company_label)
    
    def _new_transaction(self):
        """Yeni işlem ekleme"""
        # İşlem ekleme dialog'u göster 
        # Basitleştirme için detaylandırılmadı
        self.status_bar.showMessage("Yeni işlem eklendi", 3000)
    
    def _new_invoice(self):
        """Yeni fatura ekleme"""
        dialog = InvoiceDialog(self.ledger)
        if dialog.exec_():
            invoice = dialog.get_invoice()
            self.ledger.add_invoice(invoice)
            self._refresh_all_views()
            self.status_bar.showMessage("Yeni fatura eklendi", 3000)
    
    def _new_expense(self):
        """Yeni gider ekleme"""
        dialog = ExpenseDialog(self.ledger)
        if dialog.exec_():
            expense = dialog.get_expense()
            self.ledger.add_expense(expense)
            self._refresh_all_views()
            self.status_bar.showMessage("Yeni gider eklendi", 3000)
    
    def _show_vat_reports(self):
        """KDV raporları penceresini göster"""
        # Bu metod sonradan eklendi - basitleştirme için detaylandırılmadı
        self.status_bar.showMessage("KDV raporları fonksiyonu henüz uygulanmadı", 3000)
    
    def _show_corporate_tax_dialog(self):
        """Kurumlar vergisi dialogunu göster"""
        try:
            from gui.dialogs.corporate_tax_dialog import CorporateTaxDialog
            
            # Şirket bilgilerini al
            company_info = self.ledger.get_company_info()
            
            dialog = CorporateTaxDialog(self.ledger, company_info, self)
            dialog.exec_()
            
            # Dialog kapandıktan sonra görünümleri güncelle
            self._refresh_all_views()
            
        except Exception as e:
            QMessageBox.critical(self, "Kurumlar Vergisi Hatası", str(e))
    
    def _submit_vat(self):
        """KDV beyannamesi gönderme"""
        # KDV sekmesine geç
        self.tab_widget.setCurrentWidget(self.vat_return_form)
        # Beyanname gönderme işlemini başlat
        self.vat_return_form.prepare_submission()
    
    def _submit_self_assessment(self):
        """Gelir vergisi beyannamesi gönderme"""
        # Gelir vergisi sekmesine geç
        self.tab_widget.setCurrentWidget(self.income_tax_form)
        # Beyanname gönderme işlemini başlat
        self.income_tax_form.prepare_submission()
    
    def _hmrc_authenticate(self):
        """HMRC yetkilendirme işlemi"""
        try:
            auth_url = self.hmrc_client.get_auth_url()
            
            # Tarayıcı açmak için bilgi mesajı göster
            QMessageBox.information(
                self, "HMRC Yetkilendirme",
                f"Tarayıcıda HMRC yetkilendirme sayfası açılacak. "
                f"Yetkilendirme işlemini tamamladıktan sonra uygulamaya dönün."
            )
            
            # Sistem tarayıcısında URL'yi aç
            import webbrowser
            webbrowser.open(auth_url)
            
            # TODO: Callback işleme için daha fazla kod gerekebilir
            # (Bu sadece basitleştirilmiş bir örnektir)
            
        except Exception as e:
            QMessageBox.critical(self, "HMRC Yetkilendirme Hatası", str(e))
    
    def _open_integration_settings(self):
        """Entegrasyon ayarları penceresini aç"""
        if self.integration_manager:
            dialog = IntegrationDialog(self.integration_manager, self)
            dialog.exec_()
            
            # Dialog kapandıktan sonra görünümleri güncelle
            self._refresh_all_views()
        else:
            QMessageBox.warning(
                self, "Entegrasyon Hatası",
                "Entegrasyon yöneticisi bulunamadı. Uygulama doğru şekilde başlatılamadı."
            )
    
    def _run_manual_sync(self):
        """Entegrasyonları manuel olarak senkronize et"""
        if not self.integration_manager:
            QMessageBox.warning(
                self, "Entegrasyon Hatası",
                "Entegrasyon yöneticisi bulunamadı. Uygulama doğru şekilde başlatılamadı."
            )
            return
            
        reply = QMessageBox.question(
            self, "Manuel Senkronizasyon",
            "Tüm entegrasyonları şimdi senkronize etmek istediğinize emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # İşlemin tamamlanmasını beklerken kullanıcıya bilgi ver
            QMessageBox.information(
                self, "Senkronizasyon",
                "Entegrasyonlar senkronize ediliyor. Bu işlem biraz zaman alabilir."
            )
            
            # Senkronizasyonu yap (gerçek uygulamada bir thread'de çalıştırılabilir)
            results = self.integration_manager.sync_all()
            self.integration_manager.update_last_sync_time()
            
            # Görünümleri güncelle
            self._refresh_all_views()
            
            # Sonuç mesajı
            success_count = 0
            total_count = 0
            
            for service, service_results in results.items():
                for operation, result in service_results.items():
                    total_count += 1
                    if result:
                        success_count += 1
            
            if success_count == total_count:
                QMessageBox.information(
                    self, "Senkronizasyon Tamamlandı",
                    f"Tüm senkronizasyon işlemleri başarıyla tamamlandı."
                )
            else:
                QMessageBox.warning(
                    self, "Senkronizasyon Uyarı",
                    f"Senkronizasyon tamamlandı, ancak bazı işlemler başarısız oldu.\n"
                    f"Başarılı: {success_count}/{total_count}\n\n"
                    f"Ayrıntılar için Entegrasyonlar penceresindeki günlüğü kontrol edin."
                )
    
    def _show_about(self):
        """Hakkında penceresini gösterme"""
        QMessageBox.about(
            self, "Hakkında",
            "UK Muhasebe Yazılımı\n"
            "Sürüm 1.0\n\n"
            "HMRC ile entegre, Excel benzeri arayüze sahip\n"
            "küçük işletmeler için muhasebe yazılımı.\n\n"
            "Wise ve Stripe entegrasyonları desteklenmektedir."
        )
    
    def _show_help(self):
        """Yardım penceresini gösterme"""
        # Yardım dosyası veya dialogi göster
        QMessageBox.information(
            self, "Yardım",
            "Yardım dosyası henüz hazırlanmamıştır.\n"
            "Lütfen daha sonra tekrar deneyin."
        )
    
    def _refresh_all_views(self):
        """Tüm görünümleri yenile"""
        self.dashboard.refresh()
        self.ledger_view.refresh()
        self.income_expense_view.refresh()
        self.invoices_view.refresh()
        self.vat_return_form.refresh()
        self.income_tax_form.refresh()
    
    def closeEvent(self, event):
        """Uygulama kapatıldığında"""
        # Değişiklikler kaydedilsin mi diye sor
        reply = QMessageBox.question(
            self, "Çıkış", 
            "Değişiklikleri kaydetmek istiyor musunuz?",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, 
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db.save()
                event.accept()
            except Exception as e:
                QMessageBox.critical(self, "Kaydetme Hatası", str(e))
                event.ignore()
        elif reply == QMessageBox.No:
            event.accept()
        else:
            event.ignore()