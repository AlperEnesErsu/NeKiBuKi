# NeKiBuKi

Sek Quark Protein Sade 165gr gibi zor bulunan urunler icin masaustu fiyat + stok takip uygulamasi.

## Ozellikler

- Belirli URL'leri periyodik olarak tarar (CarrefourSA, Akakce, Trendyol dahil)
- Hedef fiyatin altina dusen urunler icin bildirim gonderir
- "stokta yok / tukendi" gibi ibareleri yakalayip stoga girince bildirim atar
- Tkinter UI ile urun ekleme, silme, manuel kontrol ve fiyat grafigi goruntuleme
- Verileri JSON dosyasinda saklar (`data/products.json`)

## Kurulum

```bash
pip install -r requirements.txt
```

## Calistirma

```bash
python app.py
```

## E-posta Bildirimi (Opsiyonel)

E-posta bildirimini acarsan su ortam degiskenlerini tanimla:

- `NEKIBUKI_SMTP_HOST`
- `NEKIBUKI_SMTP_PORT` (varsayilan 587)
- `NEKIBUKI_SMTP_USER`
- `NEKIBUKI_SMTP_PASS`
- `NEKIBUKI_SMTP_FROM` (opsiyonel, yoksa user kullanilir)

## Notlar

- Site HTML yapi degisikligi olursa CSS secicilerinin guncellenmesi gerekebilir.
- Scraping yogunlugu dusuk tutulmali; makul araliklar (1-2 saat+) onerilir.
- Ilk hedef siteler: CarrefourSA, Akakce, Trendyol.
