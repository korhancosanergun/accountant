# UK Muhasebe Yazılımı

İngiltere vergi sistemi ile entegre çalışan, küçük işletmeler için geliştirilmiş masaüstü muhasebe yazılımı

## Proje Hakkında

Bu yazılım, İngiltere'de faaliyet gösteren küçük işletmelerin muhasebe işlemlerini takip etmesi, HMRC (İngiltere Gelir ve Gümrük İdaresi) ile entegre çalışması ve vergi beyannamelerini kolayca hazırlayıp göndermesi amacıyla geliştirilmiştir. Excel benzeri arayüz ile kullanım kolaylığı sağlar.

### Özellikler

- Excel benzeri kullanıcı arayüzü
- HMRC Making Tax Digital (MTD) entegrasyonu
- KDV beyanname hazırlama ve gönderme
- Gelir Vergisi beyanname hazırlama ve gönderme
- Fatura oluşturma ve takibi
- Gelir ve gider kaydı ve takibi
- Gösterge paneli ile finansal durum özeti
- Ödemeleri takip etme
- CSV/Excel/JSON formatlarında veri içe/dışa aktarma
- Modüler tasarım ve genişletilebilirlik
- Türkçe ve İngilizce dil desteği

## Kurulum

### Gereksinimler

- Python 3.8 veya üzeri
- PyQt5
- Diğer bağımlılıklar

```bash
# Bağımlılıkları yükleme
pip install -r requirements.txt
```

### Kurulum Adımları

1. Repoyu klonlayın:
```bash
git clone https://github.com/kullanici/uk-muhasebe.git
cd uk-muhasebe
```

2. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

3. Uygulamayı çalıştırın:
```bash
python main.py
```

## Kullanım

### İlk Kurulum

1. Uygulamayı ilk çalıştırdığınızda şirket bilgilerinizi girmeniz istenecektir.
2. HMRC entegrasyonu için API anahtarlarınızı ekleyin.
3. Varsayılan hesap planı otomatik olarak oluşturulacaktır.

### Temel İşlemler

- **Muhasebe Defteri**: İşlem kayıtlarınızı görüntüleyin ve yönetin
- **Fatura Oluşturma**: Satış veya alış faturası oluşturun
- **Gider Ekleme**: Giderlerinizi kaydedin ve kategorize edin
- **KDV Beyannamesi**: Dönemsel KDV beyannamesi hazırlayın ve gönderin
- **Gelir Vergisi Beyannamesi**: Yıllık gelir vergisi beyannamesi hazırlayın ve gönderin
- **Raporlar**: Finansal durumunuzu analiz edin
- **Yedekleme**: Verilerinizi yedekleyin

## Proje Yapısı

```
uk_muhasebe/
│
├── main.py                     # Ana uygulama başlatıcı
├── config.json                 # Uygulama ayarları
│
├── gui/                        # Kullanıcı arayüzü modülleri
│   ├── __init__.py
│   ├── main_window.py          # Ana uygulama penceresi
│   ├── spreadsheet_view.py     # Excel benzeri tablo görünümü
│   ├── dashboard.py            # Özet bilgiler
│   ├── tax_forms.py            # Vergi formları
│   └── dialogs/                # Dialog pencereleri
│       ├── __init__.py
│       ├── invoice_dialog.py   # Fatura dialog
│       ├── expense_dialog.py   # Gider dialog
│       └── settings_dialog.py  # Ayarlar dialog
│
├── core/                       # Temel iş mantığı
│   ├── __init__.py
│   ├── account.py              # Hesap sınıfları
│   ├── ledger.py               # Muhasebe defteri
│   ├── transaction.py          # İşlem sınıfları
│   ├── invoice.py              # Fatura işlemleri
│   └── tax.py                  # Vergi hesaplamaları
│
├── data/                       # Veri işleme
│   ├── __init__.py
│   ├── database.py             # JSON veritabanı
│   ├── import_export.py        # Veri aktarım
│   └── backup.py               # Yedekleme
│
├── hmrc/                       # HMRC entegrasyonu
│   ├── __init__.py
│   ├── api_client.py           # HMRC API istemcisi
│   ├── mtd.py                  # Making Tax Digital
│   ├── vat.py                  # KDV beyanname
│   └── income_tax.py           # Gelir vergisi
│
├── utils/                      # Yardımcı işlevler
│   ├── __init__.py
│   ├── logger.py               # Loglama
│   ├── currency.py             # Para birimi işlemleri
│   └── date_utils.py           # Tarih işlemleri
│
└── resources/                  # Statik kaynaklar
    ├── icons/                  # İkonlar
    ├── templates/              # Rapor şablonları
    └── localization/           # Dil dosyaları
```

## HMRC Entegrasyonu

Uygulama, Making Tax Digital (MTD) kapsamında HMRC API'leri ile entegre çalışmaktadır. Bu entegrasyon aşağıdaki özellikleri sağlar:

- **KDV Beyannameleri**: MTD VAT API üzerinden KDV beyannamelerini doğrudan gönderme
- **Gelir Vergisi Beyannameleri**: MTD Income Tax API üzerinden beyanname gönderme
- **Yükümlülük Bilgileri**: Vergi dönemleri ve gönderimleri hakkında bilgi alma
- **Güvenli OAuth 2.0 Kimlik Doğrulama**: HMRC standartlarına uygun güvenli kimlik doğrulama

### HMRC API Kullanımı İçin Gereklilikler

HMRC API'lerini kullanabilmek için:

1. HMRC Developer Hub'dan bir geliştirici hesabı oluşturmalısınız
2. MTD VAT ve/veya MTD Income Tax API'leri için uygulama kaydı yapmalısınız
3. Aldığınız Client ID ve Client Secret bilgilerini uygulamanın yapılandırma kısmına girmelisiniz

## Veritabanı

Uygulama, JSON formatında yerel bir veritabanı kullanır. Bu, basit kurulum ve taşınabilirlik sağlar. İsteğe bağlı olarak Google Sheets veya başka bir veritabanı ile entegre çalışacak şekilde yapılandırılabilir.

## Geliştirme

### Geliştirme Ortamı Kurulumu

```bash
# Geliştirme bağımlılıklarını yükleme
pip install -r requirements-dev.txt

# Testleri çalıştırma
pytest
```

### Katkıda Bulunma

1. Repoyu fork edin
2. Özellik dalı oluşturun (`git checkout -b yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik: Açıklama'`)
4. Dalınızı push edin (`git push origin yeni-ozellik`)
5. Pull request oluşturun

## Lisans

Bu proje [MIT lisansı](LICENSE) altında lisanslanmıştır.

## İletişim

Sorularınız veya önerileriniz için [issue açabilir](https://github.com/kullanici/uk-muhasebe/issues) veya e-posta gönderebilirsiniz.
