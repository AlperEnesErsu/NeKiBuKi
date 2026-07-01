# NeKiBuKi Projesi Ajan Atamaları ve Geliştirme Yol Haritası

Bu belgede, **NeKiBuKi** masaüstü fiyat ve stok takip uygulaması üzerindeki eksiklikler tespit edilmiş, bu eksikliklerin giderilmesi için uzman yapay zeka ajan rolleri tanımlanmış ve sırasıyla gerçekleştirilecek adımlar listelenmiştir.

---

## 👥 Ajan Rolleri (Agent Roles)

Bu projeyi daha modüler, hatasız ve sağlam hale getirmek için 5 farklı uzman ajan tanımlanmıştır:

1. **Scraper & Crawler Agent (Kazıma Uzmanı)**
   - **Görevi:** Web sitelerinden fiyat/stok verilerini toplamak, engellemeleri (403 Forbidden, Cloudflare vb.) aşmak ve CSS seçicilerinin güncelliğini korumak.
   
2. **Core Architecture & UI Agent (Arayüz ve Çekirdek Geliştirici)**
   - **Görevi:** Tkinter UI bileşenlerini iyileştirmek, veri gösterimini (fiyat grafikleri, loglar) optimize etmek, kullanıcı form girişlerini doğrulamak.

3. **Storage & Models Agent (Veri ve Depolama Uzmanı)**
   - **Görevi:** JSON tabanlı yerel depolamayı yönetmek, veri tutarlılığını sağlamak, thread-safe (iş parçacığı güvenli) işlemleri garanti altına almak.

4. **Notification & SMTP Agent (Bildirim Uzmanı)**
   - **Görevi:** Hedef fiyata düşüldüğünde veya stok geldiğinde masaüstü ve e-posta bildirimlerini yönetmek. E-posta ayarlarını dinamik olarak UI'a bağlamak.

5. **QA & Test Engineer (Kalite Kontrol ve Test Mühendisi)**
   - **Görevi:** Kazıcılar (scrapers), veri tabanı işlemleri ve bildirim mekanizmaları için birim testleri (unit tests) yazarak kod kalitesini güvence altına almak.

---

## 🔍 Tespit Edilen Eksikler ve Hatalar (Deficiencies)

Yapılan ilk kod analizleri ve test çalıştırmaları sonucunda şu kritik eksikler tespit edilmiştir:

1. **403 Forbidden Engellemesi (Scraper Blocker):**
   - **Trendyol**, **Akakçe** ve **Cimri** gibi siteler standart `requests` kütüphanesini bot olarak algılamakta ve **403 Forbidden** hatası döndürmektedir. Bu durum piyasa aramasının sıfır sonuç üretmesine yol açmaktadır.
   
2. **A101 Arama URL Değişikliği (404 Not Found):**
   - A101 Kapıda arama URL'si `https://www.a101.com.tr/kapida/arama/?query={query}` şeklinde kalmış ancak bu adres **404 Not Found** vermektedir. A101'in güncel arama adresi `https://www.a101.com.tr/arama/?kelime={query}` olmalıdır.

3. **Migros SSR Olmaması (Boş Sonuç):**
   - Migros web sitesi istemci taraflı (Angular/React) yüklendiği için doğrudan `requests.get` ile çekilen HTML dosyasında ürün linkleri ve fiyatları bulunmamaktadır. Dinamik yapının çözülmesi veya API üzerinden veri çekilmesi gerekmektedir.

4. **UI'da SMTP/E-posta Yapılandırma Eksikliği:**
   - E-posta bildirim mekanizması kodda mevcut olmasına rağmen, UI formunda e-posta adresini girmek ve e-posta bildirimini aktifleştirmek için herhangi bir alan bulunmamaktadır. Ayrıca SMTP sunucu bilgileri yalnızca ortam değişkenlerinden (`.env` veya sistem değişkeni) okunabilmektedir.

5. **Fiyat Çekme Regex ve Seçici Kararsızlığı:**
   - Serbest metinden fiyat ayıklayan `_extract_price_from_free_text` yöntemi, sadece sayı içeren herhangi bir metni fiyat olarak algılayabilmekte (örneğin "stokta 200 adet" -> 200 TL), bu da hatalı eşleşmelere yol açmaktadır.

6. **Test Senaryolarının Olmaması:**
   - Projede hiçbir otomatik test (unit/integration test) bulunmamaktadır. Yapılan değişikliklerin scraper'ları bozup bozmadığını test etmek için pytest altyapısı kurulmalıdır.

---

## 🚀 Yol Haritası ve Uygulama Adımları

Aşağıdaki adımları sırayla tamamlayacağız:

- [x] **Adım 1: Scraper Güçlendirme & Engelleri Aşma (Scraper Agent)**
  - Entegre edilen `curl_cffi` kütüphanesi sayesinde Trendyol, Akakçe, Cimri ve CarrefourSA engellemeleri başarıyla aşıldı.
  - A101 arama URL'si güncellendi (`kelime=` parametresi).
  
- [x] **Adım 2: Fiyat Ayıklama ve Eşleştirme Mantığının İyileştirilmesi (Scraper Agent)**
  - Fiyat Regex formatı esnetilerek tagler arasındaki boşluklardan kaynaklanan ayrıştırma hataları giderildi.
  - Genişletilen `_is_product_url` ile ürün bazlı filtreleme ve fiyat eşleştirme hassasiyeti artırıldı.

- [x] **Adım 3: E-posta Bildirim Arayüzünün Eklenmesi (UI & Notifier Agent)**
  - Tkinter formuna "E-posta Uyarısı" onay kutusu ve "Alıcı E-posta" giriş alanı eklenerek veritabanı kaydıyla bütünleştirildi.

- [x] **Adım 4: SMTP Test ve Ayarlar UI Geliştirmesi (UI & Notifier Agent)**
  - Arayüze "SMTP Ayarları" butonu yerleştirilerek kullanıcıların SMTP sunucu detaylarını düzenleyebileceği, kaydedebileceği (`config.json`) ve anlık test maili gönderebileceği bir modal pencere eklendi.

- [x] **Adım 5: Unit Test Altyapısının Kurulması (QA Agent)**
  - `pytest` entegrasyonu ile model, scraper, storage ve service mekanizmalarını test eden 7 test senaryosu yazıldı ve başarıyla doğrulandı.

- [x] **Adım 6: UI Tasarımı ve Hata Giderme Cilası (UI Agent)**
  - Tkinter grid ve padding düzenlemeleriyle daha modern bir görünüm elde edildi.
  - Grafik çizimindeki tarih formatları, Türkçe karakter desteği ve Sleek Dark Mode görsel uyumluluğu tamamlandı.

- [x] **Adım 7: Hepsiburada Entegrasyonu ve Benzer Ürün Eşleştirme Geliştirmeleri (Scraper Agent)**
  - Hepsiburada araması (`/ara?q=...`) ve ürün sayfası fiyat/stok kazıma altyapısı entegre edildi.
  - Genel fiyat ayrıştırma mantığı optimize edilerek script içindeki kesin JSON fiyat etiketleri serbest metin regexine göre önceliklendirildi.
  - Benzer ürün bulma motoru genişletildi: Marka odaklı aramalarda marka doğrulaması zorunlu hale getirilerek ilgisiz ürünlerin elenmesi sağlandı.
  - Genel karşılaştırma modunda sorgu normalizasyonu iyileştirildi; "Süzme Peynir" gibi ürün detayları korunarak sadece marka adı filtrelendi.

