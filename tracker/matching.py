"""Marka / sorgu eşleştirme: saf fonksiyonlar ve sözcük kümeleri (ağ yok)."""

BRAND_TOKENS = {
    "sek",
    "icim",
    "i\u00e7im",
    "pinar",
    "p\u0131nar",
    "sutas",
    "s\u00fcta\u015f",
    "danone",
    "mis",
    "dost",
    "altin",
    "alt\u0131n",
    "birsah",
    "bir\u015fah",
    "torku",
    "yorukoglu",
    "y\u00f6r\u00fcko\u011flu",
    "tahsildaroglu",
    "tahsildaro\u011flu",
    "bahcivan",
    "bah\u00e7\u0131van",
    "ekici",
    "kaanlar",
    "kebir",
    "muratbey",
    "gundogdu",
    "g\u00fcndo\u011fdu",
}

CATEGORY_HINT_TOKENS = {
    "protein",
    "proteinli",
    "sut",
    "s\u00fct",
    "quark",
    "yogurt",
    "yo\u011furt",
    "kefir",
    "peynir",
}

KNOWN_BRANDS = [
    "Sek",
    "Icim",
    "İçim",
    "Pinar",
    "Pınar",
    "Sutas",
    "Sütaş",
    "Danone",
    "Mis",
    "Dost",
    "Torku",
    "Yorukoglu",
    "Yörükoğlu",
    "Tahsildaroglu",
    "Tahsildaroğlu",
    "Bahcivan",
    "Bahçıvan",
    "Ekici",
    "Kaanlar",
    "Kebir",
    "Muratbey",
    "Gundogdu",
    "Gündoğdu",
]

NON_BRAND_FIRST_WORDS = {
    "erkek", "kadin", "kadın", "cocuk", "çocuk", "bebek", "ucuz", "en", "buyuk", "büyük",
    "kucuk", "küçük", "kirmizi", "kırmızı", "mavi", "siyah", "beyaz", "yesil", "yeşil",
    "sari", "sarı", "kutu", "paket", "adet", "litre", "kilo", "gram", "saat", "telefon",
    "bilgisayar", "tablet", "ayakkabi", "ayakkabı", "elbise", "pantolon", "gomlek", "gömlek",
    "canta", "çanta", "defter", "kalem", "orjinal", "orijinal", "kaliteli", "yeni", "eski",
    "sanal", "market", "hizli", "hızlı", "kargo", "bedava", "indirim", "firsat", "fırsat",
}


def _detected_brands(first_word: str | None) -> set[str]:
    """Bilinen markalar + (genel bir sözcük değilse) sorgunun ilk sözcüğü."""
    brands = {b.lower() for b in KNOWN_BRANDS}
    if first_word and first_word not in NON_BRAND_FIRST_WORDS:
        brands.add(first_word)
    return brands


def build_query_tokens(query: str, general_mode: bool) -> list[str]:
    tokens = [w.lower().strip() for w in query.split() if len(w.strip()) > 1]
    if not general_mode:
        return tokens

    # Genel modda marka sözcüklerini at: aynı ürünün diğer markaları da eşleşsin.
    detected = _detected_brands(tokens[0] if tokens else None)
    no_brand = [t for t in tokens if t not in BRAND_TOKENS and t not in detected]
    return no_brand or tokens


def normalize_general_query(query: str) -> str:
    tokens = [w.strip() for w in query.split() if len(w.strip()) > 1]
    lowered = [t.lower() for t in tokens]

    detected = _detected_brands(lowered[0] if lowered else None)
    # Yalnızca marka sözcüklerini ele; ürünü farklı markalar arasında karşılaştırılabilir kıl.
    no_brand = [tokens[i] for i, t in enumerate(lowered) if t not in BRAND_TOKENS and t not in detected]
    return " ".join(no_brand) if no_brand else query


def is_brand_mismatch(query: str, title_lower: str, general_mode: bool) -> bool:
    """Marka odaklı aramada başlık, sorgudaki markayı içermiyorsa True."""
    if general_mode:
        return False

    query_lower = query.lower().strip()
    query_words = [w for w in query_lower.split() if len(w) > 1]
    if not query_words:
        return False

    query_brands = [b.lower() for b in KNOWN_BRANDS if b.lower() in query_lower]
    first_word = query_words[0]
    if first_word not in NON_BRAND_FIRST_WORDS and first_word not in query_brands:
        query_brands.append(first_word)

    if not query_brands:
        return False
    return not any(qb in title_lower for qb in query_brands)
