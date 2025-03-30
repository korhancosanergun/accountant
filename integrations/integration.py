#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Entegrasyonlar Yöneticisi
Wise ve Stripe gibi dış servislerle entegrasyonu yönetir.
"""

import logging
import json
import os
from datetime import datetime, timedelta

# Wise modülleri
from integrations.wise.api_client import WiseAPIClient
from integrations.wise.account_sync import WiseAccountSync

# Stripe modülleri
from integrations.stripe.api_client import StripeAPIClient
from integrations.stripe.payment_sync import StripePaymentSync

class IntegrationsManager:
    """Entegrasyonlar yöneticisi"""
    
    def __init__(self, ledger, config):
        """Yönetici başlatıcı
        
        Args:
            ledger: Muhasebe defteri nesnesi
            config: Uygulama yapılandırması
        """
        self.ledger = ledger
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Wise entegrasyonu
        self.wise_client = None
        self.wise_sync = None
        
        # Stripe entegrasyonu
        self.stripe_client = None
        self.stripe_sync = None
        
        # Entegrasyonları başlat
        self._initialize_integrations()
    
    def _initialize_integrations(self):
        """Yapılandırmaya göre desteklenen entegrasyonları başlat"""
        # Wise entegrasyonu
        if self._is_wise_enabled():
            self._initialize_wise()
        
        # Stripe entegrasyonu
        if self._is_stripe_enabled():
            self._initialize_stripe()
    
    def _is_wise_enabled(self):
        """Wise entegrasyonunun etkin olup olmadığını kontrol et"""
        wise_config = self.config.get("wise", {})
        api_token = wise_config.get("api_token")
        return bool(api_token)
    
    def _is_stripe_enabled(self):
        """Stripe entegrasyonunun etkin olup olmadığını kontrol et"""
        stripe_config = self.config.get("stripe", {})
        api_key = stripe_config.get("api_key")
        return bool(api_key)
    
    def _initialize_wise(self):
        """Wise entegrasyonunu başlat"""
        try:
            wise_config = self.config.get("wise", {})
            api_token = wise_config.get("api_token")
            profile_id = wise_config.get("profile_id")
            is_sandbox = wise_config.get("sandbox", False)
            
            if not api_token:
                self.logger.warning("Wise API token bulunamadı, entegrasyon devre dışı")
                return
            
            # Wise API istemcisini oluştur
            self.wise_client = WiseAPIClient(
                api_token=api_token,
                profile_id=profile_id,
                is_sandbox=is_sandbox
            )
            
            # Profil ID yoksa profilleri al ve ilkini kullan
            if not profile_id:
                profiles = self.wise_client.get_profiles()
                if profiles and len(profiles) > 0:
                    profile_id = profiles[0].get("id")
                    self.wise_client.set_profile_id(profile_id)
                    
                    # Yapılandırmayı güncelle
                    wise_config["profile_id"] = profile_id
                    self.config["wise"] = wise_config
                    self._save_config()
            
            # Senkronizasyon sınıfını oluştur
            self.wise_sync = WiseAccountSync(
                wise_client=self.wise_client,
                ledger=self.ledger,
                config=self.config
            )
            
            self.logger.info("Wise entegrasyonu başlatıldı")
            
        except Exception as e:
            self.logger.error(f"Wise entegrasyonu başlatılırken hata: {e}")
            self.wise_client = None
            self.wise_sync = None
    
    def _initialize_stripe(self):
        """Stripe entegrasyonunu başlat"""
        try:
            stripe_config = self.config.get("stripe", {})
            api_key = stripe_config.get("api_key")
            webhook_secret = stripe_config.get("webhook_secret")
            
            if not api_key:
                self.logger.warning("Stripe API key bulunamadı, entegrasyon devre dışı")
                return
            
            # Stripe API istemcisini oluştur
            self.stripe_client = StripeAPIClient(
                api_key=api_key,
                webhook_secret=webhook_secret
            )
            
            # Senkronizasyon sınıfını oluştur
            self.stripe_sync = StripePaymentSync(
                stripe_client=self.stripe_client,
                ledger=self.ledger,
                config=self.config
            )
            
            self.logger.info("Stripe entegrasyonu başlatıldı")
            
        except Exception as e:
            self.logger.error(f"Stripe entegrasyonu başlatılırken hata: {e}")
            self.stripe_client = None
            self.stripe_sync = None
    
    def _save_config(self):
        """Yapılandırmayı kaydet"""
        # Uygulama yapılandırmasının nasıl kaydedildiğine bağlı olarak değişir
        # Burada örnek bir implementasyon:
        config_file = os.path.join(os.path.dirname(__file__), "..", "config.json")
        
        try:
            with open(config_file, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.logger.error(f"Yapılandırma kaydedilirken hata: {e}")
    
    def sync_wise_accounts(self):
        """Wise hesaplarını senkronize et"""
        if not self.wise_sync:
            self.logger.warning("Wise entegrasyonu aktif değil")
            return False
        
        try:
            # Hesap eşleştirmelerini kur (ilk senkronizasyonda)
            if not self.config.get("wise", {}).get("account_mappings"):
                self.wise_sync.setup_account_mapping()
            
            # Hesapları senkronize et
            if self.wise_sync.sync_all_accounts():
                self.logger.info("Wise hesapları başarıyla senkronize edildi")
                return True
            else:
                self.logger.warning("Wise hesapları senkronize edilirken hata oluştu")
                return False
        except Exception as e:
            self.logger.error(f"Wise hesapları senkronize edilirken hata: {e}")
            return False
    
    def sync_wise_transactions(self, start_date=None, end_date=None):
        """Wise işlemlerini senkronize et
        
        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında, None ise son 30 gün)
            end_date: Bitiş tarihi (YYYY-MM-DD formatında, None ise bugün)
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        if not self.wise_sync:
            self.logger.warning("Wise entegrasyonu aktif değil")
            return False
        
        try:
            # İşlemleri senkronize et
            if self.wise_sync.sync_transactions(start_date, end_date):
                self.logger.info("Wise işlemleri başarıyla senkronize edildi")
                return True
            else:
                self.logger.warning("Wise işlemleri senkronize edilirken hata oluştu")
                return False
        except Exception as e:
            self.logger.error(f"Wise işlemleri senkronize edilirken hata: {e}")
            return False
    
    def sync_stripe_balance(self):
        """Stripe bakiyesini senkronize et"""
        if not self.stripe_sync:
            self.logger.warning("Stripe entegrasyonu aktif değil")
            return False
        
        try:
            # Bakiyeleri senkronize et
            if self.stripe_sync.sync_balance():
                self.logger.info("Stripe bakiyesi başarıyla senkronize edildi")
                return True
            else:
                self.logger.warning("Stripe bakiyesi senkronize edilirken hata oluştu")
                return False
        except Exception as e:
            self.logger.error(f"Stripe bakiyesi senkronize edilirken hata: {e}")
            return False
    
    def sync_stripe_payments(self, start_date=None, end_date=None, limit=100):
        """Stripe ödemelerini senkronize et
        
        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında, None ise son 30 gün)
            end_date: Bitiş tarihi (YYYY-MM-DD formatında, None ise bugün)
            limit: Alınacak maksimum işlem sayısı
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        if not self.stripe_sync:
            self.logger.warning("Stripe entegrasyonu aktif değil")
            return False
        
        try:
            # İşlemleri senkronize et
            if self.stripe_sync.sync_payments(start_date, end_date, limit):
                self.logger.info("Stripe ödemeleri başarıyla senkronize edildi")
                return True
            else:
                self.logger.warning("Stripe ödemeleri senkronize edilirken hata oluştu")
                return False
        except Exception as e:
            self.logger.error(f"Stripe ödemeleri senkronize edilirken hata: {e}")
            return False
    
    def sync_stripe_invoices(self, limit=100, status="paid"):
        """Stripe faturalarını senkronize et
        
        Args:
            limit: Alınacak maksimum fatura sayısı
            status: Fatura durumu filtresi (paid, open, draft, void, uncollectible)
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        if not self.stripe_sync:
            self.logger.warning("Stripe entegrasyonu aktif değil")
            return False
        
        try:
            # Faturaları senkronize et
            if self.stripe_sync.sync_invoices(limit, status):
                self.logger.info("Stripe faturaları başarıyla senkronize edildi")
                return True
            else:
                self.logger.warning("Stripe faturaları senkronize edilirken hata oluştu")
                return False
        except Exception as e:
            self.logger.error(f"Stripe faturaları senkronize edilirken hata: {e}")
            return False
    
    def sync_all(self):
        """Tüm entegrasyonları senkronize et
        
        Returns:
            dict: Her entegrasyon için başarı durumunu içeren sözlük
        """
        results = {
            "wise": {
                "accounts": False,
                "transactions": False
            },
            "stripe": {
                "balance": False,
                "payments": False,
                "invoices": False
            }
        }
        
        # Wise entegrasyonu
        if self.wise_sync:
            try:
                results["wise"]["accounts"] = self.sync_wise_accounts()
                results["wise"]["transactions"] = self.sync_wise_transactions()
            except Exception as e:
                self.logger.error(f"Wise senkronizasyonunda hata: {e}")
        
        # Stripe entegrasyonu
        if self.stripe_sync:
            try:
                results["stripe"]["balance"] = self.sync_stripe_balance()
                results["stripe"]["payments"] = self.sync_stripe_payments()
                results["stripe"]["invoices"] = self.sync_stripe_invoices()
            except Exception as e:
                self.logger.error(f"Stripe senkronizasyonunda hata: {e}")
        
        return results
    
    def setup_wise(self, api_token, profile_id=None, is_sandbox=False):
        """Wise entegrasyonunu ayarla
        
        Args:
            api_token: Wise API token
            profile_id: Wise profil ID (opsiyonel)
            is_sandbox: Sandbox modu kullanılacak mı
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        try:
            # Yapılandırmayı güncelle
            if "wise" not in self.config:
                self.config["wise"] = {}
                
            self.config["wise"]["api_token"] = api_token
            if profile_id:
                self.config["wise"]["profile_id"] = profile_id
            self.config["wise"]["sandbox"] = is_sandbox
            
            # Yapılandırmayı kaydet
            self._save_config()
            
            # Entegrasyonu yeniden başlat
            self._initialize_wise()
            
            return self.wise_client is not None
            
        except Exception as e:
            self.logger.error(f"Wise entegrasyonu ayarlanırken hata: {e}")
            return False
    
    def setup_stripe(self, api_key, webhook_secret=None):
        """Stripe entegrasyonunu ayarla
        
        Args:
            api_key: Stripe API anahtarı
            webhook_secret: Webhook gizli anahtarı (opsiyonel)
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        try:
            # Yapılandırmayı güncelle
            if "stripe" not in self.config:
                self.config["stripe"] = {}
                
            self.config["stripe"]["api_key"] = api_key
            if webhook_secret:
                self.config["stripe"]["webhook_secret"] = webhook_secret
            
            # Yapılandırmayı kaydet
            self._save_config()
            
            # Entegrasyonu yeniden başlat
            self._initialize_stripe()
            
            return self.stripe_client is not None
            
        except Exception as e:
            self.logger.error(f"Stripe entegrasyonu ayarlanırken hata: {e}")
            return False
    
    def schedule_sync(self, interval_hours=24):
        """Otomatik senkronizasyon zamanla
        
        Args:
            interval_hours: Senkronizasyon aralığı (saat)
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        # Bu fonksiyon uygulamanın nasıl zamanlanmış görevleri yönettiğine göre değişir
        # Burada yalnızca bir örnek mantık gösteriliyor
        
        try:
            # Zamanlanmış görev ayarları
            self.config["sync_schedule"] = {
                "enabled": True,
                "interval_hours": interval_hours,
                "last_sync": datetime.now().isoformat()
            }
            
            # Yapılandırmayı kaydet
            self._save_config()
            
            self.logger.info(f"Otomatik senkronizasyon {interval_hours} saat aralıkla zamanlandı")
            return True
            
        except Exception as e:
            self.logger.error(f"Otomatik senkronizasyon zamanlanırken hata: {e}")
            return False
    
    def should_sync(self):
        """Senkronizasyon zamanının gelip gelmediğini kontrol et
        
        Returns:
            bool: Senkronizasyon zamanı geldiyse True, aksi halde False
        """
        try:
            # Zamanlanmış görev ayarlarını al
            schedule = self.config.get("sync_schedule", {})
            enabled = schedule.get("enabled", False)
            
            if not enabled:
                return False
                
            interval_hours = schedule.get("interval_hours", 24)
            last_sync_str = schedule.get("last_sync")
            
            if not last_sync_str:
                return True
                
            last_sync = datetime.fromisoformat(last_sync_str)
            next_sync = last_sync + timedelta(hours=interval_hours)
            
            return datetime.now() >= next_sync
            
        except Exception as e:
            self.logger.error(f"Senkronizasyon zamanı kontrol edilirken hata: {e}")
            return False
    
    def update_last_sync_time(self):
        """Son senkronizasyon zamanını güncelle"""
        try:
            # Zamanlanmış görev ayarlarını al
            if "sync_schedule" not in self.config:
                self.config["sync_schedule"] = {}
                
            self.config["sync_schedule"]["last_sync"] = datetime.now().isoformat()
            
            # Yapılandırmayı kaydet
            self._save_config()
            
        except Exception as e:
            self.logger.error(f"Son senkronizasyon zamanı güncellenirken hata: {e}")
    
    def get_integration_status(self):
        """Entegrasyon durumlarını al
        
        Returns:
            dict: Entegrasyon durumlarını içeren sözlük
        """
        status = {
            "wise": {
                "enabled": self.wise_client is not None,
                "profile_id": self.config.get("wise", {}).get("profile_id"),
                "sandbox": self.config.get("wise", {}).get("sandbox", False)
            },
            "stripe": {
                "enabled": self.stripe_client is not None,
                "has_webhook": bool(self.config.get("stripe", {}).get("webhook_secret"))
            },
            "sync_schedule": {
                "enabled": self.config.get("sync_schedule", {}).get("enabled", False),
                "interval_hours": self.config.get("sync_schedule", {}).get("interval_hours", 24),
                "last_sync": self.config.get("sync_schedule", {}).get("last_sync")
            }
        }
        
        # Wise hesaplarını al
        if status["wise"]["enabled"] and self.wise_client:
            try:
                accounts = self.wise_client.get_accounts()
                if accounts:
                    status["wise"]["accounts"] = len(accounts)
                    
                    # Hesap bakiyelerini ekle
                    balances = []
                    for account in accounts:
                        account_balances = account.get("balances", [])
                        for balance in account_balances:
                            currency = balance.get("currency")
                            amount = balance.get("amount", {}).get("value", 0)
                            balances.append({
                                "currency": currency,
                                "amount": amount
                            })
                    
                    status["wise"]["balances"] = balances
            except Exception as e:
                self.logger.error(f"Wise hesapları alınırken hata: {e}")
        
        # Stripe bakiyesini al
        if status["stripe"]["enabled"] and self.stripe_client:
            try:
                balance = self.stripe_client.get_balance()
                if balance:
                    status["stripe"]["balances"] = []
                    
                    for available_balance in balance.get("available", []):
                        currency = available_balance.get("currency", "").upper()
                        amount = available_balance.get("amount", 0) / 100
                        status["stripe"]["balances"].append({
                            "currency": currency,
                            "amount": amount
                        })
            except Exception as e:
                self.logger.error(f"Stripe bakiyesi alınırken hata: {e}")
        
        return status