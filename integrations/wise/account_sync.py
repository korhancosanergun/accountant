#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Wise Hesap Senkronizasyonu
Wise hesapları ve işlemleri muhasebe sistemi ile senkronize eder.
"""

import logging
from datetime import datetime, timedelta
import json
import os
import uuid

class WiseAccountSync:
    """Wise hesap senkronizasyonu"""
    
    def __init__(self, wise_client, ledger, config):
        """Senkronizasyon başlatıcı
        
        Args:
            wise_client: Wise API istemcisi nesnesi
            ledger: Muhasebe defteri nesnesi
            config: Uygulama yapılandırması
        """
        self.wise_client = wise_client
        self.ledger = ledger
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Yapılandırmadan Wise hesap eşleştirmelerini al
        self.account_mappings = config.get("wise", {}).get("account_mappings", {})
        
    def sync_all_accounts(self):
        """Tüm Wise hesaplarını senkronize et"""
        # Wise hesaplarını al
        accounts = self.wise_client.get_accounts()
        
        if not accounts:
            self.logger.error("Wise hesapları alınamadı")
            return False
        
        success = True
        
        # Her hesabı senkronize et
        for account in accounts:
            account_id = account.get("id")
            balances = account.get("balances", [])
            
            # Her para birimi için bakiyeleri güncelle
            for balance in balances:
                currency = balance.get("currency")
                amount = balance.get("amount", {}).get("value", 0)
                
                # Bu para birimi için muhasebe hesap kodu var mı kontrol et
                account_code = self.account_mappings.get(f"{account_id}_{currency}")
                if not account_code:
                    self.logger.warning(f"Wise hesabı {account_id}, {currency} için muhasebe hesap kodu bulunamadı")
                    continue
                
                # Muhasebe hesabını güncelle
                if not self._update_account_balance(account_code, amount):
                    success = False
                    
        return success
    
    def sync_transactions(self, start_date=None, end_date=None):
        """Belirli tarih aralığındaki işlemleri senkronize et
        
        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında, None ise son 30 gün)
            end_date: Bitiş tarihi (YYYY-MM-DD formatında, None ise bugün)
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        if not start_date:
            # Varsayılan olarak son 30 günü al
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
            
        # Wise hesaplarını al
        accounts = self.wise_client.get_accounts()
        
        if not accounts:
            self.logger.error("Wise hesapları alınamadı")
            return False
        
        # Her hesap için işlemleri al ve senkronize et
        for account in accounts:
            account_id = account.get("id")
            balances = account.get("balances", [])
            
            for balance in balances:
                currency = balance.get("currency")
                
                # Bu para birimi için muhasebe hesap kodu var mı kontrol et
                account_code = self.account_mappings.get(f"{account_id}_{currency}")
                if not account_code:
                    self.logger.warning(f"Wise hesabı {account_id}, {currency} için muhasebe hesap kodu bulunamadı")
                    continue
                
                # İşlemleri al
                transactions = self.wise_client.get_transactions(
                    account_id, currency, start_date, end_date
                )
                
                if not transactions:
                    self.logger.warning(f"Wise hesabı {account_id}, {currency} için işlemler alınamadı")
                    continue
                
                # İşlemleri senkronize et
                self._sync_account_transactions(account_id, currency, account_code, transactions)
        
        return True
    
    def _sync_account_transactions(self, account_id, currency, account_code, transactions):
        """Belirli bir hesabın işlemlerini senkronize et
        
        Args:
            account_id: Wise hesap ID'si
            currency: Para birimi kodu
            account_code: Muhasebe hesap kodu
            transactions: İşlemler listesi
        """
        # Son senkronizasyon tarihini al (yerel bir dosyadan veya veritabanından)
        last_sync_date = self._get_last_sync_date(account_id, currency)
        
        # İşlemleri senkronize et
        synced_count = 0
        
        for trans in transactions:
            # İşlem tarihini kontrol et
            # NOT: Wise API'den gelen tarih formatı: "2023-03-30T12:34:56.789Z"
            trans_date_str = trans.get("date", "")
            if not trans_date_str:
                continue
                
            try:
                trans_date = datetime.strptime(trans_date_str.split("T")[0], "%Y-%m-%d")
            except ValueError:
                continue
                
            # Son senkronizasyon tarihinden sonraki işlemleri işle
            if last_sync_date and trans_date <= last_sync_date:
                continue
                
            # İşlemi muhasebe sistemine ekle
            if self._add_transaction_to_ledger(account_code, trans, currency):
                synced_count += 1
                
        # Son senkronizasyon tarihini güncelle
        if synced_count > 0:
            self._update_last_sync_date(account_id, currency)
            self.logger.info(f"Wise hesabı {account_id}, {currency} için {synced_count} işlem senkronize edildi")
    
    def _add_transaction_to_ledger(self, account_code, transaction, currency):
        """Wise işlemini muhasebe defterine ekle
        
        Args:
            account_code: Muhasebe hesap kodu
            transaction: Wise işlem verisi
            currency: Para birimi kodu
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        try:
            # İşlem detaylarını hazırla
            trans_id = transaction.get("id")
            amount = transaction.get("amount", {}).get("value", 0)
            date_str = transaction.get("date", "").split("T")[0]  # "2023-03-30T12:34:56.789Z" -> "2023-03-30"
            description = transaction.get("details", {}).get("description", "")
            reference = transaction.get("details", {}).get("reference", "")
            
            # Karşı hesabı belirle (gider kategorisi veya gelir türü)
            # Bu basit implementasyonda varsayılan hesaplar kullanıyoruz
            # Gerçek uygulamada işlem açıklamasına göre kategorize edilebilir
            is_expense = amount < 0
            counter_account = "5000" if is_expense else "4000"  # Gider veya Gelir hesabı
            
            # İşlem tutarını pozitif yap
            amount = abs(amount)
            
            # Muhasebe işlemi hazırla
            ledger_transaction = {
                "date": date_str,
                "document_number": f"WISE-{trans_id}",
                "description": description or f"Wise İşlemi - {reference or 'Açıklama Yok'}",
                "transaction_type": "bank",
                "status": "reconciled",
                "notes": f"Wise hesabından otomatik olarak senkronize edildi. İşlem ID: {trans_id}",
                "source": "wise",
                "source_id": trans_id,
                "vat": 0  # Varsayılan olarak KDV yok
            }
            
            if is_expense:
                # Gider işlemi
                # 1) Gider hesabına borç
                ledger_transaction["account"] = counter_account
                ledger_transaction["debit"] = amount
                ledger_transaction["credit"] = 0
                self.ledger.add_transaction(ledger_transaction)
                
                # 2) Banka hesabından düş
                ledger_transaction["account"] = account_code
                ledger_transaction["debit"] = 0
                ledger_transaction["credit"] = amount
                self.ledger.add_transaction(ledger_transaction)
            else:
                # Gelir işlemi
                # 1) Banka hesabına borç
                ledger_transaction["account"] = account_code
                ledger_transaction["debit"] = amount
                ledger_transaction["credit"] = 0
                self.ledger.add_transaction(ledger_transaction)
                
                # 2) Gelir hesabına alacak
                ledger_transaction["account"] = counter_account
                ledger_transaction["debit"] = 0
                ledger_transaction["credit"] = amount
                self.ledger.add_transaction(ledger_transaction)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Wise işlemi muhasebe defterine eklenirken hata: {e}")
            return False
    
    def _update_account_balance(self, account_code, balance):
        """Muhasebe hesap bakiyesini güncelle
        
        Args:
            account_code: Muhasebe hesap kodu
            balance: Yeni bakiye değeri
            
        Returns:
            bool: Başarılı olursa True, aksi halde False
        """
        try:
            # Mevcut hesabı al
            account = self.ledger.get_account_by_code(account_code)
            if not account:
                self.logger.error(f"Hesap bulunamadı: {account_code}")
                return False
            
            # Hesabı güncelle
            current_balance = account.get("balance", 0)
            
            # Bakiye değişmediyse güncelleme yapma
            if abs(current_balance - balance) < 0.01:  # Küçük farklılıkları görmezden gel
                return True
                
            self.logger.info(f"Hesap {account_code} bakiyesi güncelleniyor: {current_balance} -> {balance}")
            
            # Hesabı güncelle
            account["balance"] = balance
            return self.ledger.update_account(account_code, account)
            
        except Exception as e:
            self.logger.error(f"Hesap bakiyesi güncellenirken hata: {e}")
            return False
    
    def _get_last_sync_date(self, account_id, currency):
        """Son senkronizasyon tarihini al
        
        Returns:
            datetime: Son senkronizasyon tarihi, yoksa None
        """
        try:
            # Senkronizasyon verilerini saklamak için dizin
            sync_dir = os.path.join(os.path.dirname(__file__), "sync_data")
            os.makedirs(sync_dir, exist_ok=True)
            
            # Senkronizasyon dosyası
            sync_file = os.path.join(sync_dir, f"wise_sync_{account_id}_{currency}.json")
            
            if not os.path.exists(sync_file):
                return None
                
            with open(sync_file, "r") as f:
                data = json.load(f)
                last_sync = data.get("last_sync")
                
                if not last_sync:
                    return None
                    
                return datetime.strptime(last_sync, "%Y-%m-%d")
                
        except Exception as e:
            self.logger.error(f"Son senkronizasyon tarihi alınırken hata: {e}")
            return None
    
    def _update_last_sync_date(self, account_id, currency):
        """Son senkronizasyon tarihini güncelle"""
        try:
            # Senkronizasyon verilerini saklamak için dizin
            sync_dir = os.path.join(os.path.dirname(__file__), "sync_data")
            os.makedirs(sync_dir, exist_ok=True)
            
            # Senkronizasyon dosyası
            sync_file = os.path.join(sync_dir, f"wise_sync_{account_id}_{currency}.json")
            
            # Şu anki tarih
            now = datetime.now().strftime("%Y-%m-%d")
            
            # Senkronizasyon verisini güncelle
            sync_data = {"last_sync": now}
            
            with open(sync_file, "w") as f:
                json.dump(sync_data, f)
                
            return True
                
        except Exception as e:
            self.logger.error(f"Son senkronizasyon tarihi güncellenirken hata: {e}")
            return False
            
    def setup_account_mapping(self):
        """Wise hesapları için muhasebe hesap kodlarını ayarla"""
        # Wise hesaplarını al
        accounts = self.wise_client.get_accounts()
        
        if not accounts:
            self.logger.error("Wise hesapları alınamadı")
            return False
            
        # Her hesap ve para birimi için eşleştirme oluştur
        mappings = {}
        
        for account in accounts:
            account_id = account.get("id")
            account_name = account.get("name", "Wise Hesabı")
            balances = account.get("balances", [])
            
            for balance in balances:
                currency = balance.get("currency")
                
                # Bu para birimi için zaten bir eşleştirme var mı kontrol et
                mapping_key = f"{account_id}_{currency}"
                if mapping_key in self.account_mappings:
                    continue
                
                # Hesap adı oluştur (Wise'daki hesap adı ve para birimi)
                account_name_with_currency = f"Wise {account_name} ({currency})"
                
                # Yeni muhasebe hesabı oluştur
                new_account = {
                    "code": f"1110_{account_id}_{currency.lower()}",  # Örnek kod formatı
                    "name": account_name_with_currency,
                    "type": "asset",
                    "category": "current_asset",
                    "vat_rate": 0,
                    "balance": balance.get("amount", {}).get("value", 0)
                }
                
                # Hesabı ekle
                try:
                    self.ledger.add_account(new_account)
                    mappings[mapping_key] = new_account["code"]
                    self.logger.info(f"Wise hesabı {account_name_with_currency} için yeni muhasebe hesabı oluşturuldu: {new_account['code']}")
                except Exception as e:
                    self.logger.error(f"Wise hesabı için muhasebe hesabı oluşturulurken hata: {e}")
        
        # Eşleştirmeleri kaydet
        if mappings:
            # Mevcut eşleştirmeleri güncelle
            self.account_mappings.update(mappings)
            
            # Yapılandırmayı güncelle
            if "wise" not in self.config:
                self.config["wise"] = {}
            self.config["wise"]["account_mappings"] = self.account_mappings
            
            # Yapılandırmayı kaydet (Burada config'i nasıl kaydettiğinize bağlı)
            # Örnek olarak:
            # with open("config.json", "w") as f:
            #     json.dump(self.config, f, indent=2)
            
            return True
        
        return False
