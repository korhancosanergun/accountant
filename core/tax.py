#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Vergi İşlemleri Modülü
KDV ve gelir vergisi hesaplamaları ve beyanname işlemleri
"""

import logging
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import calendar

# Modül için logger
logger = logging.getLogger(__name__)


class TaxPeriod:
    """Vergi dönemi sınıfı"""
    
    def __init__(self, start_date, end_date, period_key=None, status="O"):
        """Vergi dönemi başlatıcı
        
        Args:
            start_date: Başlangıç tarihi (str veya date)
            end_date: Bitiş tarihi (str veya date)
            period_key: Dönem anahtarı (HMRC için kullanılır)
            status: Dönem durumu ('O': open, 'F': fulfilled)
        """
        # String ise date'e dönüştür
        if isinstance(start_date, str):
            self.start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        else:
            self.start_date = start_date
        
        if isinstance(end_date, str):
            self.end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            self.end_date = end_date
        
        self.period_key = period_key
        self.status = status
    
    def to_dict(self):
        """Vergi dönemini sözlük olarak döndür
        
        Returns:
            dict: Vergi dönemi verileri
        """
        return {
            "start": self.start_date.strftime("%Y-%m-%d"),
            "end": self.end_date.strftime("%Y-%m-%d"),
            "periodKey": self.period_key,
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data):
        """Sözlükten vergi dönemi nesnesi oluştur
        
        Args:
            data: Vergi dönemi verileri
            
        Returns:
            TaxPeriod: Vergi dönemi nesnesi
        """
        return cls(
            start_date=data.get("start"),
            end_date=data.get("end"),
            period_key=data.get("periodKey"),
            status=data.get("status", "O")
        )
    
    def contains_date(self, check_date):
        """Tarih bu dönem içinde mi kontrol et
        
        Args:
            check_date: Kontrol edilecek tarih (str veya date)
            
        Returns:
            bool: Tarih dönem içindeyse True
        """
        if isinstance(check_date, str):
            check_date = datetime.strptime(check_date, "%Y-%m-%d").date()
        
        return self.start_date <= check_date <= self.end_date
    
    def days_remaining(self):
        """Dönemin bitimine kalan gün sayısı
        
        Returns:
            int: Kalan gün sayısı (negatifse dönem bitmiş)
        """
        today = date.today()
        return (self.end_date - today).days


class VATReturn:
    """KDV beyannamesi sınıfı"""
    
    def __init__(self, period=None):
        """KDV beyannamesi başlatıcı
        
        Args:
            period: Vergi dönemi (TaxPeriod nesnesi)
        """
        self.period = period
        
        # Beyanname alanları
        self.vat_due_sales = Decimal('0.00')  # Box 1: Satışlardan KDV
        self.vat_due_acquisitions = Decimal('0.00')  # Box 2: AB Alımlarından KDV
        self.total_vat_due = Decimal('0.00')  # Box 3: Toplam KDV (Box 1 + Box 2)
        self.vat_reclaimed = Decimal('0.00')  # Box 4: İndirilecek KDV
        self.net_vat_due = Decimal('0.00')  # Box 5: Ödeme/İade (Box 3 - Box 4)
        self.total_sales_ex_vat = Decimal('0.00')  # Box 6: Toplam Satışlar (KDV hariç)
        self.total_purchases_ex_vat = Decimal('0.00')  # Box 7: Toplam Alımlar (KDV hariç)
        self.total_supplies_ex_vat = Decimal('0.00')  # Box 8: AB'ye Mal Teslimleri (KDV hariç)
        self.total_acquisitions_ex_vat = Decimal('0.00')  # Box 9: AB'den Mal Alımları (KDV hariç)
        
        # İlave bilgiler
        self.submission_date = None
        self.status = "draft"  # 'draft', 'submitted', 'accepted', 'rejected'
        self.finalised = False
    
    def calculate_totals(self):
        """Toplam değerleri hesapla"""
        self.total_vat_due = self.vat_due_sales + self.vat_due_acquisitions
        self.net_vat_due = self.total_vat_due - self.vat_reclaimed
    
    def to_dict(self):
        """KDV beyannamesini sözlük olarak döndür
        
        Returns:
            dict: KDV beyannamesi verileri
        """
        return {
            "period_start": self.period.start_date.strftime("%Y-%m-%d") if self.period else None,
            "period_end": self.period.end_date.strftime("%Y-%m-%d") if self.period else None,
            "submission_date": self.submission_date,
            "vat_due_sales": float(self.vat_due_sales),
            "vat_due_acquisitions": float(self.vat_due_acquisitions),
            "total_vat_due": float(self.total_vat_due),
            "vat_reclaimed": float(self.vat_reclaimed),
            "net_vat_due": float(self.net_vat_due),
            "total_sales_ex_vat": float(self.total_sales_ex_vat),
            "total_purchases_ex_vat": float(self.total_purchases_ex_vat),
            "total_supplies_ex_vat": float(self.total_supplies_ex_vat),
            "total_acquisitions_ex_vat": float(self.total_acquisitions_ex_vat),
            "status": self.status,
            "finalised": self.finalised
        }
    
    @classmethod
    def from_dict(cls, data):
        """Sözlükten KDV beyannamesi nesnesi oluştur
        
        Args:
            data: KDV beyannamesi verileri
            
        Returns:
            VATReturn: KDV beyannamesi nesnesi
        """
        # Dönem bilgilerini ayarla
        period = None
        if "period_start" in data and "period_end" in data:
            period = TaxPeriod(data["period_start"], data["period_end"])
        
        vat_return = cls(period)
        
        # Beyanname alanlarını yükle
        vat_return.vat_due_sales = Decimal(str(data.get("vat_due_sales", 0)))
        vat_return.vat_due_acquisitions = Decimal(str(data.get("vat_due_acquisitions", 0)))
        vat_return.total_vat_due = Decimal(str(data.get("total_vat_due", 0)))
        vat_return.vat_reclaimed = Decimal(str(data.get("vat_reclaimed", 0)))
        vat_return.net_vat_due = Decimal(str(data.get("net_vat_due", 0)))
        vat_return.total_sales_ex_vat = Decimal(str(data.get("total_sales_ex_vat", 0)))
        vat_return.total_purchases_ex_vat = Decimal(str(data.get("total_purchases_ex_vat", 0)))
        vat_return.total_supplies_ex_vat = Decimal(str(data.get("total_supplies_ex_vat", 0)))
        vat_return.total_acquisitions_ex_vat = Decimal(str(data.get("total_acquisitions_ex_vat", 0)))
        
        # İlave bilgiler
        vat_return.submission_date = data.get("submission_date")
        vat_return.status = data.get("status", "draft")
        vat_return.finalised = data.get("finalised", False)
        
        return vat_return
    
    def to_hmrc_format(self):
        """KDV beyannamesini HMRC formatına dönüştür
        
        Returns:
            dict: HMRC API'ye gönderilecek format
        """
        return {
            "periodKey": self.period.period_key if self.period else "",
            "vatDueSales": float(self.vat_due_sales),
            "vatDueAcquisitions": float(self.vat_due_acquisitions),
            "totalVatDue": float(self.total_vat_due),
            "vatReclaimedCurrPeriod": float(self.vat_reclaimed),
            "netVatDue": float(self.net_vat_due),
            "totalValueSalesExVAT": float(self.total_sales_ex_vat),
            "totalValuePurchasesExVAT": float(self.total_purchases_ex_vat),
            "totalValueGoodsSuppliedExVAT": float(self.total_supplies_ex_vat),
            "totalAcquisitionsExVAT": float(self.total_acquisitions_ex_vat),
            "finalised": self.finalised
        }
    
    def validate(self):
        """Beyanname doğrula
        
        Returns:
            bool: Beyanname geçerli mi
            str: Hata mesajı (geçerliyse None)
        """
        # Dönem kontrolü
        if not self.period:
            return False, "Dönem bilgileri eksik"
        
        # Zorunlu alanlar
        if self.vat_due_sales < 0:
            return False, "Satışlardan KDV negatif olamaz"
        
        if self.vat_due_acquisitions < 0:
            return False, "AB Alımlarından KDV negatif olamaz"
        
        if self.vat_reclaimed < 0:
            return False, "İndirilecek KDV negatif olamaz"
        
        if self.total_sales_ex_vat < 0:
            return False, "Toplam Satışlar negatif olamaz"
        
        if self.total_purchases_ex_vat < 0:
            return False, "Toplam Alımlar negatif olamaz"
        
        if self.total_supplies_ex_vat < 0:
            return False, "AB'ye Mal Teslimleri negatif olamaz"
        
        if self.total_acquisitions_ex_vat < 0:
            return False, "AB'den Mal Alımları negatif olamaz"
        
        # Toplam KDV kontrolü
        expected_total = self.vat_due_sales + self.vat_due_acquisitions
        if abs(self.total_vat_due - expected_total) > Decimal('0.01'):
            return False, "Toplam KDV hesaplaması yanlış"
        
        # Net KDV kontrolü
        expected_net = self.total_vat_due - self.vat_reclaimed
        if abs(self.net_vat_due - expected_net) > Decimal('0.01'):
            return False, "Net KDV hesaplaması yanlış"
        
        return True, None


class IncomeTaxReturn:
    """Gelir vergisi beyannamesi sınıfı"""
    
    def __init__(self, tax_year=None):
        """Gelir vergisi beyannamesi başlatıcı
        
        Args:
            tax_year: Vergi yılı (örn: "2022-23")
        """
        self.tax_year = tax_year
        
        # Dönem başlangıç ve bitiş tarihleri
        self.period_start = None
        self.period_end = None
        
        if tax_year:
            self._set_tax_year_dates(tax_year)
        
        # Beyanname alanları
        self.total_income = Decimal('0.00')
        self.total_expenses = Decimal('0.00')
        self.net_profit = Decimal('0.00')
        self.tax_allowance = Decimal('0.00')
        self.taxable_income = Decimal('0.00')
        self.tax_due = Decimal('0.00')
        
        # İlave bilgiler
        self.submission_date = None
        self.status = "draft"  # 'draft', 'submitted', 'accepted', 'rejected'
    
    def _set_tax_year_dates(self, tax_year):
        """Vergi yılına göre dönem tarihlerini ayarla
        
        Args:
            tax_year: Vergi yılı (örn: "2022-23")
        """
        try:
            # Vergi yılını ayrıştır (örn: "2022-23")
            parts = tax_year.split("-")
            start_year = int(parts[0])
            
            # İngiltere vergi yılı: 6 Nisan - 5 Nisan
            self.period_start = date(start_year, 4, 6)
            self.period_end = date(start_year + 1, 4, 5)
        except (ValueError, IndexError):
            logger.error(f"Geçersiz vergi yılı formatı: {tax_year}")
    
    def calculate_totals(self):
        """Toplam değerleri hesapla"""
        self.net_profit = self.total_income - self.total_expenses
        self.taxable_income = max(Decimal('0.00'), self.net_profit - self.tax_allowance)
        self._calculate_tax()
    
    def _calculate_tax(self):
        """Gelir vergisini hesapla
        
        İngiltere gelir vergisi basamakları (2022-23):
        - Kişisel muafiyet: £12,570
        - Temel oran: £12,571 - £50,270 arası %20
        - Yüksek oran: £50,271 - £150,000 arası %40
        - Ek oran: £150,000 üzeri %45
        """
        if self.taxable_income <= 0:
            self.tax_due = Decimal('0.00')
            return
        
        # Vergi basamakları (2022-23 vergi yılı için)
        basic_rate_limit = Decimal('37700.00')  # Temel oran limiti
        higher_rate_limit = Decimal('150000.00')  # Yüksek oran limiti
        
        basic_rate = Decimal('0.20')  # %20
        higher_rate = Decimal('0.40')  # %40
        additional_rate = Decimal('0.45')  # %45
        
        tax = Decimal('0.00')
        
        # Temel oran: 0 - 37,700 arası %20
        if self.taxable_income <= basic_rate_limit:
            tax = self.taxable_income * basic_rate
        else:
            tax = basic_rate_limit * basic_rate
            
            # Yüksek oran: 37,701 - 150,000 arası %40
            if self.taxable_income <= higher_rate_limit:
                tax += (self.taxable_income - basic_rate_limit) * higher_rate
            else:
                tax += (higher_rate_limit - basic_rate_limit) * higher_rate
                
                # Ek oran: 150,000 üzeri %45
                tax += (self.taxable_income - higher_rate_limit) * additional_rate
        
        self.tax_due = tax.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    def to_dict(self):
        """Gelir vergisi beyannamesini sözlük olarak döndür
        
        Returns:
            dict: Gelir vergisi beyannamesi verileri
        """
        return {
            "tax_year": self.tax_year,
            "period_start": self.period_start.strftime("%Y-%m-%d") if self.period_start else None,
            "period_end": self.period_end.strftime("%Y-%m-%d") if self.period_end else None,
            "submission_date": self.submission_date,
            "total_income": float(self.total_income),
            "total_expenses": float(self.total_expenses),
            "net_profit": float(self.net_profit),
            "tax_allowance": float(self.tax_allowance),
            "taxable_income": float(self.taxable_income),
            "tax_due": float(self.tax_due),
            "status": self.status
        }
    
    @classmethod
    def from_dict(cls, data):
        """Sözlükten gelir vergisi beyannamesi nesnesi oluştur
        
        Args:
            data: Gelir vergisi beyannamesi verileri
            
        Returns:
            IncomeTaxReturn: Gelir vergisi beyannamesi nesnesi
        """
        # Vergi yılı
        tax_year = data.get("tax_year")
        tax_return = cls(tax_year)
        
        # Dönem tarihlerini yükle
        if "period_start" in data and data["period_start"]:
            tax_return.period_start = datetime.strptime(data["period_start"], "%Y-%m-%d").date()
        
        if "period_end" in data and data["period_end"]:
            tax_return.period_end = datetime.strptime(data["period_end"], "%Y-%m-%d").date()
        
        # Beyanname alanlarını yükle
        tax_return.total_income = Decimal(str(data.get("total_income", 0)))
        tax_return.total_expenses = Decimal(str(data.get("total_expenses", 0)))
        tax_return.net_profit = Decimal(str(data.get("net_profit", 0)))
        tax_return.tax_allowance = Decimal(str(data.get("tax_allowance", 0)))
        tax_return.taxable_income = Decimal(str(data.get("taxable_income", 0)))
        tax_return.tax_due = Decimal(str(data.get("tax_due", 0)))
        
        # İlave bilgiler
        tax_return.submission_date = data.get("submission_date")
        tax_return.status = data.get("status", "draft")
        
        return tax_return
    
    def validate(self):
        """Beyanname doğrula
        
        Returns:
            bool: Beyanname geçerli mi
            str: Hata mesajı (geçerliyse None)
        """
        # Vergi yılı kontrolü
        if not self.tax_year or not self.period_start or not self.period_end:
            return False, "Vergi yılı ve dönem bilgileri eksik"
        
        # Zorunlu alanlar
        if self.total_income < 0:
            return False, "Toplam gelir negatif olamaz"
        
        if self.total_expenses < 0:
            return False, "Toplam gider negatif olamaz"
        
        if self.tax_allowance < 0:
            return False, "Vergi muafiyeti negatif olamaz"
        
        # Net kâr kontrolü
        expected_net = self.total_income - self.total_expenses
        if abs(self.net_profit - expected_net) > Decimal('0.01'):
            return False, "Net kâr hesaplaması yanlış"
        
        # Vergilendirilecek gelir kontrolü
        expected_taxable = max(Decimal('0.00'), self.net_profit - self.tax_allowance)
        if abs(self.taxable_income - expected_taxable) > Decimal('0.01'):
            return False, "Vergilendirilecek gelir hesaplaması yanlış"
        
        return True, None


class TaxManager:
    """Vergi yöneticisi"""
    
    def __init__(self, database, ledger):
        """Yönetici başlatıcı
        
        Args:
            database: Veritabanı nesnesi
            ledger: Muhasebe defteri nesnesi
        """
        self.db = database
        self.ledger = ledger
    
    def calculate_vat_return(self, start_date, end_date):
        """KDV beyannamesi hesapla
        
        Args:
            start_date: Başlangıç tarihi (str veya date)
            end_date: Bitiş tarihi (str veya date)
            
        Returns:
            VATReturn: KDV beyannamesi nesnesi
        """
        # String ise date'e dönüştür
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        # KDV beyannamesi oluştur
        period = TaxPeriod(start_date, end_date)
        vat_return = VATReturn(period)
        
        try:
            # Tarih aralığındaki işlemleri al
            transactions = self.ledger.get_transactions_by_date_range(
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d")
            )
            
            # KDV hesapla
            for trans in transactions:
                account_code = trans.account
                
                # Satışlardan KDV (Box 1)
                if account_code == "2100" and trans.credit > 0:  # Ödenecek KDV
                    vat_return.vat_due_sales += Decimal(str(trans.credit))
                
                # İndirilecek KDV (Box 4)
                if account_code == "2200" and trans.debit > 0:  # İndirilecek KDV
                    vat_return.vat_reclaimed += Decimal(str(trans.debit))
                
                # Toplam Satışlar (KDV hariç) (Box 6)
                if account_code.startswith("4") and trans.credit > 0:  # Gelir hesapları
                    vat_return.total_sales_ex_vat += Decimal(str(trans.credit))
                
                # Toplam Alımlar (KDV hariç) (Box 7)
                if account_code.startswith("5") and trans.debit > 0:  # Gider hesapları
                    vat_return.total_purchases_ex_vat += Decimal(str(trans.debit))
            
            # Toplam değerleri hesapla
            vat_return.calculate_totals()
            
            return vat_return
            
        except Exception as e:
            logger.error(f"KDV beyannamesi hesaplanırken hata: {e}")
            raise
    
    def submit_vat_return(self, vat_return):
        """KDV beyannamesini kaydet
        
        Args:
            vat_return: KDV beyannamesi nesnesi veya sözlük
            
        Returns:
            bool: İşlem başarılı mı
            str: Sonuç mesajı
        """
        try:
            # Sözlük ise VATReturn nesnesine dönüştür
            if isinstance(vat_return, dict):
                vat_return = VATReturn.from_dict(vat_return)
            
            # Beyanname doğrula
            is_valid, error = vat_return.validate()
            if not is_valid:
                return False, error
            
            # Gönderim tarihini ve durumu güncelle
            vat_return.submission_date = datetime.now().isoformat()
            vat_return.status = "submitted"
            
            # Veritabanına ekle
            vat_return_dict = vat_return.to_dict()
            self.db.add_vat_return(vat_return_dict)
            
            logger.info(f"KDV beyannamesi gönderildi: {vat_return.period.start_date} - {vat_return.period.end_date}")
            return True, "KDV beyannamesi başarıyla gönderildi"
            
        except Exception as e:
            logger.error(f"KDV beyannamesi gönderilirken hata: {e}")
            return False, str(e)
    
    def get_vat_returns(self):
        """KDV beyannamelerini al
        
        Returns:
            list: KDV beyannamesi nesneleri listesi
        """
        vat_returns = self.db.get_vat_returns()
        return [VATReturn.from_dict(vat_ret) for vat_ret in vat_returns]
    
    def get_vat_return_by_period(self, start_date, end_date):
        """Dönem bilgisine göre KDV beyannamesi al
        
        Args:
            start_date: Başlangıç tarihi (str veya date)
            end_date: Bitiş tarihi (str veya date)
            
        Returns:
            VATReturn: KDV beyannamesi nesnesi veya None
        """
        # String ise date'e dönüştür
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        
        if isinstance(end_date, str):
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        vat_returns = self.get_vat_returns()
        
        for vat_return in vat_returns:
            if (vat_return.period and 
                vat_return.period.start_date == start_date and 
                vat_return.period.end_date == end_date):
                return vat_return
        
        return None
    
    def calculate_income_tax_return(self, tax_year):
        """Gelir vergisi beyannamesi hesapla
        
        Args:
            tax_year: Vergi yılı (örn: "2022-23")
            
        Returns:
            IncomeTaxReturn: Gelir vergisi beyannamesi nesnesi
        """
        # Gelir vergisi beyannamesi oluştur
        tax_return = IncomeTaxReturn(tax_year)
        
        try:
            # Dönem tarihlerini al
            if not tax_return.period_start or not tax_return.period_end:
                return tax_return
            
            start_date = tax_return.period_start.strftime("%Y-%m-%d")
            end_date = tax_return.period_end.strftime("%Y-%m-%d")
            
            # Gelir ve giderleri hesapla
            income_expenses = self.ledger.get_income_expenses()
            
            # Dönem filtresi
            period_items = [ie for ie in income_expenses 
                         if start_date <= ie.get("date", "") <= end_date]
            
            # Toplam gelir ve giderleri hesapla
            for item in period_items:
                tax_return.total_income += Decimal(str(item.get("income", 0)))
                tax_return.total_expenses += Decimal(str(item.get("expense", 0)))
            
            # Kişisel vergi muafiyeti (2022-23 için £12,570)
            tax_return.tax_allowance = Decimal('12570.00')
            
            # Toplam değerleri hesapla
            tax_return.calculate_totals()
            
            return tax_return
            
        except Exception as e:
            logger.error(f"Gelir vergisi beyannamesi hesaplanırken hata: {e}")
            raise
    
    def submit_income_tax_return(self, tax_return):
        """Gelir vergisi beyannamesini kaydet
        
        Args:
            tax_return: Gelir vergisi beyannamesi nesnesi veya sözlük
            
        Returns:
            bool: İşlem başarılı mı
            str: Sonuç mesajı
        """
        try:
            # Sözlük ise IncomeTaxReturn nesnesine dönüştür
            if isinstance(tax_return, dict):
                tax_return = IncomeTaxReturn.from_dict(tax_return)
            
            # Beyanname doğrula
            is_valid, error = tax_return.validate()
            if not is_valid:
                return False, error
            
            # Gönderim tarihini ve durumu güncelle
            tax_return.submission_date = datetime.now().isoformat()
            tax_return.status = "submitted"
            
            # Veritabanına ekle
            tax_return_dict = tax_return.to_dict()
            self.db.add_tax_return(tax_return_dict)
            
            logger.info(f"Gelir vergisi beyannamesi gönderildi: {tax_return.tax_year}")
            return True, "Gelir vergisi beyannamesi başarıyla gönderildi"
            
        except Exception as e:
            logger.error(f"Gelir vergisi beyannamesi gönderilirken hata: {e}")
            return False, str(e)
    
    def get_tax_returns(self):
        """Gelir vergisi beyannamelerini al
        
        Returns:
            list: Gelir vergisi beyannamesi nesneleri listesi
        """
        tax_returns = self.db.get_tax_returns()
        return [IncomeTaxReturn.from_dict(tax_ret) for tax_ret in tax_returns]
    
    def get_tax_return_by_year(self, tax_year):
        """Vergi yılına göre gelir vergisi beyannamesi al
        
        Args:
            tax_year: Vergi yılı (örn: "2022-23")
            
        Returns:
            IncomeTaxReturn: Gelir vergisi beyannamesi nesnesi veya None
        """
        tax_returns = self.get_tax_returns()
        
        for tax_return in tax_returns:
            if tax_return.tax_year == tax_year:
                return tax_return
        
        return None
    
    def get_vat_periods(self, year=None):
        """KDV dönemlerini hesapla
        
        Args:
            year: Yıl (None ise geçerli yıl)
            
        Returns:
            list: TaxPeriod nesneleri listesi
        """
        if year is None:
            year = date.today().year
        
        # Üç aylık dönemler
        periods = []
        
        for quarter in range(1, 5):
            # Dönem başlangıç ayı
            start_month = (quarter - 1) * 3 + 1
            
            # Dönem başlangıç tarihi
            start_date = date(year, start_month, 1)
            
            # Dönem bitiş tarihi
            if quarter == 4:
                end_date = date(year, 12, 31)
            else:
                end_month = start_month + 2
                _, last_day = calendar.monthrange(year, end_month)
                end_date = date(year, end_month, last_day)
            
            # Dönem anahtarı
            period_key = f"{year}-Q{quarter}"
            
            # Dönem durumu (geçmiş dönemler F, gelecek dönemler O)
            status = "F" if end_date < date.today() else "O"
            
            periods.append(TaxPeriod(start_date, end_date, period_key, status))
        
        return periods
    
    def get_current_vat_period(self):
        """Geçerli KDV dönemini al
        
        Returns:
            TaxPeriod: Geçerli KDV dönemi
        """
        today = date.today()
        year = today.year
        
        # Geçerli çeyreği belirle
        quarter = (today.month - 1) // 3 + 1
        
        # Dönem başlangıç ayı
        start_month = (quarter - 1) * 3 + 1
        
        # Dönem başlangıç tarihi
        start_date = date(year, start_month, 1)
        
        # Dönem bitiş tarihi
        if quarter == 4:
            end_date = date(year, 12, 31)
        else:
            end_month = start_month + 2
            _, last_day = calendar.monthrange(year, end_month)
            end_date = date(year, end_month, last_day)
        
        # Dönem anahtarı
        period_key = f"{year}-Q{quarter}"
        
        return TaxPeriod(start_date, end_date, period_key, "O")
    
    def get_current_tax_year(self):
        """Geçerli vergi yılını al
        
        Returns:
            str: Vergi yılı (örn: "2022-23")
        """
        today = date.today()
        
        # İngiltere vergi yılı: 6 Nisan - 5 Nisan
        if today.month < 4 or (today.month == 4 and today.day < 6):
            # Önceki vergi yılı
            start_year = today.year - 1
        else:
            # Şimdiki vergi yılı
            start_year = today.year
        
        return f"{start_year}-{str(start_year + 1)[2:]}"
    
    def get_vat_liability(self):
        """Net KDV yükümlülüğünü hesapla
        
        Returns:
            Decimal: Net KDV yükümlülüğü (pozitif: borç, negatif: alacak)
        """
        # Ödenecek KDV bakiyesi
        output_vat = Decimal('0.00')
        account = self.ledger.get_account_by_code("2100")
        if account:
            output_vat = Decimal(str(account.get("balance", 0)))
        
        # İndirilecek KDV bakiyesi
        input_vat = Decimal('0.00')
        account = self.ledger.get_account_by_code("2200")
        if account:
            input_vat = Decimal(str(account.get("balance", 0)))
        
        # Net KDV hesapla (pozitif: borç, negatif: alacak)
        return output_vat - input_vat
