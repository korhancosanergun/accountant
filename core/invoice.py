#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Fatura Modülü
Satış ve alış faturaları için sınıflar ve işlevler
"""

import uuid
from datetime import datetime, timedelta
import logging
from decimal import Decimal, ROUND_HALF_UP

from core.transaction import Transaction

# Modül için logger
logger = logging.getLogger(__name__)


class InvoiceItem:
    """Fatura kalemi sınıfı"""
    
    def __init__(self, description, quantity, unit_price, vat_rate=20, vat_amount=None, total=None):
        """Fatura kalemi başlatıcı
        
        Args:
            description: Kalem açıklaması
            quantity: Miktar
            unit_price: Birim fiyat
            vat_rate: KDV oranı (%)
            vat_amount: KDV tutarı (None ise hesaplanır)
            total: Toplam tutar (None ise hesaplanır)
        """
        self.description = description
        self.quantity = Decimal(str(quantity))
        self.unit_price = Decimal(str(unit_price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.vat_rate = Decimal(str(vat_rate))
        
        # KDV tutarı ve toplam tutar hesapla
        self.net_amount = (self.quantity * self.unit_price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if vat_amount is not None:
            self.vat_amount = Decimal(str(vat_amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            self.vat_amount = (self.net_amount * self.vat_rate / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        if total is not None:
            self.total = Decimal(str(total)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            self.total = (self.net_amount + self.vat_amount).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def to_dict(self):
        """Fatura kalemini sözlük olarak döndür
        
        Returns:
            dict: Fatura kalemi verileri
        """
        return {
            "description": self.description,
            "quantity": float(self.quantity),
            "unit_price": float(self.unit_price),
            "vat_rate": float(self.vat_rate),
            "vat_amount": float(self.vat_amount),
            "total": float(self.total)
        }
    
    @classmethod
    def from_dict(cls, data):
        """Sözlükten fatura kalemi nesnesi oluştur
        
        Args:
            data: Fatura kalemi verileri
            
        Returns:
            InvoiceItem: Fatura kalemi nesnesi
        """
        return cls(
            description=data.get("description", ""),
            quantity=data.get("quantity", 1),
            unit_price=data.get("unit_price", 0),
            vat_rate=data.get("vat_rate", 20),
            vat_amount=data.get("vat_amount"),
            total=data.get("total")
        )


class Invoice:
    """Fatura sınıfı"""
    
    def __init__(self, invoice_id=None, invoice_number=None, invoice_type="sales", date=None, 
                 due_date=None, entity_name="", entity_id=None, items=None, notes="", 
                 payment_status="unpaid", payment_date=None, payment_method=None, 
                 payment_reference=None, auto_post=True):
        """Fatura başlatıcı
        
        Args:
            invoice_id: Fatura ID (None ise otomatik oluşturulur)
            invoice_number: Fatura numarası (None ise otomatik oluşturulur)
            invoice_type: Fatura tipi ('sales' veya 'purchase')
            date: Fatura tarihi (None ise bugün)
            due_date: Vade tarihi (None ise fatura tarihine 30 gün eklenir)
            entity_name: Müşteri/tedarikçi adı
            entity_id: Müşteri/tedarikçi ID
            items: Fatura kalemleri listesi
            notes: İlave notlar
            payment_status: Ödeme durumu ('unpaid', 'paid', 'partial', 'overdue')
            payment_date: Ödeme tarihi
            payment_method: Ödeme yöntemi
            payment_reference: Ödeme referansı
            auto_post: Otomatik muhasebeleştirme yapılsın mı
        """
        self.id = invoice_id if invoice_id is not None else str(uuid.uuid4())
        
        # Fatura numarası
        if invoice_number is None:
            prefix = "INV" if invoice_type == "sales" else "PUR"
            current_date = datetime.now().strftime("%Y%m%d")
            self.invoice_number = f"{prefix}-{current_date}-{str(uuid.uuid4())[:8].upper()}"
        else:
            self.invoice_number = invoice_number
        
        self.type = invoice_type
        
        # Fatura tarihi
        if date is None:
            self.date = datetime.now().strftime("%Y-%m-%d")
        else:
            self.date = date
        
        # Vade tarihi
        if due_date is None:
            # Fatura tarihinin 30 gün sonrası
            invoice_date = datetime.strptime(self.date, "%Y-%m-%d")
            self.due_date = (invoice_date + timedelta(days=30)).strftime("%Y-%m-%d")
        else:
            self.due_date = due_date
        
        self.entity_name = entity_name
        self.entity_id = entity_id
        self.notes = notes
        self.payment_status = payment_status
        self.payment_date = payment_date
        self.payment_method = payment_method
        self.payment_reference = payment_reference
        self.auto_post = auto_post
        
        # Fatura kalemleri
        self.items = []
        if items:
            for item in items:
                if isinstance(item, dict):
                    self.items.append(InvoiceItem.from_dict(item))
                else:
                    self.items.append(item)
        
        # Toplam tutarlar
        self._calculate_totals()
    
    def _calculate_totals(self):
        """Toplam tutarları hesapla"""
        self.net_amount = sum(item.net_amount for item in self.items)
        self.vat_amount = sum(item.vat_amount for item in self.items)
        self.total_amount = sum(item.total for item in self.items)
    
    def add_item(self, item):
        """Faturaya kalem ekle
        
        Args:
            item: Fatura kalemi nesnesi veya sözlük
        """
        if isinstance(item, dict):
            item = InvoiceItem.from_dict(item)
        
        self.items.append(item)
        self._calculate_totals()
    
    def remove_item(self, index):
        """Faturadan kalem çıkar
        
        Args:
            index: Kalem indeksi
            
        Returns:
            bool: İşlem başarılı mı
        """
        if 0 <= index < len(self.items):
            del self.items[index]
            self._calculate_totals()
            return True
        return False
    
    def to_dict(self):
        """Faturayı sözlük olarak döndür
        
        Returns:
            dict: Fatura verileri
        """
        return {
            "id": self.id,
            "invoice_number": self.invoice_number,
            "type": self.type,
            "date": self.date,
            "due_date": self.due_date,
            "entity_name": self.entity_name,
            "entity_id": self.entity_id,
            "amount": float(self.net_amount),
            "vat": float(self.vat_amount),
            "payment_status": self.payment_status,
            "payment_date": self.payment_date,
            "payment_method": self.payment_method,
            "payment_reference": self.payment_reference,
            "notes": self.notes,
            "auto_post": self.auto_post,
            "items": [item.to_dict() for item in self.items]
        }
    
    @classmethod
    def from_dict(cls, data):
        """Sözlükten fatura nesnesi oluştur
        
        Args:
            data: Fatura verileri
            
        Returns:
            Invoice: Fatura nesnesi
        """
        # Fatura kalemlerini al
        items_data = data.get("items", [])
        items = [InvoiceItem.from_dict(item) for item in items_data]
        
        return cls(
            invoice_id=data.get("id"),
            invoice_number=data.get("invoice_number"),
            invoice_type=data.get("type", "sales"),
            date=data.get("date"),
            due_date=data.get("due_date"),
            entity_name=data.get("entity_name", ""),
            entity_id=data.get("entity_id"),
            items=items,
            notes=data.get("notes", ""),
            payment_status=data.get("payment_status", "unpaid"),
            payment_date=data.get("payment_date"),
            payment_method=data.get("payment_method"),
            payment_reference=data.get("payment_reference"),
            auto_post=data.get("auto_post", True)
        )
    
    def validate(self):
        """Faturayı doğrula
        
        Returns:
            bool: Fatura geçerli mi
            str: Hata mesajı (geçerliyse None)
        """
        # Gerekli alanlar
        if not self.invoice_number:
            return False, "Fatura numarası gereklidir"
        
        if not self.date:
            return False, "Fatura tarihi gereklidir"
        
        if not self.entity_name:
            return False, "Müşteri/tedarikçi adı gereklidir"
        
        if not self.items:
            return False, "En az bir fatura kalemi gereklidir"
        
        if self.type not in ["sales", "purchase"]:
            return False, "Geçersiz fatura tipi"
        
        return True, None
    
    def is_overdue(self):
        """Fatura vadesi geçmiş mi
        
        Returns:
            bool: Vade tarihi geçmiş ve ödenmemiş mi
        """
        if self.payment_status != "unpaid":
            return False
        
        today = datetime.now().date()
        due_date = datetime.strptime(self.due_date, "%Y-%m-%d").date()
        
        return today > due_date
    
    def update_payment_status(self):
        """Fatura ödeme durumunu güncelle
        
        Vade tarihini kontrol eder ve ödenmemiş faturalar için 'overdue' durumunu ayarlar.
        """
        if self.payment_status == "unpaid" and self.is_overdue():
            self.payment_status = "overdue"


class InvoiceManager:
    """Fatura yöneticisi"""
    
    def __init__(self, database):
        """Yönetici başlatıcı
        
        Args:
            database: Veritabanı nesnesi
        """
        self.db = database
    
    def get_all_invoices(self):
        """Tüm faturaları al
        
        Returns:
            list: Fatura nesneleri listesi
        """
        invoices = self.db.get_all_invoices()
        return [Invoice.from_dict(inv) for inv in invoices]
    
    def get_invoice_by_id(self, invoice_id):
        """ID ile fatura al
        
        Args:
            invoice_id: Fatura ID
            
        Returns:
            Invoice: Fatura nesnesi veya None
        """
        invoices = self.get_all_invoices()
        for invoice in invoices:
            if invoice.id == invoice_id:
                return invoice
        return None
    
    def get_invoice_by_number(self, invoice_number):
        """Numara ile fatura al
        
        Args:
            invoice_number: Fatura numarası
            
        Returns:
            Invoice: Fatura nesnesi veya None
        """
        invoices = self.get_all_invoices()
        for invoice in invoices:
            if invoice.invoice_number == invoice_number:
                return invoice
        return None
    
    def add_invoice(self, invoice, create_transactions=True):
        """Fatura ekle
        
        Args:
            invoice: Fatura nesnesi veya sözlük
            create_transactions: Muhasebe işlemleri oluşturulsun mu
            
        Returns:
            bool: İşlem başarılı mı
            str: Fatura ID veya hata mesajı
        """
        try:
            # Sözlük ise fatura nesnesine dönüştür
            if isinstance(invoice, dict):
                invoice = Invoice.from_dict(invoice)
            
            # Faturayı doğrula
            is_valid, error = invoice.validate()
            if not is_valid:
                return False, error
            
            # Faturayı veritabanına ekle
            invoice_dict = invoice.to_dict()
            self.db.add_invoice(invoice_dict)
            
            # Muhasebe işlemlerini oluştur
            if create_transactions and invoice.auto_post:
                self._create_invoice_transactions(invoice)
            
            logger.info(f"Fatura eklendi: {invoice.invoice_number}")
            return True, invoice.id
            
        except Exception as e:
            logger.error(f"Fatura eklenirken hata: {e}")
            return False, str(e)
    
    def update_invoice(self, invoice_id, updated_data, update_transactions=True):
        """Fatura güncelle
        
        Args:
            invoice_id: Fatura ID
            updated_data: Güncellenmiş veriler (dict)
            update_transactions: Muhasebe işlemleri güncellensin mi
            
        Returns:
            bool: İşlem başarılı mı
            str: Sonuç mesajı
        """
        try:
            # Mevcut faturayı al
            invoice = self.get_invoice_by_id(invoice_id)
            if not invoice:
                return False, f"Fatura bulunamadı: {invoice_id}"
            
            # Verileri güncelle
            old_invoice = Invoice.from_dict(invoice.to_dict())  # Eski halini kopyala
            
            if isinstance(updated_data, dict):
                # Güncellenmiş fatura kalemleri
                if "items" in updated_data:
                    items_data = updated_data.pop("items", [])
                    invoice.items = [InvoiceItem.from_dict(item) if isinstance(item, dict) else item for item in items_data]
                    invoice._calculate_totals()
                
                # Diğer alanları güncelle
                for key, value in updated_data.items():
                    if hasattr(invoice, key):
                        setattr(invoice, key, value)
            else:
                # Doğrudan Invoice nesnesi
                invoice = updated_data
            
            # Faturayı doğrula
            is_valid, error = invoice.validate()
            if not is_valid:
                return False, error
            
            # Veritabanını güncelle
            invoice_dict = invoice.to_dict()
            self.db.update_invoice(invoice_id, invoice_dict)
            
            # Muhasebe işlemlerini güncelle
            if update_transactions and invoice.auto_post:
                self._update_invoice_transactions(old_invoice, invoice)
            
            logger.info(f"Fatura güncellendi: {invoice.invoice_number}")
            return True, "Fatura başarıyla güncellendi"
            
        except Exception as e:
            logger.error(f"Fatura güncellenirken hata: {e}")
            return False, str(e)
    
    def delete_invoice(self, invoice_id, delete_transactions=True):
        """Fatura sil
        
        Args:
            invoice_id: Fatura ID
            delete_transactions: İlişkili muhasebe işlemleri silinsin mi
            
        Returns:
            bool: İşlem başarılı mı
            str: Sonuç mesajı
        """
        try:
            # Mevcut faturayı al
            invoice = self.get_invoice_by_id(invoice_id)
            if not invoice:
                return False, f"Fatura bulunamadı: {invoice_id}"
            
            # Muhasebe işlemlerini sil
            if delete_transactions:
                self._delete_invoice_transactions(invoice)
            
            # Faturayı sil
            if self.db.delete_invoice(invoice_id):
                logger.info(f"Fatura silindi: {invoice.invoice_number}")
                return True, "Fatura başarıyla silindi"
            else:
                return False, "Fatura silinirken hata oluştu"
            
        except Exception as e:
            logger.error(f"Fatura silinirken hata: {e}")
            return False, str(e)
    
    def mark_as_paid(self, invoice_id, payment_date=None, payment_method=None, 
                     payment_reference=None, create_transactions=True):
        """Faturayı ödenmiş olarak işaretle
        
        Args:
            invoice_id: Fatura ID
            payment_date: Ödeme tarihi (None ise bugün)
            payment_method: Ödeme yöntemi
            payment_reference: Ödeme referansı
            create_transactions: Ödeme işlemleri oluşturulsun mu
            
        Returns:
            bool: İşlem başarılı mı
            str: Sonuç mesajı
        """
        try:
            # Mevcut faturayı al
            invoice = self.get_invoice_by_id(invoice_id)
            if not invoice:
                return False, f"Fatura bulunamadı: {invoice_id}"
            
            # Zaten ödenmişse
            if invoice.payment_status == "paid":
                return False, "Fatura zaten ödenmiş"
            
            # Ödeme verilerini güncelle
            updated_data = {
                "payment_status": "paid",
                "payment_date": payment_date or datetime.now().strftime("%Y-%m-%d")
            }
            
            if payment_method:
                updated_data["payment_method"] = payment_method
            
            if payment_reference:
                updated_data["payment_reference"] = payment_reference
            
            # Faturayı güncelle
            success, message = self.update_invoice(invoice_id, updated_data, False)
            
            if success:
                # Ödeme işlemlerini oluştur
                if create_transactions:
                    invoice = self.get_invoice_by_id(invoice_id)  # Güncel fatura bilgilerini al
                    self._create_payment_transactions(invoice)
                
                logger.info(f"Fatura ödendi olarak işaretlendi: {invoice.invoice_number}")
                return True, "Fatura ödendi olarak işaretlendi"
            else:
                return False, message
            
        except Exception as e:
            logger.error(f"Fatura ödendi olarak işaretlenirken hata: {e}")
            return False, str(e)
    
    def get_invoices_by_date_range(self, start_date, end_date, invoice_type=None):
        """Tarih aralığına göre faturaları al
        
        Args:
            start_date: Başlangıç tarihi (str, YYYY-MM-DD)
            end_date: Bitiş tarihi (str, YYYY-MM-DD)
            invoice_type: Fatura tipi filtresi ('sales', 'purchase' veya None)
            
        Returns:
            list: Fatura nesneleri listesi
        """
        invoices = self.get_all_invoices()
        
        # Tarih filtreleme
        filtered = [inv for inv in invoices if start_date <= inv.date <= end_date]
        
        # Tip filtreleme
        if invoice_type:
            filtered = [inv for inv in filtered if inv.type == invoice_type]
        
        return filtered
    
    def get_invoices_by_entity(self, entity_name, invoice_type=None):
        """Müşteri/tedarikçiye göre faturaları al
        
        Args:
            entity_name: Müşteri/tedarikçi adı
            invoice_type: Fatura tipi filtresi ('sales', 'purchase' veya None)
            
        Returns:
            list: Fatura nesneleri listesi
        """
        invoices = self.get_all_invoices()
        
        # Müşteri/tedarikçi filtreleme
        filtered = [inv for inv in invoices if inv.entity_name == entity_name]
        
        # Tip filtreleme
        if invoice_type:
            filtered = [inv for inv in filtered if inv.type == invoice_type]
        
        return filtered
    
    def get_overdue_invoices(self, invoice_type=None):
        """Vadesi geçmiş faturaları al
        
        Args:
            invoice_type: Fatura tipi filtresi ('sales', 'purchase' veya None)
            
        Returns:
            list: Fatura nesneleri listesi
        """
        invoices = self.get_all_invoices()
        
        # Tüm faturaların ödeme durumunu güncelle
        for invoice in invoices:
            invoice.update_payment_status()
        
        # Vadesi geçmiş faturaları filtrele
        filtered = [inv for inv in invoices if inv.payment_status == "overdue"]
        
        # Tip filtreleme
        if invoice_type:
            filtered = [inv for inv in filtered if inv.type == invoice_type]
        
        return filtered
    
    def get_unpaid_invoices(self, invoice_type=None):
        """Ödenmemiş faturaları al
        
        Args:
            invoice_type: Fatura tipi filtresi ('sales', 'purchase' veya None)
            
        Returns:
            list: Fatura nesneleri listesi
        """
        invoices = self.get_all_invoices()
        
        # Ödenmemiş faturaları filtrele
        filtered = [inv for inv in invoices if inv.payment_status in ["unpaid", "overdue"]]
        
        # Tip filtreleme
        if invoice_type:
            filtered = [inv for inv in filtered if inv.type == invoice_type]
        
        return filtered
    
    def _create_invoice_transactions(self, invoice):
        """Fatura için muhasebe işlemleri oluştur
        
        Args:
            invoice: Fatura nesnesi
            
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            # İşlem yöneticisi oluştur
            from core.transaction import TransactionManager
            transaction_manager = TransactionManager(self.db)
            
            # Fatura tipi kontrolü
            if invoice.type == "sales":
                # Satış faturası
                # 1) Alacak hesaplarına borç (alacak artırma)
                transaction = Transaction(
                    date=invoice.date,
                    description=f"Satış Faturası - {invoice.entity_name}",
                    account="1200",  # Alacak Hesapları
                    debit=float(invoice.total_amount),
                    credit=0,
                    vat=0,
                    document_number=invoice.invoice_number,
                    status="unreconciled",
                    transaction_type="invoice",
                    notes=invoice.notes
                )
                transaction_manager.add_transaction(transaction)
                
                # 2) Satış gelirine alacak
                transaction = Transaction(
                    date=invoice.date,
                    description=f"Satış Faturası - {invoice.entity_name}",
                    account="4000",  # Satış Gelirleri
                    debit=0,
                    credit=float(invoice.net_amount),
                    vat=0,
                    document_number=invoice.invoice_number,
                    status="unreconciled",
                    transaction_type="invoice",
                    notes=invoice.notes
                )
                transaction_manager.add_transaction(transaction)
                
                # 3) Ödenecek KDV'ye alacak
                if invoice.vat_amount > 0:
                    transaction = Transaction(
                        date=invoice.date,
                        description=f"Satış Faturası - {invoice.entity_name}",
                        account="2100",  # Ödenecek KDV
                        debit=0,
                        credit=float(invoice.vat_amount),
                        vat=float(invoice.vat_amount),
                        document_number=invoice.invoice_number,
                        status="unreconciled",
                        transaction_type="invoice",
                        notes=invoice.notes
                    )
                    transaction_manager.add_transaction(transaction)
                
            elif invoice.type == "purchase":
                # Alış faturası
                # 1) Gider hesabına borç
                transaction = Transaction(
                    date=invoice.date,
                    description=f"Alış Faturası - {invoice.entity_name}",
                    account="5000",  # Mal ve Hizmet Alımları
                    debit=float(invoice.net_amount),
                    credit=0,
                    vat=0,
                    document_number=invoice.invoice_number,
                    status="unreconciled",
                    transaction_type="invoice",
                    notes=invoice.notes
                )
                transaction_manager.add_transaction(transaction)
                
                # 2) İndirilecek KDV'ye borç
                if invoice.vat_amount > 0:
                    transaction = Transaction(
                        date=invoice.date,
                        description=f"Alış Faturası - {invoice.entity_name}",
                        account="2200",  # İndirilecek KDV
                        debit=float(invoice.vat_amount),
                        credit=0,
                        vat=float(invoice.vat_amount),
                        document_number=invoice.invoice_number,
                        status="unreconciled",
                        transaction_type="invoice",
                        notes=invoice.notes
                    )
                    transaction_manager.add_transaction(transaction)
                
                # 3) Borç hesaplarına alacak
                transaction = Transaction(
                    date=invoice.date,
                    description=f"Alış Faturası - {invoice.entity_name}",
                    account="2000",  # Borç Hesapları
                    debit=0,
                    credit=float(invoice.total_amount),
                    vat=0,
                    document_number=invoice.invoice_number,
                    status="unreconciled",
                    transaction_type="invoice",
                    notes=invoice.notes
                )
                transaction_manager.add_transaction(transaction)
            
            logger.info(f"Fatura işlemleri oluşturuldu: {invoice.invoice_number}")
            return True
            
        except Exception as e:
            logger.error(f"Fatura işlemleri oluşturulurken hata: {e}")
            return False
    
    def _update_invoice_transactions(self, old_invoice, new_invoice):
        """Fatura işlemlerini güncelle
        
        Args:
            old_invoice: Eski fatura nesnesi
            new_invoice: Yeni fatura nesnesi
            
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            # Basitleştirme için, eski işlemleri silip yenilerini oluştur
            self._delete_invoice_transactions(old_invoice)
            self._create_invoice_transactions(new_invoice)
            
            logger.info(f"Fatura işlemleri güncellendi: {new_invoice.invoice_number}")
            return True
            
        except Exception as e:
            logger.error(f"Fatura işlemleri güncellenirken hata: {e}")
            return False
    
    def _delete_invoice_transactions(self, invoice):
        """Fatura işlemlerini sil
        
        Args:
            invoice: Fatura nesnesi
            
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            # İşlem yöneticisi oluştur
            from core.transaction import TransactionManager
            transaction_manager = TransactionManager(self.db)
            
            # Fatura numarasına göre işlemleri al
            transactions = transaction_manager.get_transactions_by_document(invoice.invoice_number)
            
            # İşlemleri sil
            for transaction in transactions:
                transaction_manager.delete_transaction(transaction.id)
            
            logger.info(f"Fatura işlemleri silindi: {invoice.invoice_number}")
            return True
            
        except Exception as e:
            logger.error(f"Fatura işlemleri silinirken hata: {e}")
            return False
    
    def _create_payment_transactions(self, invoice):
        """Fatura ödeme işlemlerini oluştur
        
        Args:
            invoice: Fatura nesnesi
            
        Returns:
            bool: İşlem başarılı mı
        """
        try:
            # İşlem yöneticisi oluştur
            from core.transaction import TransactionManager
            transaction_manager = TransactionManager(self.db)
            
            # Ödeme belge numarası
            payment_document = f"PMT-{invoice.invoice_number}"
            
            # Fatura tipi kontrolü
            if invoice.type == "sales":
                # Satış faturası ödemesi
                # 1) Bankaya borç
                transaction = Transaction(
                    date=invoice.payment_date,
                    description=f"Fatura Tahsilatı - {invoice.entity_name}",
                    account="1100",  # Banka
                    debit=float(invoice.total_amount),
                    credit=0,
                    vat=0,
                    document_number=payment_document,
                    status="unreconciled",
                    transaction_type="receipt",
                    notes=f"{invoice.invoice_number} nolu fatura tahsilatı"
                )
                transaction_manager.add_transaction(transaction)
                
                # 2) Alacak hesaplarından düş
                transaction = Transaction(
                    date=invoice.payment_date,
                    description=f"Fatura Tahsilatı - {invoice.entity_name}",
                    account="1200",  # Alacak Hesapları
                    debit=0,
                    credit=float(invoice.total_amount),
                    vat=0,
                    document_number=payment_document,
                    status="unreconciled",
                    transaction_type="receipt",
                    notes=f"{invoice.invoice_number} nolu fatura tahsilatı"
                )
                transaction_manager.add_transaction(transaction)
                
            elif invoice.type == "purchase":
                # Alış faturası ödemesi
                # 1) Borç hesaplarına borç (borç azaltma)
                transaction = Transaction(
                    date=invoice.payment_date,
                    description=f"Fatura Ödemesi - {invoice.entity_name}",
                    account="2000",  # Borç Hesapları
                    debit=float(invoice.total_amount),
                    credit=0,
                    vat=0,
                    document_number=payment_document,
                    status="unreconciled",
                    transaction_type="payment",
                    notes=f"{invoice.invoice_number} nolu fatura ödemesi"
                )
                transaction_manager.add_transaction(transaction)
                
                # 2) Bankadan düş
                transaction = Transaction(
                    date=invoice.payment_date,
                    description=f"Fatura Ödemesi - {invoice.entity_name}",
                    account="1100",  # Banka
                    debit=0,
                    credit=float(invoice.total_amount),
                    vat=0,
                    document_number=payment_document,
                    status="unreconciled",
                    transaction_type="payment",
                    notes=f"{invoice.invoice_number} nolu fatura ödemesi"
                )
                transaction_manager.add_transaction(transaction)
            
            logger.info(f"Fatura ödeme işlemleri oluşturuldu: {invoice.invoice_number}")
            return True
            
        except Exception as e:
            logger.error(f"Fatura ödeme işlemleri oluşturulurken hata: {e}")
            return False
