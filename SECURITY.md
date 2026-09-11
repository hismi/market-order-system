# Guvenlik Notlari

Bu projede kritik kurallar backend tarafinda uygulanir.

## Para ve Siparis Kurallari

- Frontend'den gelen fiyat, ara toplam, gonderim ucreti veya genel toplam degerlerine guvenilmez.
- Siparis olusturulurken urun fiyatlari veritabanindan tekrar okunur.
- Minimum siparis tutari veritabanindaki `market_settings.minimum_order_amount` alanindan okunur.
- Gonderim ucreti veritabanindaki `market_settings.delivery_fee` alanindan okunur ve her siparise eklenir.
- Market acik/kapali durumu ve calisma saatleri backend tarafindan kontrol edilir; frontend'in gosterdigi duruma guvenilmez.
- Calisma saati kontrolu `APP_TIMEZONE` degerine gore yapilir.
- Online odeme alinmaz; kart bilgisi, odeme token'i veya odeme provider secret'i tutulmaz.
- Urun stogu siparis onaylanirken backend tarafindan kontrol edilir ve dusulur.
- Hazirlanan veya yoldaki siparis iptal edilirse stok backend tarafindan geri eklenir.

## Siparis Takibi

- Musteri siparis durumunu gorebilmek icin siparis numarasi ve telefondaki son 10 rakami birlikte girmelidir.
- Yeni siparis numaralari sirali ID yerine tahmin edilmesi zor alfanumerik takip kodu olarak uretilir.
- Takip endpoint'i tam ad soyad, tam telefon, sokak, apartman, daire, acik adres, adres tarifi, siparis notu, internal ID veya teknik token dondurmez.
- Public takip cevabinda musteri adi, telefon ve teslimat bolgesi maskelenmis olarak dondurulur.
- Tam musteri adi, telefon, adres ve siparis notu sadece yetkili `EMPLOYEE` ve `ADMIN` endpoint'lerinde gorulur.

## Secret Yonetimi

- `.env` dosyasi Git'e eklenmez.
- Database sifresi ve JWT secret kaynak koda yazilmaz.
- Development icin `backend/.env.example` kopyalanarak `backend/.env` olusturulabilir.
- Production icin `backend/.env.production.example` ornek alinmalidir.
- Production modunda kisa, bos, placeholder veya development `JWT_SECRET` ile uygulama baslamaz.
- Production modunda varsayilan veya zayif seed kullanici sifreleri kabul edilmez.

## Sifre Degistirme

- Giris yapan kullanici kendi sifresini degistirmek icin mevcut sifresini tekrar girmelidir.
- Yeni sifre mevcut sifreyle ayni olamaz.
- Sifre degisiklikleri audit log'a yazilir.
- Admin, baska kullanicilarin sifresini Kullanıcılar ekranindan yenileyebilir.

## Login Rate Limit

- Login endpoint'i ayni IP ve kullanici adi icin hatali denemeleri sinirlar.
- Varsayilan sinir 10 dakika icinde 5 hatali denemedir.
- Sinir asildiktan sonra varsayilan 15 dakika gecici engelleme uygulanir.
- Basarili giriste ilgili deneme sayaci sifirlanir.
- Coklu sunucu kurulumunda bu mekanizma Redis gibi ortak bir depoya tasinmalidir.

## WhatsApp Kullanimi

- WhatsApp bu MVP'de sadece canli destek linki olarak kullanilir.
- Siparis olusturma, siparis durumu veya otomatik bildirim icin WhatsApp API entegrasyonu yoktur.
- Bu nedenle WhatsApp token veya API key tutulmaz.

## Urun Gorseli Yukleme

- Urun gorseli yukleme sadece `ADMIN` rolu ile yapilir.
- Varsayilan dosya boyutu siniri 2 MB'tir.
- Sadece JPG, PNG, WebP ve GIF dosyalari kabul edilir.
- Backend dosya uzantisina tek basina guvenmez; temel dosya imzasi kontrolu yapar.
- Yuklenen dosyalar `uploads/` altinda tutulur ve Git'e eklenmez.

## Yedekleme

- Yedek indirme ve geri yukleme sadece `ADMIN` rolu ile yapilir.
- Yedek dosyasi siparis, kullanici, adres, telefon ve sifre hash kayitlarini icerir; public paylasilmamalidir.
- Varsayilan yedek yukleme siniri 50 MB'tir.
- Geri yukleme mevcut verilerin yerine yedekteki verileri yazar.
- Yedek indirme ve geri yukleme audit log'a yazilir.

## Ileride Eklenecekler

- Admin paneli icin 2FA'ya uygun auth mimarisi
- Input validation testlerinin genisletilmesi

## Mevcut Auth Temeli

- Admin ve calisan kullanicilari `users` tablosunda tutulur.
- Sifreler Argon2 ile hash'lenir.
- Gecici oturum icin JWT kullanilir.
- Calisan siparis endpoint'leri `EMPLOYEE` veya `ADMIN` rolu ister.
- Siparis durumu degisiklikleri audit log'a yazilir.
- Audit log kayitlari sadece `ADMIN` rolu ile goruntulenir.
- Kullanici yonetimi sadece `ADMIN` rolu ile yapilir.
- Kullanici silmek yerine pasife alma kullanilir; pasif kullanici giris yapamaz.
- Admin kendi hesabini pasife alamaz veya kendi admin yetkisini kaldiramaz.
