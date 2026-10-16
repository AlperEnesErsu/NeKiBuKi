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


def test_dynamic_brand_matching():
    scraper = ProductScraper()
    # Brand-focused mode:
    # 1. Hardcoded brand
    assert scraper._is_brand_mismatch("Sek Quark", "sek quark", False) is False
    assert scraper._is_brand_mismatch("Sek Quark", "icim quark", False) is True

    # 2. Dynamic brand (watches)
    assert scraper._is_brand_mismatch("Casio F-91W", "casio watch", False) is False
    assert scraper._is_brand_mismatch("Casio F-91W", "seiko f-91w", False) is True

    # 3. Dynamic brand (phones)
    assert scraper._is_brand_mismatch("Samsung Galaxy S24", "samsung galaxy s24 ultra", False) is False
    assert scraper._is_brand_mismatch("Samsung Galaxy S24", "apple iphone 15", False) is True

    # 4. Common words (should not trigger brand mismatch)
    assert scraper._is_brand_mismatch("Erkek Kol Saati", "casio kol saati", False) is False



def test_price_pattern_keeps_thousands_groups():
    scraper = ProductScraper()
    assert scraper._extract_price_from_free_text("Fiyat 12.499,00 TL sepete ekle") == 12499.0
    assert scraper._extract_price_from_free_text("1.250 TL") == 1250.0
    assert scraper._extract_price_from_free_text("65,95 ₺") == 65.95
    assert scraper._extract_price_from_free_text("65 , 95 TL") == 65.95


def test_parse_price_treats_dotted_groups_as_thousands():
    scraper = ProductScraper()
    assert scraper._parse_price("1.250") == 1250.0
    assert scraper._parse_price("12.499") == 12499.0
    # İki ondalıklı nokta hâlâ ondalık
    assert scraper._parse_price("65.95") == 65.95


def test_free_text_price_ignores_plain_quantities():
    scraper = ProductScraper()
    assert scraper._extract_price_from_free_text("stokta 200 adet") is None
    assert scraper._extract_price_from_free_text("2 x 140 g quark") is None
    assert scraper._extract_price_from_free_text("Sek Quark 140 g") is None
    # Para birimi yazmasa da ondalıklı fiyat yakalanır
    assert scraper._extract_price_from_free_text("Sek Quark 29,90") == 29.9


def test_build_query_tokens_general_mode_drops_the_brand():
    scraper = ProductScraper()
    # Non-general mode keeps every token (lower-cased, 1-char words dropped).
    assert scraper._build_query_tokens("Sek Quark 140 g x", False) == ["sek", "quark", "140"]
    # General mode removes known and first-word brands so other brands match.
    assert scraper._build_query_tokens("Sek Quark Sade", True) == ["quark", "sade"]
    assert scraper._build_query_tokens("Casio F-91W Saat", True) == ["f-91w", "saat"]
    # A leading generic word is not a brand and stays.
    assert scraper._build_query_tokens("erkek kol saati", True) == ["erkek", "kol", "saati"]
    # Nothing left after removing the brand -> fall back to all tokens.
    assert scraper._build_query_tokens("sek", True) == ["sek"]


def test_normalize_general_query_keeps_original_casing_without_the_brand():
    scraper = ProductScraper()
    assert scraper._normalize_general_query("Sek Quark Sade") == "Quark Sade"
    assert scraper._normalize_general_query("Casio F-91W Saat") == "F-91W Saat"
    assert scraper._normalize_general_query("erkek kol saati") == "erkek kol saati"
    assert scraper._normalize_general_query("Sek") == "Sek"


def test_is_brand_mismatch_requires_the_query_brand_in_the_title():
    scraper = ProductScraper()
    assert scraper._is_brand_mismatch("Sek Quark", "icim quark sade", False) is True
    assert scraper._is_brand_mismatch("Sek Quark", "sek quark sade", False) is False
    assert scraper._is_brand_mismatch("Sek Quark", "icim quark sade", True) is False  # general mode
    assert scraper._is_brand_mismatch("erkek kol saati", "casio kol saati", False) is False
    assert scraper._is_brand_mismatch("", "anything", False) is False


def test_is_product_url_real_migros_slug():
    # Gerçek Migros ürün adresi /urun/ içermez, onaltılık kimlikle biter
    assert _is_product_url("https://www.migros.com.tr/sek-quark-sade-140-g-p-9ed4a5") is True
    assert _is_product_url("https://www.migros.com.tr/peynir-c-6d") is False


MIGROS_PAYLOAD = {
    "successful": True,
    "data": {"searchInfo": {"storeProductInfos": [
        {"name": "Sek Quark Sade 140 G", "prettyName": "sek-quark-sade-140-g-p-9ed4a5", "shownPrice": 6595, "status": "IN_SALE"},
        {"name": "Sek Quark Çilek 140 G", "prettyName": "sek-quark-cilek-140-g-p-9ed4a6", "shownPrice": 6595, "status": "OUT_OF_STOCK"},
        {"name": "Pınar Labne 200 G", "prettyName": "pinar-labne-200-g-p-1a2b", "shownPrice": 8990, "status": "IN_SALE"},
        {"name": "Fiyatsız", "prettyName": "x-p-1", "shownPrice": None},
    ]}},
}


def test_parse_migros_search_converts_kurus_and_skips_unavailable():
    from tracker.scraper import parse_migros_search

    products = parse_migros_search(MIGROS_PAYLOAD)
    assert products == [
        {"title": "Sek Quark Sade 140 G", "price": 65.95, "url": "https://www.migros.com.tr/sek-quark-sade-140-g-p-9ed4a5"},
        {"title": "Pınar Labne 200 G", "price": 89.9, "url": "https://www.migros.com.tr/pinar-labne-200-g-p-1a2b"},
    ]
    assert parse_migros_search({}) == []


class _FakeResponse:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return MIGROS_PAYLOAD


def test_migros_offers_come_from_the_search_api(monkeypatch):
    import tracker.scraper as scraper

    calls = []

    def fake_get(url, timeout=20, headers=None):
        calls.append((url, headers))
        return _FakeResponse()

    monkeypatch.setattr(scraper, "_http_get", fake_get)
    debug: dict = {}
    offers = ProductScraper()._collect_migros_offers("sek quark sade", debug)

    assert calls[0][0].startswith("https://www.migros.com.tr/rest/search/screens/products?q=sek+quark+sade")
    assert calls[0][1] == {"Accept": "application/json"}
    assert [o["title"] for o in offers] == ["Sek Quark Sade 140 G"]   # Pınar labne kelime filtresine takılır
    assert offers[0]["site"] == "Migros" and offers[0]["price"] == 65.95
    assert debug["accepted"] == 1 and debug["status_code"] == 200
