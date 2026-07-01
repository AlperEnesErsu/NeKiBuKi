from tracker.scraper import ProductScraper, _is_product_url

def test_is_product_url():
    # Trendyol
    assert _is_product_url("https://www.trendyol.com/sek/quark-sade-p-123456") is True
    assert _is_product_url("https://www.trendyol.com/sr?q=Quark") is False

    # CarrefourSA
    assert _is_product_url("https://www.carrefoursa.com/sek-quark-sade-140-g-p-30162892") is True
    assert _is_product_url("https://www.carrefoursa.com/search?q=Quark") is False

    # Akakce
    assert _is_product_url("https://www.akakce.com/peynir/en-ucuz-sek-quark-sade-140-gr-fiyati,537161532.html") is True
    assert _is_product_url("https://www.akakce.com/arama/?q=Quark") is False

    # Migros
    assert _is_product_url("https://www.migros.com.tr/urun/sek-quark-sade-140g-p-1234") is True
    assert _is_product_url("https://www.migros.com.tr/arama?q=Quark") is False

    # A101
    assert _is_product_url("https://www.a101.com.tr/market/sek-quark-sade-140g/") is True
    assert _is_product_url("https://www.a101.com.tr/arama/?kelime=Quark") is False

    # Hepsiburada
    assert _is_product_url("https://www.hepsiburada.com/sek-quark-protein-sade-165-g-x4-adet-pm-HBC0000CHSG2K") is True
    assert _is_product_url("https://www.hepsiburada.com/ara?q=Quark") is False



def test_parse_price():
    scraper = ProductScraper()
    assert scraper._parse_price("65,95 TL") == 65.95
    assert scraper._parse_price(" 65.95 ₺ ") == 65.95
    assert scraper._parse_price("1.250,50 TL") == 1250.50
    assert scraper._parse_price("1,250.50") == 1250.50
    assert scraper._parse_price("invalid-price") is None
    assert scraper._parse_price("") is None
    assert scraper._parse_price("65 , 95 TL") == 65.95
