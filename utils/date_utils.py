#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UK Muhasebe Yazılımı - Tarih İşlemleri Modülü
Tarih formatları ve hesaplamaları için yardımcı fonksiyonlar
"""

from datetime import datetime, date, timedelta
import calendar


def get_current_tax_year():
    """Geçerli İngiltere vergi yılını döndür
    
    İngiltere vergi yılı 6 Nisan - 5 Nisan aralığındadır.
    
    Returns:
        str: Vergi yılı (örn: "2023-24")
    """
    today = date.today()
    current_year = today.year
    
    # 6 Nisan öncesiyse, vergi yılı geçen yıldan başlar
    if today.month < 4 or (today.month == 4 and today.day < 6):
        tax_year_start = current_year - 1
    else:
        tax_year_start = current_year
    
    tax_year_end = tax_year_start + 1
    
    # "2023-24" formatında vergi yılını döndür
    return f"{tax_year_start}-{str(tax_year_end)[-2:]}"


def get_tax_year_dates(tax_year):
    """İngiltere vergi yılının başlangıç ve bitiş tarihlerini döndür
    
    Args:
        tax_year: Vergi yılı (örn: "2023-24")
    
    Returns:
        tuple: Başlangıç ve bitiş tarihleri (start_date, end_date)
        
    Raises:
        ValueError: Geçersiz vergi yılı
    """
    try:
        # Vergi yılından yılları ayıkla
        parts = tax_year.split("-")
        if len(parts) != 2:
            raise ValueError(f"Geçersiz vergi yılı formatı: {tax_year}")
        
        start_year = int(parts[0])
        end_year = int(f"20{parts[1]}") if len(parts[1]) == 2 else int(parts[1])
        
        # Tutarlılık kontrolü
        if end_year != start_year + 1:
            raise ValueError(f"Geçersiz vergi yılı: {tax_year}")
        
        # Tarih nesneleri oluştur
        start_date = date(start_year, 4, 6)
        end_date = date(end_year, 4, 5)
        
        return start_date, end_date
    
    except Exception as e:
        raise ValueError(f"Vergi yılı ayrıştırılamadı: {tax_year}. Hata: {e}")


def format_date(date_value, output_format="%Y-%m-%d"):
    """Tarih formatla
    
    Args:
        date_value: Formatlanacak tarih (str, datetime veya date)
        output_format: Çıktı formatı
    
    Returns:
        str: Formatlanmış tarih
        
    Raises:
        ValueError: Geçersiz tarih
    """
    if isinstance(date_value, (datetime, date)):
        return date_value.strftime(output_format)
    
    if isinstance(date_value, str):
        # Yaygın tarih formatlarını dene
        formats = [
            "%Y-%m-%d",       # 2023-04-06
            "%d/%m/%Y",       # 06/04/2023
            "%d-%m-%Y",       # 06-04-2023
            "%d.%m.%Y",       # 06.04.2023
            "%Y/%m/%d",       # 2023/04/06
            "%d %b %Y",       # 06 Apr 2023
            "%d %B %Y",       # 06 April 2023
            "%b %d, %Y",      # Apr 06, 2023
            "%B %d, %Y",      # April 06, 2023
            "%d.%m.%y",       # 06.04.23
            "%d/%m/%y",       # 06/04/23
            "%Y.%m.%d",       # 2023.04.06
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_value, fmt)
                return dt.strftime(output_format)
            except ValueError:
                continue
        
        raise ValueError(f"Tarih formatı tanınamadı: {date_value}")
    
    raise ValueError(f"Geçersiz tarih tipi: {type(date_value)}")


def parse_date(date_str):
    """Tarih string'ini datetime nesnesine dönüştür
    
    Args:
        date_str: Tarih string'i
    
    Returns:
        datetime: Datetime nesnesi
        
    Raises:
        ValueError: Geçersiz tarih formatı
    """
    # Yaygın tarih formatlarını dene
    formats = [
        "%Y-%m-%d",       # 2023-04-06
        "%d/%m/%Y",       # 06/04/2023
        "%d-%m-%Y",       # 06-04-2023
        "%d.%m.%Y",       # 06.04.2023
        "%Y/%m/%d",       # 2023/04/06
        "%d %b %Y",       # 06 Apr 2023
        "%d %B %Y",       # 06 April 2023
        "%b %d, %Y",      # Apr 06, 2023
        "%B %d, %Y",      # April 06, 2023
        "%d.%m.%y",       # 06.04.23
        "%d/%m/%y",       # 06/04/23
        "%Y.%m.%d",       # 2023.04.06
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Tarih formatı tanınamadı: {date_str}")


def get_date_range_for_period(period_type, date_value=None):
    """Belirli bir dönem için tarih aralığı hesapla
    
    Args:
        period_type: Dönem tipi ('month', 'quarter', 'year', 'tax_year')
        date_value: Referans tarihi (None ise bugün)
    
    Returns:
        tuple: Başlangıç ve bitiş tarihleri (start_date, end_date)
    """
    if date_value is None:
        ref_date = date.today()
    elif isinstance(date_value, str):
        ref_date = parse_date(date_value).date()
    elif isinstance(date_value, datetime):
        ref_date = date_value.date()
    else:
        ref_date = date_value
    
    if period_type == "month":
        # Ay başı
        start_date = date(ref_date.year, ref_date.month, 1)
        
        # Ay sonu
        if ref_date.month == 12:
            end_date = date(ref_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(ref_date.year, ref_date.month + 1, 1) - timedelta(days=1)
    
    elif period_type == "quarter":
        # Çeyreği belirle
        quarter = (ref_date.month - 1) // 3 + 1
        
        # Çeyrek başı
        start_month = (quarter - 1) * 3 + 1
        start_date = date(ref_date.year, start_month, 1)
        
        # Çeyrek sonu
        if quarter == 4:
            end_date = date(ref_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(ref_date.year, start_month + 3, 1) - timedelta(days=1)
    
    elif period_type == "year":
        # Yıl başı
        start_date = date(ref_date.year, 1, 1)
        
        # Yıl sonu
        end_date = date(ref_date.year, 12, 31)
    
    elif period_type == "tax_year":
        # İngiltere vergi yılı: 6 Nisan - 5 Nisan
        if ref_date.month < 4 or (ref_date.month == 4 and ref_date.day < 6):
            # Önceki vergi yılındayız
            start_date = date(ref_date.year - 1, 4, 6)
            end_date = date(ref_date.year, 4, 5)
        else:
            # Şimdiki vergi yılındayız
            start_date = date(ref_date.year, 4, 6)
            end_date = date(ref_date.year + 1, 4, 5)
    
    else:
        raise ValueError(f"Geçersiz dönem tipi: {period_type}")
    
    return start_date, end_date


def get_vat_periods(year):
    """Bir yıl için KDV dönemlerini hesapla
    
    Varsayılan olarak üç aylık dönemler:
    Q1: Ocak-Mart, Q2: Nisan-Haziran, Q3: Temmuz-Eylül, Q4: Ekim-Aralık
    
    Args:
        year: Yıl
    
    Returns:
        list: Dönem başlangıç ve bitiş tarihleri listesi ([(start_date, end_date), ...])
    """
    periods = []
    
    # Üç aylık dönemler
    for quarter in range(1, 5):
        # Dönem başlangıç ayı
        start_month = (quarter - 1) * 3 + 1
        
        # Dönem başlangıç tarihi
        start_date = date(year, start_month, 1)
        
        # Dönem bitiş tarihi
        if quarter == 4:
            end_date = date(year, 12, 31)
        else:
            end_month = start_month + 2
            _, last_day = calendar.monthrange(year, end_month)
            end_date = date(year, end_month, last_day)
        
        periods.append((start_date, end_date))
    
    return periods


def get_months_between(start_date, end_date):
    """İki tarih arasındaki ayları hesapla
    
    Args:
        start_date: Başlangıç tarihi (datetime.date)
        end_date: Bitiş tarihi (datetime.date)
    
    Returns:
        list: Ay başlangıç tarihleri listesi ([date, ...])
    """
    months = []
    current_date = date(start_date.year, start_date.month, 1)
    
    while current_date <= end_date:
        months.append(current_date)
        
        # Sonraki ay
        month = current_date.month + 1
        year = current_date.year
        
        if month > 12:
            month = 1
            year += 1
        
        current_date = date(year, month, 1)
    
    return months


def get_date_diff_days(date1, date2):
    """İki tarih arasındaki gün farkını hesapla
    
    Args:
        date1: Birinci tarih (datetime.date, datetime.datetime veya str)
        date2: İkinci tarih (datetime.date, datetime.datetime veya str)
    
    Returns:
        int: Gün farkı
    """
    # String ise tarihe dönüştür
    if isinstance(date1, str):
        date1 = parse_date(date1).date()
    elif isinstance(date1, datetime):
        date1 = date1.date()
    
    if isinstance(date2, str):
        date2 = parse_date(date2).date()
    elif isinstance(date2, datetime):
        date2 = date2.date()
    
    # Gün farkını hesapla
    delta = date2 - date1
    return abs(delta.days)


def get_date_diff_months(date1, date2):
    """İki tarih arasındaki ay farkını hesapla
    
    Args:
        date1: Birinci tarih (datetime.date, datetime.datetime veya str)
        date2: İkinci tarih (datetime.date, datetime.datetime veya str)
    
    Returns:
        int: Ay farkı
    """
    # String ise tarihe dönüştür
    if isinstance(date1, str):
        date1 = parse_date(date1).date()
    elif isinstance(date1, datetime):
        date1 = date1.date()
    
    if isinstance(date2, str):
        date2 = parse_date(date2).date()
    elif isinstance(date2, datetime):
        date2 = date2.date()
    
    # Ay farkını hesapla
    months_diff = (date2.year - date1.year) * 12 + (date2.month - date1.month)
    
    return abs(months_diff)


def add_months(date_value, months):
    """Tarihe belirli sayıda ay ekle
    
    Args:
        date_value: Tarih (datetime.date, datetime.datetime veya str)
        months: Eklenecek ay sayısı
    
    Returns:
        datetime.date: Yeni tarih
    """
    # String ise tarihe dönüştür
    if isinstance(date_value, str):
        dt = parse_date(date_value)
    elif isinstance(date_value, datetime):
        dt = date_value
    else:
        dt = datetime.combine(date_value, datetime.min.time())
    
    # Ay ekle
    month = dt.month + months
    year = dt.year + month // 12
    month = month % 12
    
    if month == 0:
        month = 12
        year -= 1
    
    # Gün değeri yeni ayın son gününü aşmasın
    _, last_day = calendar.monthrange(year, month)
    day = min(dt.day, last_day)
    
    return date(year, month, day)


def is_date_between(check_date, start_date, end_date):
    """Tarih belirli bir aralıkta mı kontrol et
    
    Args:
        check_date: Kontrol edilecek tarih
        start_date: Başlangıç tarihi
        end_date: Bitiş tarihi
    
    Returns:
        bool: Tarih aralıkta ise True
    """
    # String ise tarihe dönüştür
    if isinstance(check_date, str):
        check_date = parse_date(check_date).date()
    elif isinstance(check_date, datetime):
        check_date = check_date.date()
    
    if isinstance(start_date, str):
        start_date = parse_date(start_date).date()
    elif isinstance(start_date, datetime):
        start_date = start_date.date()
    
    if isinstance(end_date, str):
        end_date = parse_date(end_date).date()
    elif isinstance(end_date, datetime):
        end_date = end_date.date()
    
    # Aralık kontrolü
    return start_date <= check_date <= end_date


def get_uk_date_format(date_value, separator="."):
    """Tarihi İngiltere formatında döndür (DD.MM.YYYY)
    
    Args:
        date_value: Tarih
        separator: Ayırıcı karakter
    
    Returns:
        str: Formatlanmış tarih
    """
    return format_date(date_value, f"%d{separator}%m{separator}%Y")


def get_iso_date_format(date_value):
    """Tarihi ISO formatında döndür (YYYY-MM-DD)
    
    Args:
        date_value: Tarih
    
    Returns:
        str: Formatlanmış tarih
    """
    return format_date(date_value, "%Y-%m-%d")


def is_valid_date(date_str):
    """Tarih string'i geçerli mi kontrol et
    
    Args:
        date_str: Tarih string'i
    
    Returns:
        bool: Geçerli tarih ise True
    """
    try:
        parse_date(date_str)
        return True
    except ValueError:
        return False


def get_month_name(month, abbreviated=False, locale="tr"):
    """Ay adını döndür
    
    Args:
        month: Ay numarası (1-12)
        abbreviated: Kısaltılmış ad mı
        locale: Dil kodu ('tr', 'en')
    
    Returns:
        str: Ay adı
    """
    if not 1 <= month <= 12:
        raise ValueError(f"Geçersiz ay numarası: {month}")
    
    if locale == "tr":
        month_names = [
            "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]
        month_abbr = [
            "Oca", "Şub", "Mar", "Nis", "May", "Haz",
            "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"
        ]
    else:  # "en"
        month_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        month_abbr = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
        ]
    
    if abbreviated:
        return month_abbr[month - 1]
    else:
        return month_names[month - 1]
