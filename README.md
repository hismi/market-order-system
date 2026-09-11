# Yerel Market Siparis Sistemi

Bu proje, yerel bir market icin mobil uyumlu web tabanli siparis sistemi olarak adim adim gelistirilecek.

Ana prensip: frontend guvenilir degildir. Urun fiyati, minimum siparis tutari, gonderim ucreti, stok, rol ve siparis durumu backend tarafindan kontrol edilir.

## Su Anki Asama

Asama 2-4 baslangici:

- Proje klasor yapisi olusturuldu.
- FastAPI uygulama iskeleti eklendi.
- SQLite baglantisi eklendi.
- Admin panelinden ileride degistirilecek temel `market_settings` modeli eklendi.
- Public market ayarlari endpoint'i eklendi.
- Kategori ve urun modelleri eklendi.
- Musteri katalog endpoint'leri eklendi.
- Teslimat bolgesi, siparis ve siparis kalemi modelleri eklendi.
- Siparis olusturma endpoint'i backend fiyat hesaplamasi ile eklendi.
- Musteri ekranina checkout formu eklendi.
- Online odeme yoktur; odeme kapida nakit veya kapida kart/POS olarak alinir.
- Argon2 sifre hash'i ve JWT tabanli giris eklendi.
- `EMPLOYEE` ve `ADMIN` rolleri icin yetki kontrolu eklendi.
- Calisan siparis endpoint'leri ve calisan paneli eklendi.
- Admin market ayarlari endpoint'i ve admin paneli eklendi.
- Admin kategori ve urun yonetimi eklendi.
- Admin teslimat bolgesi yonetimi eklendi.
- WhatsApp sadece canli destek baglantisi olarak eklendi; siparis veya durum bildirimi icin otomatik WhatsApp API kullanilmaz.
- Admin siparis listesi, durum filtresi ve siparis ozeti eklendi.
- Siparis takip endpoint'i ve musteri ekraninda siparis takip formu eklendi.
- Yeni siparisler icin tahmin edilemeyen alfanumerik takip kodu eklendi.
- Public siparis takip cevabi sadece minimum ve maskelenmis musteri bilgisi dondurur.
- Siparis onaylaninca stok dusme, hazirlanan/yoldaki siparis iptal edilirse stok geri ekleme kurali eklendi.
- Admin kullanici/rol yonetimi eklendi.
- Admin siparis raporlari eklendi.
- Admin islem gecmisi ekrani eklendi.
- Admin panelinden urun gorseli yukleme eklendi.
- Admin yedekleme ve geri yukleme ekrani eklendi.
- Admin sistem durumu ekrani eklendi.
- Adminin kendi sifresini mevcut sifreyle degistirebilmesi eklendi.
- Login rate limit eklendi.
- Production guvenlik ayarlari kontrolu eklendi.
- Market calisma saatleri backend tarafindan otomatik siparis kabul kuralina baglandi.
- Musteri ekrani market durumunu periyodik yeniler; admin ve calisan siparis listeleri otomatik yenilenir.

## Calistirma

PowerShell ile:

```powershell
cd "C:\Users\saith\Documents\New project\market-order-system\backend"
py -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\uvicorn app.main:app --reload
```

`backend/.env` dosyasinda `JWT_SECRET`, `SEED_ADMIN_PASSWORD` ve `SEED_EMPLOYEE_PASSWORD` degerlerini kendin belirlemelisin. `APP_TIMEZONE` varsayilan olarak `Europe/Istanbul` gelir; farkli ulke veya sehir icin bunu degistirebilirsin. Guclu secret uretmek icin PowerShell'de su komut kullanilabilir:

```powershell
py -c "import secrets; print(secrets.token_urlsafe(48))"
```

Tarayicida:

- API saglik kontrolu: http://127.0.0.1:8000/health
- API dokumani: http://127.0.0.1:8000/docs
- Public market ayarlari: http://127.0.0.1:8000/api/market-settings/public
- Kategoriler: http://127.0.0.1:8000/api/catalog/categories
- Urunler: http://127.0.0.1:8000/api/catalog/products
- Teslimat bolgeleri: http://127.0.0.1:8000/api/delivery-areas
- Siparis olusturma: `POST /api/orders`
- Siparis takip: `GET /api/orders/track?order_number=MKT-7H3Q-9X2K&phone=0532%20111%2022%2033`

Musteri katalog ekranini ayri bir PowerShell penceresinde calistirmak icin:

```powershell
cd "C:\Users\saith\Documents\New project\market-order-system\frontend\customer"
py -m http.server 5500
```

Tarayicida:

- Musteri katalog ekrani: http://127.0.0.1:5500/

Calisan panelini ayri bir PowerShell penceresinde calistirmak icin:

```powershell
cd "C:\Users\saith\Documents\New project\market-order-system\frontend\employee"
py -m http.server 5501
```

Tarayicida:

- Calisan paneli: http://127.0.0.1:5501/

Local development calisan girisi:

- Kullanici adi: `employee`
- Sifre: `backend/.env` icinde belirledigin `SEED_EMPLOYEE_PASSWORD`

Production'da development sifreleri kullanilmamalidir.

## Production Guvenlik

Canli ortama gecmeden once `backend/.env.production.example` dosyasi ornek alinmalidir.

Production modunda uygulama su riskli ayarlarla baslamaz:

- Eksik, kisa veya placeholder `JWT_SECRET`
- Varsayilan veya zayif seed sifreleri
- `CORS_ORIGINS=*`
- `CORS_ORIGINS` icinde `localhost` veya `127.0.0.1`

Login rate limit varsayilani:

- 10 dakika icinde 5 hatali giris denemesi
- Sonrasinda 15 dakika gecici engelleme
- Basarili giriste sayac sifirlanir

Admin panelini ayri bir PowerShell penceresinde calistirmak icin:

```powershell
cd "C:\Users\saith\Documents\New project\market-order-system\frontend\admin"
py -m http.server 5502
```

Tarayicida:

- Admin paneli: http://127.0.0.1:5502/

Local development admin girisi:

- Kullanici adi: `admin`
- Sifre: `backend/.env` icinde belirledigin `SEED_ADMIN_PASSWORD`

Admin panelinden su ayarlar degistirilebilir:

- Market adi
- Telefon
- WhatsApp numarasi
- Market acik/kapali durumu
- Acilis/kapanis saatleri
- Minimum siparis tutari
- Gonderim ucreti

Market acik olsa bile acilis/kapanis saatleri disindaysa backend yeni siparis kabul etmez. Saat kontrolu `APP_TIMEZONE` degerine gore yapilir.

Admin panelindeki Sistem Durumu ekraninda su bilgiler gorulebilir:

- API ve market acik/kapali durumu
- Marketin su anda siparis kabul edip etmedigi
- Online odemenin kapali oldugu ve sadece kapida odeme kullanildigi
- Gonderim ucretinin her sipariste alindigi
- Urun, kategori, teslimat bolgesi ve siparis ozetleri
- Son siparis, son islem ve son yedek bilgisi
- Varsayilan admin/calisan kullanici adlari icin uyarilar

WhatsApp numarasi girilirse musteri ekraninda "WhatsApp Destek" baglantisi gorunur. Bu baglanti yalnizca musterinin markete kendi istegiyle mesaj yazmasi icindir; siparisler WhatsApp'tan degil backend siparis sistemi uzerinden alinir.

Admin panelinden urun/kategori tarafinda su islemler yapilabilir:

- Kategori ekleme
- Kategori duzenleme
- Kategoriyi aktif/pasif yapma
- Urun ekleme
- Urun gorseli yukleme veya dis gorsel URL'i girme
- Urun fiyatini degistirme
- Urun stok miktarini degistirme
- Urunu aktif/pasif yapma

Admin panelinden teslimat bolgesi tarafinda su islemler yapilabilir:

- Teslimat bolgesi ekleme
- Teslimat bolgesi duzenleme
- Teslimat bolgesini aktif/pasif yapma
- Pasif bolgeleri musteri checkout listesinden gizleme

Admin panelinden siparis tarafinda su islemler yapilabilir:

- Siparisleri durumuna gore listeleme
- Admin ve calisan panelinde siparis listesinin otomatik yenilenmesi
- Aktif siparis, yeni siparis, teslim edilen ciro ve aktif toplam ozetini gorme
- Yeni siparisi onaylama veya iptal etme
- Onaylanan sipariste urun stoklarini otomatik dusme
- Hazirlanan siparisi yola cikarma
- Yoldaki siparisi teslim edildi olarak isaretleme
- Hazirlanan veya yoldaki siparis iptal edilirse stoklari geri ekleme

Musteri siparis takip ekraninda su bilgiler gorulebilir:

- Siparis numarasi, siparis tarihi ve siparis durumu
- Maskelenmis musteri adi ve maskelenmis telefon
- Maskelenmis teslimat bolgesi
- Odeme yontemi, urun bulunamazsa tercihi ve iptal nedeni
- Siparis kalemleri, adetler, birim fiyatlar, ara toplam, gonderim ucreti ve genel toplam

Public siparis takip API'si tam ad soyad, tam telefon, sokak, apartman, daire, acik adres, adres tarifi, siparis notu, internal ID veya teknik token dondurmez. Bu bilgiler sadece yetkili calisan ve admin ekranlarinda gorulur.

Yeni siparis numaralari `MKT-7H3Q-9X2K` gibi rastgele takip kodu olarak uretilir. Kodlar sirali database ID'den turetilmez; eski `#1001` bicimindeki arsiv siparisleri varsa takip uyumlulugu korunur.

Admin panelinden kullanici tarafinda su islemler yapilabilir:

- Yeni calisan veya admin kullanicisi ekleme
- Kullanici ad soyadini, rolunu ve aktif/pasif durumunu duzenleme
- Kullanici sifresini yenileme
- Pasif kullanicilarin girisini engelleme

Admin panelindeki Hesabim ekraninda giris yapan admin kendi sifresini degistirebilir. Bu islem mevcut sifre dogrulanmadan yapilmaz ve islem gecmisine yazilir.

Admin panelinden rapor tarafinda su bilgiler gorulebilir:

- Toplam siparis, teslim edilen siparis, iptal ve aktif siparis sayilari
- Teslim edilen ciro, gonderim geliri, ortalama sepet ve aktif toplam
- Tarih araligina gore filtreleme
- En cok satan urunler
- Gunluk siparis ozeti

Admin panelinden islem gecmisi tarafinda su kayitlar gorulebilir:

- Market ayari degisiklikleri
- Kategori, urun ve teslimat bolgesi islemleri
- Kullanici yonetimi islemleri
- Siparis durum degisiklikleri

Admin panelinden yedekleme tarafinda su islemler yapilabilir:

- Market verisini ZIP yedegi olarak indirme
- Siparisler, urunler, kategoriler, teslimat bolgeleri, market ayarlari ve kullanicilari yedekleme
- Yuklenen urun gorsellerini yedek ZIP'ine dahil etme
- Yedek ZIP dosyasindan geri yukleme
- Yedek indirme ve geri yukleme islemlerini audit log'a yazma

## Klasor Yapisi

```text
market-order-system/
  backend/
    app/
      api/
      core/
      database/
      models/
      schemas/
      services/
      main.py
    tests/
    .env.example
    requirements.txt
  frontend/
    customer/
    employee/
    admin/
```

## Sonraki Asama

Bir sonraki adimda production deployment hazirligi ve domain/SSL gibi canli kullanima gecis konularina gecilebilir.
