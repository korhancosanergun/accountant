#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - HMRC Gelir Vergisi MTD Modülü
Self Assessment gelir vergisi beyanlarını HMRC'ye iletmek için sınıflar ve fonksiyonlar.
"""

import logging
import json
from datetime import datetime
from dateutil.relativedelta import relativedelta
import requests
import uuid
from . import mtd

# Loglayıcıyı yapılandır
logger = logging.getLogger(__name__)

class IncomeTaxClient:
    """HMRC Income Tax MTD API istemcisi"""
    
    def __init__(self, mtd_client, nino=None):
        """
        Income Tax MTD API istemcisini başlat
        
        Args:
            mtd_client: MTDClient istemcisi
            nino: National Insurance Number (opsiyonel)
        """
        self.mtd_client = mtd_client
        self.nino = nino
        
        # Income Tax API izinleri
        self.income_tax_scopes = [
            "read:self-assessment",
            "write:self-assessment"
        ]
    
    def authenticate(self):
        """Income Tax API için kimlik doğrulama yap"""
        return self.mtd_client.auth.authenticate(self.income_tax_scopes)
    
    def set_nino(self, nino):
        """National Insurance Number'ı ayarla"""
        self.nino = nino
    
    def _get_nino(self):
        """İç kullanım için NINO doğrulama"""
        if not self.nino:
            raise ValueError("NINO (National Insurance Number) ayarlanmamış")
        return self.nino
    
    def get_income_tax_calculations(self, tax_year=None):
        """
        Tamamlanan gelir vergisi hesaplamalarını getir
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında, ör: "2022-23")
        
        Returns:
            Tamamlanan hesaplamalar listesi
        """
        nino = self._get_nino()
        
        # Vergi yılını kontrol et
        if tax_year and not self._validate_tax_year(tax_year):
            raise ValueError("Geçersiz vergi yılı formatı. YYYY-YY kullanın (örn: 2022-23)")
        
        # API isteği gönder
        endpoint = f"/individuals/calculations/{nino}/self-assessment"
        
        if tax_year:
            endpoint += f"/{tax_year}"
        
        return self.mtd_client.get(endpoint)
    
    def get_income_tax_calculation(self, calculation_id):
        """
        Belirli bir gelir vergisi hesaplamasının detaylarını getir
        
        Args:
            calculation_id: Hesaplama ID'si
        
        Returns:
            Hesaplama detayları
        """
        nino = self._get_nino()
        
        # API isteği gönder
        endpoint = f"/individuals/calculations/{nino}/self-assessment/{calculation_id}"
        return self.mtd_client.get(endpoint)
    
    def get_income_tax_obligations(self, from_date=None, to_date=None, status=None):
        """
        Gelir vergisi yükümlülüklerini getir
        
        Args:
            from_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            to_date: Bitiş tarihi (YYYY-MM-DD formatında)
            status: Durum filtresi ('Open' veya 'Fulfilled')
        
        Returns:
            Yükümlülükler listesi
        """
        nino = self._get_nino()
        
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
            from_date = (today - relativedelta(months=12)).strftime("%Y-%m-%d")
            to_date = today.strftime("%Y-%m-%d")
        
        # Durum parametresini kontrol et
        if status and status not in ['Open', 'Fulfilled']:
            raise ValueError("Geçersiz durum. 'Open' veya 'Fulfilled' kullanın.")
        
        # Parametreleri hazırla
        params = {
            'from': from_date,
            'to': to_date
        }
        
        if status:
            params['status'] = status
        
        # API isteği gönder
        endpoint = f"/individuals/obligations/{nino}/income-and-expenditure"
        response = self.mtd_client.get(endpoint, params=params)
        
        return response.get('obligations', [])
    
    def submit_income_sources(self, tax_year, income_sources_data):
        """
        Gelir kaynaklarını gönder
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
            income_sources_data: Gelir kaynakları verileri
        
        Returns:
            Gönderim yanıtı
        """
        nino = self._get_nino()
        
        # Vergi yılını doğrula
        if not self._validate_tax_year(tax_year):
            raise ValueError("Geçersiz vergi yılı formatı. YYYY-YY kullanın (örn: 2022-23)")
        
        # API isteği gönder
        endpoint = f"/individuals/income-sources/{nino}/{tax_year}"
        return self.mtd_client.post(endpoint, income_sources_data)
    
    def submit_self_employment_income(self, tax_year, self_employment_id, income_data):
        """
        Serbest meslek gelirlerini gönder
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
            self_employment_id: Serbest meslek ID'si
            income_data: Gelir verileri
        
        Returns:
            Gönderim yanıtı
        """
        nino = self._get_nino()
        
        # Vergi yılını doğrula
        if not self._validate_tax_year(tax_year):
            raise ValueError("Geçersiz vergi yılı formatı. YYYY-YY kullanın (örn: 2022-23)")
        
        # API isteği gönder
        endpoint = f"/individuals/business/self-employment/{nino}/{self_employment_id}/income-summary/{tax_year}"
        return self.mtd_client.post(endpoint, income_data)
    
    def submit_property_income(self, tax_year, property_type, income_data):
        """
        Mülk gelirlerini gönder
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
            property_type: Mülk tipi ('uk-property' veya 'foreign-property')
            income_data: Gelir verileri
        
        Returns:
            Gönderim yanıtı
        """
        nino = self._get_nino()
        
        # Vergi yılını doğrula
        if not self._validate_tax_year(tax_year):
            raise ValueError("Geçersiz vergi yılı formatı. YYYY-YY kullanın (örn: 2022-23)")
        
        # Mülk tipini doğrula
        if property_type not in ['uk-property', 'foreign-property']:
            raise ValueError("Geçersiz mülk tipi. 'uk-property' veya 'foreign-property' kullanın.")
        
        # API isteği gönder
        endpoint = f"/individuals/business/property/{nino}/{property_type}/income-summary/{tax_year}"
        return self.mtd_client.post(endpoint, income_data)
    
    def submit_final_declaration(self, tax_year, calculation_id):
        """
        Final beyanını gönder
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
            calculation_id: Hesaplama ID'si
        
        Returns:
            Gönderim yanıtı
        """
        nino = self._get_nino()
        
        # Vergi yılını doğrula
        if not self._validate_tax_year(tax_year):
            raise ValueError("Geçersiz vergi yılı formatı. YYYY-YY kullanın (örn: 2022-23)")
        
        # Beyan verilerini oluştur
        declaration_data = {
            "calculationId": calculation_id,
            "declaration": {
                "declaration": True
            }
        }
        
        # API isteği gönder
        endpoint = f"/individuals/self-assessment/{nino}/final-declaration/{tax_year}"
        return self.mtd_client.post(endpoint, declaration_data)
    
    def get_self_employment_details(self, self_employment_id):
        """
        Serbest meslek detaylarını getir
        
        Args:
            self_employment_id: Serbest meslek ID'si
        
        Returns:
            Serbest meslek detayları
        """
        nino = self._get_nino()
        
        endpoint = f"/individuals/business/details/{nino}/self-employment/{self_employment_id}"
        return self.mtd_client.get(endpoint)
    
    def get_property_details(self, property_type):
        """
        Mülk detaylarını getir
        
        Args:
            property_type: Mülk tipi ('uk-property' veya 'foreign-property')
        
        Returns:
            Mülk detayları
        """
        nino = self._get_nino()
        
        # Mülk tipini doğrula
        if property_type not in ['uk-property', 'foreign-property']:
            raise ValueError("Geçersiz mülk tipi. 'uk-property' veya 'foreign-property' kullanın.")
        
        endpoint = f"/individuals/business/details/{nino}/property/{property_type}"
        return self.mtd_client.get(endpoint)
    
    def get_business_income_sources(self):
        """
        Tüm iş ve mülk gelir kaynaklarını getir
        
        Returns:
            İş ve mülk gelir kaynakları listesi
        """
        nino = self._get_nino()
        
        endpoint = f"/individuals/business/details/{nino}"
        return self.mtd_client.get(endpoint)
    
    def trigger_tax_calculation(self, tax_year):
        """
        Vergi hesaplaması başlat
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
        
        Returns:
            Hesaplama ID'si
        """
        nino = self._get_nino()
        
        # Vergi yılını doğrula
        if not self._validate_tax_year(tax_year):
            raise ValueError("Geçersiz vergi yılı formatı. YYYY-YY kullanın (örn: 2022-23)")
        
        # Hesaplama isteği verileri
        calc_data = {
            "taxYear": tax_year
        }
        
        # API isteği gönder
        endpoint = f"/individuals/calculations/{nino}/self-assessment"
        response = self.mtd_client.post(endpoint, calc_data)
        
        return response.get('calculationId')
    
    def get_calculation_messages(self, calculation_id):
        """
        Hesaplama mesajlarını getir (uyarılar, hatalar, bilgiler)
        
        Args:
            calculation_id: Hesaplama ID'si
        
        Returns:
            Hesaplama mesajları
        """
        nino = self._get_nino()
        
        endpoint = f"/individuals/calculations/{nino}/self-assessment/{calculation_id}/messages"
        return self.mtd_client.get(endpoint)
    
    def get_income_summary(self, calculation_id):
        """
        Hesaplamanın gelir özetini getir
        
        Args:
            calculation_id: Hesaplama ID'si
        
        Returns:
            Gelir özeti
        """
        nino = self._get_nino()
        
        endpoint = f"/individuals/calculations/{nino}/self-assessment/{calculation_id}/income-summary"
        return self.mtd_client.get(endpoint)
    
    def get_income_tax_summary(self, calculation_id):
        """
        Hesaplamanın gelir vergisi özetini getir
        
        Args:
            calculation_id: Hesaplama ID'si
        
        Returns:
            Gelir vergisi özeti
        """
        nino = self._get_nino()
        
        endpoint = f"/individuals/calculations/{nino}/self-assessment/{calculation_id}/income-tax"
        return self.mtd_client.get(endpoint)
    
    def _validate_tax_year(self, tax_year):
        """
        Vergi yılı formatını doğrula
        
        Args:
            tax_year: Doğrulanacak vergi yılı (YYYY-YY formatında)
        
        Returns:
            Geçerli ise True, değilse False
        """
        # Format: YYYY-YY (örn: 2022-23)
        if not isinstance(tax_year, str) or len(tax_year) != 7:
            return False
        
        try:
            start_year = int(tax_year[0:4])
            end_year = int(tax_year[5:7])
            
            # Son iki basamağın bir sonraki yıla ait olduğunu doğrula
            if end_year != (start_year + 1) % 100:
                return False
            
            return True
        except:
            return False


class IncomeTaxCalculator:
    """Gelir vergisi hesaplama ve hazırlama sınıfı"""
    
    def __init__(self, database):
        """
        Gelir vergisi hesaplayıcısını başlat
        
        Args:
            database: Veritabanı bağlantısı
        """
        self.db = database
        
        # Vergi oranları ve dilimleri için sabitler (2023-24 vergi yılı için)
        # Not: Bu değerler gerçek vergi yılına göre güncellenmeli
        self.tax_bands = {
            "2023-24": {
                "personal_allowance": 12570,  # Kişisel muafiyet
                "basic_rate": {
                    "threshold": 50270,  # Temel oran üst sınırı
                    "rate": 0.20  # %20
                },
                "higher_rate": {
                    "threshold": 125140,  # Yüksek oran üst sınırı
                    "rate": 0.40  # %40
                },
                "additional_rate": {
                    "rate": 0.45  # %45
                }
            }
        }
        
        # Ulusal Sigorta katkı oranları (2023-24 vergi yılı için)
        self.ni_rates = {
            "2023-24": {
                "class2": {
                    "rate": 3.45,  # Haftalık £3.45
                    "threshold": 12570,  # Small Profits Threshold (Yıllık)
                },
                "class4": {
                    "lower_threshold": 12570,  # Lower Profits Limit
                    "upper_threshold": 50270,  # Upper Profits Limit
                    "lower_rate": 0.09,  # %9 (£12,570 ile £50,270 arası)
                    "upper_rate": 0.02  # %2 (£50,270 üzeri)
                }
            }
        }
        
        # Dividend vergi oranları (2023-24 vergi yılı için)
        self.dividend_rates = {
            "2023-24": {
                "allowance": 1000,  # Dividend muafiyeti
                "basic_rate": 0.085,  # %8.75 (temel oran)
                "higher_rate": 0.3375,  # %33.75 (yüksek oran)
                "additional_rate": 0.3935  # %39.35 (ek oran)
            }
        }
    
    def calculate_income_tax(self, tax_year, income_data):
        """
        Gelir vergisi hesapla
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
            income_data: Gelir verileri
                {
                    "employment_income": 0,  # İşveren maaşı
                    "self_employment_income": 0,  # Serbest meslek geliri
                    "property_income": 0,  # Mülk gelirleri
                    "dividends": 0,  # Temettüler
                    "pension_contributions": 0,  # Emeklilik katkıları
                    "gift_aid_donations": 0,  # Bağışlar
                    "other_deductions": 0  # Diğer indirimler
                }
        
        Returns:
            Hesaplanmış vergi detayları
        """
        # Vergi yılı için oranları al
        if tax_year not in self.tax_bands:
            raise ValueError(f"Vergi yılı için oranlar bulunamadı: {tax_year}")
        
        bands = self.tax_bands[tax_year]
        
        # Toplam vergilendirilebilir geliri hesapla
        total_income = sum([
            income_data.get("employment_income", 0),
            income_data.get("self_employment_income", 0),
            income_data.get("property_income", 0),
            income_data.get("dividends", 0)
        ])
        
        # Toplam indirimleri hesapla
        total_deductions = sum([
            income_data.get("pension_contributions", 0),
            income_data.get("gift_aid_donations", 0),
            income_data.get("other_deductions", 0)
        ])
        
        # Net vergilendirilebilir geliri hesapla
        taxable_income = max(0, total_income - total_deductions)
        
        # Kişisel muafiyeti hesapla
        # Not: £100,000 üzerindeki her £2 için £1 azalır
        personal_allowance = bands["personal_allowance"]
        if total_income > 100000:
            reduction = min(personal_allowance, (total_income - 100000) / 2)
            personal_allowance -= reduction
        
        # Vergiye tabi geliri hesapla
        taxable_after_allowance = max(0, taxable_income - personal_allowance)
        
        # Vergi dilimleri hesapla
        basic_rate_band = min(bands["basic_rate"]["threshold"] - bands["personal_allowance"], taxable_after_allowance)
        higher_rate_band = min(
            bands["higher_rate"]["threshold"] - bands["basic_rate"]["threshold"],
            max(0, taxable_after_allowance - basic_rate_band)
        )
        additional_rate_band = max(0, taxable_after_allowance - basic_rate_band - higher_rate_band)
        
        # Vergileri hesapla
        basic_rate_tax = basic_rate_band * bands["basic_rate"]["rate"]
        higher_rate_tax = higher_rate_band * bands["higher_rate"]["rate"]
        additional_rate_tax = additional_rate_band * bands["additional_rate"]["rate"]
        
        # Toplam vergiyi hesapla
        total_tax = basic_rate_tax + higher_rate_tax + additional_rate_tax
        
        # Temettü vergisini hesapla (ayrı olarak)
        dividend_tax = self._calculate_dividend_tax(
            tax_year, 
            income_data.get("dividends", 0),
            taxable_after_allowance - income_data.get("dividends", 0)
        )
        
        # Ulusal Sigorta katkılarını hesapla
        ni_contributions = self._calculate_national_insurance(
            tax_year,
            income_data.get("self_employment_income", 0)
        )
        
        # Sonuçları oluştur
        result = {
            "tax_year": tax_year,
            "total_income": round(total_income, 2),
            "total_deductions": round(total_deductions, 2),
            "taxable_income": round(taxable_income, 2),
            "personal_allowance": round(personal_allowance, 2),
            "taxable_after_allowance": round(taxable_after_allowance, 2),
            
            "tax_bands": {
                "basic_rate": {
                    "amount": round(basic_rate_band, 2),
                    "tax": round(basic_rate_tax, 2)
                },
                "higher_rate": {
                    "amount": round(higher_rate_band, 2),
                    "tax": round(higher_rate_tax, 2)
                },
                "additional_rate": {
                    "amount": round(additional_rate_band, 2),
                    "tax": round(additional_rate_tax, 2)
                }
            },
            
            "income_tax": round(total_tax, 2),
            "dividend_tax": round(dividend_tax, 2),
            "total_income_tax": round(total_tax + dividend_tax, 2),
            
            "national_insurance": ni_contributions,
            
            "total_tax_and_ni": round(total_tax + dividend_tax + ni_contributions["total"], 2)
        }
        
        return result
    
    def _calculate_dividend_tax(self, tax_year, dividend_income, other_taxable_income):
        """
        Temettü vergisini hesapla
        
        Args:
            tax_year: Vergi yılı
            dividend_income: Temettü geliri
            other_taxable_income: Diğer vergilendirilebilir gelir
        
        Returns:
            Hesaplanan temettü vergisi
        """
        # Vergi yılı için oranları al
        if tax_year not in self.dividend_rates:
            raise ValueError(f"Temettü oranları bulunamadı: {tax_year}")
        
        if tax_year not in self.tax_bands:
            raise ValueError(f"Vergi oranları bulunamadı: {tax_year}")
        
        div_rates = self.dividend_rates[tax_year]
        bands = self.tax_bands[tax_year]
        
        # Temettü yoksa, vergi de yoktur
        if dividend_income <= 0:
            return 0
        
        # Temettü muafiyetini hesapla
        dividend_allowance = div_rates["allowance"]
        
        # Mevcut vergi bandını belirle
        basic_limit = bands["basic_rate"]["threshold"] - bands["personal_allowance"]
        higher_limit = bands["higher_rate"]["threshold"] - bands["personal_allowance"]
        
        # Diğer gelirin kullandığı bandı hesapla
        remaining_basic_band = max(0, basic_limit - other_taxable_income)
        remaining_higher_band = max(0, higher_limit - max(0, other_taxable_income - basic_limit))
        
        # Temettü gelirini muafiyet ve her dilime dağıt
        taxable_dividend = max(0, dividend_income - dividend_allowance)
        
        div_basic_band = min(remaining_basic_band, taxable_dividend)
        div_higher_band = min(remaining_higher_band, max(0, taxable_dividend - div_basic_band))
        div_additional_band = max(0, taxable_dividend - div_basic_band - div_higher_band)
        
        # Temettü vergisini hesapla
        basic_rate_div_tax = div_basic_band * div_rates["basic_rate"]
        higher_rate_div_tax = div_higher_band * div_rates["higher_rate"]
        additional_rate_div_tax = div_additional_band * div_rates["additional_rate"]
        
        # Toplam temettü vergisi
        total_dividend_tax = basic_rate_div_tax + higher_rate_div_tax + additional_rate_div_tax
        
        return total_dividend_tax
    
    def _calculate_national_insurance(self, tax_year, self_employment_income):
        """
        Ulusal Sigorta katkılarını hesapla
        
        Args:
            tax_year: Vergi yılı
            self_employment_income: Serbest meslek geliri
        
        Returns:
            Hesaplanan Ulusal Sigorta katkıları
        """
        # Vergi yılı için oranları al
        if tax_year not in self.ni_rates:
            raise ValueError(f"Ulusal Sigorta oranları bulunamadı: {tax_year}")
        
        ni_rates = self.ni_rates[tax_year]
        
        # Class 2 katkıları (haftalık sabit oran)
        class2 = 0
        if self_employment_income > ni_rates["class2"]["threshold"]:
            class2 = ni_rates["class2"]["rate"] * 52  # 52 hafta
        
        # Class 4 katkıları (gelire bağlı yüzde)
        class4 = 0
        class4_lower = 0
        class4_upper = 0
        
        if self_employment_income > ni_rates["class4"]["lower_threshold"]:
            # Alt dilim katkısı
            class4_income_lower = min(
                self_employment_income - ni_rates["class4"]["lower_threshold"],
                ni_rates["class4"]["upper_threshold"] - ni_rates["class4"]["lower_threshold"]
            )
            class4_lower = class4_income_lower * ni_rates["class4"]["lower_rate"]
            
            # Üst dilim katkısı
            if self_employment_income > ni_rates["class4"]["upper_threshold"]:
                class4_income_upper = self_employment_income - ni_rates["class4"]["upper_threshold"]
                class4_upper = class4_income_upper * ni_rates["class4"]["upper_rate"]
            
            class4 = class4_lower + class4_upper
        
        return {
            "class2": round(class2, 2),
            "class4": round(class4, 2),
            "class4_lower": round(class4_lower, 2),
            "class4_upper": round(class4_upper, 2),
            "total": round(class2 + class4, 2)
        }
    
    def prepare_self_employment_data(self, tax_year, business_id=None):
        """
        Serbest meslek verilerini hazırla
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
            business_id: İş ID'si (opsiyonel, mevcut değilse yeni oluşturulur)
        
        Returns:
            HMRC API için hazırlanmış serbest meslek verileri
        """
        # Vergi yılı başlangıç ve bitiş tarihlerini hesapla
        start_year = int(tax_year.split("-")[0])
        start_date = f"{start_year}-04-06"
        end_date = f"{start_year + 1}-04-05"
        
        # Bu dönemdeki işlemleri filtrele
        transactions = self.db.filter_transactions(
            start_date=start_date,
            end_date=end_date
        )
        
        # Serbest meslek hesaplarını filtrele
        chart_of_accounts = self.db.get_chart_of_accounts()
        self_emp_accounts = []
        for account in chart_of_accounts:
            if account.get("self_employment", False):
                self_emp_accounts.append(account.get("code"))
        
        # Serbest meslek gelirleri ve giderleri
        income = 0
        expenses = {}
        
        for transaction in transactions:
            for entry in transaction.get("entries", []):
                account_code = entry.get("account_code")
                if account_code in self_emp_accounts:
                    amount = entry.get("amount", 0)
                    account = self.db.get_account_by_code(account_code)
                    
                    # Gelir hesabı mı?
                    if account.get("type") == "income":
                        if entry.get("type") == "credit":
                            income += amount
                        else:
                            income -= amount
                    # Gider hesabı mı?
                    elif account.get("type") == "expense":
                        category = account.get("category", "other")
                        if category not in expenses:
                            expenses[category] = 0
                        
                        if entry.get("type") == "debit":
                            expenses[category] += amount
                        else:
                            expenses[category] -= amount
        
        # İş ID'sini hazırla
        if not business_id:
            business_id = str(uuid.uuid4())
        
        # HMRC API formatında serbest meslek verileri
        self_employment_data = {
            "businessId": business_id,
            "businessName": self.db.get_company_info().get("business_name", "Self Employment"),
            "businessAddressLineOne": self.db.get_company_info().get("address_line1", ""),
            "businessAddressLineTwo": self.db.get_company_info().get("address_line2", ""),
            "businessAddressLineThree": self.db.get_company_info().get("address_line3", ""),
            "businessAddressLineFour": self.db.get_company_info().get("address_line4", ""),
            "businessAddressPostcode": self.db.get_company_info().get("postcode", ""),
            "businessAddressCountryCode": self.db.get_company_info().get("country", "GB"),
            "accountingPeriodStartDate": start_date,
            "accountingPeriodEndDate": end_date,
            "tradingStartDate": self.db.get_company_info().get("trading_start_date", start_date),
            "cashOrAccruals": "ACCRUALS",
            "cessationDate": None,
            "cessationReason": None,
            "paperlessSettings": {
                "email": self.db.get_company_info().get("email", ""),
                "consent": True
            },
            "income": {
                "turnover": round(income, 2),
                "other": 0
            },
            "expenses": {
                "costOfGoods": round(expenses.get("cost_of_goods", 0), 2),
                "paymentsToSubcontractors": round(expenses.get("subcontractors", 0), 2),
                "wagesAndStaffCosts": round(expenses.get("staff_costs", 0), 2),
                "carVanTravelExpenses": round(expenses.get("travel", 0), 2),
                "premisesRunningCosts": round(expenses.get("premises", 0), 2),
                "maintenanceCosts": round(expenses.get("maintenance", 0), 2),
                "adminCosts": round(expenses.get("admin", 0), 2),
                "advertisingCosts": round(expenses.get("advertising", 0), 2),
                "businessEntertainmentCosts": round(expenses.get("entertainment", 0), 2),
                "interestOnBankOtherLoans": round(expenses.get("interest", 0), 2),
                "financeCharges": round(expenses.get("finance", 0), 2),
                "irrecoverableDebts": round(expenses.get("bad_debts", 0), 2),
                "professionalFees": round(expenses.get("professional", 0), 2),
                "depreciation": round(expenses.get("depreciation", 0), 2),
                "other": round(expenses.get("other", 0), 2)
            },
            "additions": {
                "costOfGoodsDisallowable": 0,
                "paymentsToSubcontractorsDisallowable": 0,
                "wagesAndStaffCostsDisallowable": 0,
                "carVanTravelExpensesDisallowable": 0,
                "premisesRunningCostsDisallowable": 0,
                "maintenanceCostsDisallowable": 0,
                "adminCostsDisallowable": 0,
                "advertisingCostsDisallowable": 0,
                "businessEntertainmentCostsDisallowable": round(expenses.get("entertainment", 0), 2),  # Eğlence giderleri indirimli değil
                "interestOnBankOtherLoansDisallowable": 0,
                "financeChargesDisallowable": 0,
                "irrecoverableDebtsDisallowable": 0,
                "professionalFeesDisallowable": 0,
                "depreciationDisallowable": round(expenses.get("depreciation", 0), 2),  # Amortisman indirimli değil
                "otherDisallowable": 0
            },
            "allowances": {
                "annualInvestmentAllowance": 0,
                "capitalAllowanceMainPool": 0,
                "capitalAllowanceSpecialRatePool": 0,
                "zeroEmissionGoodsVehicleAllowance": 0,
                "businessPremisesRenovationAllowance": 0,
                "enhancedCapitalAllowance": 0,
                "allowanceOnSales": 0
            }
        }
        
        return self_employment_data
    
    def prepare_property_data(self, tax_year, property_type="uk-property", property_id=None):
        """
        Mülk verilerini hazırla
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
            property_type: Mülk tipi ('uk-property' veya 'foreign-property')
            property_id: Mülk ID'si (opsiyonel, mevcut değilse yeni oluşturulur)
        
        Returns:
            HMRC API için hazırlanmış mülk verileri
        """
        # Vergi yılı başlangıç ve bitiş tarihlerini hesapla
        start_year = int(tax_year.split("-")[0])
        start_date = f"{start_year}-04-06"
        end_date = f"{start_year + 1}-04-05"
        
        # Bu dönemdeki işlemleri filtrele
        transactions = self.db.filter_transactions(
            start_date=start_date,
            end_date=end_date
        )
        
        # Mülk hesaplarını filtrele
        chart_of_accounts = self.db.get_chart_of_accounts()
        property_accounts = []
        for account in chart_of_accounts:
            if (property_type == "uk-property" and account.get("uk_property", False)) or \
               (property_type == "foreign-property" and account.get("foreign_property", False)):
                property_accounts.append(account.get("code"))
        
        # Mülk gelirleri ve giderleri
        income = 0
        expenses = {}
        
        for transaction in transactions:
            for entry in transaction.get("entries", []):
                account_code = entry.get("account_code")
                if account_code in property_accounts:
                    amount = entry.get("amount", 0)
                    account = self.db.get_account_by_code(account_code)
                    
                    # Gelir hesabı mı?
                    if account.get("type") == "income":
                        if entry.get("type") == "credit":
                            income += amount
                        else:
                            income -= amount
                    # Gider hesabı mı?
                    elif account.get("type") == "expense":
                        category = account.get("category", "other")
                        if category not in expenses:
                            expenses[category] = 0
                        
                        if entry.get("type") == "debit":
                            expenses[category] += amount
                        else:
                            expenses[category] -= amount
        
        # Mülk ID'sini hazırla
        if not property_id:
            property_id = str(uuid.uuid4())
        
        # HMRC API formatında mülk verileri
        property_data = {
            "propertyId": property_id,
            "propertyType": "FHL" if property_type == "uk-property" and self.db.get_company_info().get("is_furnished_holiday_let", False) else "NON-FHL",
            "isPropertyForeignCountryLet": property_type == "foreign-property",
            "propertyAddressLineOne": self.db.get_company_info().get("property_address_line1", ""),
            "propertyAddressLineTwo": self.db.get_company_info().get("property_address_line2", ""),
            "propertyAddressLineThree": self.db.get_company_info().get("property_address_line3", ""),
            "propertyAddressLineFour": self.db.get_company_info().get("property_address_line4", ""),
            "propertyAddressPostcode": self.db.get_company_info().get("property_postcode", ""),
            "propertyAddressCountryCode": "GB" if property_type == "uk-property" else self.db.get_company_info().get("property_country", ""),
            "accountingPeriodStartDate": start_date,
            "accountingPeriodEndDate": end_date,
            "cashOrAccruals": "ACCRUALS",
            "income": {
                "rentIncome": round(income, 2),
                "premiumsOfLeaseGrant": 0,
                "reversePremiums": 0,
                "otherPropertyIncome": 0
            },
            "expenses": {
                "premisesRunningCosts": round(expenses.get("premises", 0), 2),
                "repairsAndMaintenance": round(expenses.get("maintenance", 0), 2),
                "financialCosts": round(expenses.get("finance", 0), 2),
                "professionalFees": round(expenses.get("professional", 0), 2),
                "costOfServices": round(expenses.get("services", 0), 2),
                "other": round(expenses.get("other", 0), 2)
            },
            "allowances": {
                "annualInvestmentAllowance": 0,
                "otherCapitalAllowance": 0,
                "electricChargePointAllowance": 0,
                "zeroEmissionsCarAllowance": 0
            },
            "adjustments": {
                "privateUseAdjustment": 0,
                "balancingCharge": 0,
                "propertyIncomeAllowance": 0
            }
        }
        
        return property_data
    
    def prepare_dividends_data(self, tax_year):
        """
        Temettü verilerini hazırla
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
        
        Returns:
            HMRC API için hazırlanmış temettü verileri
        """
        # Vergi yılı başlangıç ve bitiş tarihlerini hesapla
        start_year = int(tax_year.split("-")[0])
        start_date = f"{start_year}-04-06"
        end_date = f"{start_year + 1}-04-05"
        
        # Bu dönemdeki işlemleri filtrele
        transactions = self.db.filter_transactions(
            start_date=start_date,
            end_date=end_date
        )
        
        # Temettü hesaplarını filtrele
        chart_of_accounts = self.db.get_chart_of_accounts()
        dividend_accounts = []
        for account in chart_of_accounts:
            if account.get("dividend", False):
                dividend_accounts.append(account.get("code"))
        
        # Temettü gelirlerini topla
        uk_dividends = 0
        other_dividends = 0
        
        for transaction in transactions:
            for entry in transaction.get("entries", []):
                account_code = entry.get("account_code")
                if account_code in dividend_accounts:
                    amount = entry.get("amount", 0)
                    account = self.db.get_account_by_code(account_code)
                    
                    # Gelir hesabı mı?
                    if account.get("type") == "income":
                        # UK temettüsü mü yoksa diğer mi?
                        if account.get("uk_dividend", True):
                            if entry.get("type") == "credit":
                                uk_dividends += amount
                            else:
                                uk_dividends -= amount
                        else:
                            if entry.get("type") == "credit":
                                other_dividends += amount
                            else:
                                other_dividends -= amount
        
        # HMRC API formatında temettü verileri
        dividend_data = {
            "ukDividends": round(uk_dividends, 2),
            "otherUkDividends": round(other_dividends, 2)
        }
        
        return dividend_data
    
    def save_tax_return(self, tax_year, tax_calculation, status="draft"):
        """
        Vergi beyanını veritabanına kaydet
        
        Args:
            tax_year: Vergi yılı
            tax_calculation: Vergi hesaplaması verileri
            status: Beyan durumu ("draft", "submitted", "accepted")
        
        Returns:
            Eklenen beyan ID'si
        """
        # Beyan nesnesini oluştur
        tax_return = {
            "id": None,  # Veritabanı tarafından atanacak
            "tax_year": tax_year,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": status,
            "submission_date": datetime.now().isoformat() if status == "submitted" else None,
            "data": tax_calculation
        }
        
        # Veritabanına kaydet
        return self.db.add_tax_return(tax_return)
    
    def get_tax_return(self, tax_return_id):
        """
        Vergi beyanını getir
        
        Args:
            tax_return_id: Vergi beyanı ID'si
        
        Returns:
            Vergi beyanı verisi
        """
        return self.db.get_tax_return_by_id(tax_return_id)
    
    def update_tax_return_status(self, tax_return_id, status, submission_data=None):
        """
        Vergi beyanı durumunu güncelle
        
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
    
    def get_income_data_for_tax_year(self, tax_year):
        """
        Vergi yılı için gelir verilerini topla
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
        
        Returns:
            Gelir vergileri hesaplaması için veri
        """
        # Vergi yılı başlangıç ve bitiş tarihlerini hesapla
        start_year = int(tax_year.split("-")[0])
        start_date = f"{start_year}-04-06"
        end_date = f"{start_year + 1}-04-05"
        
        # Toplam gelir ve gider hesaplamalarını sıfırla
        income_data = {
            "employment_income": 0,
            "self_employment_income": 0,
            "property_income": 0,
            "dividends": 0,
            "pension_contributions": 0,
            "gift_aid_donations": 0,
            "other_deductions": 0
        }
        
        # Bu dönemdeki işlemleri filtrele
        transactions = self.db.filter_transactions(
            start_date=start_date,
            end_date=end_date
        )
        
        # Hesap planını al
        chart_of_accounts = self.db.get_chart_of_accounts()
        
        # Her işlemi kategorize et
        for transaction in transactions:
            for entry in transaction.get("entries", []):
                account_code = entry.get("account_code")
                account = self.db.get_account_by_code(account_code)
                
                if not account:
                    continue
                
                amount = entry.get("amount", 0)
                account_type = account.get("type")
                
                # Gelir hesabı mı?
                if account_type == "income":
                    # Gelir tipini belirle
                    if account.get("employment", False):
                        if entry.get("type") == "credit":
                            income_data["employment_income"] += amount
                        else:
                            income_data["employment_income"] -= amount
                    
                    elif account.get("self_employment", False):
                        if entry.get("type") == "credit":
                            income_data["self_employment_income"] += amount
                        else:
                            income_data["self_employment_income"] -= amount
                    
                    elif account.get("uk_property", False) or account.get("foreign_property", False):
                        if entry.get("type") == "credit":
                            income_data["property_income"] += amount
                        else:
                            income_data["property_income"] -= amount
                    
                    elif account.get("dividend", False):
                        if entry.get("type") == "credit":
                            income_data["dividends"] += amount
                        else:
                            income_data["dividends"] -= amount
                
                # Gider hesabı mı? (indirimler)
                elif account_type == "expense":
                    # Gider tipini belirle
                    if account.get("pension", False):
                        if entry.get("type") == "debit":
                            income_data["pension_contributions"] += amount
                        else:
                            income_data["pension_contributions"] -= amount
                    
                    elif account.get("gift_aid", False):
                        if entry.get("type") == "debit":
                            income_data["gift_aid_donations"] += amount
                        else:
                            income_data["gift_aid_donations"] -= amount
                    
                    elif account.get("tax_deduction", False):
                        if entry.get("type") == "debit":
                            income_data["other_deductions"] += amount
                        else:
                            income_data["other_deductions"] -= amount
        
        # Tüm değerleri yuvarla
        for key in income_data:
            income_data[key] = round(income_data[key], 2)
        
        return income_data
    
    def generate_tax_summary(self, tax_year):
        """
        Vergi yılı için özet vergi raporu oluştur
        
        Args:
            tax_year: Vergi yılı (YYYY-YY formatında)
        
        Returns:
            Vergi özet raporu
        """
        # Gelir verilerini topla
        income_data = self.get_income_data_for_tax_year(tax_year)
        
        # Vergiyi hesapla
        tax_calculation = self.calculate_income_tax(tax_year, income_data)
        
        # Özel modül verilerini hazırla
        self_employment_data = self.prepare_self_employment_data(tax_year)
        uk_property_data = self.prepare_property_data(tax_year, "uk-property")
        dividend_data = self.prepare_dividends_data(tax_year)
        
        # Özet rapor
        summary = {
            "tax_year": tax_year,
            "generated_at": datetime.now().isoformat(),
            "income_summary": {
                "total_income": tax_calculation["total_income"],
                "taxable_income": tax_calculation["taxable_income"],
                "breakdown": {
                    "employment": income_data["employment_income"],
                    "self_employment": income_data["self_employment_income"],
                    "property": income_data["property_income"],
                    "dividends": income_data["dividends"],
                }
            },
            "deductions_summary": {
                "total_deductions": tax_calculation["total_deductions"],
                "breakdown": {
                    "personal_allowance": tax_calculation["personal_allowance"],
                    "pension_contributions": income_data["pension_contributions"],
                    "gift_aid_donations": income_data["gift_aid_donations"],
                    "other_deductions": income_data["other_deductions"]
                }
            },
            "tax_summary": {
                "income_tax": tax_calculation["income_tax"],
                "dividend_tax": tax_calculation["dividend_tax"],
                "national_insurance": tax_calculation["national_insurance"]["total"],
                "total_tax": tax_calculation["total_tax_and_ni"]
            },
            "self_employment_summary": {
                "income": self_employment_data["income"]["turnover"],
                "expenses": sum(self_employment_data["expenses"].values()),
                "profit": self_employment_data["income"]["turnover"] - sum(self_employment_data["expenses"].values())
            },
            "property_summary": {
                "income": uk_property_data["income"]["rentIncome"],
                "expenses": sum(uk_property_data["expenses"].values()),
                "profit": uk_property_data["income"]["rentIncome"] - sum(uk_property_data["expenses"].values())
            }
        }
        
        return summary
