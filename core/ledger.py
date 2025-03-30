#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Muhasebe Defteri Modülü
Temel muhasebe işlemlerini yönetir.
"""

import logging
from datetime import datetime, timedelta
import uuid
import json
from decimal import Decimal


class Ledger:
    """Muhasebe defteri sınıfı"""
    
    def __init__(self, database):
        """Muhasebe defteri başlatıcı
        
        Args:
            database: Veritabanı nesnesi
        """
        self.db = database
        self.logger = logging.getLogger(__name__)
        
        # Varsayılan hesap planını yükle (sadece boşsa)
        if not self.db.get_chart_of_accounts():
            self._setup_default_chart_of_accounts()
    
    def _setup_default_chart_of_accounts(self):
        """Varsayılan hesap planını oluştur"""
        default_accounts = [
            # Varlık Hesapları (1000-1999)
            {"code": "1000", "name": "Kasa", "type": "asset", "category": "current_asset", "vat_rate": 0, "balance": 0},
            {"code": "1100", "name": "Banka", "type": "asset", "category": "current_asset", "vat_rate": 0, "balance": 0},
            {"code": "1200", "name": "Alacak Hesapları", "type": "asset", "category": "current_asset", "vat_rate": 0, "balance": 0},
            {"code": "1300", "name": "Stoklar", "type": "asset", "category": "current_asset", "vat_rate": 0, "balance": 0},
            {"code": "1400", "name": "Peşin Ödenmiş Giderler", "type": "asset", "category": "current_asset", "vat_rate": 0, "balance": 0},
            {"code": "1500", "name": "Sabit Varlıklar", "type": "asset", "category": "fixed_asset", "vat_rate": 0, "balance": 0},
            {"code": "1600", "name": "Birikmiş Amortisman", "type": "asset", "category": "fixed_asset", "vat_rate": 0, "balance": 0},
            
            # Borç Hesapları (2000-2999)
            {"code": "2000", "name": "Borç Hesapları", "type": "liability", "category": "current_liability", "vat_rate": 0, "balance": 0},
            {"code": "2100", "name": "Ödenecek KDV", "type": "liability", "category": "current_liability", "vat_rate": 0, "balance": 0},
            {"code": "2200", "name": "İndirilecek KDV", "type": "liability", "category": "current_liability", "vat_rate": 0, "balance": 0},
            {"code": "2300", "name": "Ödenecek Vergiler", "type": "liability", "category": "current_liability", "vat_rate": 0, "balance": 0},
            {"code": "2400", "name": "Uzun Vadeli Borçlar", "type": "liability", "category": "long_term_liability", "vat_rate": 0, "balance": 0},
            
            # Öz Sermaye Hesapları (3000-3999)
            {"code": "3000", "name": "Sermaye", "type": "equity", "category": "equity", "vat_rate": 0, "balance": 0},
            {"code": "3100", "name": "Geçmiş Dönem Kar/Zarar", "type": "equity", "category": "equity", "vat_rate": 0, "balance": 0},
            {"code": "3200", "name": "Dönem Net Kar/Zarar", "type": "equity", "category": "equity", "vat_rate": 0, "balance": 0},
            
            # Gelir Hesapları (4000-4999)
            {"code": "4000", "name": "Satış Gelirleri", "type": "income", "category": "revenue", "vat_rate": 20, "balance": 0},
            {"code": "4100", "name": "Hizmet Gelirleri", "type": "income", "category": "revenue", "vat_rate": 20, "balance": 0},
            {"code": "4200", "name": "İndirim ve İadeler (-)", "type": "income", "category": "revenue", "vat_rate": 20, "balance": 0},
            {"code": "4300", "name": "Diğer Gelirler", "type": "income", "category": "other_income", "vat_rate": 0, "balance": 0},
            
            # Gider Hesapları (5000-5999)
            {"code": "5000", "name": "Mal ve Hizmet Alımları", "type": "expense", "category": "cost_of_sales", "vat_rate": 20, "balance": 0},
            {"code": "5100", "name": "Personel Giderleri", "type": "expense", "category": "operating_expense", "vat_rate": 0, "balance": 0},
            {"code": "5200", "name": "Kira Giderleri", "type": "expense", "category": "operating_expense", "vat_rate": 20, "balance": 0},
            {"code": "5300", "name": "Ofis Giderleri", "type": "expense", "category": "operating_expense", "vat_rate": 20, "balance": 0},
            {"code": "5400", "name": "Amortisman Giderleri", "type": "expense", "category": "operating_expense", "vat_rate": 0, "balance": 0},
            {"code": "5500", "name": "Pazarlama ve Reklam", "type": "expense", "category": "operating_expense", "vat_rate": 20, "balance": 0},
            {"code": "5600", "name": "İletişim ve Internet", "type": "expense", "category": "operating_expense", "vat_rate": 20, "balance": 0},
            {"code": "5700", "name": "Seyahat ve Konaklama", "type": "expense", "category": "operating_expense", "vat_rate": 20, "balance": 0},
            {"code": "5800", "name": "Profesyonel Hizmetler", "type": "expense", "category": "operating_expense", "vat_rate": 20, "balance": 0},
            {"code": "5900", "name": "Banka ve Finansman Giderleri", "type": "expense", "category": "financial_expense", "vat_rate": 0, "balance": 0}
        ]
        
        # Hesapları veritabanına ekle
        for account in default_accounts:
            try:
                self.db.add_account(account)
            except Exception as e:
                self.logger.error(f"Varsayılan hesap eklenirken hata: {e}")
    
    def get_chart_of_accounts(self):
        """Hesap planını al"""
        return self.db.get_chart_of_accounts()
    
    def get_account_by_code(self, code):
        """Kod ile hesap al"""
        accounts = self.db.get_chart_of_accounts()
        for account in accounts:
            if account.get("code") == code:
                return account
        return None
    
    def add_account(self, account_data):
        """Yeni hesap ekle"""
        return self.db.add_account(account_data)
    
    def update_account(self, code, account_data):
        """Hesap güncelle"""
        return self.db.update_account(code, account_data)
    
    def delete_account(self, code):
        """Hesap sil"""
        return self.db.delete_account(code)
    
    def get_all_transactions(self):
        """Tüm işlemleri al"""
        return self.db.get_all_transactions()
    
    def get_transactions_by_date_range(self, start_date, end_date):
        """Tarih aralığına göre işlemleri filtrele"""
        transactions = self.db.get_all_transactions()
        filtered = []
        
        for trans in transactions:
            try:
                trans_date = datetime.strptime(trans.get("date", ""), "%Y-%m-%d")
                if start_date <= trans_date <= end_date:
                    filtered.append(trans)
            except ValueError:
                # Geçersiz tarih formatı, işlemi atla
                pass
        
        return filtered
    
    def get_transactions_by_account(self, account_code):
        """Hesaba göre işlemleri filtrele"""
        transactions = self.db.get_all_transactions()
        filtered = []
        
        for trans in transactions:
            if trans.get("account") == account_code:
                filtered.append(trans)
        
        return filtered
    
    def add_transaction(self, transaction_data):
        """Yeni işlem ekle"""
        # İşlem doğrulama kontrolleri
        if "account" not in transaction_data:
            raise ValueError("İşlem için hesap kodu gereklidir")
        
        # Hesabın varlığını kontrol et
        account = self.get_account_by_code(transaction_data["account"])
        if not account:
            raise ValueError(f"Hesap bulunamadı: {transaction_data['account']}")
        
        # Diğer doğrulamalar burada yapılabilir
        
        # İşlemi ekle
        trans_id = self.db.add_transaction(transaction_data)
        
        # Hesap bakiyesini güncelle
        self._update_account_balance(
            transaction_data["account"],
            transaction_data.get("debit", 0) - transaction_data.get("credit", 0)
        )
        
        return trans_id
    
    def update_transaction(self, transaction_id, transaction_data):
        """İşlem güncelle"""
        # Eski işlemi al
        old_transaction = None
        for trans in self.get_all_transactions():
            if trans.get("id") == transaction_id:
                old_transaction = trans
                break
        
        if not old_transaction:
            raise ValueError(f"İşlem bulunamadı: {transaction_id}")
        
        # İşlemi güncelle
        success = self.db.update_transaction(transaction_id, transaction_data)
        
        if success:
            # Eski işlem etkisini geri al
            if "account" in old_transaction:
                self._update_account_balance(
                    old_transaction["account"],
                    -(old_transaction.get("debit", 0) - old_transaction.get("credit", 0))
                )
            
            # Yeni işlem etkisini uygula
            if "account" in transaction_data:
                self._update_account_balance(
                    transaction_data["account"],
                    transaction_data.get("debit", 0) - transaction_data.get("credit", 0)
                )
        
        return success
    
    def delete_transaction(self, transaction_id):
        """İşlem sil"""
        # İşlemi al
        transaction = None
        for trans in self.get_all_transactions():
            if trans.get("id") == transaction_id:
                transaction = trans
                break
        
        if not transaction:
            raise ValueError(f"İşlem bulunamadı: {transaction_id}")
        
        # İşlemi sil
        success = self.db.delete_transaction(transaction_id)
        
        if success and "account" in transaction:
            # İşlem etkisini geri al
            self._update_account_balance(
                transaction["account"],
                -(transaction.get("debit", 0) - transaction.get("credit", 0))
            )
        
        return success
    
    def _update_account_balance(self, account_code, amount_change):
        """Hesap bakiyesini güncelle"""
        account = self.get_account_by_code(account_code)
        if not account:
            self.logger.error(f"Bakiye güncellenecek hesap bulunamadı: {account_code}")
            return False
        
        # Bakiyeyi güncelle
        current_balance = account.get("balance", 0)
        updated_balance = current_balance + amount_change
        
        # Hesabı güncelle
        account["balance"] = updated_balance
        return self.db.update_account(account_code, account)
    
    def get_all_invoices(self):
        """Tüm faturaları al"""
        return self.db.get_all_invoices()
    
    def get_invoice_by_id(self, invoice_id):
        """ID ile fatura al"""
        invoices = self.db.get_all_invoices()
        for invoice in invoices:
            if invoice.get("id") == invoice_id:
                return invoice
        return None
    
    def add_invoice(self, invoice_data):
        """Yeni fatura ekle"""
        # Fatura doğrulama kontrolleri
        required_fields = ["type", "entity_name", "amount"]
        for field in required_fields:
            if field not in invoice_data:
                raise ValueError(f"Fatura için {field} alanı gereklidir")
        
        # Fatura tipi kontrol
        if invoice_data["type"] not in ["sales", "purchase"]:
            raise ValueError("Fatura tipi 'sales' veya 'purchase' olmalıdır")
        
        # Fatura numarası oluştur (varsayılan)
        if "invoice_number" not in invoice_data:
            prefix = "INV" if invoice_data["type"] == "sales" else "PUR"
            invoice_data["invoice_number"] = f"{prefix}-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        
        # Tarih kontrolü
        if "date" not in invoice_data:
            invoice_data["date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Vade tarihi kontrolü
        if "due_date" not in invoice_data:
            # Varsayılan olarak 30 gün vade ekleyelim
            try:
                invoice_date = datetime.strptime(invoice_data["date"], "%Y-%m-%d")
                due_date = invoice_date + timedelta(days=30)
                invoice_data["due_date"] = due_date.strftime("%Y-%m-%d")
            except ValueError:
                # Geçersiz tarih formatı
                invoice_data["due_date"] = ""
        
        # Ödeme durumu kontrolü
        if "payment_status" not in invoice_data:
            invoice_data["payment_status"] = "unpaid"
        
        # KDV hesaplama (varsayılan olarak %20)
        if "amount" in invoice_data and "vat" not in invoice_data:
            vat_rate = invoice_data.get("vat_rate", 20)  # Varsayılan %20
            amount = invoice_data["amount"]
            invoice_data["vat"] = round(amount * (vat_rate / 100), 2)
        
        # Faturayı ekle
        invoice_id = self.db.add_invoice(invoice_data)
        
        # Fatura işlemini oluştur (otomatik muhasebeleştirme)
        if invoice_data.get("auto_post", True):
            self._create_invoice_transaction(invoice_data)
        
        return invoice_id
    
    def _create_invoice_transaction(self, invoice_data):
        """Fatura için muhasebe işlemi oluştur"""
        invoice_type = invoice_data["type"]
        amount = invoice_data["amount"]
        vat = invoice_data.get("vat", 0)
        total = amount + vat
        
        transaction = {
            "date": invoice_data["date"],
            "document_number": invoice_data["invoice_number"],
            "description": f"{'Satış' if invoice_type == 'sales' else 'Alış'} Faturası - {invoice_data['entity_name']}",
            "transaction_type": "invoice",
            "status": "unreconciled",
            "notes": invoice_data.get("notes", "")
        }
        
        if invoice_type == "sales":
            # Satış faturası
            # 1) Alacak hesaplarına borç (alacak artırma)
            transaction["account"] = "1200"  # Alacak Hesapları
            transaction["debit"] = total
            transaction["credit"] = 0
            transaction["vat"] = 0
            self.add_transaction(transaction)
            
            # 2) Satış gelirine alacak
            transaction["account"] = "4000"  # Satış Gelirleri
            transaction["debit"] = 0
            transaction["credit"] = amount
            transaction["vat"] = 0
            self.add_transaction(transaction)
            
            # 3) Ödenecek KDV'ye alacak
            if vat > 0:
                transaction["account"] = "2100"  # Ödenecek KDV
                transaction["debit"] = 0
                transaction["credit"] = vat
                transaction["vat"] = vat
                self.add_transaction(transaction)
                
        elif invoice_type == "purchase":
            # Alış faturası
            # 1) Gider hesabına borç
            transaction["account"] = "5000"  # Mal ve Hizmet Alımları
            transaction["debit"] = amount
            transaction["credit"] = 0
            transaction["vat"] = 0
            self.add_transaction(transaction)
            
            # 2) İndirilecek KDV'ye borç
            if vat > 0:
                transaction["account"] = "2200"  # İndirilecek KDV
                transaction["debit"] = vat
                transaction["credit"] = 0
                transaction["vat"] = vat
                self.add_transaction(transaction)
            
            # 3) Borç hesaplarına alacak
            transaction["account"] = "2000"  # Borç Hesapları
            transaction["debit"] = 0
            transaction["credit"] = total
            transaction["vat"] = 0
            self.add_transaction(transaction)
    
    def update_invoice(self, invoice_id, invoice_data):
        """Fatura güncelle"""
        # Faturayı al
        old_invoice = self.get_invoice_by_id(invoice_id)
        if not old_invoice:
            raise ValueError(f"Fatura bulunamadı: {invoice_id}")
        
        # Faturayı güncelle
        success = self.db.update_invoice(invoice_id, invoice_data)
        
        # Burada fatura güncellemesi için muhasebe işlemleri yapılabilir
        # Basitleştirme için şimdilik atlandı
        
        return success
    
    def delete_invoice(self, invoice_id):
        """Fatura sil"""
        # Faturayı al
        invoice = self.get_invoice_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Fatura bulunamadı: {invoice_id}")
        
        # Faturayı sil
        success = self.db.delete_invoice(invoice_id)
        
        # Burada fatura silme için muhasebe işlemleri yapılabilir
        # Basitleştirme için şimdilik atlandı
        
        return success
    
    def mark_invoice_as_paid(self, invoice_id, payment_date=None, payment_method=None, reference=None):
        """Faturayı ödenmiş olarak işaretle"""
        # Faturayı al
        invoice = self.get_invoice_by_id(invoice_id)
        if not invoice:
            raise ValueError(f"Fatura bulunamadı: {invoice_id}")
        
        # Faturanın ödeme durumunu güncelle
        invoice["payment_status"] = "paid"
        invoice["payment_date"] = payment_date or datetime.now().strftime("%Y-%m-%d")
        if payment_method:
            invoice["payment_method"] = payment_method
        if reference:
            invoice["payment_reference"] = reference
        
        # Faturayı güncelle
        success = self.db.update_invoice(invoice_id, invoice)
        
        if success:
            # Ödeme işlemini oluştur
            self._create_payment_transaction(invoice)
        
        return success
    
    def _create_payment_transaction(self, invoice):
        """Fatura ödemesi için muhasebe işlemi oluştur"""
        invoice_type = invoice["type"]
        total = invoice["amount"] + invoice.get("vat", 0)
        
        transaction = {
            "date": invoice.get("payment_date", datetime.now().strftime("%Y-%m-%d")),
            "document_number": f"PMT-{invoice['invoice_number']}",
            "description": f"{'Satış' if invoice_type == 'sales' else 'Alış'} Faturası Ödemesi - {invoice['entity_name']}",
            "transaction_type": "payment",
            "status": "unreconciled",
            "notes": f"Fatura Ödemesi: {invoice['invoice_number']}"
        }
        
        if invoice_type == "sales":
            # Satış faturası ödemesi
            # 1) Bankaya borç
            transaction["account"] = "1100"  # Banka
            transaction["debit"] = total
            transaction["credit"] = 0
            transaction["vat"] = 0
            self.add_transaction(transaction)
            
            # 2) Alacak hesaplarından düş
            transaction["account"] = "1200"  # Alacak Hesapları
            transaction["debit"] = 0
            transaction["credit"] = total
            transaction["vat"] = 0
            self.add_transaction(transaction)
            
        elif invoice_type == "purchase":
            # Alış faturası ödemesi
            # 1) Borç hesaplarına borç (borç azaltma)
            transaction["account"] = "2000"  # Borç Hesapları
            transaction["debit"] = total
            transaction["credit"] = 0
            transaction["vat"] = 0
            self.add_transaction(transaction)
            
            # 2) Bankadan düş
            transaction["account"] = "1100"  # Banka
            transaction["debit"] = 0
            transaction["credit"] = total
            transaction["vat"] = 0
            self.add_transaction(transaction)
    
    def get_all_expenses(self):
        """Tüm giderleri al"""
        return self.db.get_all_expenses()
    
    def add_expense(self, expense_data):
        """Yeni gider ekle"""
        # Gider doğrulama kontrolleri
        required_fields = ["amount", "category", "description"]
        for field in required_fields:
            if field not in expense_data:
                raise ValueError(f"Gider için {field} alanı gereklidir")
        
        # Tarih kontrolü
        if "date" not in expense_data:
            expense_data["date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Fiş/Fatura no kontrolü
        if "receipt_number" not in expense_data:
            expense_data["receipt_number"] = f"EXP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"
        
        # Ödeme durumu kontrolü
        if "status" not in expense_data:
            expense_data["status"] = "paid"  # Varsayılan olarak ödenmiş
        
        # KDV hesaplama (varsayılan olarak %20)
        if "amount" in expense_data and "vat" not in expense_data:
            vat_rate = expense_data.get("vat_rate", 20)  # Varsayılan %20
            amount = expense_data["amount"]
            expense_data["vat"] = round(amount * (vat_rate / 100), 2)
        
        # Giderin tipini ayarla
        expense_data["type"] = "expense"
        
        # Gideri ekle
        expense_id = self.db.add_expense(expense_data)
        
        # Gider işlemini oluştur (otomatik muhasebeleştirme)
        if expense_data.get("auto_post", True):
            self._create_expense_transaction(expense_data)
        
        return expense_id
    
    def _create_expense_transaction(self, expense_data):
        """Gider için muhasebe işlemi oluştur"""
        amount = expense_data["amount"]
        vat = expense_data.get("vat", 0)
        total = amount + vat
        category = expense_data["category"]
        
        # Kategori -> Hesap kodu eşleşmesi
        category_account_map = {
            "office": "5300",      # Ofis Giderleri
            "travel": "5700",      # Seyahat ve Konaklama
            "marketing": "5500",   # Pazarlama ve Reklam
            "rent": "5200",        # Kira Giderleri
            "utilities": "5300",   # Ofis Giderleri (Faturalar)
            "software": "5300",    # Ofis Giderleri (Yazılım)
            "professional": "5800", # Profesyonel Hizmetler
            "salary": "5100",      # Personel Giderleri
            "bank": "5900",        # Banka ve Finansman Giderleri
            "other": "5000"        # Mal ve Hizmet Alımları
        }
        
        expense_account = category_account_map.get(category, "5000")
        
        transaction = {
            "date": expense_data["date"],
            "document_number": expense_data["receipt_number"],
            "description": expense_data["description"],
            "transaction_type": "expense",
            "status": "unreconciled",
            "notes": expense_data.get("notes", "")
        }
        
        # Ödeme yöntemi kontrolü
        payment_method = expense_data.get("payment_method", "cash")
        payment_account = "1000" if payment_method == "cash" else "1100"  # Kasa veya Banka
        
        # 1) Gider hesabına borç
        transaction["account"] = expense_account
        transaction["debit"] = amount
        transaction["credit"] = 0
        transaction["vat"] = 0
        self.add_transaction(transaction)
        
        # 2) İndirilecek KDV'ye borç
        if vat > 0:
            transaction["account"] = "2200"  # İndirilecek KDV
            transaction["debit"] = vat
            transaction["credit"] = 0
            transaction["vat"] = vat
            self.add_transaction(transaction)
        
        # 3) Kasa/Banka'dan düş
        transaction["account"] = payment_account
        transaction["debit"] = 0
        transaction["credit"] = total
        transaction["vat"] = 0
        self.add_transaction(transaction)
    
    def get_income_expenses(self):
        """Gelir ve giderleri al (faturalar + giderler)"""
        # Satış faturaları için gelirler
        invoices = self.get_all_invoices()
        income_expenses = []
        
        # Satış faturaları
        for inv in invoices:
            if inv["type"] == "sales":
                item = {
                    "date": inv["date"],
                    "type": "income",
                    "category": "sales",
                    "description": f"Satış Faturası - {inv['entity_name']}",
                    "income": inv["amount"],
                    "expense": 0,
                    "vat": inv.get("vat", 0),
                    "payment_method": inv.get("payment_method", ""),
                    "receipt_number": inv["invoice_number"],
                    "status": inv["payment_status"]
                }
                income_expenses.append(item)
        
        # Giderler
        expenses = self.get_all_expenses()
        for exp in expenses:
            item = {
                "date": exp["date"],
                "type": "expense",
                "category": exp["category"],
                "description": exp["description"],
                "income": 0,
                "expense": exp["amount"],
                "vat": exp.get("vat", 0),
                "payment_method": exp.get("payment_method", ""),
                "receipt_number": exp["receipt_number"],
                "status": exp["status"]
            }
            income_expenses.append(item)
        
        # Tarihe göre sırala
        income_expenses.sort(key=lambda x: x["date"], reverse=True)
        
        return income_expenses
    
    def get_summary_data(self):
        """Özet verileri hesapla"""
        summary = {
            "total_income": 0,
            "total_expense": 0,
            "total_profit": 0,
            "vat_payable": 0,
            "vat_receivable": 0,
            "net_vat": 0,
            "accounts_receivable": 0,
            "accounts_payable": 0,
            "bank_balance": 0,
            "cash_balance": 0
        }
        
        # Gelir ve giderler
        income_expenses = self.get_income_expenses()
        for item in income_expenses:
            summary["total_income"] += item["income"]
            summary["total_expense"] += item["expense"]
        
        summary["total_profit"] = summary["total_income"] - summary["total_expense"]
        
        # KDV hesaplamaları
        accounts = self.get_chart_of_accounts()
        for account in accounts:
            code = account.get("code")
            balance = account.get("balance", 0)
            
            if code == "2100":  # Ödenecek KDV
                summary["vat_payable"] = balance
            elif code == "2200":  # İndirilecek KDV
                summary["vat_receivable"] = balance
            elif code == "1200":  # Alacak Hesapları
                summary["accounts_receivable"] = balance
            elif code == "2000":  # Borç Hesapları
                summary["accounts_payable"] = balance
            elif code == "1100":  # Banka
                summary["bank_balance"] = balance
            elif code == "1000":  # Kasa
                summary["cash_balance"] = balance
        
        # Net KDV
        summary["net_vat"] = summary["vat_payable"] - summary["vat_receivable"]
        
        return summary
    
    def refresh(self):
        """Hesap bakiyelerini yeniden hesapla (tutarsızlık durumunda)"""
        # Tüm hesapları sıfırla
        accounts = self.get_chart_of_accounts()
        for account in accounts:
            account["balance"] = 0
            self.db.update_account(account["code"], account)
        
        # Tüm işlemleri yeniden uygula
        transactions = self.get_all_transactions()
        for trans in transactions:
            if "account" in trans:
                amount_change = trans.get("debit", 0) - trans.get("credit", 0)
                self._update_account_balance(trans["account"], amount_change)
        
        self.logger.info("Hesap bakiyeleri yeniden hesaplandı")
        return True
    
    def calculate_vat_return(self, start_date, end_date):
        """KDV beyannamesi hesapla"""
        # Tarih kontrolü
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Geçersiz tarih formatı. Beklenen format: YYYY-MM-DD")
        
        # Belirtilen tarih aralığındaki işlemleri al
        transactions = self.get_transactions_by_date_range(start, end)
        
        vat_return = {
            "period_start": start_date,
            "period_end": end_date,
            "vat_due_sales": 0,             # Box 1: Satışlardan KDV
            "vat_due_acquisitions": 0,       # Box 2: AB Alımlarından KDV
            "total_vat_due": 0,              # Box 3: Toplam KDV (Box 1 + Box 2)
            "vat_reclaimed": 0,              # Box 4: İndirilecek KDV
            "net_vat_due": 0,                # Box 5: Ödenecek KDV (Box 3 - Box 4)
            "total_sales_ex_vat": 0,         # Box 6: Toplam Satışlar (KDV hariç)
            "total_purchases_ex_vat": 0,     # Box 7: Toplam Alımlar (KDV hariç)
            "total_supplies_ex_vat": 0,      # Box 8: AB'ye Mal Teslimleri (KDV hariç)
            "total_acquisitions_ex_vat": 0   # Box 9: AB'den Mal Alımları (KDV hariç)
        }
        
        # KDV hesaplama
        for trans in transactions:
            account = trans.get("account", "")
            debit = trans.get("debit", 0)
            credit = trans.get("credit", 0)
            vat = trans.get("vat", 0)
            
            # Satışlardan KDV (Box 1)
            if account == "2100" and credit > 0:  # Ödenecek KDV
                vat_return["vat_due_sales"] += credit
            
            # İndirilecek KDV (Box 4)
            if account == "2200" and debit > 0:  # İndirilecek KDV
                vat_return["vat_reclaimed"] += debit
            
            # Toplam Satışlar (KDV hariç) (Box 6)
            if account.startswith("4"):  # Gelir hesapları
                if credit > 0:
                    vat_return["total_sales_ex_vat"] += credit
            
            # Toplam Alımlar (KDV hariç) (Box 7)
            if account.startswith("5"):  # Gider hesapları
                if debit > 0:
                    vat_return["total_purchases_ex_vat"] += debit
        
        # Toplam ve Net KDV hesapla
        vat_return["total_vat_due"] = vat_return["vat_due_sales"] + vat_return["vat_due_acquisitions"]
        vat_return["net_vat_due"] = vat_return["total_vat_due"] - vat_return["vat_reclaimed"]
        
        # Yuvarla (2 ondalık basamak)
        for key, value in vat_return.items():
            if isinstance(value, (int, float, Decimal)):
                vat_return[key] = round(value, 2)
        
        return vat_return
    
    def submit_vat_return(self, vat_data):
        """KDV beyanını kaydet"""
        # HMRC API ile gönderim burada yapılabilir
        # Basitleştirme için sadece veritabanına kaydediyoruz
        
        # Tarih alanlarını kontrol et
        period_start = vat_data.get("period_start")
        period_end = vat_data.get("period_end")
        
        vat_return = {
            "period_start": period_start,
            "period_end": period_end,
            "submission_date": datetime.now().isoformat(),
            "vat_due_sales": vat_data.get("vat_due_sales", 0),
            "vat_due_acquisitions": vat_data.get("vat_due_acquisitions", 0),
            "total_vat_due": vat_data.get("total_vat_due", 0),
            "vat_reclaimed": vat_data.get("vat_reclaimed", 0),
            "net_vat_due": vat_data.get("net_vat_due", 0),
            "total_sales_ex_vat": vat_data.get("total_sales_ex_vat", 0),
            "total_purchases_ex_vat": vat_data.get("total_purchases_ex_vat", 0),
            "total_supplies_ex_vat": vat_data.get("total_supplies_ex_vat", 0),
            "total_acquisitions_ex_vat": vat_data.get("total_acquisitions_ex_vat", 0),
            "status": "submitted"
        }
        
        # Veritabanına ekle
        return self.db.add_vat_return(vat_return)
    
    def get_vat_returns(self):
        """KDV beyanlarını al"""
        return self.db.get_vat_returns()
    
    def calculate_tax_return(self, tax_year):
        """Gelir vergisi beyannamesi hesapla"""
        # Vergi yılı formatı: "2022-23"
        try:
            year_parts = tax_year.split("-")
            start_year = int(year_parts[0])
            end_year = int(year_parts[1])
            
            # İngiltere vergi yılı: 6 Nisan - 5 Nisan
            start_date = f"{start_year}-04-06"
            end_date = f"{end_year}-04-05"
            
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
        except (ValueError, IndexError):
            raise ValueError("Geçersiz vergi yılı formatı. Beklenen format: YYYY-YY (ör: 2022-23)")
        
        # İlgili dönemdeki gelir/giderleri al
        income_expenses = self.get_income_expenses()
        period_items = []
        
        for item in income_expenses:
            try:
                item_date = datetime.strptime(item["date"], "%Y-%m-%d")
                if start <= item_date <= end:
                    period_items.append(item)
            except ValueError:
                # Geçersiz tarih formatı, öğeyi atla
                pass
        
        # Gelir vergisi hesapla
        tax_return = {
            "tax_year": tax_year,
            "period_start": start_date,
            "period_end": end_date,
            "total_income": 0,
            "total_expenses": 0,
            "net_profit": 0,
            "tax_allowance": 12570,  # 2022-23 için kişisel vergi muafiyeti (örnek değer)
            "taxable_income": 0,
            "tax_due": 0
        }
        
        # Gelir ve giderleri topla
        for item in period_items:
            tax_return["total_income"] += item["income"]
            tax_return["total_expenses"] += item["expense"]
        
        # Net kâr hesapla
        tax_return["net_profit"] = tax_return["total_income"] - tax_return["total_expenses"]
        
        # Vergilendirilecek gelir hesapla
        tax_return["taxable_income"] = max(0, tax_return["net_profit"] - tax_return["tax_allowance"])
        
        # Vergi hesapla (2022-23 oranlarına göre)
        taxable = tax_return["taxable_income"]
        tax = 0
        
        if taxable > 0:
            # Temel oran: £0-£37,700 arası %20
            basic_limit = 37700
            if taxable <= basic_limit:
                tax += taxable * 0.2
            else:
                tax += basic_limit * 0.2
                
                # Yüksek oran: £37,701-£150,000 arası %40
                higher_limit = 150000
                higher_band = min(taxable - basic_limit, higher_limit - basic_limit)
                if higher_band > 0:
                    tax += higher_band * 0.4
                
                # Ek oran: £150,000 üzeri %45
                additional_band = max(0, taxable - higher_limit)
                if additional_band > 0:
                    tax += additional_band * 0.45
        
        tax_return["tax_due"] = round(tax, 2)
        
        return tax_return
    
    def submit_tax_return(self, tax_data):
        """Gelir vergisi beyanını kaydet"""
        # HMRC API ile gönderim burada yapılabilir
        # Basitleştirme için sadece veritabanına kaydediyoruz
        
        tax_return = {
            "tax_year": tax_data.get("tax_year"),
            "period_start": tax_data.get("period_start"),
            "period_end": tax_data.get("period_end"),
            "submission_date": datetime.now().isoformat(),
            "total_income": tax_data.get("total_income", 0),
            "total_expenses": tax_data.get("total_expenses", 0),
            "net_profit": tax_data.get("net_profit", 0),
            "tax_allowance": tax_data.get("tax_allowance", 0),
            "taxable_income": tax_data.get("taxable_income", 0),
            "tax_due": tax_data.get("tax_due", 0),
            "status": "submitted"
        }
        
        # Veritabanına ekle
        return self.db.add_tax_return(tax_return)
    
    def get_tax_returns(self):
        """Gelir vergisi beyanlarını al"""
        return self.db.get_tax_returns()
        
    def get_tax_return_by_id(self, tax_return_id):
        """ID ile vergi beyannamesi al"""
        tax_returns = self.get_tax_returns()
        for tax_return in tax_returns:
            if tax_return.get("id") == tax_return_id:
                return tax_return
        return None
    
    def delete_tax_return(self, tax_return_id):
        """Vergi beyanını sil"""
        # Veritabanından silme işlemi
        return self.db.delete_tax_return(tax_return_id)
    
    def get_company_info(self):
        """Şirket bilgilerini al"""
        try:
            # Veritabanından şirket bilgilerini al
            return self.db.get_company_info()
        except AttributeError:
            # Eğer veritabanında bu metod yoksa varsayılan değer döndür
            self.logger.warning("Veritabanında get_company_info() metodu bulunamadı, varsayılan değerler kullanılıyor.")
            return {
                "company_name": "Varsayılan Şirket Ltd",
                "crn": "12345678",
                "utr": "1234567890",
                "accounting_period_start": datetime.now().replace(month=4, day=1).strftime("%Y-%m-%d"),
                "accounting_period_end": datetime.now().replace(year=datetime.now().year + 1, month=3, day=31).strftime("%Y-%m-%d"),
                "company_address": "Örnek Adres, Şehir, Ülke, Posta Kodu",
                "company_phone": "+90 123 456 7890",
                "company_email": "info@ornek-sirket.com",
                "company_website": "www.ornek-sirket.com",
                "vat_number": "GB123456789"
            }