#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - HMRC API İstemcisi
Making Tax Digital (MTD) için HMRC API entegrasyonu.
"""

import requests
import json
import base64
import time
import uuid
import logging
from urllib.parse import urlencode
from datetime import datetime, timedelta


class HMRCApiClient:
    """HMRC API istemcisi"""
    
    def __init__(self, client_id, client_secret, endpoint, redirect_uri):
        """İstemci başlatıcı
        
        Args:
            client_id: HMRC Developer Hub üzerinden alınan client ID
            client_secret: HMRC Developer Hub üzerinden alınan client secret
            endpoint: API endpoint URL (prod veya test)
            redirect_uri: Yetkilendirme sonrası yönlendirilecek URL
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.endpoint = endpoint.rstrip('/')
        self.redirect_uri = redirect_uri
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.logger = logging.getLogger(__name__)
    
    def update_config(self, client_id=None, client_secret=None, endpoint=None, redirect_uri=None):
        """Yapılandırma bilgilerini güncelle"""
        if client_id:
            self.client_id = client_id
        if client_secret:
            self.client_secret = client_secret
        if endpoint:
            self.endpoint = endpoint.rstrip('/')
        if redirect_uri:
            self.redirect_uri = redirect_uri
    
    def get_auth_url(self):
        """HMRC yetkilendirme URL'sini oluştur"""
        if not self.client_id or not self.redirect_uri:
            raise ValueError("Client ID ve Redirect URI tanımlanmalıdır")
        
        # MTD-VAT ve MTD-INCOME-TAX için kapsamlar
        scopes = [
            "read:vat",
            "write:vat",
            "read:self-assessment",
            "write:self-assessment"
        ]
        
        # OAuth 2.0 yetkilendirme parametreleri
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(scopes),
            "state": str(uuid.uuid4())  # CSRF koruması için rastgele string
        }
        
        # Yetkilendirme URL'sini oluştur
        auth_url = f"{self.endpoint}/oauth/authorize?{urlencode(params)}"
        self.logger.info(f"HMRC OAuth URL oluşturuldu: {auth_url}")
        
        return auth_url
    
    def exchange_code_for_tokens(self, auth_code):
        """Yetkilendirme kodunu token'lar ile değiştir
        
        Args:
            auth_code: Yetkilendirme sonrası alınan kod
            
        Returns:
            bool: Token alımı başarılı mı?
        """
        if not auth_code:
            raise ValueError("Yetkilendirme kodu gereklidir")
        
        # Token URL'si
        token_url = f"{self.endpoint}/oauth/token"
        
        # İstek parametreleri
        payload = {
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": self.redirect_uri,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        # Basic auth için istemci bilgilerini kodla
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        # HTTP isteği gönder
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_header}"
        }
        
        try:
            response = requests.post(token_url, data=payload, headers=headers)
            response.raise_for_status()  # HTTP hata kontrolü
            
            # Yanıtı JSON olarak ayrıştır
            token_data = response.json()
            
            # Token bilgilerini sakla
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token")
            expires_in = token_data.get("expires_in", 3600)  # Varsayılan 1 saat
            
            # Token son kullanma tarihini hesapla
            self.token_expires_at = time.time() + expires_in
            
            self.logger.info("HMRC API için token alındı")
            return True
            
        except requests.RequestException as e:
            self.logger.error(f"Token alımında hata: {e}")
            return False
    
    def refresh_access_token(self):
        """Yenileme token'ı ile erişim token'ını yenile
        
        Returns:
            bool: Token yenileme başarılı mı?
        """
        if not self.refresh_token:
            self.logger.error("Yenileme token'ı mevcut değil")
            return False
        
        # Token URL'si
        token_url = f"{self.endpoint}/oauth/token"
        
        # İstek parametreleri
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        # Basic auth için istemci bilgilerini kodla
        auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        
        # HTTP isteği gönder
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {auth_header}"
        }
        
        try:
            response = requests.post(token_url, data=payload, headers=headers)
            response.raise_for_status()  # HTTP hata kontrolü
            
            # Yanıtı JSON olarak ayrıştır
            token_data = response.json()
            
            # Token bilgilerini güncelle
            self.access_token = token_data.get("access_token")
            self.refresh_token = token_data.get("refresh_token", self.refresh_token)  # Yeni yenileme token'ı yoksa eskisini kullan
            expires_in = token_data.get("expires_in", 3600)  # Varsayılan 1 saat
            
            # Token son kullanma tarihini güncelle
            self.token_expires_at = time.time() + expires_in
            
            self.logger.info("HMRC API için token yenilendi")
            return True
            
        except requests.RequestException as e:
            self.logger.error(f"Token yenilemede hata: {e}")
            return False
    
    def ensure_token_valid(self):
        """Token'ın geçerli olduğundan emin ol, gerekirse yenile
        
        Returns:
            bool: Geçerli token var mı?
        """
        # Token yok veya süresi dolmak üzere mi?
        if not self.access_token or not self.token_expires_at:
            self.logger.warning("Token mevcut değil")
            return False
        
        # Token'ın süresi dolmak üzere mi? (5 dakika marj bırak)
        if time.time() > (self.token_expires_at - 300):
            self.logger.info("Token süresi dolmak üzere, yenileniyor...")
            return self.refresh_access_token()
        
        return True
    
    def _make_api_request(self, method, path, data=None, params=None, headers=None):
        """HMRC API'ye istek gönder
        
        Args:
            method: HTTP metodu ('GET', 'POST', vb.)
            path: API yolu ('/organisations/vat/...' gibi)
            data: İstek gövdesi (dict olarak)
            params: URL parametreleri (dict olarak)
            headers: İlave HTTP başlıkları
            
        Returns:
            dict: API yanıtı
            
        Raises:
            ValueError: Token geçersiz veya eksik
            requests.RequestException: API isteği başarısız
        """
        # Token'ın geçerli olduğundan emin ol
        if not self.ensure_token_valid():
            raise ValueError("Geçerli token mevcut değil")
        
        # Tam URL oluştur
        url = f"{self.endpoint}{path}"
        
        # Varsayılan başlıklar
        default_headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/vnd.hmrc.1.0+json",
            "Content-Type": "application/json"
        }
        
        # Özel başlıkları varsayılanlarla birleştir
        if headers:
            default_headers.update(headers)
        
        # İstek gövdesini JSON'a dönüştür (varsa)
        json_data = json.dumps(data) if data else None
        
        try:
            # İsteği gönder
            response = requests.request(
                method=method,
                url=url,
                headers=default_headers,
                params=params,
                data=json_data
            )
            
            # HTTP durum kodunu kontrol et
            response.raise_for_status()
            
            # Yanıt JSON ise ayrıştır
            if response.headers.get('Content-Type', '').startswith('application/json'):
                return response.json()
            
            # JSON değilse metin olarak döndür
            return {"status": "success", "text": response.text}
            
        except requests.RequestException as e:
            self.logger.error(f"API isteği başarısız: {e}")
            
            # Hata yanıtını ayrıştırmaya çalış
            error_message = str(e)
            if hasattr(e, 'response') and e.response:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get('message', str(e))
                except:
                    pass
            
            raise requests.RequestException(f"HMRC API hatası: {error_message}")
    
    # VAT API Metodları
    
    def get_vat_obligations(self, vrn, from_date, to_date, status="O"):
        """VAT yükümlülüklerini al
        
        Args:
            vrn: VAT Kayıt Numarası
            from_date: Başlangıç tarihi (YYYY-MM-DD)
            to_date: Bitiş tarihi (YYYY-MM-DD)
            status: Yükümlülük durumu ('O' açık, 'F' tamamlanmış)
            
        Returns:
            dict: Yükümlülük bilgileri
        """
        path = f"/organisations/vat/{vrn}/obligations"
        params = {
            "from": from_date,
            "to": to_date,
            "status": status
        }
        
        return self._make_api_request("GET", path, params=params)
    
    def submit_vat_return(self, vrn, period_key, vat_data):
        """VAT beyannamesi gönder
        
        Args:
            vrn: VAT Kayıt Numarası
            period_key: Dönem anahtarı (obligations'dan alınır)
            vat_data: VAT beyanname verileri
            
        Returns:
            dict: Gönderim sonucu
        """
        path = f"/organisations/vat/{vrn}/returns"
        
        # Zorunlu VAT beyanname alanları
        required_fields = [
            "vatDueSales", "vatDueAcquisitions", "totalVatDue", "vatReclaimedCurrPeriod",
            "netVatDue", "totalValueSalesExVAT", "totalValuePurchasesExVAT", 
            "totalValueGoodsSuppliedExVAT", "totalAcquisitionsExVAT", "finalised"
        ]
        
        # Eksik alanları kontrol et
        for field in required_fields:
            if field not in vat_data:
                raise ValueError(f"Eksik VAT beyanname alanı: {field}")
        
        # Zorunlu 'finalised' alanını kontrol et
        if not vat_data.get("finalised", False):
            raise ValueError("VAT beyannamesi 'finalised' olarak işaretlenmelidir")
        
        # Period key ekleyin
        vat_data["periodKey"] = period_key
        
        return self._make_api_request("POST", path, data=vat_data)
    
    def get_vat_liabilities(self, vrn, from_date, to_date):
        """VAT borçlarını al
        
        Args:
            vrn: VAT Kayıt Numarası
            from_date: Başlangıç tarihi (YYYY-MM-DD)
            to_date: Bitiş tarihi (YYYY-MM-DD)
            
        Returns:
            dict: Borç bilgileri
        """
        path = f"/organisations/vat/{vrn}/liabilities"
        params = {
            "from": from_date,
            "to": to_date
        }
        
        return self._make_api_request("GET", path, params=params)
    
    def get_vat_payments(self, vrn, from_date, to_date):
        """VAT ödemelerini al
        
        Args:
            vrn: VAT Kayıt Numarası
            from_date: Başlangıç tarihi (YYYY-MM-DD)
            to_date: Bitiş tarihi (YYYY-MM-DD)
            
        Returns:
            dict: Ödeme bilgileri
        """
        path = f"/organisations/vat/{vrn}/payments"
        params = {
            "from": from_date,
            "to": to_date
        }
        
        return self._make_api_request("GET", path, params=params)
    
    # Self Assessment API Metodları
    
    def get_self_assessment_obligations(self, utr, from_date, to_date):
        """Self Assessment yükümlülüklerini al
        
        Args:
            utr: Unique Taxpayer Reference
            from_date: Başlangıç tarihi (YYYY-MM-DD)
            to_date: Bitiş tarihi (YYYY-MM-DD)
            
        Returns:
            dict: Yükümlülük bilgileri
        """
        path = f"/self-assessment/ni/{utr}/self-employments/obligations"
        params = {
            "from": from_date,
            "to": to_date
        }
        
        return self._make_api_request("GET", path, params=params)
    
    def submit_self_employment_period(self, utr, tax_year, period_data):
        """Self Employment dönem verilerini gönder
        
        Args:
            utr: Unique Taxpayer Reference
            tax_year: Vergi yılı (örn: "2022-23")
            period_data: Dönem verileri
            
        Returns:
            dict: Gönderim sonucu
        """
        path = f"/self-assessment/ni/{utr}/self-employments/{tax_year}/periods"
        
        # Zorunlu alanları kontrol et
        required_fields = ["from", "to", "incomes", "expenses"]
        
        for field in required_fields:
            if field not in period_data:
                raise ValueError(f"Eksik Self Employment dönem alanı: {field}")
        
        return self._make_api_request("POST", path, data=period_data)
    
    def submit_final_declaration(self, utr, tax_year, declaration_data):
        """Nihai beyanı gönder
        
        Args:
            utr: Unique Taxpayer Reference
            tax_year: Vergi yılı (örn: "2022-23")
            declaration_data: Beyan verileri
            
        Returns:
            dict: Gönderim sonucu
        """
        path = f"/self-assessment/ni/{utr}/self-employments/{tax_year}/declaration"
        
        return self._make_api_request("POST", path, data=declaration_data)
