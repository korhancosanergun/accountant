#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - HMRC Kurumlar Vergisi MTD Modülü
Kurumlar vergisi hesaplamaları ve HMRC entegrasyonu.
"""

import logging
import json
from datetime import datetime, timedelta
import requests
from typing import Dict, List, Any, Optional
from . import mtd

# Loglayıcıyı yapılandır
logger = logging.getLogger(__name__)

class CorporateTaxClient:
    """HMRC Corporation Tax MTD API istemcisi"""
    
    def __init__(self, mtd_client, crn=None, utr=None):
        """
        Corporation Tax MTD API istemcisini başlat
        
        Args:
            mtd_client: MTDClient istemcisi
            crn: Company Registration Number (şirket kayıt numarası, opsiyonel)
            utr: Unique Taxpayer Reference (benzersiz vergi referansı, opsiyonel)
        """
        self.mtd_client = mtd_client
        self.crn = crn
        self.utr = utr
        
        # Corporation Tax API izinleri
        self.corp_tax_scopes = [
            "read:corporation-tax",
            "write:corporation-tax"
        ]
    
    def authenticate(self):
        """Corporation Tax API için kimlik doğrulama yap"""
        return self.mtd_client.auth.authenticate(self.corp_tax_scopes)
    
    def set_crn(self, crn):
        """Company Registration Number'ı ayarla"""
        self.crn = crn
    
    def set_utr(self, utr):
        """Unique Taxpayer Reference'ı ayarla"""
        self.utr = utr
    
    def _get_utr(self):
        """İç kullanım için UTR doğrulama"""
        if not self.utr:
            raise ValueError("UTR (Unique Taxpayer Reference) ayarlanmamış")
        return self.utr
    
    def get_company_details(self):
        """
        Şirket detaylarını getir
        
        Returns:
            Şirket detayları
        """
        utr = self._get_utr()
        
        # API isteği gönder
        endpoint = f"/organisations/corporation-tax/{utr}/company"
        return self.mtd_client.get(endpoint)
    
    def get_corporation_tax_obligations(self, from_date=None, to_date=None, status=None):
        """
        Kurumlar vergisi yükümlülüklerini getir
        
        Args:
            from_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            to_date: Bitiş tarihi (YYYY-MM-DD formatında)
            status: Durum filtresi ('O' (açık) veya 'F' (tamamlanmış))
        
        Returns:
            Yükümlülükler listesi
        """
        utr = self._get_utr()
        
        # Tarih parametrelerini kontrol et
        if from_date and to_date:
            # Tarih formatını kontrol et
            try:
                datetime.strptime(from_date, "%Y-%m-%d")
                datetime.strptime(to_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError("Tarih formatı geçersiz. YYYY-MM-DD kullanın.")
        else:
            # Varsayılan olarak son 12 ayı kullan
            today = datetime.now()
            from_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
        
        # Durum parametresini kontrol et
        if status and status not in ['O', 'F']:
            raise ValueError("Geçersiz durum. 'O' (açık) veya 'F' (tamamlanmış) kullanın.")
        
        # Parametreleri hazırla
        params = {
            'from': from_date,
            'to': to_date
        }
        
        if status:
            params['status'] = status
        
        # API isteği gönder
        endpoint = f"/organisations/corporation-tax/{utr}/obligations"
        response = self.mtd_client.get(endpoint, params=params)
        
        return response.get('obligations', [])
    
    def get_accounting_period(self, period_key):
        """
        Belirli bir hesap dönemi için vergi beyanını al
        
        Args:
            period_key: Dönem anahtarı (HMRC tarafından sağlanan)
        
        Returns:
            Hesap dönemi bilgileri
        """
        utr = self._get_utr()
        
        # API isteği gönder
        endpoint = f"/organisations/corporation-tax/{utr}/period/{period_key}"
        return self.mtd_client.get(endpoint)
    
    def submit_corporation_tax_return(self, period_key, tax_data):
        """
        Kurumlar vergisi beyanı gönder
        
        Args:
            period_key: Dönem anahtarı
            tax_data: Vergi beyanı verileri (API şemasına uygun olmalı)
                {
                    "companyName": "string",
                    "companyRegistrationNumber": "string",
                    "accountingPeriod": {
                        "startDate": "string (YYYY-MM-DD)",
                        "endDate": "string (YYYY-MM-DD)"
                    },
                    "income": {
                        "tradingIncome": 0,
                        "nonTradingIncome": 0,
                        "totalIncome": 0
                    },
                    "expenses": {
                        "tradingExpenses": 0,
                        "nonTradingExpenses": 0,
                        "totalExpenses": 0
                    },
                    "allowances": [...],
                    "adjustments": [...],
                    "taxableProfit": 0,
                    "taxDue": 0,
                    "declaration": true
                }
        
        Returns:
            Gönderim yanıtı
        """
        utr = self._get_utr()
        
        # Zorunlu alanları kontrol et
        required_fields = [
            "companyName", "accountingPeriod", "income", "expenses", 
            "taxableProfit", "taxDue", "declaration"
        ]
        
        for field in required_fields:
            if field not in tax_data:
                raise ValueError(f"Eksik alan: {field}")
        
        # Declaration alanını kontrol et
        if not tax_data.get("declaration", False):
            logger.warning("Beyan onaylanmamış (declaration=False)")
        
        # API isteği gönder
        endpoint = f"/organisations/corporation-tax/{utr}/period/{period_key}/return"
        return self.mtd_client.post(endpoint, tax_data)
    
    def get_tax_calculation(self, calculation_id):
        """
        Vergi hesaplama detaylarını al
        
        Args:
            calculation_id: Hesaplama ID'si
        
        Returns:
            Vergi hesaplama detayları
        """
        utr = self._get_utr()
        
        # API isteği gönder
        endpoint = f"/organisations/corporation-tax/{utr}/calculations/{calculation_id}"
        return self.mtd_client.get(endpoint)
    
    def get_company_payments(self, from_date=None, to_date=None):
        """
        Şirket ödemelerini getir
        
        Args:
            from_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            to_date: Bitiş tarihi (YYYY-MM-DD formatında)
        
        Returns:
            Ödeme bilgileri listesi
        """
        utr = self._get_utr()
        
        # Tarih parametrelerini kontrol et
        if not (from_date and to_date):
            # Varsayılan olarak son 12 ayı kullan
            today = datetime.now()
            from_date = (today - timedelta(days=365)).strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
        
        # Tarih formatını kontrol et
        try:
            datetime.strptime(from_date, "%Y-%m-%d")
            datetime.strptime(to_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Tarih formatı geçersiz. YYYY-MM-DD kullanın.")
        
        # Parametreleri hazırla
        params = {
            'from': from_date,
            'to': to_date
        }
        
        # API isteği gönder
        endpoint = f"/organisations/corporation-tax/{utr}/payments"
        response = self.mtd_client.get(endpoint, params=params)
        
        return response.get('payments', [])
    
    def get_payment_allocations(self, payment_id):
        """
        Ödeme tahsislerini getir
        
        Args:
            payment_id: Ödeme ID'si
        
        Returns:
            Ödeme tahsis detayları
        """
        utr = self._get_utr()
        
        # API isteği gönder
        endpoint = f"/organisations/corporation-tax/{utr}/payments/{payment_id}/allocations"
        return self.mtd_client.get(endpoint)


class CorporateTaxCalculator:
    """Kurumlar vergisi hesaplama ve hazırlama sınıfı"""
    
    def __init__(self, database):
        """
        Kurumlar vergisi hesaplayıcısını başlat
        
        Args:
            database: Veritabanı bağlantısı
        """
        self.db = database
        
        # Vergi oranları ve limitleri için sabitler (2023-24 vergi yılı için)
        # Not: Bu değerler gerçek vergi yılına göre güncellenmeli
        self.tax_rates = {
            "2023-24": {
                "small_profits_rate": 0.19,  # %19 (£50,000 altındaki kârlar için)
                "main_rate": 0.25,           # %25 (£250,000 üzerindeki kârlar için)
                "lower_limit": 50000,        # Alt limit
                "upper_limit": 250000        # Üst limit
            }
        }
    
    def calculate_corporation_tax(self, accounting_period_start, accounting_period_end, tax_year=None):
        """
        Kurumlar vergisi hesapla
        
        Args:
            accounting_period_start: Hesap dönemi başlangıç tarihi (YYYY-MM-DD formatında)
            accounting_period_end: Hesap dönemi bitiş tarihi (YYYY-MM-DD formatında)
            tax_year: Vergi yılı (opsiyonel, hesap döneminden belirlenecek)
        
        Returns:
            Hesaplanmış kurumlar vergisi detayları
        """
        # Tarih formatlarını kontrol et
        try:
            start_date = datetime.strptime(accounting_period_start, "%Y-%m-%d")
            end_date = datetime.strptime(accounting_period_end, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Tarih formatı geçersiz. YYYY-MM-DD kullanın.")
        
        # Vergi yılını belirle (hesap döneminin çoğunluğunun düştüğü yıl)
        if not tax_year:
            # Hesap döneminin ortası
            mid_date = start_date + (end_date - start_date) / 2
            
            # UK vergi yılı 1 Nisan'da başlar (örn: 2023-24)
            tax_year_start = mid_date.year
            if mid_date.month < 4 or (mid_date.month == 4 and mid_date.day < 1):
                tax_year_start -= 1
                
            tax_year = f"{tax_year_start}-{str(tax_year_start + 1)[-2:]}"
        
        # Vergi yılı için oranları al
        if tax_year not in self.tax_rates:
            raise ValueError(f"Vergi yılı için oranlar bulunamadı: {tax_year}")
        
        rates = self.tax_rates[tax_year]
        
        # Bu dönemdeki işlemleri filtrele
        transactions = self.db.filter_transactions(
            start_date=accounting_period_start,
            end_date=accounting_period_end
        )
        
        # Hesap planını al
        chart_of_accounts = self.db.get_chart_of_accounts()
        
        # Ticari gelir ve giderleri hesapla
        trading_income = 0
        trading_expenses = 0
        non_trading_income = 0
        non_trading_expenses = 0
        
        for transaction in transactions:
            for entry in transaction.get("entries", []):
                account_code = entry.get("account_code")
                account = self.db.get_account_by_code(account_code)
                
                if not account:
                    continue
                
                amount = entry.get("amount", 0)
                account_type = account.get("type")
                
                # Ticari gelir
                if account_type == "income" and account.get("trading", True):
                    if entry.get("type") == "credit":
                        trading_income += amount
                    else:
                        trading_income -= amount
                
                # Ticari gider
                elif account_type == "expense" and account.get("trading", True):
                    if entry.get("type") == "debit":
                        trading_expenses += amount
                    else:
                        trading_expenses -= amount
                
                # Ticari olmayan gelir (yatırım, faiz geliri, vb.)
                elif account_type == "income" and not account.get("trading", True):
                    if entry.get("type") == "credit":
                        non_trading_income += amount
                    else:
                        non_trading_income -= amount
                
                # Ticari olmayan gider (faiz gideri, vb.)
                elif account_type == "expense" and not account.get("trading", True):
                    if entry.get("type") == "debit":
                        non_trading_expenses += amount
                    else:
                        non_trading_expenses -= amount
        
        # Toplam gelir ve gider
        total_income = trading_income + non_trading_income
        total_expenses = trading_expenses + non_trading_expenses
        
        # Vergilendirilebilir kâr
        taxable_profit = total_income - total_expenses
        
        # Vergilendirilebilir kâr, negatifse sıfır olarak değerlendirilir
        taxable_profit = max(0, taxable_profit)
        
        # Vergi tutarını hesapla
        tax_due = 0
        if taxable_profit <= rates["lower_limit"]:
            # Düşük kâr oranı
            tax_due = taxable_profit * rates["small_profits_rate"]
        elif taxable_profit >= rates["upper_limit"]:
            # Ana oran
            tax_due = taxable_profit * rates["main_rate"]
        else:
            # Marjinal rahatlama formülü
            # (R - r) * [2 * (U - P) / (U - L)] * P / 100
            # R: Ana oran (%), r: Küçük kârlar oranı (%)
            # U: Üst limit, L: Alt limit, P: Kâr
            
            r_diff = rates["main_rate"] - rates["small_profits_rate"]
            u_l_diff = rates["upper_limit"] - rates["lower_limit"]
            u_p_diff = rates["upper_limit"] - taxable_profit
            
            marginal_relief = r_diff * (2 * u_p_diff / u_l_diff) * taxable_profit
            tax_at_main_rate = taxable_profit * rates["main_rate"]
            
            tax_due = tax_at_main_rate - marginal_relief
        
        # Sonuçları oluştur
        result = {
            "tax_year": tax_year,
            "accounting_period": {
                "start_date": accounting_period_start,
                "end_date": accounting_period_end,
                "length_days": (end_date - start_date).days + 1
            },
            "income": {
                "trading_income": round(trading_income, 2),
                "non_trading_income": round(non_trading_income, 2),
                "total_income": round(total_income, 2)
            },
            "expenses": {
                "trading_expenses": round(trading_expenses, 2),
                "non_trading_expenses": round(non_trading_expenses, 2),
                "total_expenses": round(total_expenses, 2)
            },
            "taxable_profit": round(taxable_profit, 2),
            "tax_rates": {
                "small_profits_rate": rates["small_profits_rate"],
                "main_rate": rates["main_rate"],
                "lower_limit": rates["lower_limit"],
                "upper_limit": rates["upper_limit"]
            },
            "tax_due": round(tax_due, 2),
            "effective_rate": round((tax_due / taxable_profit * 100) if taxable_profit > 0 else 0, 2)
        }
        
        return result
    
    def prepare_corporation_tax_return(self, accounting_period_start, accounting_period_end, company_info):
        """
        Kurumlar vergisi beyannamesi hazırla
        
        Args:
            accounting_period_start: Hesap dönemi başlangıç tarihi
            accounting_period_end: Hesap dönemi bitiş tarihi
            company_info: Şirket bilgileri
        
        Returns:
            HMRC API için hazırlanmış kurumlar vergisi beyanı
        """
        # Vergi hesaplamasını yap
        tax_calculation = self.calculate_corporation_tax(
            accounting_period_start, 
            accounting_period_end
        )
        
        # Şirket bilgilerini hazırla
        company_name = company_info.get("company_name", "")
        company_crn = company_info.get("crn", "")
        
        # HMRC API için formatla
        tax_return = {
            "companyName": company_name,
            "companyRegistrationNumber": company_crn,
            "accountingPeriod": {
                "startDate": accounting_period_start,
                "endDate": accounting_period_end
            },
            "income": {
                "tradingIncome": tax_calculation["income"]["trading_income"],
                "nonTradingIncome": tax_calculation["income"]["non_trading_income"],
                "totalIncome": tax_calculation["income"]["total_income"]
            },
            "expenses": {
                "tradingExpenses": tax_calculation["expenses"]["trading_expenses"],
                "nonTradingExpenses": tax_calculation["expenses"]["non_trading_expenses"],
                "totalExpenses": tax_calculation["expenses"]["total_expenses"]
            },
            "taxableProfit": tax_calculation["taxable_profit"],
            "taxDue": tax_calculation["tax_due"],
            "declaration": False  # Varsayılan olarak onaylanmamış
        }
        
        return tax_return
    
    def save_corporation_tax_return(self, period_start, period_end, tax_calculation, status="draft"):
        """
        Kurumlar vergisi beyanını veritabanına kaydet
        
        Args:
            period_start: Dönem başlangıç tarihi
            period_end: Dönem bitiş tarihi
            tax_calculation: Vergi hesaplaması verileri
            status: Beyan durumu ("draft", "submitted", "accepted")
        
        Returns:
            Eklenen beyan ID'si
        """
        # Beyan nesnesini oluştur
        # Yıl formatı olarak başlangıç ve bitiş yıllarını kullan (örn: 2023-2024)
        start_year = datetime.strptime(period_start, "%Y-%m-%d").year
        end_year = datetime.strptime(period_end, "%Y-%m-%d").year
        period_key = f"{start_year}-{end_year}"
        
        tax_return = {
            "id": None,  # Veritabanı tarafından atanacak
            "type": "corporation_tax",
            "period_key": period_key,
            "period_start": period_start,
            "period_end": period_end,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": status,
            "submission_date": datetime.now().isoformat() if status == "submitted" else None,
            "data": tax_calculation
        }
        
        # Veritabanına kaydet (veritabanı yapısına göre ayarlanmalı)
        return self.db.add_tax_return(tax_return)
    
    def update_corporation_tax_status(self, tax_return_id, status, submission_data=None):
        """
        Kurumlar vergisi beyanı durumunu güncelle
        
        Args:
            tax_return_id: Vergi beyanı ID'si
            status: Yeni durum
            submission_data: Gönderim verileri (opsiyonel)
        
        Returns:
            Güncellenen beyan verisi
        """
        # Beyanı al
        tax_return = self.db.get_tax_return_by_id(tax_return_id)
        if not tax_return:
            raise ValueError(f"Vergi beyanı bulunamadı: {tax_return_id}")
        
        # Beyanı güncelle
        updated_tax_return = tax_return.copy()
        updated_tax_return["status"] = status
        updated_tax_return["updated_at"] = datetime.now().isoformat()
        
        if status == "submitted":
            updated_tax_return["submission_date"] = datetime.now().isoformat()
            
            if submission_data:
                # Veriyi güncelle
                updated_data = updated_tax_return["data"].copy()
                updated_data["submission"] = submission_data
                updated_tax_return["data"] = updated_data
        
        # Veritabanında güncelle
        success = self.db.update_tax_return(tax_return_id, updated_tax_return)
        if not success:
            raise ValueError(f"Vergi beyanı güncellenirken hata oluştu: {tax_return_id}")
        
        return updated_tax_return
    
    def get_next_filing_deadline(self, company_info):
        """
        Sonraki beyanname son tarihini hesapla
        
        Args:
            company_info: Şirket bilgileri
        
        Returns:
            Sonraki beyanname son tarihi ve kalan gün sayısı
        """
        # Şirket hesap dönemini al
        accounting_period_end = company_info.get("accounting_period_end")
        
        if not accounting_period_end:
            return None, None
        
        try:
            end_date = datetime.strptime(accounting_period_end, "%Y-%m-%d")
            
            # Kurumlar vergisi için son tarih genellikle hesap döneminin 
            # bitiminden 12 ay sonradır
            filing_deadline = end_date.replace(year=end_date.year + 1)
            
            # Kalan gün sayısı
            today = datetime.now()
            days_remaining = (filing_deadline - today).days
            
            return filing_deadline.strftime("%Y-%m-%d"), days_remaining
            
        except ValueError:
            return None, None
