#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Wise API İstemcisi
Wise (TransferWise) hesapları ve işlemleri için API istemcisi.
"""

import requests
import json
import time
import base64
import logging
from datetime import datetime, timedelta

class WiseAPIClient:
    """Wise API istemcisi"""
    
    # API URL'leri
    SANDBOX_API_URL = "https://api.sandbox.transferwise.tech"
    PRODUCTION_API_URL = "https://api.wise.com"
    
    def __init__(self, api_token, profile_id=None, is_sandbox=False):
        """API istemcisi başlatıcı
        
        Args:
            api_token: Wise API token (Personal token)
            profile_id: Profil ID (Opsiyonel, sonradan da ayarlanabilir)
            is_sandbox: Sandbox modu (Test için True, Gerçek için False)
        """
        self.api_token = api_token
        self.profile_id = profile_id
        self.base_url = self.SANDBOX_API_URL if is_sandbox else self.PRODUCTION_API_URL
        self.logger = logging.getLogger(__name__)
        
    def set_profile_id(self, profile_id):
        """Profil ID'sini ayarla"""
        self.profile_id = profile_id
        
    def get_headers(self):
        """API istekleri için header'ları oluştur"""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
    
    def get_profiles(self):
        """Kullanıcının profillerini al"""
        url = f"{self.base_url}/v1/profiles"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Wise API profil alınırken hata: {e}")
            return None
    
    def get_accounts(self):
        """Kullanıcının banka hesaplarını al
        
        Returns:
            list: Hesap nesnelerinin listesi
        """
        if not self.profile_id:
            self.logger.error("Hesapları almak için önce profile_id ayarlanmalıdır")
            return None
        
        url = f"{self.base_url}/v1/borderless-accounts?profileId={self.profile_id}"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Wise API hesaplar alınırken hata: {e}")
            return None
    
    def get_account_balances(self, account_id):
        """Belirli bir hesabın bakiyelerini al
        
        Args:
            account_id: Hesap ID
            
        Returns:
            list: Para birimi bazında bakiye nesnelerinin listesi
        """
        url = f"{self.base_url}/v1/borderless-accounts/{account_id}/balances"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Wise API bakiyeler alınırken hata: {e}")
            return None
    
    def get_account_statement(self, account_id, currency, start_date, end_date=None):
        """Hesap ekstresini al
        
        Args:
            account_id: Hesap ID
            currency: Para birimi kodu (GBP, EUR, USD, vb.)
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            end_date: Bitiş tarihi (YYYY-MM-DD formatında, None ise bugün)
            
        Returns:
            dict: Ekstresi verisi
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        url = f"{self.base_url}/v1/borderless-accounts/{account_id}/statements/{currency}"
        params = {
            "intervalStart": start_date,
            "intervalEnd": end_date
        }
        
        try:
            response = requests.get(url, headers=self.get_headers(), params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Wise API ekstresi alınırken hata: {e}")
            return None
    
    def get_statement_pdf(self, account_id, statement_id):
        """Hesap ekstresini PDF olarak al
        
        Args:
            account_id: Hesap ID
            statement_id: Ekstre ID
            
        Returns:
            bytes: PDF verisi
        """
        url = f"{self.base_url}/v1/borderless-accounts/{account_id}/statements/{statement_id}"
        
        try:
            response = requests.get(url, headers=self.get_headers())
            response.raise_for_status()
            return response.content
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Wise API ekstre PDF'i alınırken hata: {e}")
            return None
    
    def get_transactions(self, account_id, currency, start_date, end_date=None):
        """Hesap işlemlerini al
        
        Args:
            account_id: Hesap ID
            currency: Para birimi kodu (GBP, EUR, USD, vb.)
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            end_date: Bitiş tarihi (YYYY-MM-DD formatında, None ise bugün)
            
        Returns:
            list: İşlem nesnelerinin listesi
        """
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        url = f"{self.base_url}/v1/borderless-accounts/{account_id}/transactions"
        params = {
            "currency": currency,
            "intervalStart": f"{start_date}T00:00:00.000Z",
            "intervalEnd": f"{end_date}T23:59:59.999Z"
        }
        
        try:
            response = requests.get(url, headers=self.get_headers(), params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Wise API işlemler alınırken hata: {e}")
            return None
    
    def get_exchange_rates(self, source_currency, target_currency, from_date=None, to_date=None):
        """Döviz kurlarını al
        
        Args:
            source_currency: Kaynak para birimi (GBP, EUR, USD, vb.)
            target_currency: Hedef para birimi
            from_date: Başlangıç tarihi (YYYY-MM-DD formatında, None ise 7 gün önce)
            to_date: Bitiş tarihi (YYYY-MM-DD formatında, None ise bugün)
            
        Returns:
            list: Döviz kuru nesnelerinin listesi
        """
        if not from_date:
            from_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")
            
        url = f"{self.base_url}/v1/rates"
        params = {
            "source": source_currency,
            "target": target_currency,
            "from": from_date,
            "to": to_date
        }
        
        try:
            response = requests.get(url, headers=self.get_headers(), params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Wise API döviz kurları alınırken hata: {e}")
            return None
