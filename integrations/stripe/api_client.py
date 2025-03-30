#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Stripe API İstemcisi
Stripe ödemeleri, abonelikler ve müşteriler için API istemcisi.
"""

import stripe
import logging
from datetime import datetime, timedelta

class StripeAPIClient:
    """Stripe API istemcisi"""
    
    def __init__(self, api_key, webhook_secret=None):
        """API istemcisi başlatıcı
        
        Args:
            api_key: Stripe API anahtarı
            webhook_secret: Webhook imzalama anahtarı (Webhook kullanılacaksa)
        """
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.logger = logging.getLogger(__name__)
        
        # Stripe API'yi yapılandır
        stripe.api_key = api_key
    
    def get_balance(self):
        """Stripe hesap bakiyesini al
        
        Returns:
            dict: Bakiye bilgileri
        """
        try:
            return stripe.Balance.retrieve()
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe bakiyesi alınırken hata: {e}")
            return None
    
    def get_balance_transactions(self, limit=100, starting_after=None, ending_before=None):
        """Stripe bakiye işlemlerini al
        
        Args:
            limit: En fazla kaç işlem alınacağı
            starting_after: Bu ID'den sonraki işlemleri al
            ending_before: Bu ID'den önceki işlemleri al
            
        Returns:
            list: İşlem nesneleri listesi
        """
        try:
            params = {"limit": limit}
            if starting_after:
                params["starting_after"] = starting_after
            if ending_before:
                params["ending_before"] = ending_before
                
            return stripe.BalanceTransaction.list(**params)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe bakiye işlemleri alınırken hata: {e}")
            return None
    
    def get_transactions_by_date(self, start_date, end_date=None, limit=100):
        """Belirli tarih aralığındaki işlemleri al
        
        Args:
            start_date: Başlangıç tarihi (YYYY-MM-DD formatında)
            end_date: Bitiş tarihi (YYYY-MM-DD formatında, None ise bugün)
            limit: En fazla kaç işlem alınacağı
            
        Returns:
            list: İşlem nesneleri listesi
        """
        try:
            # Tarihleri Unix timestamp'e dönüştür
            start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
            
            if end_date:
                end_timestamp = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
            else:
                end_timestamp = int(datetime.now().timestamp())
            
            return stripe.BalanceTransaction.list(
                limit=limit,
                created={
                    "gte": start_timestamp,
                    "lte": end_timestamp
                }
            )
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe tarih aralığındaki işlemler alınırken hata: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"Tarih biçimi hatalı: {e}")
            return None
    
    def get_payment_intents(self, limit=100, status=None):
        """Ödeme niyetlerini al
        
        Args:
            limit: En fazla kaç ödeme niyeti alınacağı
            status: Filtrelenecek durum (requires_payment_method, requires_confirmation,
                    requires_action, processing, requires_capture, canceled, succeeded)
                    
        Returns:
            list: Ödeme niyeti nesneleri listesi
        """
        try:
            params = {"limit": limit}
            if status:
                params["status"] = status
                
            return stripe.PaymentIntent.list(**params)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe ödeme niyetleri alınırken hata: {e}")
            return None
    
    def get_payment_intent(self, payment_intent_id):
        """Belirli bir ödeme niyeti al
        
        Args:
            payment_intent_id: Ödeme niyeti ID'si
            
        Returns:
            dict: Ödeme niyeti nesnesi
        """
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe ödeme niyeti alınırken hata: {e}")
            return None
    
    def get_charges(self, limit=100, starting_after=None, ending_before=None):
        """Ödemeleri al
        
        Args:
            limit: En fazla kaç ödeme alınacağı
            starting_after: Bu ID'den sonraki ödemeleri al
            ending_before: Bu ID'den önceki ödemeleri al
            
        Returns:
            list: Ödeme nesneleri listesi
        """
        try:
            params = {"limit": limit}
            if starting_after:
                params["starting_after"] = starting_after
            if ending_before:
                params["ending_before"] = ending_before
                
            return stripe.Charge.list(**params)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe ödemeler alınırken hata: {e}")
            return None
    
    def get_charge(self, charge_id):
        """Belirli bir ödeme al
        
        Args:
            charge_id: Ödeme ID'si
            
        Returns:
            dict: Ödeme nesnesi
        """
        try:
            return stripe.Charge.retrieve(charge_id)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe ödeme alınırken hata: {e}")
            return None
    
    def get_customers(self, limit=100, starting_after=None, ending_before=None):
        """Müşterileri al
        
        Args:
            limit: En fazla kaç müşteri alınacağı
            starting_after: Bu ID'den sonraki müşterileri al
            ending_before: Bu ID'den önceki müşterileri al
            
        Returns:
            list: Müşteri nesneleri listesi
        """
        try:
            params = {"limit": limit}
            if starting_after:
                params["starting_after"] = starting_after
            if ending_before:
                params["ending_before"] = ending_before
                
            return stripe.Customer.list(**params)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe müşteriler alınırken hata: {e}")
            return None
    
    def get_customer(self, customer_id):
        """Belirli bir müşteri al
        
        Args:
            customer_id: Müşteri ID'si
            
        Returns:
            dict: Müşteri nesnesi
        """
        try:
            return stripe.Customer.retrieve(customer_id)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe müşteri alınırken hata: {e}")
            return None
    
    def get_subscriptions(self, limit=100, customer=None, status=None):
        """Abonelikleri al
        
        Args:
            limit: En fazla kaç abonelik alınacağı
            customer: Belirli bir müşterinin abonelikleri (müşteri ID'si)
            status: Filtrelenecek durum (active, past_due, unpaid, canceled, incomplete, incomplete_expired, trialing, all)
            
        Returns:
            list: Abonelik nesneleri listesi
        """
        try:
            params = {"limit": limit}
            if customer:
                params["customer"] = customer
            if status:
                params["status"] = status
                
            return stripe.Subscription.list(**params)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe abonelikler alınırken hata: {e}")
            return None
    
    def get_invoice(self, invoice_id):
        """Belirli bir fatura al
        
        Args:
            invoice_id: Fatura ID'si
            
        Returns:
            dict: Fatura nesnesi
        """
        try:
            return stripe.Invoice.retrieve(invoice_id)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe fatura alınırken hata: {e}")
            return None
    
    def get_invoices(self, limit=100, customer=None, status=None):
        """Faturaları al
        
        Args:
            limit: En fazla kaç fatura alınacağı
            customer: Belirli bir müşterinin faturaları (müşteri ID'si)
            status: Filtrelenecek durum (draft, open, paid, uncollectible, void)
            
        Returns:
            list: Fatura nesneleri listesi
        """
        try:
            params = {"limit": limit}
            if customer:
                params["customer"] = customer
            if status:
                params["status"] = status
                
            return stripe.Invoice.list(**params)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe faturalar alınırken hata: {e}")
            return None
    
    def create_invoice(self, customer, auto_advance=True, collection_method="charge_automatically"):
        """Yeni fatura oluştur
        
        Args:
            customer: Müşteri ID'si
            auto_advance: Fatura otomatik olarak ilerlesin mi
            collection_method: Tahsilat yöntemi
            
        Returns:
            dict: Oluşturulan fatura nesnesi
        """
        try:
            return stripe.Invoice.create(
                customer=customer,
                auto_advance=auto_advance,
                collection_method=collection_method
            )
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe fatura oluşturulurken hata: {e}")
            return None
    
    def finalize_invoice(self, invoice_id):
        """Faturayı sonlandır
        
        Args:
            invoice_id: Fatura ID'si
            
        Returns:
            dict: Sonlandırılan fatura nesnesi
        """
        try:
            return stripe.Invoice.finalize_invoice(invoice_id)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe fatura sonlandırılırken hata: {e}")
            return None
    
    def pay_invoice(self, invoice_id):
        """Faturayı öde
        
        Args:
            invoice_id: Fatura ID'si
            
        Returns:
            dict: Ödenen fatura nesnesi
        """
        try:
            return stripe.Invoice.pay(invoice_id)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe fatura ödenirken hata: {e}")
            return None
    
    def create_refund(self, charge, amount=None, reason=None):
        """İade oluştur
        
        Args:
            charge: Ödeme ID'si
            amount: İade tutarı (None ise tamamı iade edilir)
            reason: İade nedeni (duplicate, fraudulent, requested_by_customer)
            
        Returns:
            dict: Oluşturulan iade nesnesi
        """
        try:
            params = {"charge": charge}
            if amount:
                params["amount"] = amount
            if reason:
                params["reason"] = reason
                
            return stripe.Refund.create(**params)
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe iade oluşturulurken hata: {e}")
            return None
    
    def validate_webhook(self, payload, signature, endpoint_secret=None):
        """Webhook imzasını doğrula
        
        Args:
            payload: Webhook verisi (HTTP isteğinin gövdesi)
            signature: Stripe-Signature başlığı
            endpoint_secret: Webhook endpoint gizli anahtarı (None ise init'te verilen kullanılır)
            
        Returns:
            dict: Doğrulanmış olay nesnesi
        """
        try:
            if not endpoint_secret:
                endpoint_secret = self.webhook_secret
                
            if not endpoint_secret:
                raise ValueError("Webhook gizli anahtarı belirtilmedi")
                
            return stripe.Webhook.construct_event(
                payload, signature, endpoint_secret
            )
        except stripe.error.SignatureVerificationError as e:
            self.logger.error(f"Stripe webhook imzası doğrulanamadı: {e}")
            return None
        except ValueError as e:
            self.logger.error(f"Webhook doğrulanırken hata: {e}")
            return None