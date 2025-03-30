#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - İşlem Modülü
Muhasebe işlemleri için sınıflar ve işlevler
"""

import uuid
from datetime import datetime
import logging
from decimal import Decimal, ROUND_HALF_UP

# Modül için logger
logger = logging.getLogger(__name__)


class Transaction:
    """Temel işlem sınıfı"""
    
    def __init__(self, transaction_id=None, date=None, description="", account="", 
                 debit=0.0, credit=0.0, vat=0.0, document_number="", status="unreconciled",
                 transaction_type="manual", notes=""):
        """İşlem başlatıcı
        
        Args:
            transaction_id: İşlem ID (None ise otomatik oluşturulur)
            date: İşlem tarihi (None ise bugün)
            description: Açıklama
            account: Hesap kodu
            debit: Borç tutarı
            credit: Alacak tutarı
            vat: KDV tutarı
            document_number: Belge numarası
            status: İşlem durumu ('unreconciled', 'reconciled', 'pending')
            transaction_type: İşlem tipi ('manual', 'invoice', 'payment', 'receipt', 'expense', 'transfer', 'opening_balance')
            notes: İlave notlar
        """
        self.id = transaction_id if transaction_id is not None else str(uuid.uuid4())
        self.date = date if date is not None else datetime.now().strftime("%Y-%m-%d")
        self.description = description
        self.account = account
        self.debit = Decimal(str(debit)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.credit = Decimal(str(credit)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.vat = Decimal(str(vat)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.document_number = document_number
        self.status = status
        self.transaction_type = transaction_type
        self.notes = notes
    
    def to_dict(self):
        """İşlemi sözlük olarak döndür
        
        Returns:
            dict: İşlem verileri
        """
        return {
            "id": self.id,
            "date": self.date,
            "description": self.description,
            "account": self.account,
            "debit": float(self.debit),
            "credit": float(self.credit),
            "vat": float(self.vat),
            "document_number": self.document_number,
            "status": self.status,
            "transaction_type": self.transaction_type,
            "notes": self.notes
        }
    
    @classmethod
    def from_dict(cls, data):
        """Sözlükten işlem nesnesi oluştur
        
        Args:
            data: İşlem verileri
            
        Returns:
            Transaction: İşlem nesnesi
        """
        return cls(
            transaction_id=data.get("id"),
            date=data.get("date"),
            description=data.get("description", ""),
            account=data.get("account", ""),
            debit=data.get("debit", 0.0),
            credit=data.get("credit", 0.0),
            vat=data.get("vat", 0.0),
            document_number=data.get("document_number", ""),
            status=data.get("status", "unreconciled"),
            transaction_type=data.get("transaction_type", "manual"),
            notes=data.get("notes", "")
        )
    
    def validate(self):
        """İşlemi doğrula
        
        Returns:
            bool: İşlem geçerli mi
            str: Hata mesajı (geçerliyse None)
        """
        # Gerekli alanlar
        if not self.date:
            return False, "Tarih gereklidir"
        
        if not self.account:
            return False, "Hesap kodu gereklidir"
        
        if self.debit == 0 and self.credit == 0:
            return False, "Borç veya alacak tutarı sıfırdan büyük olmalıdır"
        
        if self.debit > 0 and self.credit > 0:
            return False, "Borç ve alacak tutarları aynı anda pozitif olamaz"
        
        return True, None


class TransactionManager:
    """İşlem yöneticisi"""
    
    def __init__(self, database):
        """Yönetici başlatıcı
        
        Args:
            database: Veritabanı nesnesi
        """
        self.db = database
    
    def get_all_transactions(self):
        """Tüm işlemleri al
        
        Returns:
            list: İşlem nesneleri listesi
        """
        transactions = self.db.get_all_transactions()
        return [Transaction.from_dict(trans) for trans in transactions]
    
    def get_transaction_by_id(self, transaction_id):
        """ID ile işlem al
        
        Args:
            transaction_id: İşlem ID
            
        Returns:
            Transaction: İşlem nesnesi veya None
        """
        transactions = self.get_all_transactions()
        for transaction in transactions:
            if transaction.id == transaction_id:
                return transaction
        return None
    
    def add_transaction(self, transaction):
        """İşlem ekle
        
        Args:
            transaction: İşlem nesnesi veya sözlük
            
        Returns:
            bool: İşlem başarılı mı
            str: İşlem ID veya hata mesajı
        """
        try:
            # Sözlük ise işlem nesnesine dönüştür
            if isinstance(transaction, dict):
                transaction = Transaction.from_dict(transaction)
            
            # İşlemi doğrula
            is_valid, error = transaction.validate()
            if not is_valid:
                return False, error
            
            # İşlemi veritabanına ekle
            transaction_dict = transaction.to_dict()
            self.db.add_transaction(transaction_dict)
            
            logger.info(f"İşlem eklendi: {transaction.id}")
            return True, transaction.id
            
        except Exception as e:
            logger.error(f"İşlem eklenirken hata: {e}")
            return False, str(e)
    
    def update_transaction(self, transaction_id, updated_data):
        """İşlem güncelle
        
        Args:
            transaction_id: İşlem ID
            updated_data: Güncellenmiş veriler (dict)
            
        Returns:
            bool: İşlem başarılı mı
            str: Sonuç mesajı
        """
        try:
            # Mevcut işlemi al
            transaction = self.get_transaction_by_id(transaction_id)
            if not transaction:
                return False, f"İşlem bulunamadı: {transaction_id}"
            
            # Verileri güncelle
            for key, value in updated_data.items():
                if hasattr(transaction, key):
                    setattr(transaction, key, value)
            
            # İşlemi doğrula
            is_valid, error = transaction.validate()
            if not is_valid:
                return False, error
            
            # Veritabanını güncelle
            transaction_dict = transaction.to_dict()
            self.db.update_transaction(transaction_id, transaction_dict)
            
            logger.info(f"İşlem güncellendi: {transaction_id}")
            return True, "İşlem başarıyla güncellendi"
            
        except Exception as e:
            logger.error(f"İşlem güncellenirken hata: {e}")
            return False, str(e)
    
    def delete_transaction(self, transaction_id):
        """İşlem sil
        
        Args:
            transaction_id: İşlem ID
            
        Returns:
            bool: İşlem başarılı mı
            str: Sonuç mesajı
        """
        try:
            # İşlemi sil
            if self.db.delete_transaction(transaction_id):
                logger.info(f"İşlem silindi: {transaction_id}")
                return True, "İşlem başarıyla silindi"
            else:
                return False, f"İşlem bulunamadı: {transaction_id}"
            
        except Exception as e:
            logger.error(f"İşlem silinirken hata: {e}")
            return False, str(e)
    
    def get_transactions_by_date_range(self, start_date, end_date):
        """Tarih aralığına göre işlemleri al
        
        Args:
            start_date: Başlangıç tarihi (str, YYYY-MM-DD)
            end_date: Bitiş tarihi (str, YYYY-MM-DD)
            
        Returns:
            list: İşlem nesneleri listesi
        """
        transactions = self.get_all_transactions()
        return [t for t in transactions if start_date <= t.date <= end_date]
    
    def get_transactions_by_account(self, account_code):
        """Hesaba göre işlemleri al
        
        Args:
            account_code: Hesap kodu
            
        Returns:
            list: İşlem nesneleri listesi
        """
        transactions = self.get_all_transactions()
        return [t for t in transactions if t.account == account_code]
    
    def get_transactions_by_document(self, document_number):
        """Belge numarasına göre işlemleri al
        
        Args:
            document_number: Belge numarası
            
        Returns:
            list: İşlem nesneleri listesi
        """
        transactions = self.get_all_transactions()
        return [t for t in transactions if t.document_number == document_number]
    
    def get_account_balance(self, account_code, end_date=None):
        """Hesap bakiyesini hesapla
        
        Args:
            account_code: Hesap kodu
            end_date: Hesaplanacak son tarih (None ise tüm işlemler)
            
        Returns:
            Decimal: Hesap bakiyesi
        """
        transactions = self.get_transactions_by_account(account_code)
        
        # Tarihe göre filtrele
        if end_date:
            transactions = [t for t in transactions if t.date <= end_date]
        
        # Bakiyeyi hesapla
        balance = Decimal('0.00')
        for trans in transactions:
            balance += trans.debit - trans.credit
        
        return balance
    
    def create_journal_entry(self, date, description, entries, document_number=None, notes=""):
        """Yevmiye kaydı oluştur
        
        Args:
            date: Kayıt tarihi
            description: Açıklama
            entries: Kayıt girişleri listesi [{"account": "...", "debit": 0.0, "credit": 0.0, "vat": 0.0}, ...]
            document_number: Belge numarası (None ise otomatik oluşturulur)
            notes: İlave notlar
            
        Returns:
            bool: İşlem başarılı mı
            str: Sonuç mesajı
        """
        try:
            # Belge numarası
            if document_number is None:
                doc_date = datetime.strptime(date, "%Y-%m-%d").strftime("%Y%m%d")
                document_number = f"JRN-{doc_date}-{str(uuid.uuid4())[:8]}"
            
            # Borç/alacak dengesi kontrolü
            total_debit = sum(Decimal(str(entry.get("debit", 0))) for entry in entries)
            total_credit = sum(Decimal(str(entry.get("credit", 0))) for entry in entries)
            
            if total_debit != total_credit:
                return False, "Borç ve alacak toplamları eşit olmalıdır"
            
            # İşlemleri oluştur ve ekle
            success_count = 0
            for entry in entries:
                transaction = Transaction(
                    date=date,
                    description=description,
                    account=entry["account"],
                    debit=entry.get("debit", 0),
                    credit=entry.get("credit", 0),
                    vat=entry.get("vat", 0),
                    document_number=document_number,
                    status="unreconciled",
                    transaction_type="journal",
                    notes=notes
                )
                
                success, result = self.add_transaction(transaction)
                if success:
                    success_count += 1
            
            logger.info(f"Yevmiye kaydı oluşturuldu: {document_number}, {success_count} işlem")
            return True, f"Yevmiye kaydı başarıyla oluşturuldu: {document_number}"
            
        except Exception as e:
            logger.error(f"Yevmiye kaydı oluşturulurken hata: {e}")
            return False, str(e)
    
    def reconcile_transaction(self, transaction_id):
        """İşlemi mutabakatlandır
        
        Args:
            transaction_id: İşlem ID
            
        Returns:
            bool: İşlem başarılı mı
            str: Sonuç mesajı
        """
        try:
            transaction = self.get_transaction_by_id(transaction_id)
            if not transaction:
                return False, f"İşlem bulunamadı: {transaction_id}"
            
            # Durumu güncelle
            updated_data = {"status": "reconciled"}
            return self.update_transaction(transaction_id, updated_data)
            
        except Exception as e:
            logger.error(f"İşlem mutabakatlandırılırken hata: {e}")
            return False, str(e)
