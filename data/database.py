#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Veritabanı Modülü
JSON tabanlı veritabanı işlemleri.
"""

import os
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path


class Database:
    """JSON veritabanı yöneticisi"""
    
    def __init__(self, db_file, backup_dir):
        """Veritabanı başlatıcı
        
        Args:
            db_file: Veritabanı dosya yolu
            backup_dir: Yedekleme dizini
        """
        self.db_file = Path(db_file)
        self.backup_dir = Path(backup_dir)
        self.logger = logging.getLogger(__name__)
        
        # Veritabanı şeması
        self.data = {
            "metadata": {
                "version": "1.0.0",
                "last_updated": datetime.now().isoformat(),
                "company_info": {}
            },
            "chart_of_accounts": [],
            "transactions": [],
            "invoices": [],
            "expenses": [],
            "customers": [],
            "suppliers": [],
            "vat_returns": [],
            "tax_returns": []
        }
        
        # Dizinlerin var olduğundan emin ol
        os.makedirs(self.db_file.parent, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Veritabanını yükle
        self._load_database()
    
    def _load_database(self):
        """Veritabanı dosyasını yükle"""
        if not self.db_file.exists():
            self.logger.info(f"Veritabanı dosyası bulunamadı, yeni oluşturuluyor: {self.db_file}")
            self.save()
            return
        
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.logger.info(f"Veritabanı başarıyla yüklendi: {self.db_file}")
        except Exception as e:
            self.logger.error(f"Veritabanı yüklenirken hata: {e}")
            # Bozuk veritabanı dosyasını yedekle
            self._backup_corrupt_database()
            # Yeni bir veritabanı oluştur
            self.save()
    
    def save(self):
        """Veritabanını kaydet"""
        try:
            # Metadata'yı güncelle
            self.data["metadata"]["last_updated"] = datetime.now().isoformat()
            
            # JSON dosyasına kaydet
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Veritabanı başarıyla kaydedildi: {self.db_file}")
            return True
        except Exception as e:
            self.logger.error(f"Veritabanı kaydedilirken hata: {e}")
            return False
    
    def _backup_corrupt_database(self):
        """Bozuk veritabanı dosyasını yedekle"""
        if not self.db_file.exists():
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"corrupt_db_{timestamp}.json"
        
        try:
            shutil.copy2(self.db_file, backup_file)
            self.logger.warning(f"Bozuk veritabanı yedeklendi: {backup_file}")
        except Exception as e:
            self.logger.error(f"Bozuk veritabanı yedeklenirken hata: {e}")
    
    def create_backup(self):
        """Manuel yedek oluştur"""
        if not self.db_file.exists():
            self.logger.error("Yedeklenecek veritabanı dosyası bulunamadı")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"db_backup_{timestamp}.json"
        
        try:
            shutil.copy2(self.db_file, backup_file)
            self.logger.info(f"Veritabanı başarıyla yedeklendi: {backup_file}")
            return str(backup_file)
        except Exception as e:
            self.logger.error(f"Veritabanı yedeklenirken hata: {e}")
            return None
    
    def load_from_file(self, file_path):
        """Farklı bir veritabanı dosyasından yükle"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Dosya bulunamadı: {file_path}")
        
        try:
            # Önce mevcut veritabanını yedekle
            self.create_backup()
            
            # Yeni dosyayı yükle
            with open(file_path, 'r', encoding='utf-8') as f:
                new_data = json.load(f)
            
            # Şema uyumluluğunu doğrula
            self._validate_schema(new_data)
            
            # Verileri güncelle
            self.data = new_data
            
            # Değişiklikleri kaydet
            self.save()
            
            self.logger.info(f"Veritabanı başarıyla yüklendi: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Veritabanı yüklenirken hata: {e}")
            raise
    
    def _validate_schema(self, data):
        """Veritabanı şemasını doğrula"""
        required_keys = [
            "metadata", "chart_of_accounts", "transactions", 
            "invoices", "expenses", "customers", "suppliers"
        ]
        
        for key in required_keys:
            if key not in data:
                raise ValueError(f"Geçersiz veritabanı şeması: '{key}' anahtarı eksik")
        
        if "version" not in data["metadata"]:
            raise ValueError("Geçersiz veritabanı şeması: 'metadata.version' eksik")
    
    def clear_database(self):
        """Veritabanını temizle (yeni şirket oluşturma için)"""
        # Önce mevcut veritabanını yedekle
        self.create_backup()
        
        # Veritabanını sıfırla ama metadata'yı koru
        metadata = self.data["metadata"].copy()
        
        self.data = {
            "metadata": metadata,
            "chart_of_accounts": [],
            "transactions": [],
            "invoices": [],
            "expenses": [],
            "customers": [],
            "suppliers": [],
            "vat_returns": [],
            "tax_returns": []
        }
        
        # Değişiklikleri kaydet
        self.save()
        self.logger.info("Veritabanı temizlendi")
    
    def update_company_info(self, company_info):
        """Şirket bilgilerini güncelle"""
        self.data["metadata"]["company_info"] = company_info
        self.save()
    
    def get_company_info(self):
        """Şirket bilgilerini al"""
        return self.data["metadata"].get("company_info", {})
    
    # Muhasebe defteri işlemleri
    
    def get_all_transactions(self):
        """Tüm işlemleri al"""
        return self.data["transactions"]
    
    def add_transaction(self, transaction):
        """Yeni işlem ekle"""
        if not isinstance(transaction, dict):
            raise ValueError("İşlem bir sözlük olmalıdır")
        
        # İşlem ID'si atama (basit artırımlı)
        if "id" not in transaction:
            # Mevcut en yüksek ID'yi bul
            max_id = 0
            for t in self.data["transactions"]:
                if "id" in t and isinstance(t["id"], int) and t["id"] > max_id:
                    max_id = t["id"]
            
            transaction["id"] = max_id + 1
        
        # Tarih alanını kontrol et
        if "date" not in transaction:
            transaction["date"] = datetime.now().strftime("%Y-%m-%d")
        
        # İşlemi ekle
        self.data["transactions"].append(transaction)
        self.save()
        
        return transaction["id"]
    
    def update_transaction(self, transaction_id, updated_data):
        """İşlem güncelle"""
        for i, transaction in enumerate(self.data["transactions"]):
            if transaction.get("id") == transaction_id:
                # ID'yi koruyarak güncelle
                updated_data["id"] = transaction_id
                self.data["transactions"][i] = updated_data
                self.save()
                return True
        
        return False
    
    def delete_transaction(self, transaction_id):
        """İşlem sil"""
        for i, transaction in enumerate(self.data["transactions"]):
            if transaction.get("id") == transaction_id:
                del self.data["transactions"][i]
                self.save()
                return True
        
        return False
    
    def get_transaction_by_id(self, transaction_id):
        """ID'ye göre işlem getir"""
        for transaction in self.data["transactions"]:
            if transaction.get("id") == transaction_id:
                return transaction
        return None
    
    def filter_transactions(self, start_date=None, end_date=None, account_code=None, type=None):
        """İşlemleri filtrele"""
        filtered_transactions = self.data["transactions"]
        
        # Tarih filtreleme
        if start_date:
            filtered_transactions = [t for t in filtered_transactions 
                                    if t.get("date", "") >= start_date]
        
        if end_date:
            filtered_transactions = [t for t in filtered_transactions 
                                    if t.get("date", "") <= end_date]
        
        # Hesap kodu filtreleme
        if account_code:
            filtered_transactions = [t for t in filtered_transactions 
                                    if any(entry.get("account_code") == account_code 
                                          for entry in t.get("entries", []))]
        
        # İşlem tipi filtreleme
        if type:
            filtered_transactions = [t for t in filtered_transactions 
                                    if t.get("type") == type]
        
        return filtered_transactions
    
    # Hesap planı işlemleri
    
    def get_chart_of_accounts(self):
        """Hesap planını al"""
        return self.data["chart_of_accounts"]
    
    def add_account(self, account):
        """Yeni hesap ekle"""
        if not isinstance(account, dict):
            raise ValueError("Hesap bir sözlük olmalıdır")
        
        # Hesap kodu benzersiz olmalı
        if "code" not in account:
            raise ValueError("Hesap kodu gereklidir")
        
        # Kod benzersizliğini kontrol et
        for existing_account in self.data["chart_of_accounts"]:
            if existing_account.get("code") == account["code"]:
                raise ValueError(f"Bu kod zaten kullanılıyor: {account['code']}")
        
        # Hesabı ekle
        self.data["chart_of_accounts"].append(account)
        self.save()
        
        return account["code"]
    
    def update_account(self, account_code, updated_data):
        """Hesap güncelle"""
        for i, account in enumerate(self.data["chart_of_accounts"]):
            if account.get("code") == account_code:
                # Kodu koruyarak güncelle
                updated_data["code"] = account_code
                self.data["chart_of_accounts"][i] = updated_data
                self.save()
                return True
        
        return False
    
    def delete_account(self, account_code):
        """Hesap sil"""
        for i, account in enumerate(self.data["chart_of_accounts"]):
            if account.get("code") == account_code:
                del self.data["chart_of_accounts"][i]
                self.save()
                return True
        
        return False
    
    def get_account_by_code(self, account_code):
        """Kod ile hesap getir"""
        for account in self.data["chart_of_accounts"]:
            if account.get("code") == account_code:
                return account
        return None
    
    def filter_accounts(self, account_type=None, is_active=None):
        """Hesapları filtrele"""
        filtered_accounts = self.data["chart_of_accounts"]
        
        if account_type:
            filtered_accounts = [a for a in filtered_accounts 
                                if a.get("type") == account_type]
        
        if is_active is not None:
            filtered_accounts = [a for a in filtered_accounts 
                                if a.get("is_active", True) == is_active]
        
        return filtered_accounts
    
    # Fatura işlemleri
    
    def get_all_invoices(self):
        """Tüm faturaları al"""
        return self.data["invoices"]
    
    def add_invoice(self, invoice):
        """Yeni fatura ekle"""
        if not isinstance(invoice, dict):
            raise ValueError("Fatura bir sözlük olmalıdır")
        
        # Fatura ID'si atama
        if "id" not in invoice:
            # Mevcut en yüksek ID'yi bul
            max_id = 0
            for inv in self.data["invoices"]:
                if "id" in inv and isinstance(inv["id"], int) and inv["id"] > max_id:
                    max_id = inv["id"]
            
            invoice["id"] = max_id + 1
        
        # Tarih alanını kontrol et
        if "date" not in invoice:
            invoice["date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Faturayı ekle
        self.data["invoices"].append(invoice)
        self.save()
        
        return invoice["id"]
    
    def update_invoice(self, invoice_id, updated_data):
        """Fatura güncelle"""
        for i, invoice in enumerate(self.data["invoices"]):
            if invoice.get("id") == invoice_id:
                # ID'yi koruyarak güncelle
                updated_data["id"] = invoice_id
                self.data["invoices"][i] = updated_data
                self.save()
                return True
        
        return False
    
    def delete_invoice(self, invoice_id):
        """Fatura sil"""
        for i, invoice in enumerate(self.data["invoices"]):
            if invoice.get("id") == invoice_id:
                del self.data["invoices"][i]
                self.save()
                return True
        
        return False
    
    def get_invoice_by_id(self, invoice_id):
        """ID'ye göre fatura getir"""
        for invoice in self.data["invoices"]:
            if invoice.get("id") == invoice_id:
                return invoice
        return None
    
    def get_invoice_by_number(self, invoice_number):
        """Fatura numarasına göre fatura getir"""
        for invoice in self.data["invoices"]:
            if invoice.get("invoice_number") == invoice_number:
                return invoice
        return None
    
    def filter_invoices(self, start_date=None, end_date=None, customer_id=None, status=None):
        """Faturaları filtrele"""
        filtered_invoices = self.data["invoices"]
        
        # Tarih filtreleme
        if start_date:
            filtered_invoices = [i for i in filtered_invoices 
                               if i.get("date", "") >= start_date]
        
        if end_date:
            filtered_invoices = [i for i in filtered_invoices 
                               if i.get("date", "") <= end_date]
        
        # Müşteri filtreleme
        if customer_id:
            filtered_invoices = [i for i in filtered_invoices 
                               if i.get("customer_id") == customer_id]
        
        # Durum filtreleme
        if status:
            filtered_invoices = [i for i in filtered_invoices 
                               if i.get("status") == status]
        
        return filtered_invoices
    
    # Gider işlemleri
    
    def get_all_expenses(self):
        """Tüm giderleri al"""
        return self.data["expenses"]
    
    def add_expense(self, expense):
        """Yeni gider ekle"""
        if not isinstance(expense, dict):
            raise ValueError("Gider bir sözlük olmalıdır")
        
        # Gider ID'si atama
        if "id" not in expense:
            # Mevcut en yüksek ID'yi bul
            max_id = 0
            for exp in self.data["expenses"]:
                if "id" in exp and isinstance(exp["id"], int) and exp["id"] > max_id:
                    max_id = exp["id"]
            
            expense["id"] = max_id + 1
        
        # Tarih alanını kontrol et
        if "date" not in expense:
            expense["date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Gideri ekle
        self.data["expenses"].append(expense)
        self.save()
        
        return expense["id"]
    
    def update_expense(self, expense_id, updated_data):
        """Gider güncelle"""
        for i, expense in enumerate(self.data["expenses"]):
            if expense.get("id") == expense_id:
                # ID'yi koruyarak güncelle
                updated_data["id"] = expense_id
                self.data["expenses"][i] = updated_data
                self.save()
                return True
        
        return False
    
    def delete_expense(self, expense_id):
        """Gider sil"""
        for i, expense in enumerate(self.data["expenses"]):
            if expense.get("id") == expense_id:
                del self.data["expenses"][i]
                self.save()
                return True
        
        return False
    
    def get_expense_by_id(self, expense_id):
        """ID'ye göre gider getir"""
        for expense in self.data["expenses"]:
            if expense.get("id") == expense_id:
                return expense
        return None
    
    def filter_expenses(self, start_date=None, end_date=None, supplier_id=None, category=None):
        """Giderleri filtrele"""
        filtered_expenses = self.data["expenses"]
        
        # Tarih filtreleme
        if start_date:
            filtered_expenses = [e for e in filtered_expenses 
                               if e.get("date", "") >= start_date]
        
        if end_date:
            filtered_expenses = [e for e in filtered_expenses 
                               if e.get("date", "") <= end_date]
        
        # Tedarikçi filtreleme
        if supplier_id:
            filtered_expenses = [e for e in filtered_expenses 
                               if e.get("supplier_id") == supplier_id]
        
        # Kategori filtreleme
        if category:
            filtered_expenses = [e for e in filtered_expenses 
                               if e.get("category") == category]
        
        return filtered_expenses
    
    # Müşteri ve tedarikçi işlemleri
    
    def get_all_customers(self):
        """Tüm müşterileri al"""
        return self.data["customers"]
    
    def add_customer(self, customer):
        """Yeni müşteri ekle"""
        if not isinstance(customer, dict):
            raise ValueError("Müşteri bir sözlük olmalıdır")
        
        # Müşteri ID'si atama
        if "id" not in customer:
            # Mevcut en yüksek ID'yi bul
            max_id = 0
            for cust in self.data["customers"]:
                if "id" in cust and isinstance(cust["id"], int) and cust["id"] > max_id:
                    max_id = cust["id"]
            
            customer["id"] = max_id + 1
        
        # Müşteriyi ekle
        self.data["customers"].append(customer)
        self.save()
        
        return customer["id"]
    
    def update_customer(self, customer_id, updated_data):
        """Müşteri güncelle"""
        for i, customer in enumerate(self.data["customers"]):
            if customer.get("id") == customer_id:
                # ID'yi koruyarak güncelle
                updated_data["id"] = customer_id
                self.data["customers"][i] = updated_data
                self.save()
                return True
        
        return False
    
    def delete_customer(self, customer_id):
        """Müşteri sil"""
        for i, customer in enumerate(self.data["customers"]):
            if customer.get("id") == customer_id:
                del self.data["customers"][i]
                self.save()
                return True
        
        return False
    
    def get_customer_by_id(self, customer_id):
        """ID'ye göre müşteri getir"""
        for customer in self.data["customers"]:
            if customer.get("id") == customer_id:
                return customer
        return None
    
    def get_all_suppliers(self):
        """Tüm tedarikçileri al"""
        return self.data["suppliers"]
    
    def add_supplier(self, supplier):
        """Yeni tedarikçi ekle"""
        if not isinstance(supplier, dict):
            raise ValueError("Tedarikçi bir sözlük olmalıdır")
        
        # Tedarikçi ID'si atama
        if "id" not in supplier:
            # Mevcut en yüksek ID'yi bul
            max_id = 0
            for supp in self.data["suppliers"]:
                if "id" in supp and isinstance(supp["id"], int) and supp["id"] > max_id:
                    max_id = supp["id"]
            
            supplier["id"] = max_id + 1
        
        # Tedarikçiyi ekle
        self.data["suppliers"].append(supplier)
        self.save()
        
        return supplier["id"]
    
    def update_supplier(self, supplier_id, updated_data):
        """Tedarikçi güncelle"""
        for i, supplier in enumerate(self.data["suppliers"]):
            if supplier.get("id") == supplier_id:
                # ID'yi koruyarak güncelle
                updated_data["id"] = supplier_id
                self.data["suppliers"][i] = updated_data
                self.save()
                return True
        
        return False
    
    def delete_supplier(self, supplier_id):
        """Tedarikçi sil"""
        for i, supplier in enumerate(self.data["suppliers"]):
            if supplier.get("id") == supplier_id:
                del self.data["suppliers"][i]
                self.save()
                return True
        
        return False
    
    def get_supplier_by_id(self, supplier_id):
        """ID'ye göre tedarikçi getir"""
        for supplier in self.data["suppliers"]:
            if supplier.get("id") == supplier_id:
                return supplier
        return None
    
    # Vergi beyanı işlemleri
    
    def add_vat_return(self, vat_return):
        """VAT beyanı ekle"""
        if not isinstance(vat_return, dict):
            raise ValueError("VAT beyanı bir sözlük olmalıdır")
        
        # Beyan ID'si atama
        if "id" not in vat_return:
            # Mevcut en yüksek ID'yi bul
            max_id = 0
            for ret in self.data["vat_returns"]:
                if "id" in ret and isinstance(ret["id"], int) and ret["id"] > max_id:
                    max_id = ret["id"]
            
            vat_return["id"] = max_id + 1
        
        # Tarih alanını kontrol et
        if "submission_date" not in vat_return:
            vat_return["submission_date"] = datetime.now().isoformat()
        
        # Beyanı ekle
        self.data["vat_returns"].append(vat_return)
        self.save()
        
        return vat_return["id"]
    
    def get_vat_returns(self):
        """VAT beyanlarını al"""
        return self.data["vat_returns"]
    
    def update_vat_return(self, vat_return_id, updated_data):
        """VAT beyanı güncelle"""
        for i, vat_return in enumerate(self.data["vat_returns"]):
            if vat_return.get("id") == vat_return_id:
                # ID'yi koruyarak güncelle
                updated_data["id"] = vat_return_id
                self.data["vat_returns"][i] = updated_data
                self.save()
                return True
        
        return False
    
    def get_vat_return_by_id(self, vat_return_id):
        """ID'ye göre VAT beyanı getir"""
        for vat_return in self.data["vat_returns"]:
            if vat_return.get("id") == vat_return_id:
                return vat_return
        return None
    
    def add_tax_return(self, tax_return):
        """Vergi beyanı ekle"""
        if not isinstance(tax_return, dict):
            raise ValueError("Vergi beyanı bir sözlük olmalıdır")
        
        # Beyan ID'si atama
        if "id" not in tax_return:
            # Mevcut en yüksek ID'yi bul
            max_id = 0
            for ret in self.data["tax_returns"]:
                if "id" in ret and isinstance(ret["id"], int) and ret["id"] > max_id:
                    max_id = ret["id"]
            
            tax_return["id"] = max_id + 1
        
        # Tarih alanını kontrol et
        if "submission_date" not in tax_return:
            tax_return["submission_date"] = datetime.now().isoformat()
        
        # Beyanı ekle
        self.data["tax_returns"].append(tax_return)
        self.save()
        
        return tax_return["id"]
    
    def get_tax_returns(self):
        """Vergi beyanlarını al"""
        return self.data["tax_returns"]
    
    def update_tax_return(self, tax_return_id, updated_data):
        """Vergi beyanı güncelle"""
        for i, tax_return in enumerate(self.data["tax_returns"]):
            if tax_return.get("id") == tax_return_id:
                # ID'yi koruyarak güncelle
                updated_data["id"] = tax_return_id
                self.data["tax_returns"][i] = updated_data
                self.save()
                return True
        
        return False
    
    def get_tax_return_by_id(self, tax_return_id):
        """ID'ye göre vergi beyanı getir"""
        for tax_return in self.data["tax_returns"]:
            if tax_return.get("id") == tax_return_id:
                return tax_return
        return None
    
    # Raporlama işlemleri
    
    def generate_trial_balance(self, as_of_date=None):
        """Mizan raporu oluştur"""
        accounts = self.get_chart_of_accounts()
        transactions = self.get_all_transactions()
        
        # Belirli bir tarihe kadar olan işlemleri filtrele
        if as_of_date:
            transactions = [t for t in transactions if t.get("date", "") <= as_of_date]
        
        # Hesap bakiyelerini hesapla
        account_balances = {}
        for account in accounts:
            account_code = account.get("code")
            account_balances[account_code] = {
                "code": account_code,
                "name": account.get("name"),
                "type": account.get("type"),
                "debit_total": 0,
                "credit_total": 0,
                "balance": 0
            }
        
        # İşlemleri hesaplara dağıt
        for transaction in transactions:
            for entry in transaction.get("entries", []):
                account_code = entry.get("account_code")
                if account_code in account_balances:
                    amount = entry.get("amount", 0)
                    if entry.get("type") == "debit":
                        account_balances[account_code]["debit_total"] += amount
                    else:
                        account_balances[account_code]["credit_total"] += amount
        
        # Son bakiyeleri hesapla
        for code, account in account_balances.items():
            account["balance"] = account["debit_total"] - account["credit_total"]
        
        return list(account_balances.values())
    
    def generate_income_statement(self, start_date, end_date):
        """Gelir tablosu oluştur"""
        accounts = self.get_chart_of_accounts()
        transactions = self.filter_transactions(start_date=start_date, end_date=end_date)
        
        # Gelir ve gider hesaplarını filtrele
        income_expense_accounts = [a for a in accounts 
                                  if a.get("type") in ["income", "expense"]]
        
        # Hesap bakiyelerini hesapla
        account_balances = {}
        for account in income_expense_accounts:
            account_code = account.get("code")
            account_balances[account_code] = {
                "code": account_code,
                "name": account.get("name"),
                "type": account.get("type"),
                "amount": 0
            }
        
        # İşlemleri hesaplara dağıt
        for transaction in transactions:
            for entry in transaction.get("entries", []):
                account_code = entry.get("account_code")
                if account_code in account_balances:
                    amount = entry.get("amount", 0)
                    account_type = account_balances[account_code]["type"]
                    
                    # Gelir ve gider hesaplarını doğru şekilde topla
                    if account_type == "income":
                        if entry.get("type") == "credit":
                            account_balances[account_code]["amount"] += amount
                        else:
                            account_balances[account_code]["amount"] -= amount
                    elif account_type == "expense":
                        if entry.get("type") == "debit":
                            account_balances[account_code]["amount"] += amount
                        else:
                            account_balances[account_code]["amount"] -= amount
        
        # Gelir ve gider toplamlarını hesapla
        total_income = sum(account["amount"] for account in account_balances.values() 
                         if account["type"] == "income")
        total_expenses = sum(account["amount"] for account in account_balances.values() 
                           if account["type"] == "expense")
        net_income = total_income - total_expenses
        
        return {
            "accounts": list(account_balances.values()),
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_income": net_income
        }
    
    def generate_balance_sheet(self, as_of_date=None):
        """Bilanço oluştur"""
        accounts = self.get_chart_of_accounts()
        transactions = self.get_all_transactions()
        
        # Belirli bir tarihe kadar olan işlemleri filtrele
        if as_of_date:
            transactions = [t for t in transactions if t.get("date", "") <= as_of_date]
        
        # Varlık, borç ve özkaynak hesaplarını filtrele
        balance_sheet_accounts = [a for a in accounts 
                                if a.get("type") in ["asset", "liability", "equity"]]
        
        # Hesap bakiyelerini hesapla
        account_balances = {}
        for account in balance_sheet_accounts:
            account_code = account.get("code")
            account_balances[account_code] = {
                "code": account_code,
                "name": account.get("name"),
                "type": account.get("type"),
                "debit_total": 0,
                "credit_total": 0,
                "balance": 0
            }
        
        # İşlemleri hesaplara dağıt
        for transaction in transactions:
            for entry in transaction.get("entries", []):
                account_code = entry.get("account_code")
                if account_code in account_balances:
                    amount = entry.get("amount", 0)
                    if entry.get("type") == "debit":
                        account_balances[account_code]["debit_total"] += amount
                    else:
                        account_balances[account_code]["credit_total"] += amount
        
        # Son bakiyeleri hesapla
        for code, account in account_balances.items():
            account_type = account["type"]
            
            if account_type == "asset":
                # Varlıklar normal olarak borç bakiyesine sahiptir
                account["balance"] = account["debit_total"] - account["credit_total"]
            else:
                # Borçlar ve özkaynaklar normal olarak alacak bakiyesine sahiptir
                account["balance"] = account["credit_total"] - account["debit_total"]
        
        # Toplam hesaplamalarını yap
        total_assets = sum(account["balance"] for account in account_balances.values() 
                         if account["type"] == "asset")
        total_liabilities = sum(account["balance"] for account in account_balances.values() 
                              if account["type"] == "liability")
        total_equity = sum(account["balance"] for account in account_balances.values() 
                         if account["type"] == "equity")
        
        return {
            "accounts": list(account_balances.values()),
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "balanced": abs(total_assets - (total_liabilities + total_equity)) < 0.01
        }
