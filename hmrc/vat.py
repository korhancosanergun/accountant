#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - HMRC VAT MTD Modülü
VAT (Katma Değer Vergisi) beyanlarını HMRC'ye iletmek için sınıflar ve fonksiyonlar.
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

class VATClient:
    """HMRC VAT MTD API istemcisi"""
    
    def __init__(self, mtd_client, vrn=None):
        """
        VAT MTD API istemcisini başlat
        
        Args:
            mtd_client: MTDClient istemcisi
            vrn: VAT kayıt numarası (opsiyonel)
        """
        self.mtd_client = mtd_client
        self.vrn = vrn
        
        # VAT API izinleri
        self.vat_scopes = [
            "read:vat",
            "write:vat"
        ]
    
    def authenticate(self):
        """VAT API için kimlik doğrulama yap"""
        return self.mtd_client.auth.authenticate(self.vat_scopes)
    
    def set_vrn(self, vrn):
        """VAT kayıt numarasını ayarla"""
        self.vrn = vrn
    
    def _get_vrn(self):
        """İç kullanım için VRN doğrulama"""
        if not self.vrn:
            raise ValueError("VRN (VAT kayıt numarası) ayarlanmamış")
        return self.vrn
    
    def get_vat_obligations(self, from_date=None, to_date=None, status=None):
        """
        Vergi mükellefi için VAT yükümlülüklerini al
        
        Args:
            from_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            to_date: Bitiş tarihi (YYYY-MM-DD formatında)
            status: Durum filtresi ('O' (açık) veya 'F' (tamamlanmış))
        
        Returns:
            Yükümlülük (dönem) listesi
        """
        vrn = self._get_vrn()
        
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
        endpoint = f"/organisations/vat/{vrn}/obligations"
        response = self.mtd_client.get(endpoint, params=params)
        
        return response.get('obligations', [])
    
    def get_vat_return(self, period_key):
        """
        Belirli bir dönem için VAT beyanını al
        
        Args:
            period_key: Dönem anahtarı (HMRC tarafından sağlanan)
        
        Returns:
            Dönem için VAT beyanı bilgileri
        """
        vrn = self._get_vrn()
        
        # API isteği gönder
        endpoint = f"/organisations/vat/{vrn}/returns/{period_key}"
        return self.mtd_client.get(endpoint)
    
    def submit_vat_return(self, vat_data):
        """
        VAT beyanı gönder
        
        Args:
            vat_data: VAT beyanı verileri (API şemasına uygun olmalı)
                {
                    "periodKey": "string", # HMRC tarafından sağlanan dönem anahtarı
                    "vatDueSales": 0,      # KDV'ye tabi satışlar için ödenmesi gereken KDV
                    "vatDueAcquisitions": 0, # AB'den alımlar için ödenmesi gereken KDV
                    "totalVatDue": 0,      # Toplam ödenmesi gereken KDV
                    "vatReclaimedCurrPeriod": 0, # Bu dönemde iade edilecek KDV
                    "netVatDue": 0,        # Ödenmesi gereken net KDV
                    "totalValueSalesExVAT": 0,  # KDV hariç toplam satış değeri
                    "totalValuePurchasesExVAT": 0, # KDV hariç toplam alım değeri
                    "totalValueGoodsSuppliedExVAT": 0, # KDV hariç AB'ye tedarik edilen malların toplam değeri
                    "totalAcquisitionsExVAT": 0,   # KDV hariç AB'den alımların toplam değeri
                    "finalised": true      # Beyanın nihai olduğunu onaylar
                }
        
        Returns:
            Gönderim yanıtı
        """
        vrn = self._get_vrn()
        
        # Gerekli alanları doğrula
        required_fields = [
            "periodKey", "vatDueSales", "vatDueAcquisitions", "totalVatDue",
            "vatReclaimedCurrPeriod", "netVatDue", "totalValueSalesExVAT",
            "totalValuePurchasesExVAT", "totalValueGoodsSuppliedExVAT",
            "totalAcquisitionsExVAT", "finalised"
        ]
        
        for field in required_fields:
            if field not in vat_data:
                raise ValueError(f"Eksik alan: {field}")
        
        # finalised alanını kontrol et
        if not vat_data.get("finalised", False):
            logger.warning("Beyan nihai olarak işaretlenmemiş (finalised=False)")
        
        # Sayısal alanları kontrol et
        numeric_fields = [
            "vatDueSales", "vatDueAcquisitions", "totalVatDue",
            "vatReclaimedCurrPeriod", "netVatDue", "totalValueSalesExVAT",
            "totalValuePurchasesExVAT", "totalValueGoodsSuppliedExVAT",
            "totalAcquisitionsExVAT"
        ]
        
        for field in numeric_fields:
            try:
                vat_data[field] = float(vat_data[field])
            except (ValueError, TypeError):
                raise ValueError(f"Geçersiz sayısal değer: {field}")
        
        # API isteği gönder
        endpoint = f"/organisations/vat/{vrn}/returns"
        return self.mtd_client.post(endpoint, vat_data)
    
    def get_vat_liabilities(self, from_date=None, to_date=None):
        """
        Vergi mükellefi için VAT borçlarını al
        
        Args:
            from_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            to_date: Bitiş tarihi (YYYY-MM-DD formatında)
        
        Returns:
            Borç bilgileri listesi
        """
        vrn = self._get_vrn()
        
        # Tarih parametrelerini kontrol et
        if not (from_date and to_date):
            raise ValueError("from_date ve to_date parametreleri gereklidir")
        
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
        endpoint = f"/organisations/vat/{vrn}/liabilities"
        response = self.mtd_client.get(endpoint, params=params)
        
        return response.get('liabilities', [])
    
    def get_vat_payments(self, from_date=None, to_date=None):
        """
        Vergi mükellefi için VAT ödemelerini al
        
        Args:
            from_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            to_date: Bitiş tarihi (YYYY-MM-DD formatında)
        
        Returns:
            Ödeme bilgileri listesi
        """
        vrn = self._get_vrn()
        
        # Tarih parametrelerini kontrol et
        if not (from_date and to_date):
            raise ValueError("from_date ve to_date parametreleri gereklidir")
        
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
        endpoint = f"/organisations/vat/{vrn}/payments"
        response = self.mtd_client.get(endpoint, params=params)
        
        return response.get('payments', [])


class VATReturnCalculator:
    """VAT beyannamesi hesaplama ve hazırlama sınıfı"""
    
    def __init__(self, database):
        """
        VAT beyannamesi hesaplayıcısını başlat
        
        Args:
            database: Veritabanı bağlantısı
        """
        self.db = database
    
    def calculate_vat_return(self, start_date, end_date):
        """
        Belirli bir dönem için VAT beyannamesi hesapla
        
        Args:
            start_date: Dönem başlangıç tarihi (YYYY-MM-DD formatında)
            end_date: Dönem bitiş tarihi (YYYY-MM-DD formatında)
        
        Returns:
            VAT beyannamesi verileri (HMRC API formatında)
        """
        # Tarih formatını kontrol et
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Tarih formatı geçersiz. YYYY-MM-DD kullanın.")
        
        # Bu dönem için tüm işlemleri al
        transactions = self.db.filter_transactions(
            start_date=start_date,
            end_date=end_date
        )
        
        # İşlemlerden fatura ve giderleri ayrıştır
        vat_transactions = []
        for transaction in transactions:
            # VAT bilgisi olan işlemleri filtrele
            if "vat_amount" in transaction and transaction["vat_amount"] > 0:
                vat_transactions.append(transaction)
        
        # Tüm faturaları al
        invoices = self.db.filter_invoices(
            start_date=start_date,
            end_date=end_date
        )
        
        # Tüm giderleri al
        expenses = self.db.filter_expenses(
            start_date=start_date,
            end_date=end_date
        )
        
        # VAT hesaplamalarını yap
        vat_output = 0  # Satışlardan kaynaklanan KDV (Box 1)
        vat_input = 0   # Alımlardan iade edilebilir KDV (Box 4)
        
        sales_ex_vat = 0  # KDV hariç satışlar (Box 6)
        purchases_ex_vat = 0  # KDV hariç alımlar (Box 7)
        
        # AB işlemleri
        ec_sales_ex_vat = 0  # AB'ye yapılan mal teslimatları (Box 8)
        ec_purchases_ex_vat = 0  # AB'den alınan mallar (Box 9)
        vat_on_ec_acquisitions = 0  # AB alımları üzerindeki KDV (Box 2)
        
        # Faturaları işle (satışlar)
        for invoice in invoices:
            if invoice.get("status") not in ["void", "draft"]:
                # Box 6: KDV hariç satışlar
                sales_ex_vat += invoice.get("total_net", 0)
                
                # Box 1: Satışlardan kaynaklanan KDV
                vat_output += invoice.get("total_vat", 0)
                
                # Satış AB'ye mi?
                if invoice.get("is_ec_sale", False):
                    # Box 8: AB'ye yapılan mal teslimatları
                    ec_sales_ex_vat += invoice.get("total_net", 0)
        
        # Giderleri işle (alımlar)
        for expense in expenses:
            if expense.get("status") != "void":
                # Box 7: KDV hariç alımlar
                purchases_ex_vat += expense.get("net_amount", 0)
                
                # Box 4: Alımlardan iade edilebilir KDV
                vat_input += expense.get("vat_amount", 0)
                
                # Alım AB'den mi?
                if expense.get("is_ec_purchase", False):
                    # Box 9: AB'den alınan mallar
                    ec_purchases_ex_vat += expense.get("net_amount", 0)
                    
                    # Box 2: AB alımları üzerindeki KDV
                    vat_on_ec_acquisitions += expense.get("vat_amount", 0)
        
        # Toplam ödenecek KDV (Box 3)
        total_vat_due = vat_output + vat_on_ec_acquisitions
        
        # Net ödenecek KDV (Box 5)
        net_vat_due = abs(total_vat_due - vat_input)
        
        # HMRC API formatında VAT beyanı oluştur
        vat_return = {
            "periodKey": f"{start_date_obj.strftime('%y%m')}-{end_date_obj.strftime('%y%m')}",  # Örnek: "2204-2207"
            "vatDueSales": round(vat_output, 2),  # Box 1
            "vatDueAcquisitions": round(vat_on_ec_acquisitions, 2),  # Box 2
            "totalVatDue": round(total_vat_due, 2),  # Box 3
            "vatReclaimedCurrPeriod": round(vat_input, 2),  # Box 4
            "netVatDue": round(net_vat_due, 2),  # Box 5
            "totalValueSalesExVAT": round(sales_ex_vat, 0),  # Box 6
            "totalValuePurchasesExVAT": round(purchases_ex_vat, 0),  # Box 7
            "totalValueGoodsSuppliedExVAT": round(ec_sales_ex_vat, 0),  # Box 8
            "totalAcquisitionsExVAT": round(ec_purchases_ex_vat, 0),  # Box 9
            "finalised": False  # Varsayılan olarak nihai değil
        }
        
        return vat_return
    
    def save_draft_vat_return(self, vat_return_data, period_start, period_end):
        """
        Taslak VAT beyanını veritabanına kaydet
        
        Args:
            vat_return_data: VAT beyannamesi verileri
            period_start: Dönem başlangıç tarihi
            period_end: Dönem bitiş tarihi
        
        Returns:
            Eklenen beyan ID'si
        """
        # Beyan nesnesini oluştur
        vat_return = {
            "id": None,  # Veritabanı tarafından atanacak
            "period_start": period_start,
            "period_end": period_end,
            "period_key": vat_return_data.get("periodKey", ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": "draft",
            "submission_date": None,
            "hmrc_receipt": None,
            "data": vat_return_data
        }
        
        # Veritabanına kaydet
        return self.db.add_vat_return(vat_return)
    
    def finalize_vat_return(self, vat_return_id):
        """
        VAT beyanını nihai hale getir
        
        Args:
            vat_return_id: VAT beyanı ID'si
        
        Returns:
            Güncellenen beyan verisi
        """
        # Beyanı al
        vat_return = self.db.get_vat_return_by_id(vat_return_id)
        if not vat_return:
            raise ValueError(f"VAT beyanı bulunamadı: {vat_return_id}")
        
        # Beyan durumunu kontrol et
        if vat_return.get("status") != "draft":
            raise ValueError(f"Yalnızca taslak beyanlar nihai hale getirilebilir. Mevcut durum: {vat_return.get('status')}")
        
        # Beyan verilerini güncelle
        vat_data = vat_return.get("data", {})
        vat_data["finalised"] = True
        
        # Beyanı güncelle
        updated_vat_return = vat_return.copy()
        updated_vat_return["data"] = vat_data
        updated_vat_return["updated_at"] = datetime.now().isoformat()
        
        # Veritabanında güncelle
        success = self.db.update_vat_return(vat_return_id, updated_vat_return)
        if not success:
            raise ValueError(f"VAT beyanı güncellenirken hata oluştu: {vat_return_id}")
        
        return updated_vat_return
    
    def mark_submitted(self, vat_return_id, receipt=None):
        """
        VAT beyanını gönderilmiş olarak işaretle
        
        Args:
            vat_return_id: VAT beyanı ID'si
            receipt: HMRC'den alınan makbuz verisi (opsiyonel)
        
        Returns:
            Güncellenen beyan verisi
        """
        # Beyanı al
        vat_return = self.db.get_vat_return_by_id(vat_return_id)
        if not vat_return:
            raise ValueError(f"VAT beyanı bulunamadı: {vat_return_id}")
        
        # Beyan durumunu kontrol et
        if vat_return.get("status") not in ["draft", "finalized"]:
            raise ValueError(f"Yalnızca taslak veya nihai beyanlar gönderilebilir. Mevcut durum: {vat_return.get('status')}")
        
        # Beyanı güncelle
        updated_vat_return = vat_return.copy()
        updated_vat_return["status"] = "submitted"
        updated_vat_return["submission_date"] = datetime.now().isoformat()
        updated_vat_return["hmrc_receipt"] = receipt
        updated_vat_return["updated_at"] = datetime.now().isoformat()
        
        # Veritabanında güncelle
        success = self.db.update_vat_return(vat_return_id, updated_vat_return)
        if not success:
            raise ValueError(f"VAT beyanı güncellenirken hata oluştu: {vat_return_id}")
        
        return updated_vat_return
