#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Hesap Modülü
Hesap sınıfları ve işlemleri
"""

import logging
from decimal import Decimal

# Modül için logger
logger = logging.getLogger(__name__)


class Account:
    """Hesap sınıfı - Temel işlemler için hesap sınıfı"""
    
    # Hesap türleri
    ACCOUNT_TYPES = {
        "asset": "Varlık",
        "liability": "Borç",
        "equity": "Öz Sermaye",
        "income": "Gelir",
        "expense": "Gider"
    }
    
    # Hesap kategorileri
    ACCOUNT_CATEGORIES = {
        "current_asset": "Dönen Varlık",
        "fixed_asset": "Duran Varlık",
        "current_liability": "Kısa Vadeli Borç",
        "long_term_liability": "Uzun Vadeli Borç",
        "equity": "Öz Sermaye",
        "revenue": "Hasılat",
        "cost_of_sales": "Satış Maliyeti",
        "operating_expense": "Faaliyet Gideri",
        "financial_expense": "Finansman Gideri",
        "other_income": "Diğer Gelir"
    }
    
    def __init__(self, code, name, account_type, category=None, vat_rate=0, balance=0):
        """Hesap başlatıcı
        
        Args:
            code: Hesap kodu
            name: Hesap adı
            account_type: Hesap türü
            category: Hesap kategorisi
            vat_rate: KDV oranı
            balance: Başlangıç bakiyesi
        """
        self.code = code
        self.name = name
        
        # Hesap türü kontrolü
        if account_type not in self.ACCOUNT_TYPES:
            raise ValueError(f"Geçersiz hesap türü: {account_type}")
        self.account_type = account_type
        
        # Kategori kontrolü
        if category and category not in self.ACCOUNT_CATEGORIES:
            raise ValueError(f"Geçersiz hesap kategorisi: {category}")
        self.category = category
        
        self.vat_rate = vat_rate
        self.balance = Decimal(str(balance))
        
        logger.debug(f"Hesap oluşturuldu: {self.code} - {self.name}")
    
    def debit(self, amount):
        """Hesaba borç ekle
        
        Args:
            amount: Borç tutarı
            
        Returns:
            Decimal: Güncel bakiye
        """
        amount = Decimal(str(amount))
        
        # Hesap türüne göre bakiye güncellemesi
        if self.account_type in ["asset", "expense"]:
            self.balance += amount
        else:
            self.balance -= amount
        
        logger.debug(f"Hesaba borç eklendi: {self.code}, Tutar: {amount}, Bakiye: {self.balance}")
        return self.balance
    
    def credit(self, amount):
        """Hesaba alacak ekle
        
        Args:
            amount: Alacak tutarı
            
        Returns:
            Decimal: Güncel bakiye
        """
        amount = Decimal(str(amount))
        
        # Hesap türüne göre bakiye güncellemesi
        if self.account_type in ["asset", "expense"]:
            self.balance -= amount
        else:
            self.balance += amount
        
        logger.debug(f"Hesaba alacak eklendi: {self.code}, Tutar: {amount}, Bakiye: {self.balance}")
        return self.balance
    
    def get_balance(self):
        """Hesap bakiyesini döndür
        
        Returns:
            Decimal: Güncel bakiye
        """
        return self.balance
    
    def reset_balance(self):
        """Hesap bakiyesini sıfırla
        
        Returns:
            Decimal: Güncel bakiye
        """
        self.balance = Decimal("0")
        logger.debug(f"Hesap bakiyesi sıfırlandı: {self.code}")
        return self.balance
    
    def to_dict(self):
        """Hesabı sözlük formatına dönüştür
        
        Returns:
            dict: Hesap bilgileri
        """
        return {
            "code": self.code,
            "name": self.name,
            "type": self.account_type,
            "category": self.category,
            "vat_rate": self.vat_rate,
            "balance": float(self.balance)
        }
    
    @classmethod
    def from_dict(cls, data):
        """Sözlük formatından hesap nesnesi oluştur
        
        Args:
            data: Hesap bilgileri sözlüğü
            
        Returns:
            Account: Hesap nesnesi
        """
        return cls(
            code=data.get("code"),
            name=data.get("name"),
            account_type=data.get("type"),
            category=data.get("category"),
            vat_rate=data.get("vat_rate", 0),
            balance=data.get("balance", 0)
        )
    
    def __str__(self):
        return f"{self.code} - {self.name}: {self.balance:.2f}"


class ChartOfAccounts:
    """Hesap planı sınıfı - Hesapları yönetir"""
    
    def __init__(self):
        """Hesap planı başlatıcı"""
        self.accounts = {}
        logger.debug("Hesap planı oluşturuldu")
    
    def add_account(self, account):
        """Hesap ekle
        
        Args:
            account: Account nesnesi
            
        Returns:
            bool: İşlem başarılı mı
            
        Raises:
            ValueError: Hesap kodu zaten mevcut
        """
        # Hesap nesne kontrolü
        if not isinstance(account, Account):
            raise TypeError("Geçersiz hesap nesnesi")
        
        # Hesap kodu çoklanma kontrolü
        if account.code in self.accounts:
            raise ValueError(f"Hesap kodu zaten mevcut: {account.code}")
        
        # Hesabı ekle
        self.accounts[account.code] = account
        logger.debug(f"Hesap eklendi: {account.code}")
        return True
    
    def get_account(self, code):
        """Hesap koduna göre hesap al
        
        Args:
            code: Hesap kodu
            
        Returns:
            Account: Hesap nesnesi
            
        Raises:
            KeyError: Hesap bulunamadı
        """
        if code not in self.accounts:
            raise KeyError(f"Hesap bulunamadı: {code}")
        
        return self.accounts[code]
    
    def update_account(self, code, updated_data):
        """Hesap güncelle
        
        Args:
            code: Hesap kodu
            updated_data: Güncellenecek veri
            
        Returns:
            Account: Güncellenmiş hesap nesnesi
            
        Raises:
            KeyError: Hesap bulunamadı
        """
        if code not in self.accounts:
            raise KeyError(f"Hesap bulunamadı: {code}")
        
        account = self.accounts[code]
        
        # İzin verilen alanları güncelle
        if "name" in updated_data:
            account.name = updated_data["name"]
        
        if "category" in updated_data:
            if updated_data["category"] not in Account.ACCOUNT_CATEGORIES:
                raise ValueError(f"Geçersiz hesap kategorisi: {updated_data['category']}")
            account.category = updated_data["category"]
        
        if "vat_rate" in updated_data:
            account.vat_rate = updated_data["vat_rate"]
        
        logger.debug(f"Hesap güncellendi: {code}")
        return account
    
    def delete_account(self, code):
        """Hesap sil
        
        Args:
            code: Hesap kodu
            
        Returns:
            bool: İşlem başarılı mı
            
        Raises:
            KeyError: Hesap bulunamadı
        """
        if code not in self.accounts:
            raise KeyError(f"Hesap bulunamadı: {code}")
        
        del self.accounts[code]
        logger.debug(f"Hesap silindi: {code}")
        return True
    
    def get_all_accounts(self):
        """Tüm hesapları al
        
        Returns:
            list: Hesap nesneleri listesi
        """
        return list(self.accounts.values())
    
    def get_accounts_by_type(self, account_type):
        """Türe göre hesapları filtrele
        
        Args:
            account_type: Hesap türü
            
        Returns:
            list: Filtreli hesap listesi
        """
        if account_type not in Account.ACCOUNT_TYPES:
            raise ValueError(f"Geçersiz hesap türü: {account_type}")
        
        return [acc for acc in self.accounts.values() if acc.account_type == account_type]
    
    def get_accounts_by_category(self, category):
        """Kategoriye göre hesapları filtrele
        
        Args:
            category: Hesap kategorisi
            
        Returns:
            list: Filtreli hesap listesi
        """
        if category not in Account.ACCOUNT_CATEGORIES:
            raise ValueError(f"Geçersiz hesap kategorisi: {category}")
        
        return [acc for acc in self.accounts.values() if acc.category == category]
    
    def to_dict_list(self):
        """Hesap planını sözlük listesine dönüştür
        
        Returns:
            list: Hesap bilgileri listesi
        """
        return [account.to_dict() for account in self.accounts.values()]
    
    @classmethod
    def from_dict_list(cls, accounts_data):
        """Sözlük listesinden hesap planı oluştur
        
        Args:
            accounts_data: Hesap bilgileri listesi
            
        Returns:
            ChartOfAccounts: Hesap planı nesnesi
        """
        coa = cls()
        
        for data in accounts_data:
            account = Account.from_dict(data)
            coa.add_account(account)
        
        return coa
    
    def __len__(self):
        return len(self.accounts)
    
    def __iter__(self):
        return iter(self.accounts.values())


class AccountFactory:
    """Hesap fabrikası sınıfı - Standart hesaplar oluşturur"""
    
    @staticmethod
    def create_default_chart_of_accounts():
        """Varsayılan hesap planı oluştur
        
        Returns:
            ChartOfAccounts: Hesap planı nesnesi
        """
        coa = ChartOfAccounts()
        
        # Varlık Hesapları (1000-1999)
        coa.add_account(Account("1000", "Kasa", "asset", "current_asset"))
        coa.add_account(Account("1100", "Banka", "asset", "current_asset"))
        coa.add_account(Account("1200", "Alacak Hesapları", "asset", "current_asset"))
        coa.add_account(Account("1300", "Stoklar", "asset", "current_asset"))
        coa.add_account(Account("1400", "Peşin Ödenmiş Giderler", "asset", "current_asset"))
        coa.add_account(Account("1500", "Sabit Varlıklar", "asset", "fixed_asset"))
        coa.add_account(Account("1600", "Birikmiş Amortisman", "asset", "fixed_asset"))
        
        # Borç Hesapları (2000-2999)
        coa.add_account(Account("2000", "Borç Hesapları", "liability", "current_liability"))
        coa.add_account(Account("2100", "Ödenecek KDV", "liability", "current_liability"))
        coa.add_account(Account("2200", "İndirilecek KDV", "liability", "current_liability"))
        coa.add_account(Account("2300", "Ödenecek Vergiler", "liability", "current_liability"))
        coa.add_account(Account("2400", "Uzun Vadeli Borçlar", "liability", "long_term_liability"))
        
        # Öz Sermaye Hesapları (3000-3999)
        coa.add_account(Account("3000", "Sermaye", "equity", "equity"))
        coa.add_account(Account("3100", "Geçmiş Dönem Kar/Zarar", "equity", "equity"))
        coa.add_account(Account("3200", "Dönem Net Kar/Zarar", "equity", "equity"))
        
        # Gelir Hesapları (4000-4999)
        coa.add_account(Account("4000", "Satış Gelirleri", "income", "revenue", 20))
        coa.add_account(Account("4100", "Hizmet Gelirleri", "income", "revenue", 20))
        coa.add_account(Account("4200", "İndirim ve İadeler (-)", "income", "revenue", 20))
        coa.add_account(Account("4300", "Diğer Gelirler", "income", "other_income"))
        
        # Gider Hesapları (5000-5999)
        coa.add_account(Account("5000", "Mal ve Hizmet Alımları", "expense", "cost_of_sales", 20))
        coa.add_account(Account("5100", "Personel Giderleri", "expense", "operating_expense"))
        coa.add_account(Account("5200", "Kira Giderleri", "expense", "operating_expense"))
        coa.add_account(Account("5300", "Ofis Giderleri", "expense", "operating_expense", 20))
        coa.add_account(Account("5400", "Amortisman Giderleri", "expense", "operating_expense"))
        coa.add_account(Account("5500", "Pazarlama ve Reklam", "expense", "operating_expense", 20))
        coa.add_account(Account("5600", "İletişim ve Internet", "expense", "operating_expense", 20))
        coa.add_account(Account("5700", "Seyahat ve Konaklama", "expense", "operating_expense", 20))
        coa.add_account(Account("5800", "Profesyonel Hizmetler", "expense", "operating_expense", 20))
        coa.add_account(Account("5900", "Banka ve Finansman Giderleri", "expense", "financial_expense"))
        
        logger.info("Varsayılan hesap planı oluşturuldu")
        return coa
    
    @staticmethod
    def create_uk_chart_of_accounts():
        """İngiltere hesap planı oluştur
        
        Returns:
            ChartOfAccounts: Hesap planı nesnesi
        """
        coa = ChartOfAccounts()
        
        # Varlık Hesapları
        coa.add_account(Account("1000", "Petty Cash", "asset", "current_asset"))
        coa.add_account(Account("1100", "Bank Current Account", "asset", "current_asset"))
        coa.add_account(Account("1200", "Bank Savings Account", "asset", "current_asset"))
        coa.add_account(Account("1300", "Accounts Receivable", "asset", "current_asset"))
        coa.add_account(Account("1400", "Inventory", "asset", "current_asset"))
        coa.add_account(Account("1500", "Prepaid Expenses", "asset", "current_asset"))
        coa.add_account(Account("1600", "Fixed Assets", "asset", "fixed_asset"))
        coa.add_account(Account("1700", "Accumulated Depreciation", "asset", "fixed_asset"))
        
        # Borç Hesapları
        coa.add_account(Account("2000", "Accounts Payable", "liability", "current_liability"))
        coa.add_account(Account("2100", "VAT Output", "liability", "current_liability"))
        coa.add_account(Account("2200", "VAT Input", "liability", "current_liability"))
        coa.add_account(Account("2300", "PAYE/NI Payable", "liability", "current_liability"))
        coa.add_account(Account("2400", "Corporation Tax Payable", "liability", "current_liability"))
        coa.add_account(Account("2500", "Loans", "liability", "long_term_liability"))
        
        # Öz Sermaye Hesapları
        coa.add_account(Account("3000", "Capital", "equity", "equity"))
        coa.add_account(Account("3100", "Retained Earnings", "equity", "equity"))
        coa.add_account(Account("3200", "Current Year Earnings", "equity", "equity"))
        coa.add_account(Account("3300", "Drawings", "equity", "equity"))
        
        # Gelir Hesapları
        coa.add_account(Account("4000", "Sales Revenue", "income", "revenue", 20))
        coa.add_account(Account("4100", "Service Revenue", "income", "revenue", 20))
        coa.add_account(Account("4200", "Discounts Given", "income", "revenue", 20))
        coa.add_account(Account("4300", "Other Income", "income", "other_income"))
        
        # Gider Hesapları
        coa.add_account(Account("5000", "Cost of Goods Sold", "expense", "cost_of_sales", 20))
        coa.add_account(Account("5100", "Salaries and Wages", "expense", "operating_expense"))
        coa.add_account(Account("5200", "Rent", "expense", "operating_expense"))
        coa.add_account(Account("5300", "Office Expenses", "expense", "operating_expense", 20))
        coa.add_account(Account("5400", "Depreciation", "expense", "operating_expense"))
        coa.add_account(Account("5500", "Marketing and Advertising", "expense", "operating_expense", 20))
        coa.add_account(Account("5600", "Communication", "expense", "operating_expense", 20))
        coa.add_account(Account("5700", "Travel and Accommodation", "expense", "operating_expense", 20))
        coa.add_account(Account("5800", "Professional Services", "expense", "operating_expense", 20))
        coa.add_account(Account("5900", "Bank Charges", "expense", "financial_expense"))
        
        logger.info("İngiltere hesap planı oluşturuldu")
        return coa
