#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - HMRC MTD (Making Tax Digital) Modülü
HMRC MTD API ile etkileşim için temel sınıf ve fonksiyonlar.
"""

import requests
import logging
import json
import base64
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path
import webbrowser
import time
import socket
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Loglayıcıyı yapılandır
logger = logging.getLogger(__name__)

class MTDAuth:
    """HMRC MTD OAuth2 yetkilendirme ve yenileme işleyicisi"""
    
    def __init__(self, client_id, client_secret, redirect_uri, config_file=None):
        """
        HMRC MTD OAuth2 yetkilendirme yöneticisini başlat
        
        Args:
            client_id: HMRC Developer hesabından alınan client ID
            client_secret: HMRC Developer hesabından alınan client secret
            redirect_uri: Yönlendirme URI (callback URL)
            config_file: Token bilgilerinin saklanacağı yapılandırma dosyası
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.config_file = Path(config_file) if config_file else None
        
        # HMRC OAuth2 uç noktaları
        self.auth_url = "https://test.api.service.hmrc.gov.uk/oauth/authorize" # Test ortamı
        self.token_url = "https://test.api.service.hmrc.gov.uk/oauth/token" # Test ortamı
        
        # Canlı ortam için bu URL'leri kullanın
        # self.auth_url = "https://api.service.hmrc.gov.uk/oauth/authorize"
        # self.token_url = "https://api.service.hmrc.gov.uk/oauth/token"
        
        # Token bilgilerini saklamak için değişkenler
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # Yapılandırma dosyasından token bilgilerini yükle
        self._load_tokens()
    
    def _load_tokens(self):
        """Yapılandırma dosyasından kayıtlı token bilgilerini yükle"""
        if not self.config_file or not self.config_file.exists():
            return
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.access_token = config.get('access_token')
                self.refresh_token = config.get('refresh_token')
                expires_at = config.get('token_expires_at')
                self.token_expires_at = datetime.fromisoformat(expires_at) if expires_at else None
                
                logger.info("Token bilgileri yapılandırma dosyasından yüklendi")
        except Exception as e:
            logger.error(f"Token bilgileri yüklenirken hata: {e}")
    
    def _save_tokens(self):
        """Token bilgilerini yapılandırma dosyasına kaydet"""
        if not self.config_file:
            return
        
        try:
            config = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'token_expires_at': self.token_expires_at.isoformat() if self.token_expires_at else None
            }
            
            # Dizini oluştur
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
            logger.info("Token bilgileri yapılandırma dosyasına kaydedildi")
        except Exception as e:
            logger.error(f"Token bilgileri kaydedilirken hata: {e}")
    
    def is_authenticated(self):
        """Kimlik doğrulama durumunu kontrol et"""
        if not self.access_token or not self.token_expires_at:
            return False
        
        # Token süresi dolmuş mu kontrol et (5 dakika güvenlik payı ile)
        return datetime.now() < (self.token_expires_at - timedelta(minutes=5))
    
    def refresh_auth_tokens(self):
        """Yenileme token'ını kullanarak access token'ını yenile"""
        if not self.refresh_token:
            logger.error("Yenileme tokeni yok, önce kimlik doğrulama yapın")
            return False
        
        try:
            # Token yenileme isteği gönder
            auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token
            }
            
            response = requests.post(
                self.token_url,
                headers=headers,
                data=data
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 14400)  # 4 saat varsayılan
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                # Token'ları kaydet
                self._save_tokens()
                
                logger.info("Access token başarıyla yenilendi")
                return True
            else:
                logger.error(f"Token yenileme hatası: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Token yenileme sırasında hata: {e}")
            return False
    
    def get_authorization_url(self, scopes):
        """
        HMRC yetkilendirme URL'sini oluştur
        
        Args:
            scopes: İstenilen erişim izinleri listesi 
                   (örn. ["read:vat", "write:vat"])
        
        Returns:
            Yetkilendirme URL'si
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes)
        }
        
        auth_url = f"{self.auth_url}?{urllib.parse.urlencode(params)}"
        return auth_url
    
    def open_auth_page(self, scopes):
        """
        Kullanıcıyı HMRC yetkilendirme sayfasına yönlendir
        
        Args:
            scopes: İstenilen erişim izinleri listesi
        """
        auth_url = self.get_authorization_url(scopes)
        webbrowser.open(auth_url)
        
        return auth_url
    
    class CallbackHandler(BaseHTTPRequestHandler):
        """Yetkilendirme kodunu almak için callback işleyicisi"""
        
        def __init__(self, *args, auth_callback=None, **kwargs):
            self.auth_callback = auth_callback
            super().__init__(*args, **kwargs)
        
        def do_GET(self):
            """GET isteğini işle ve yetkilendirme kodunu çıkar"""
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            query = urllib.parse.urlparse(self.path).query
            params = urllib.parse.parse_qs(query)
            
            auth_code = params.get('code', [''])[0]
            error = params.get('error', [''])[0]
            
            if auth_code:
                self.wfile.write(b"<html><head><title>Authentication Successful</title></head>")
                self.wfile.write(b"<body><h1>Authentication Successful!</h1>")
                self.wfile.write(b"<p>You can now close this window and return to the application.</p></body></html>")
                
                if self.auth_callback:
                    self.auth_callback(auth_code)
            else:
                self.wfile.write(b"<html><head><title>Authentication Failed</title></head>")
                self.wfile.write(b"<body><h1>Authentication Failed</h1>")
                self.wfile.write(f"<p>Error: {error}</p></body></html>".encode())
    
    def start_auth_server(self, callback_port=8000):
        """
        Yetkilendirme kodunu almak için yerel sunucuyu başlat
        
        Args:
            callback_port: Callback için kullanılacak yerel port
        
        Returns:
            HTTPServer nesnesi
        """
        # Özel handler sınıfını oluştur
        def handler_factory(*args, **kwargs):
            return self.CallbackHandler(*args, auth_callback=self.process_auth_code, **kwargs)
        
        # Sunucuyu başlat
        server = HTTPServer(('localhost', callback_port), handler_factory)
        
        return server
    
    def process_auth_code(self, auth_code):
        """
        Yetkilendirme kodunu işle ve token al
        
        Args:
            auth_code: HMRC'den alınan yetkilendirme kodu
        
        Returns:
            İşlem başarılı ise True, değilse False
        """
        try:
            # Temel kimlik doğrulama başlığını oluştur
            auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            
            headers = {
                "Authorization": f"Basic {auth_header}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": self.redirect_uri
            }
            
            response = requests.post(
                self.token_url,
                headers=headers,
                data=data
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get("access_token")
                self.refresh_token = token_data.get("refresh_token")
                expires_in = token_data.get("expires_in", 14400)  # 4 saat varsayılan
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
                
                # Token'ları kaydet
                self._save_tokens()
                
                logger.info("Kimlik doğrulama başarılı")
                return True
            else:
                logger.error(f"Token alınırken hata: {response.status_code} - {response.text}")
                return False
        
        except Exception as e:
            logger.error(f"Token işleme sırasında hata: {e}")
            return False
    
    def authenticate(self, scopes):
        """
        Tam yetkilendirme sürecini başlat
        
        Args:
            scopes: İstenilen erişim izinleri listesi
        
        Returns:
            İşlem başarılı ise True, değilse False
        """
        # Zaten kimlik doğrulanmış mı kontrol et
        if self.is_authenticated():
            logger.info("Zaten kimlik doğrulanmış")
            return True
        
        # Yenileme token'ı varsa, onu kullanmayı dene
        if self.refresh_token:
            success = self.refresh_auth_tokens()
            if success:
                return True
        
        try:
            # Callback sunucusunu başlat
            callback_parts = urllib.parse.urlparse(self.redirect_uri)
            callback_port = callback_parts.port or 8000
            
            server = self.start_auth_server(callback_port)
            
            # Sunucuyu ayrı bir thread'de çalıştır
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            # Yetkilendirme URL'sini aç
            self.open_auth_page(scopes)
            
            # Kullanıcıdan yetkilendirme tamamlandığında bir girdi bekle
            input("HMRC yetkilendirme sayfasını tamamladıktan sonra Enter tuşuna basın...")
            
            # Sunucuyu durdur
            server.shutdown()
            server_thread.join()
            
            return self.is_authenticated()
        
        except Exception as e:
            logger.error(f"Kimlik doğrulama sırasında hata: {e}")
            return False
    
    def get_access_token(self):
        """Gerekirse token'ı yenileyerek geçerli access token'ını döndür"""
        if not self.is_authenticated():
            if self.refresh_token:
                success = self.refresh_auth_tokens()
                if not success:
                    return None
            else:
                return None
        
        return self.access_token


class MTDClient:
    """HMRC MTD API istemcisi"""
    
    def __init__(self, auth_manager, test_mode=True):
        """
        MTD API istemcisini başlat
        
        Args:
            auth_manager: MTDAuth yetkilendirme yöneticisi
            test_mode: Test ortamını mı kullanılacak?
        """
        self.auth = auth_manager
        self.test_mode = test_mode
        
        # API tabanı URL'leri
        if test_mode:
            self.api_base_url = "https://test.api.service.hmrc.gov.uk"
        else:
            self.api_base_url = "https://api.service.hmrc.gov.uk"
    
    def _get_headers(self):
        """API isteği için başlıkları oluştur"""
        access_token = self.auth.get_access_token()
        if not access_token:
            raise ValueError("Geçerli erişim token'ı yok, önce kimlik doğrulama yapın")
        
        return {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.hmrc.1.0+json",
            "Content-Type": "application/json"
        }
    
    def get(self, endpoint, params=None):
        """
        GET isteği gönder
        
        Args:
            endpoint: API uç noktası (/ ile başlamalı)
            params: URL parametreleri (opsiyonel)
        
        Returns:
            API yanıtı
        """
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            headers = self._get_headers()
            response = requests.get(url, headers=headers, params=params)
            
            # İsteği logla
            logger.debug(f"GET {url} - Durum Kodu: {response.status_code}")
            
            return self._handle_response(response)
        
        except Exception as e:
            logger.error(f"GET isteği sırasında hata: {e}")
            raise
    
    def post(self, endpoint, data):
        """
        POST isteği gönder
        
        Args:
            endpoint: API uç noktası (/ ile başlamalı)
            data: Gönderilecek veri
        
        Returns:
            API yanıtı
        """
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            headers = self._get_headers()
            json_data = json.dumps(data)
            response = requests.post(url, headers=headers, data=json_data)
            
            # İsteği logla
            logger.debug(f"POST {url} - Durum Kodu: {response.status_code}")
            
            return self._handle_response(response)
        
        except Exception as e:
            logger.error(f"POST isteği sırasında hata: {e}")
            raise
    
    def _handle_response(self, response):
        """API yanıtını işle"""
        try:
            # Başarılı yanıt
            if 200 <= response.status_code < 300:
                return response.json() if response.content else {}
            
            # Hata yanıtı
            error_info = {
                "status_code": response.status_code,
                "reason": response.reason
            }
            
            try:
                error_info["detail"] = response.json()
            except:
                error_info["detail"] = response.text
            
            logger.error(f"API Hatası: {error_info}")
            
            # 401 hatası, token yenileme dene
            if response.status_code == 401 and self.auth.refresh_token:
                success = self.auth.refresh_auth_tokens()
                if success:
                    # İsteği yeniden dene
                    logger.info("Token yenileme başarılı, isteği yeniden deneniyor")
                    return self._retry_request(response.request)
            
            raise MTDError(f"API Hatası: {response.status_code}", error_info)
        
        except json.JSONDecodeError:
            logger.error(f"API yanıtı geçersiz JSON: {response.text}")
            raise MTDError("Geçersiz API yanıtı", {"response_text": response.text})
    
    def _retry_request(self, original_request):
        """Yeni token ile isteği yeniden dene"""
        try:
            # Yeni istekte kullanılacak güncel başlıkları al
            headers = self._get_headers()
            
            # Orijinal isteği yeniden oluştur
            method = original_request.method
            url = original_request.url
            
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                data = original_request.body
                response = requests.post(url, headers=headers, data=data)
            else:
                raise ValueError(f"Desteklenmeyen HTTP metodu: {method}")
            
            return self._handle_response(response)
        
        except Exception as e:
            logger.error(f"İstek yeniden denenirken hata: {e}")
            raise


class MTDError(Exception):
    """HMRC MTD hata sınıfı"""
    
    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details or {}
