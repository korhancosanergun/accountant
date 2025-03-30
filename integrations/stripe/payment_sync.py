#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Stripe Ödeme Senkronizasyonu
Stripe ödemeleri ve faturaları muhasebe sistemi ile senkronize eder.
"""

import logging
from datetime import datetime, timedelta
import json
import os
import uuid

class StripePaymentSync:
    """Stripe ödeme senkronizasyonu"""
    
    def __init__(self, stripe_client, ledger, config):
        """Senkronizasyon başlatıcı
        
        Args:
            stripe_client: Stripe API istemcisi nesnesi
            ledger: Muhasebe defteri nesnesi
            config: Uygulama yapılandırması
        """
        self.stripe_client = stripe_client
        self.ledger = ledger
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Yapılandırmadan hesap kodlarını al
        self.account_mappings = config.get("stripe", {}).get("account_mappings", {})
        
        # Varsayılan hesap kodları
        self.default_accounts = {
            "stripe_revenue": "4100",  # Gelir hesabı
            "stripe_fees": "5900",     # Banka masrafları hesabı
            "stripe_balance": "1110",  # Banka hesabı (Stripe bakiyesi)
            "accounts_receivable": "1200", # Alacak hesapları
            "vat_payable": "2100"     # Ödenecek KDV
        }
        
        # Yapılandırmada yoksa varsayılan hesapları kullan
        if not self.account_mappings:
            self.account_mappings = self.default_accounts
    
    def sync_balance(self):
        """Stripe bakiyesini senkronize et"""
        # Stripe bakiyesini al
        balance = self.stripe_client.get_balance()
        
        if not balance:
            self.logger.error("Stripe bakiyesi alınamadı")
            return False
        
        # Bakiyeleri her para birimi için güncelle
        for available_balance in balance.get("available", []):
            currency = available_balance.get("currency", "").upper()
            amount = available_balance.get("amount", 0) / 100  # Cent'ten para birimine dönüştür
            
            # Para birimi için muhasebe hesap kodu 
            account_code = self.account_mappings.get(f"stripe_balance_{currency.lower()}")
            if not account_code:
                account_code = f"{self.default_accounts['stripe_balance']}_{currency.lower()}"
                
                # Hesap yoksa oluştur
                account = self.ledger.get_account_by_code(account_code)
                if not account:
                    self._create_stripe_balance_account(account_code, currency)
            
            # Hesap bakiyesini güncelle
            account = self.ledger.get_account_by_code(account_code)
            if account:
                account["balance"] = amount
                self.ledger.update_account(account_code, account)
                self.logger.info(f"Stripe {currency} bakiyesi güncellendi: {amount}")
            else:
                self.logger.error(f"Stripe {currency} bakiyesi için hesap bulunamadı: {account_code}")
        
        return True
    
    def _create_stripe_balance_account(self, account_code, currency):
        """Stripe bakiyesi için muhasebe hesabı oluştur
        
        Args:
            account_code: Hesap kodu
            currency: Para birimi
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        try:
            account_data = {
                "code": account_code,
                "name": f"Stripe Bakiye ({currency.upper()})",
                "type": "asset",
                "category": "current_asset",
                "vat_rate": 0,
                "balance": 0
            }
            
            self.ledger.add_account(account_data)
            
            # Hesap eşleştirmesini güncelle
            self.account_mappings[f"stripe_balance_{currency.lower()}"] = account_code
            
            # Yapılandırmayı güncelle
            if "stripe" not in self.config:
                self.config["stripe"] = {}
            self.config["stripe"]["account_mappings"] = self.account_mappings
            
            # Yapılandırmayı kaydet (Burada config'i nasıl kaydettiğinize bağlı)
            
            return True
        except Exception as e:
            self.logger.error(f"Stripe bakiye hesabı oluşturulurken hata: {e}")
            return False
    
    def sync_payments(self, start_date=None, end_date=None, limit=100):
        """Stripe ödemelerini senkronize et
        
        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında, None ise son 30 gün)
            end_date: Bitiş tarihi (YYYY-MM-DD formatında, None ise bugün)
            limit: Alınacak maksimum ödeme sayısı
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        if not start_date:
            # Varsayılan olarak son 30 günü al
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        # Stripe işlemlerini al
        transactions = self.stripe_client.get_transactions_by_date(start_date, end_date, limit)
        
        if not transactions:
            self.logger.warning(f"Stripe işlemleri alınamadı veya işlem yok ({start_date} - {end_date})")
            return False
        
        # Son senkronizasyon tarihini al
        last_sync_date = self._get_last_sync_date()
        
        # İşlemleri senkronize et
        synced_count = 0
        
        for transaction in transactions.auto_paging_iter():
            # İşlem ID'si
            transaction_id = transaction.get("id")
            
            # Zaten senkronize edilmiş mi kontrol et
            if self._is_transaction_synced(transaction_id):
                continue
                
            # İşlemi senkronize et
            if self._sync_transaction(transaction):
                synced_count += 1
                
                # İşlemi işaretlemek için işlem ID'sini kaydet
                self._mark_transaction_synced(transaction_id)
        
        # Son senkronizasyon tarihini güncelle
        if synced_count > 0:
            self._update_last_sync_date()
            self.logger.info(f"Stripe: {synced_count} işlem senkronize edildi")
        
        return True
    
    def _sync_transaction(self, transaction):
        """Bir Stripe işlemini senkronize et
        
        Args:
            transaction: Stripe işlem nesnesi
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        try:
            # İşlem tipi
            transaction_type = transaction.get("type")
            
            # Farklı işlem tiplerini farklı şekilde işle
            if transaction_type == "charge":
                return self._sync_charge_transaction(transaction)
            elif transaction_type == "payment":
                return self._sync_payment_transaction(transaction)
            elif transaction_type == "payout":
                return self._sync_payout_transaction(transaction)
            elif transaction_type == "refund":
                return self._sync_refund_transaction(transaction)
            elif transaction_type == "adjustment":
                return self._sync_adjustment_transaction(transaction)
            elif transaction_type == "stripe_fee":
                return self._sync_fee_transaction(transaction)
            else:
                self.logger.warning(f"Bilinmeyen Stripe işlem tipi: {transaction_type}")
                return False
        except Exception as e:
            self.logger.error(f"Stripe işlemi senkronize edilirken hata: {e}")
            return False
    
    def _sync_charge_transaction(self, transaction):
        """Ödeme işlemini senkronize et
        
        Args:
            transaction: Stripe işlem nesnesi
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        # İşlem detayları
        amount = transaction.get("amount", 0) / 100  # Cent'ten para birimine dönüştür
        currency = transaction.get("currency", "").upper()
        description = transaction.get("description", "")
        created = datetime.fromtimestamp(transaction.get("created", 0))
        date_str = created.strftime("%Y-%m-%d")
        
        # İşlem kaydı için gerekli alanları hazırla
        ledger_transaction = {
            "date": date_str,
            "document_number": f"STRIPE-{transaction.get('id')}",
            "description": description or "Stripe Ödemesi",
            "transaction_type": "payment",
            "status": "reconciled",
            "notes": f"Stripe'dan otomatik olarak senkronize edildi. İşlem ID: {transaction.get('id')}",
            "source": "stripe",
            "source_id": transaction.get("id"),
            "vat": 0
        }
        
        # Gelir KDV'si (UK veya AB için %20, diğerleri için %0)
        # Bu basit bir örnektir. Gerçek uygulamada müşteri ülkesine göre KDV oranı belirlenmelidir.
        vat_rate = 20  # Varsayılan UK KDV oranı
        vat_amount = round(amount * vat_rate / (100 + vat_rate), 2)  # KDV dahil tutardan KDV'yi hesapla
        net_amount = amount - vat_amount
        
        # Stripe bakiye hesabını belirle
        balance_account_code = self.account_mappings.get(f"stripe_balance_{currency.lower()}")
        if not balance_account_code:
            balance_account_code = f"{self.default_accounts['stripe_balance']}_{currency.lower()}"
        
        # Gelir hesabını belirle
        revenue_account_code = self.account_mappings.get("stripe_revenue")
        if not revenue_account_code:
            revenue_account_code = self.default_accounts["stripe_revenue"]
        
        # KDV hesabını belirle
        vat_account_code = self.account_mappings.get("vat_payable")
        if not vat_account_code:
            vat_account_code = self.default_accounts["vat_payable"]
        
        # 1) Stripe bakiyesine borç
        ledger_transaction["account"] = balance_account_code
        ledger_transaction["debit"] = amount
        ledger_transaction["credit"] = 0
        self.ledger.add_transaction(ledger_transaction)
        
        # 2) Gelir hesabına alacak (net tutar)
        ledger_transaction["account"] = revenue_account_code
        ledger_transaction["debit"] = 0
        ledger_transaction["credit"] = net_amount
        self.ledger.add_transaction(ledger_transaction)
        
        # 3) KDV hesabına alacak
        if vat_amount > 0:
            ledger_transaction["account"] = vat_account_code
            ledger_transaction["debit"] = 0
            ledger_transaction["credit"] = vat_amount
            ledger_transaction["vat"] = vat_amount
            self.ledger.add_transaction(ledger_transaction)
        
        return True
    
    def _sync_payment_transaction(self, transaction):
        """Ödeme işlemini senkronize et"""
        # Basit bir uygulama için charge transaction ile aynı işlemleri yap
        return self._sync_charge_transaction(transaction)
    
    def _sync_payout_transaction(self, transaction):
        """Ödeme çıkışı işlemini senkronize et
        
        Args:
            transaction: Stripe işlem nesnesi
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        # İşlem detayları
        amount = transaction.get("amount", 0) / 100  # Cent'ten para birimine dönüştür
        currency = transaction.get("currency", "").upper()
        description = transaction.get("description", "")
        created = datetime.fromtimestamp(transaction.get("created", 0))
        date_str = created.strftime("%Y-%m-%d")
        
        # İşlem kaydı için gerekli alanları hazırla
        ledger_transaction = {
            "date": date_str,
            "document_number": f"STRIPE-PAYOUT-{transaction.get('id')}",
            "description": description or "Stripe Ödeme Çıkışı",
            "transaction_type": "transfer",
            "status": "reconciled",
            "notes": f"Stripe'dan otomatik olarak senkronize edildi. İşlem ID: {transaction.get('id')}",
            "source": "stripe",
            "source_id": transaction.get("id"),
            "vat": 0
        }
        
        # Stripe bakiye hesabını belirle
        balance_account_code = self.account_mappings.get(f"stripe_balance_{currency.lower()}")
        if not balance_account_code:
            balance_account_code = f"{self.default_accounts['stripe_balance']}_{currency.lower()}"
        
        # Banka hesabını belirle (burada varsayılan banka hesabını kullanıyoruz)
        bank_account_code = "1100"  # Banka hesabı
        
        # 1) Banka hesabına borç
        ledger_transaction["account"] = bank_account_code
        ledger_transaction["debit"] = amount
        ledger_transaction["credit"] = 0
        self.ledger.add_transaction(ledger_transaction)
        
        # 2) Stripe bakiyesinden düş
        ledger_transaction["account"] = balance_account_code
        ledger_transaction["debit"] = 0
        ledger_transaction["credit"] = amount
        self.ledger.add_transaction(ledger_transaction)
        
        return True
    
    def _sync_refund_transaction(self, transaction):
        """İade işlemini senkronize et
        
        Args:
            transaction: Stripe işlem nesnesi
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        # İşlem detayları
        amount = transaction.get("amount", 0) / 100  # Cent'ten para birimine dönüştür
        currency = transaction.get("currency", "").upper()
        description = transaction.get("description", "")
        created = datetime.fromtimestamp(transaction.get("created", 0))
        date_str = created.strftime("%Y-%m-%d")
        
        # İşlem kaydı için gerekli alanları hazırla
        ledger_transaction = {
            "date": date_str,
            "document_number": f"STRIPE-REFUND-{transaction.get('id')}",
            "description": description or "Stripe İadesi",
            "transaction_type": "refund",
            "status": "reconciled",
            "notes": f"Stripe'dan otomatik olarak senkronize edildi. İşlem ID: {transaction.get('id')}",
            "source": "stripe",
            "source_id": transaction.get("id"),
            "vat": 0
        }
        
        # Gelir KDV'si (UK veya AB için %20, diğerleri için %0)
        vat_rate = 20  # Varsayılan UK KDV oranı
        vat_amount = round(amount * vat_rate / (100 + vat_rate), 2)  # KDV dahil tutardan KDV'yi hesapla
        net_amount = amount - vat_amount
        
        # Stripe bakiye hesabını belirle
        balance_account_code = self.account_mappings.get(f"stripe_balance_{currency.lower()}")
        if not balance_account_code:
            balance_account_code = f"{self.default_accounts['stripe_balance']}_{currency.lower()}"
        
        # Gelir hesabını belirle
        revenue_account_code = self.account_mappings.get("stripe_revenue")
        if not revenue_account_code:
            revenue_account_code = self.default_accounts["stripe_revenue"]
        
        # KDV hesabını belirle
        vat_account_code = self.account_mappings.get("vat_payable")
        if not vat_account_code:
            vat_account_code = self.default_accounts["vat_payable"]
        
        # 1) Gelir hesabına borç (iade - net tutar)
        ledger_transaction["account"] = revenue_account_code
        ledger_transaction["debit"] = net_amount
        ledger_transaction["credit"] = 0
        self.ledger.add_transaction(ledger_transaction)
        
        # 2) KDV hesabına borç (iade)
        if vat_amount > 0:
            ledger_transaction["account"] = vat_account_code
            ledger_transaction["debit"] = vat_amount
            ledger_transaction["credit"] = 0
            ledger_transaction["vat"] = vat_amount
            self.ledger.add_transaction(ledger_transaction)
        
        # 3) Stripe bakiyesinden düş
        ledger_transaction["account"] = balance_account_code
        ledger_transaction["debit"] = 0
        ledger_transaction["credit"] = amount
        ledger_transaction["vat"] = 0
        self.ledger.add_transaction(ledger_transaction)
        
        return True
    
    def _sync_adjustment_transaction(self, transaction):
        """Düzeltme işlemini senkronize et
        
        Args:
            transaction: Stripe işlem nesnesi
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        # Düzeltme işlemleri için basit bir implementasyon
        # Gerçek bir uygulamada, düzeltme türüne göre daha karmaşık bir işleme gerekebilir
        
        # İşlem detayları
        amount = transaction.get("amount", 0) / 100  # Cent'ten para birimine dönüştür
        currency = transaction.get("currency", "").upper()
        description = transaction.get("description", "")
        created = datetime.fromtimestamp(transaction.get("created", 0))
        date_str = created.strftime("%Y-%m-%d")
        
        # İşlem kaydı için gerekli alanları hazırla
        ledger_transaction = {
            "date": date_str,
            "document_number": f"STRIPE-ADJ-{transaction.get('id')}",
            "description": description or "Stripe Hesap Düzeltmesi",
            "transaction_type": "adjustment",
            "status": "reconciled",
            "notes": f"Stripe'dan otomatik olarak senkronize edildi. İşlem ID: {transaction.get('id')}",
            "source": "stripe",
            "source_id": transaction.get("id"),
            "vat": 0
        }
        
        # Stripe bakiye hesabını belirle
        balance_account_code = self.account_mappings.get(f"stripe_balance_{currency.lower()}")
        if not balance_account_code:
            balance_account_code = f"{self.default_accounts['stripe_balance']}_{currency.lower()}"
        
        # İşlem artı ise Stripe bakiyesine ekle, eksi ise çıkar
        if amount >= 0:
            # Bakiyeye borç
            ledger_transaction["account"] = balance_account_code
            ledger_transaction["debit"] = amount
            ledger_transaction["credit"] = 0
            self.ledger.add_transaction(ledger_transaction)
            
            # Düzeltme için karşı hesaba alacak (Burada basit olarak gelir hesabı kullanıyoruz)
            adjustment_account = self.account_mappings.get("stripe_revenue") or self.default_accounts["stripe_revenue"]
            ledger_transaction["account"] = adjustment_account
            ledger_transaction["debit"] = 0
            ledger_transaction["credit"] = amount
            self.ledger.add_transaction(ledger_transaction)
        else:
            # Bakiyeden alacak
            ledger_transaction["account"] = balance_account_code
            ledger_transaction["debit"] = 0
            ledger_transaction["credit"] = abs(amount)
            self.ledger.add_transaction(ledger_transaction)
            
            # Düzeltme için karşı hesaba borç
            adjustment_account = self.account_mappings.get("stripe_revenue") or self.default_accounts["stripe_revenue"]
            ledger_transaction["account"] = adjustment_account
            ledger_transaction["debit"] = abs(amount)
            ledger_transaction["credit"] = 0
            self.ledger.add_transaction(ledger_transaction)
        
        return True
    
    def _sync_fee_transaction(self, transaction):
        """Stripe ücret işlemini senkronize et
        
        Args:
            transaction: Stripe işlem nesnesi
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        # İşlem detayları
        amount = transaction.get("amount", 0) / 100  # Cent'ten para birimine dönüştür
        currency = transaction.get("currency", "").upper()
        description = transaction.get("description", "")
        created = datetime.fromtimestamp(transaction.get("created", 0))
        date_str = created.strftime("%Y-%m-%d")
        
        # İşlem kaydı için gerekli alanları hazırla
        ledger_transaction = {
            "date": date_str,
            "document_number": f"STRIPE-FEE-{transaction.get('id')}",
            "description": description or "Stripe İşlem Ücreti",
            "transaction_type": "fee",
            "status": "reconciled",
            "notes": f"Stripe'dan otomatik olarak senkronize edildi. İşlem ID: {transaction.get('id')}",
            "source": "stripe",
            "source_id": transaction.get("id"),
            "vat": 0
        }
        
        # Stripe bakiye ve masraf hesaplarını belirle
        balance_account_code = self.account_mappings.get(f"stripe_balance_{currency.lower()}")
        if not balance_account_code:
            balance_account_code = f"{self.default_accounts['stripe_balance']}_{currency.lower()}"
        
        fees_account_code = self.account_mappings.get("stripe_fees")
        if not fees_account_code:
            fees_account_code = self.default_accounts["stripe_fees"]
        
        # 1) Masraf hesabına borç
        ledger_transaction["account"] = fees_account_code
        ledger_transaction["debit"] = abs(amount)
        ledger_transaction["credit"] = 0
        self.ledger.add_transaction(ledger_transaction)
        
        # 2) Stripe bakiyesinden düş
        ledger_transaction["account"] = balance_account_code
        ledger_transaction["debit"] = 0
        ledger_transaction["credit"] = abs(amount)
        self.ledger.add_transaction(ledger_transaction)
        
        return True
    
    def sync_invoices(self, limit=100, status="paid"):
        """Stripe faturalarını senkronize et
        
        Args:
            limit: Alınacak maksimum fatura sayısı
            status: Fatura durumu filtresi (paid, open, draft, void, uncollectible)
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        # Stripe faturalarını al
        invoices = self.stripe_client.get_invoices(limit=limit, status=status)
        
        if not invoices:
            self.logger.warning(f"Stripe faturaları alınamadı veya fatura yok")
            return False
        
        # Faturaları senkronize et
        synced_count = 0
        
        for invoice in invoices.auto_paging_iter():
            # Fatura ID'si
            invoice_id = invoice.get("id")
            
            # Zaten senkronize edilmiş mi kontrol et
            if self._is_invoice_synced(invoice_id):
                continue
                
            # Faturayı senkronize et
            if self._sync_invoice(invoice):
                synced_count += 1
                
                # Faturayı işaretlemek için ID'sini kaydet
                self._mark_invoice_synced(invoice_id)
        
        if synced_count > 0:
            self.logger.info(f"Stripe: {synced_count} fatura senkronize edildi")
        
        return True
    
    def _sync_invoice(self, invoice):
        """Bir Stripe faturasını senkronize et
        
        Args:
            invoice: Stripe fatura nesnesi
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        try:
            # Fatura durumu
            status = invoice.get("status")
            
            # Sadece ödenmiş faturaları senkronize et
            if status != "paid":
                return False
            
            # Fatura detayları
            invoice_id = invoice.get("id")
            invoice_number = invoice.get("number")
            customer_id = invoice.get("customer")
            customer_email = invoice.get("customer_email")
            customer_name = invoice.get("customer_name", "")
            amount_paid = invoice.get("amount_paid", 0) / 100
            amount_due = invoice.get("amount_due", 0) / 100
            currency = invoice.get("currency", "").upper()
            created = datetime.fromtimestamp(invoice.get("created", 0))
            date_str = created.strftime("%Y-%m-%d")
            due_date = datetime.fromtimestamp(invoice.get("due_date", 0)).strftime("%Y-%m-%d") if invoice.get("due_date") else None
            
            # Müşteri bilgisini getir
            customer = None
            if customer_id:
                customer = self.stripe_client.get_customer(customer_id)
                
            # Fatura verilerini hazırla
            customer_name = customer_name or (customer.get("name") if customer else "") or customer_email or "Stripe Müşterisi"
            
            # Fatura öğelerini işle (KDV hesaplaması için)
            invoice_items = []
            vat_total = 0
            
            if "lines" in invoice and "data" in invoice["lines"]:
                for item in invoice["lines"]["data"]:
                    description = item.get("description", "")
                    amount = item.get("amount", 0) / 100
                    
                    # KDV oranı - gerçek uygulamada müşteri konumuna göre değişiklik gösterir
                    vat_rate = 20  # Varsayılan UK KDV oranı
                    
                    # KDV dahil tutardan KDV'yi hesapla
                    vat_amount = round(amount * vat_rate / (100 + vat_rate), 2)
                    net_amount = amount - vat_amount
                    vat_total += vat_amount
                    
                    invoice_items.append({
                        "description": description,
                        "amount": amount,
                        "net_amount": net_amount,
                        "vat_amount": vat_amount,
                        "vat_rate": vat_rate
                    })
            
            # Muhasebe sistemine fatura ekle
            invoice_data = {
                "type": "sales",
                "invoice_number": invoice_number or f"STRIPE-INV-{invoice_id}",
                "date": date_str,
                "due_date": due_date or date_str,
                "entity_name": customer_name,
                "entity_email": customer_email,
                "entity_address": "",
                "amount": amount_paid - vat_total,  # Net tutar
                "vat": vat_total,
                "total": amount_paid,
                "currency": currency,
                "payment_status": "paid",
                "payment_date": date_str,
                "payment_method": "stripe",
                "notes": f"Stripe'dan otomatik olarak senkronize edildi. Fatura ID: {invoice_id}",
                "source": "stripe",
                "source_id": invoice_id,
                "items": invoice_items
            }
            
            # Faturayı ekle
            self.ledger.add_invoice(invoice_data)
            
            return True
        except Exception as e:
            self.logger.error(f"Stripe faturası senkronize edilirken hata: {e}")
            return False
    
    def _get_last_sync_date(self):
        """Son senkronizasyon tarihini al
        
        Returns:
            datetime: Son senkronizasyon tarihi, yoksa None
        """
        try:
            # Senkronizasyon verilerini saklamak için dizin
            sync_dir = os.path.join(os.path.dirname(__file__), "sync_data")
            os.makedirs(sync_dir, exist_ok=True)
            
            # Senkronizasyon dosyası
            sync_file = os.path.join(sync_dir, "stripe_sync.json")
            
            if not os.path.exists(sync_file):
                return None
                
            with open(sync_file, "r") as f:
                data = json.load(f)
                last_sync = data.get("last_sync")
                
                if not last_sync:
                    return None
                    
                return datetime.strptime(last_sync, "%Y-%m-%d")
                
        except Exception as e:
            self.logger.error(f"Son senkronizasyon tarihi alınırken hata: {e}")
            return None
    
    def _update_last_sync_date(self):
        """Son senkronizasyon tarihini güncelle"""
        try:
            # Senkronizasyon verilerini saklamak için dizin
            sync_dir = os.path.join(os.path.dirname(__file__), "sync_data")
            os.makedirs(sync_dir, exist_ok=True)
            
            # Senkronizasyon dosyası
            sync_file = os.path.join(sync_dir, "stripe_sync.json")
            
            # Şu anki tarih
            now = datetime.now().strftime("%Y-%m-%d")
            
            # Senkronizasyon verisini güncelle
            sync_data = {"last_sync": now}
            
            with open(sync_file, "w") as f:
                json.dump(sync_data, f)
                
            return True
                
        except Exception as e:
            self.logger.error(f"Son senkronizasyon tarihi güncellenirken hata: {e}")
            return False
    
    def _is_transaction_synced(self, transaction_id):
        """Bir işlemin daha önce senkronize edilip edilmediğini kontrol et
        
        Args:
            transaction_id: İşlem ID'si
            
        Returns:
            bool: Senkronize edilmişse True, değilse False
        """
        try:
            # Senkronize edilmiş işlemleri saklamak için dizin
            sync_dir = os.path.join(os.path.dirname(__file__), "sync_data")
            os.makedirs(sync_dir, exist_ok=True)
            
            # Senkronize edilmiş işlemler dosyası
            synced_file = os.path.join(sync_dir, "stripe_synced_transactions.json")
            
            if not os.path.exists(synced_file):
                return False
                
            with open(synced_file, "r") as f:
                synced_transactions = json.load(f)
                
            return transaction_id in synced_transactions
                
        except Exception as e:
            self.logger.error(f"İşlem senkronizasyon durumu kontrol edilirken hata: {e}")
            return False
    
    def _mark_transaction_synced(self, transaction_id):
        """Bir işlemi senkronize edilmiş olarak işaretle
        
        Args:
            transaction_id: İşlem ID'si
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        try:
            # Senkronize edilmiş işlemleri saklamak için dizin
            sync_dir = os.path.join(os.path.dirname(__file__), "sync_data")
            os.makedirs(sync_dir, exist_ok=True)
            
            # Senkronize edilmiş işlemler dosyası
            synced_file = os.path.join(sync_dir, "stripe_synced_transactions.json")
            
            # Mevcut senkronize edilmiş işlemleri yükle
            synced_transactions = []
            if os.path.exists(synced_file):
                with open(synced_file, "r") as f:
                    synced_transactions = json.load(f)
            
            # İşlemi ekle
            if transaction_id not in synced_transactions:
                synced_transactions.append(transaction_id)
                
            # Dosyaya kaydet
            with open(synced_file, "w") as f:
                json.dump(synced_transactions, f)
                
            return True
                
        except Exception as e:
            self.logger.error(f"İşlem senkronize edilmiş olarak işaretlenirken hata: {e}")
            return False
    
    def _is_invoice_synced(self, invoice_id):
        """Bir faturanın daha önce senkronize edilip edilmediğini kontrol et
        
        Args:
            invoice_id: Fatura ID'si
            
        Returns:
            bool: Senkronize edilmişse True, değilse False
        """
        try:
            # Senkronize edilmiş faturaları saklamak için dizin
            sync_dir = os.path.join(os.path.dirname(__file__), "sync_data")
            os.makedirs(sync_dir, exist_ok=True)
            
            # Senkronize edilmiş faturalar dosyası
            synced_file = os.path.join(sync_dir, "stripe_synced_invoices.json")
            
            if not os.path.exists(synced_file):
                return False
                
            with open(synced_file, "r") as f:
                synced_invoices = json.load(f)
                
            return invoice_id in synced_invoices
                
        except Exception as e:
            self.logger.error(f"Fatura senkronizasyon durumu kontrol edilirken hata: {e}")
            return False
    
    def _mark_invoice_synced(self, invoice_id):
        """Bir faturayı senkronize edilmiş olarak işaretle
        
        Args:
            invoice_id: Fatura ID'si
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        try:
            # Senkronize edilmiş faturaları saklamak için dizin
            sync_dir = os.path.join(os.path.dirname(__file__), "sync_data")
            os.makedirs(sync_dir, exist_ok=True)
            
            # Senkronize edilmiş faturalar dosyası
            synced_file = os.path.join(sync_dir, "stripe_synced_invoices.json")
            
            # Mevcut senkronize edilmiş faturaları yükle
            synced_invoices = []
            if os.path.exists(synced_file):
                with open(synced_file, "r") as f:
                    synced_invoices = json.load(f)
            
            # Faturayı ekle
            if invoice_id not in synced_invoices:
                synced_invoices.append(invoice_id)
                
            # Dosyaya kaydet
            with open(synced_file, "w") as f:
                json.dump(synced_invoices, f)
                
            return True
                
        except Exception as e:
            self.logger.error(f"Fatura senkronize edilmiş olarak işaretlenirken hata: {e}")
            return False