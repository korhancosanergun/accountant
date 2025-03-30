#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Para Birimi İşlemleri Modülü
Para birimi formatlamaları ve dönüşümleri için yardımcı fonksiyonlar
"""

import locale
import re
from decimal import Decimal, ROUND_HALF_UP
import logging

# Modül için logger
logger = logging.getLogger(__name__)

# Döviz kurları (sabit değerler)
# Gerçek uygulamada bir API üzerinden güncel kurlar alınmalıdır
EXCHANGE_RATES = {
    "GBP": {"GBP": 1.0, "EUR": 1.16, "USD": 1.25, "TRY": 40.5},
    "EUR": {"GBP": 0.86, "EUR": 1.0, "USD": 1.08, "TRY": 35.0},
    "USD": {"GBP": 0.80, "EUR": 0.93, "USD": 1.0, "TRY": 32.4},
    "TRY": {"GBP": 0.025, "EUR": 0.029, "USD": 0.031, "TRY": 1.0}
}

# Para birimi sembolleri
CURRENCY_SYMBOLS = {
    "GBP": "£",
    "EUR": "€",
    "USD": "$",
    "TRY": "₺"
}


def format_currency(amount, currency="GBP", decimal_places=2, include_symbol=True, 
                    decimal_separator=".", thousands_separator=","):
    """Para birimini formatla
    
    Args:
        amount: Miktar
        currency: Para birimi kodu
        decimal_places: Ondalık basamak sayısı
        include_symbol: Para birimi sembolü eklensin mi
        decimal_separator: Ondalık ayırıcı
        thousands_separator: Binlik ayırıcı
        
    Returns:
        str: Formatlanmış para birimi
    """
    try:
        # Decimal'e dönüştür
        if isinstance(amount, str):
            # Para birimi sembollerini ve boşlukları temizle
            clean_amount = amount.replace(CURRENCY_SYMBOLS.get(currency, ""), "").strip()
            clean_amount = clean_amount.replace(",", ".")
            amount = Decimal(clean_amount)
        else:
            amount = Decimal(str(amount))
        
        # Yuvarlama
        amount = amount.quantize(Decimal('0.' + '0' * decimal_places), rounding=ROUND_HALF_UP)
        
        # Formatla
        integer_part, decimal_part = str(amount).split(".") if "." in str(amount) else (str(amount), "0")
        
        # Binlik ayırıcı ekle
        if thousands_separator:
            parts = []
            for i in range(len(integer_part), 0, -3):
                start = max(0, i - 3)
                parts.insert(0, integer_part[start:i])
            integer_part = thousands_separator.join(parts)
        
        # Ondalık kısmı düzenle
        decimal_part = decimal_part.ljust(decimal_places, '0')
        decimal_part = decimal_part[:decimal_places]
        
        # Para birimi sembolü
        symbol = CURRENCY_SYMBOLS.get(currency, "") if include_symbol else ""
        
        # Formatlanmış değeri döndür
        if symbol and symbol in ["£", "$"]:
            # Sembol başta
            return f"{symbol}{integer_part}{decimal_separator}{decimal_part}"
        elif symbol:
            # Sembol sonda
            return f"{integer_part}{decimal_separator}{decimal_part} {symbol}"
        else:
            # Sembolsüz
            return f"{integer_part}{decimal_separator}{decimal_part}"
        
    except Exception as e:
        logger.error(f"Para birimi formatlanırken hata oluştu: {e}")
        return str(amount)


def parse_currency(value):
    """Para birimi değerini sayıya dönüştür
    
    Args:
        value: Para birimi değeri
        
    Returns:
        float: Sayısal değer
        
    Raises:
        ValueError: Geçersiz para birimi değeri
    """
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    
    if not isinstance(value, str):
        raise ValueError(f"Geçersiz para birimi değeri: {value}")
    
    # Para birimi sembollerini ve whitespace'leri temizle
    symbols = list(CURRENCY_SYMBOLS.values())
    clean_value = value
    
    for symbol in symbols:
        clean_value = clean_value.replace(symbol, "")
    
    clean_value = clean_value.strip()
    
    # Binlik ayırıcıları temizle ve nokta/virgül standardize et
    if "," in clean_value and "." in clean_value:
        # İngiltere/ABD formatı (örn: 1,234.56)
        if clean_value.rindex(".") > clean_value.rindex(","):
            clean_value = clean_value.replace(",", "")
        # Avrupa formatı (örn: 1.234,56)
        else:
            clean_value = clean_value.replace(".", "").replace(",", ".")
    elif "," in clean_value:
        # Virgül ondalık ayırıcı olabilir
        if clean_value.count(",") == 1 and clean_value.rindex(",") > len(clean_value) - 4:
            clean_value = clean_value.replace(",", ".")
        else:
            clean_value = clean_value.replace(",", "")
    
    try:
        return float(clean_value)
    except ValueError:
        raise ValueError(f"Para birimi değeri sayıya dönüştürülemedi: {value}")


def convert_currency(amount, from_currency, to_currency, decimal_places=2):
    """Para birimi dönüştür
    
    Args:
        amount: Miktar
        from_currency: Kaynak para birimi
        to_currency: Hedef para birimi
        decimal_places: Ondalık basamak sayısı
        
    Returns:
        float: Dönüştürülmüş miktar
    """
    try:
        # Miktar sayısal değilse dönüştür
        if not isinstance(amount, (int, float, Decimal)):
            amount = parse_currency(amount)
        
        # Aynı para birimi ise dönüştürme
        if from_currency == to_currency:
            return amount
        
        # Döviz kurunu al
        if from_currency not in EXCHANGE_RATES or to_currency not in EXCHANGE_RATES[from_currency]:
            raise ValueError(f"Döviz kuru bulunamadı: {from_currency} -> {to_currency}")
        
        rate = EXCHANGE_RATES[from_currency][to_currency]
        
        # Dönüştür ve yuvarla
        converted = amount * rate
        if decimal_places is not None:
            converted = round(converted, decimal_places)
        
        return converted
        
    except Exception as e:
        logger.error(f"Para birimi dönüştürülürken hata oluştu: {e}")
        raise


def format_percentage(value, decimal_places=2, include_symbol=True):
    """Yüzde değerini formatla
    
    Args:
        value: Değer (0.15 = %15)
        decimal_places: Ondalık basamak sayısı
        include_symbol: Yüzde sembolü eklensin mi
        
    Returns:
        str: Formatlanmış yüzde
    """
    try:
        # Decimal'e dönüştür
        if isinstance(value, str):
            # Yüzde sembolünü temizle
            clean_value = value.replace("%", "").strip()
            
            # Değer 0-1 aralığında mı yoksa doğrudan yüzde mi kontrol et
            try:
                decimal_value = Decimal(clean_value)
                if decimal_value > 1 and decimal_value <= 100:
                    # Doğrudan yüzde değeri
                    value = decimal_value
                else:
                    # 0-1 aralığında değer
                    value = decimal_value * 100
            except:
                # Geçersiz değer
                return value
        else:
            # Sayısal değer, yüzde olarak formatla
            if 0 <= value <= 1:
                value = value * 100
        
        # Yuvarla
        rounded = round(float(value), decimal_places)
        
        # Formatla
        if decimal_places > 0:
            formatted = f"{rounded:.{decimal_places}f}"
        else:
            formatted = f"{int(rounded)}"
        
        # Sembol ekle
        if include_symbol:
            return f"{formatted}%"
        else:
            return formatted
            
    except Exception as e:
        logger.error(f"Yüzde formatlanırken hata oluştu: {e}")
        return str(value)


def get_currency_info(currency_code):
    """Para birimi bilgilerini döndür
    
    Args:
        currency_code: Para birimi kodu
        
    Returns:
        dict: Para birimi bilgileri
    """
    currency_info = {
        "GBP": {
            "name": "Pound Sterling",
            "name_tr": "İngiliz Sterlini",
            "symbol": "£",
            "decimal_places": 2,
            "decimal_separator": ".",
            "thousands_separator": ",",
            "symbol_position": "prefix",  # prefix: başta, suffix: sonda
            "iso_numeric": "826"
        },
        "EUR": {
            "name": "Euro",
            "name_tr": "Euro",
            "symbol": "€",
            "decimal_places": 2,
            "decimal_separator": ",",
            "thousands_separator": ".",
            "symbol_position": "suffix",
            "iso_numeric": "978"
        },
        "USD": {
            "name": "US Dollar",
            "name_tr": "Amerikan Doları",
            "symbol": "$",
            "decimal_places": 2,
            "decimal_separator": ".",
            "thousands_separator": ",",
            "symbol_position": "prefix",
            "iso_numeric": "840"
        },
        "TRY": {
            "name": "Turkish Lira",
            "name_tr": "Türk Lirası",
            "symbol": "₺",
            "decimal_places": 2,
            "decimal_separator": ",",
            "thousands_separator": ".",
            "symbol_position": "suffix",
            "iso_numeric": "949"
        }
    }
    
    return currency_info.get(currency_code, None)


def get_vat_rates(country_code="GB"):
    """Ülkeye göre KDV oranlarını döndür
    
    Args:
        country_code: Ülke kodu
        
    Returns:
        dict: KDV oranları
    """
    vat_rates = {
        "GB": {  # Birleşik Krallık
            "standard": 20.0,       # Standart oran
            "reduced": 5.0,         # İndirimli oran
            "zero": 0.0,            # Sıfır oran
            "exempt": None          # Muaf
        },
        "TR": {  # Türkiye
            "standard": 20.0,       # Standart oran
            "reduced_1": 10.0,      # İndirimli oran 1
            "reduced_2": 1.0,       # İndirimli oran 2
            "zero": 0.0,            # Sıfır oran
            "exempt": None          # Muaf
        }
    }
    
    return vat_rates.get(country_code, None)


def calculate_vat(amount, vat_rate):
    """KDV tutarını hesapla
    
    Args:
        amount: KDV hariç tutar
        vat_rate: KDV oranı (% olarak)
        
    Returns:
        float: KDV tutarı
    """
    try:
        # Miktar sayısal değilse dönüştür
        if not isinstance(amount, (int, float, Decimal)):
            amount = parse_currency(amount)
        
        # KDV oranı sayısal değilse dönüştür
        if isinstance(vat_rate, str):
            vat_rate = float(vat_rate.replace("%", "").strip())
        
        # KDV hesapla
        vat_amount = amount * (vat_rate / 100)
        
        # İki ondalık basamağa yuvarla
        return round(vat_amount, 2)
        
    except Exception as e:
        logger.error(f"KDV hesaplanırken hata oluştu: {e}")
        raise


def extract_vat(total_amount, vat_rate, is_inclusive=True):
    """Toplam tutardan KDV tutarını ve KDV hariç tutarı hesapla
    
    Args:
        total_amount: Toplam tutar
        vat_rate: KDV oranı (% olarak)
        is_inclusive: Toplam tutar KDV dahil mi
        
    Returns:
        tuple: (KDV hariç tutar, KDV tutarı)
    """
    try:
        # Tutar sayısal değilse dönüştür
        if not isinstance(total_amount, (int, float, Decimal)):
            total_amount = parse_currency(total_amount)
        
        # KDV oranı sayısal değilse dönüştür
        if isinstance(vat_rate, str):
            vat_rate = float(vat_rate.replace("%", "").strip())
        
        if is_inclusive:
            # KDV dahil toplam tutardan KDV hariç tutarı hesapla
            # KDV hariç tutar = Toplam tutar / (1 + KDV oranı/100)
            net_amount = total_amount / (1 + (vat_rate / 100))
            vat_amount = total_amount - net_amount
        else:
            # KDV hariç tutar zaten verili
            net_amount = total_amount
            vat_amount = calculate_vat(net_amount, vat_rate)
        
        # İki ondalık basamağa yuvarla
        return round(net_amount, 2), round(vat_amount, 2)
        
    except Exception as e:
        logger.error(f"KDV hesaplanırken hata oluştu: {e}")
        raise


def round_to_nearest(amount, nearest=0.01):
    """En yakın değere yuvarla
    
    Args:
        amount: Miktar
        nearest: Yuvarlanacak değer (0.01 = 1 kuruş, 0.05 = 5 kuruş, vb.)
        
    Returns:
        float: Yuvarlanmış miktar
    """
    try:
        # Miktar sayısal değilse dönüştür
        if not isinstance(amount, (int, float, Decimal)):
            amount = parse_currency(amount)
        
        # Yuvarla
        return round(amount / nearest) * nearest
        
    except Exception as e:
        logger.error(f"Yuvarlama yapılırken hata oluştu: {e}")
        return amount


def number_to_words_tr(num):
    """Sayıyı Türkçe yazıya çevir
    
    Args:
        num: Sayı
        
    Returns:
        str: Türkçe yazı
    """
    birler = ["", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
    onlar = ["", "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen", "doksan"]
    
    def _convert_less_than_thousand(n):
        if n == 0:
            return ""
        
        result = ""
        
        # Yüzler basamağı
        yuzler = n // 100
        if yuzler > 0:
            if yuzler == 1:
                result += "yüz"
            else:
                result += birler[yuzler] + "yüz"
        
        # Onlar ve birler basamağı
        onlar_birler = n % 100
        if onlar_birler > 0:
            result += onlar[onlar_birler // 10] + birler[onlar_birler % 10]
        
        return result
    
    if num == 0:
        return "sıfır"
    
    # Negatif sayı kontrolü
    negative = False
    if num < 0:
        negative = True
        num = abs(num)
    
    # Para birimi kısmı
    if isinstance(num, (float, Decimal)):
        num_str = str(num)
        if "." in num_str:
            whole, fraction = num_str.split(".")
            
            # Tam kısmı
            whole_part = int(whole)
            
            # Kuruş kısmı
            fraction = fraction[:2].ljust(2, "0")  # İki ondalık basamağa tamamla
            fraction_part = int(fraction)
            
            if whole_part == 0 and fraction_part == 0:
                return "sıfır lira"
            
            result = ""
            
            # Tam kısmı
            if whole_part > 0:
                # Milyar
                milyar = whole_part // 1_000_000_000
                if milyar > 0:
                    if milyar == 1:
                        result += "bir milyar"
                    else:
                        result += _convert_less_than_thousand(milyar) + " milyar"
                
                # Milyon
                milyon = (whole_part % 1_000_000_000) // 1_000_000
                if milyon > 0:
                    if milyon == 1:
                        result += "bir milyon"
                    else:
                        result += _convert_less_than_thousand(milyon) + " milyon"
                
                # Bin
                bin_hanesi = (whole_part % 1_000_000) // 1000
                if bin_hanesi > 0:
                    if bin_hanesi == 1:
                        result += "bin"
                    else:
                        result += _convert_less_than_thousand(bin_hanesi) + " bin"
                
                # Son üç hane
                son_uc_hane = whole_part % 1000
                if son_uc_hane > 0:
                    result += _convert_less_than_thousand(son_uc_hane)
                
                result += " lira"
            
            # Kuruş kısmı
            if fraction_part > 0:
                if whole_part > 0:
                    result += " "
                
                result += _convert_less_than_thousand(fraction_part) + " kuruş"
            
            return "eksi " + result if negative else result
    
    # Tam sayı
    result = ""
    
    # Milyar
    milyar = num // 1_000_000_000
    if milyar > 0:
        if milyar == 1:
            result += "bir milyar"
        else:
            result += _convert_less_than_thousand(milyar) + " milyar"
    
    # Milyon
    milyon = (num % 1_000_000_000) // 1_000_000
    if milyon > 0:
        if result:
            result += " "
        
        if milyon == 1:
            result += "bir milyon"
        else:
            result += _convert_less_than_thousand(milyon) + " milyon"
    
    # Bin
    bin_hanesi = (num % 1_000_000) // 1000
    if bin_hanesi > 0:
        if result:
            result += " "
        
        if bin_hanesi == 1:
            result += "bin"
        else:
            result += _convert_less_than_thousand(bin_hanesi) + " bin"
    
    # Son üç hane
    son_uc_hane = num % 1000
    if son_uc_hane > 0:
        if result:
            result += " "
        
        result += _convert_less_than_thousand(son_uc_hane)
    
    return "eksi " + result if negative else result


def number_to_words_en(num):
    """Sayıyı İngilizce yazıya çevir
    
    Args:
        num: Sayı
        
    Returns:
        str: İngilizce yazı
    """
    ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
            "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
            "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    
    def _convert_less_than_thousand(n):
        if n == 0:
            return ""
        
        # Yüzler basamağı
        hundreds = n // 100
        remainder = n % 100
        
        result = ""
        
        if hundreds > 0:
            result += ones[hundreds] + " hundred"
            if remainder > 0:
                result += " and "
        
        # Onlar ve birler basamağı
        if remainder < 20:
            result += ones[remainder]
        else:
            result += tens[remainder // 10]
            if remainder % 10 > 0:
                result += "-" + ones[remainder % 10]
        
        return result
    
    if num == 0:
        return "zero"
    
    # Negatif sayı kontrolü
    negative = False
    if num < 0:
        negative = True
        num = abs(num)
    
    # Para birimi kısmı
    if isinstance(num, (float, Decimal)):
        num_str = str(num)
        if "." in num_str:
            whole, fraction = num_str.split(".")
            
            # Tam kısmı
            whole_part = int(whole)
            
            # Kuruş kısmı
            fraction = fraction[:2].ljust(2, "0")  # İki ondalık basamağa tamamla
            fraction_part = int(fraction)
            
            if whole_part == 0 and fraction_part == 0:
                return "zero pounds"
            
            result = ""
            
            # Tam kısmı
            if whole_part > 0:
                # Milyar
                billions = whole_part // 1_000_000_000
                if billions > 0:
                    result += _convert_less_than_thousand(billions) + " billion"
                    if whole_part % 1_000_000_000 > 0:
                        result += " "
                
                # Milyon
                millions = (whole_part % 1_000_000_000) // 1_000_000
                if millions > 0:
                    result += _convert_less_than_thousand(millions) + " million"
                    if whole_part % 1_000_000 > 0:
                        result += " "
                
                # Bin
                thousands = (whole_part % 1_000_000) // 1000
                if thousands > 0:
                    result += _convert_less_than_thousand(thousands) + " thousand"
                    if whole_part % 1000 > 0:
                        if whole_part % 1000 < 100:
                            result += " and "
                        else:
                            result += " "
                
                # Son üç hane
                last_three = whole_part % 1000
                if last_three > 0:
                    result += _convert_less_than_thousand(last_three)
                
                result += " pound" + ("s" if whole_part != 1 else "")
            
            # Kuruş kısmı
            if fraction_part > 0:
                if whole_part > 0:
                    result += " and "
                
                result += _convert_less_than_thousand(fraction_part) + " pence"
            
            return "minus " + result if negative else result
    
    # Tam sayı
    result = ""
    
    # Milyar
    billions = num // 1_000_000_000
    if billions > 0:
        result += _convert_less_than_thousand(billions) + " billion"
        if num % 1_000_000_000 > 0:
            result += " "
    
    # Milyon
    millions = (num % 1_000_000_000) // 1_000_000
    if millions > 0:
        result += _convert_less_than_thousand(millions) + " million"
        if num % 1_000_000 > 0:
            result += " "
    
    # Bin
    thousands = (num % 1_000_000) // 1000
    if thousands > 0:
        result += _convert_less_than_thousand(thousands) + " thousand"
        if num % 1000 > 0:
            if num % 1000 < 100:
                result += " and "
            else:
                result += " "
    
    # Son üç hane
    last_three = num % 1000
    if last_three > 0:
        result += _convert_less_than_thousand(last_three)
    
    return "minus " + result if negative else result
