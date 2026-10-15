from __future__ import annotations

import math
import re
from typing import Optional
from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .matching import (  # noqa: F401
    BRAND_TOKENS,
    CATEGORY_HINT_TOKENS,
    KNOWN_BRANDS,
    build_query_tokens,
    is_brand_mismatch,
    normalize_general_query,
)
from .models import ScrapeResult

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}

OUT_OF_STOCK_MARKERS = [
    "stokta yok",
    "tukendi",
    "tükendi",
    "urun bulunamadi",
    "ürün bulunamadı",
    "bu urun su an satista degil",
    "bu ürün şu an satışta değil",
    "gelince haber ver",
]

IN_STOCK_MARKERS = [
    "sepete ekle",
    "hemen al",
    "satın al",
    "stokta",
    "teslimat",
]

# Match patterns with optional spaces around dot/comma (e.g. 65 , 95 TL)
# "12.499,00 TL", "1.250 TL", "65,95 TL", "65 , 95 ₺": binlik ayırıcılı biçim önce denenir,
# yoksa "12.499,00" gibi fiyatlar soldaki gruplar atlanarak "499,00" diye okunurdu.
PRICE_PATTERN = re.compile(
    r"(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{1,6}(?:\s*[.,]\s*\d{1,2})?)\s*(?:tl|₺)",
    re.IGNORECASE,
)

def _http_get(url: str, timeout: int = 20) -> requests.Response:
    try:
        from curl_cffi import requests as curl_requests
        return curl_requests.get(url, impersonate="chrome120", timeout=timeout)
    except ImportError:
        return requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)

def _is_product_url(url: str) -> bool:
    """Arama sayfası değil, ürün sayfası mı?"""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path.lower()
    # Trendyol ürün URL'leri: /marka/urun-adi-p-XXXXXX
    if "trendyol.com" in domain:
        return bool(re.search(r"-p-\d+", path))
    # CarrefourSA: /p- veya /product veya -p-
    if "carrefoursa.com" in domain:
        return "/p-" in path or "/product" in path or "-p-" in path
    # Akakce: /urun/ veya /fiyati,
    if "akakce.com" in domain:
        return "/urun/" in path or "/fiyati," in path or re.search(r"/[a-z0-9-]+-\d+", path) is not None
    # Migros: genelde /urun/ ile gider
    if "migros.com.tr" in domain:
        return "/urun/" in path
    # A101: /p/ veya /urun/ veya /market/ veya /kapida/urun/
    if "a101.com.tr" in domain:
        return "/p/" in path or "/urun/" in path or "/market/" in path or "/kapida/urun/" in path or ("/kapida/" in path and "arama" not in path)
    # Hepsiburada: -p- veya -pm- veya /p/ veya /pm/ veya /urun/
    if "hepsiburada.com" in domain:
        return "-p-" in path or "-pm-" in path or "/p/" in path or "/urun/" in path
    return False


class ProductScraper:
    def __init__(self) -> None:
        self.last_search_debug: dict[str, dict[str, object]] = {}

    def scrape(self, url: str) -> ScrapeResult:
        try:
            response = _http_get(url, timeout=20)
            response.raise_for_status()
        except Exception as exc:
            return ScrapeResult(price=None, stock_in=None, status_message=f"HTTP hatasi: {exc}")

        soup = BeautifulSoup(response.text, "html.parser")
        price = self._extract_price(url, soup, response.text)
        stock_in = self._extract_stock(soup)
        status_parts = []
        status_parts.append(f"Fiyat: {price} TL" if price is not None else "Fiyat bulunamadi")
        if stock_in is None:
            status_parts.append("Stok durumu belirsiz")
        else:
            status_parts.append("Stokta" if stock_in else "Stokta degil")
        return ScrapeResult(price=price, stock_in=stock_in, status_message=" | ".join(status_parts))

    def _extract_price(self, url: str, soup: BeautifulSoup, html: str) -> Optional[float]:
        meta_price = soup.select_one('[itemprop="price"]')
        if meta_price and meta_price.get("content"):
            parsed = self._parse_price(meta_price.get("content", ""))
            if parsed is not None:
                return parsed

        domain = (urlparse(url).netloc or "").lower()
        if "trendyol" in domain:
            for selector in [".prc-dsc", ".prc-slg", "[data-testid='price-current-price']"]:
                node = soup.select_one(selector)
                if node:
                    parsed = self._parse_price(node.get_text(" ", strip=True))
                    if parsed is not None:
                        return parsed

        if "carrefoursa" in domain:
            node = soup.select_one(".product-price__sale-price") or soup.select_one(".js-variant-discounted-price")
            if node:
                parsed = self._parse_price(node.get_text(" ", strip=True))
                if parsed is not None:
                    return parsed

        if "akakce" in domain:
            node = soup.select_one("span.pt_v8") or soup.select_one(".pb_v8")
            if node:
                parsed = self._parse_price(node.get_text(" ", strip=True))
                if parsed is not None:
                    return parsed

        if "migros.com.tr" in domain:
            for selector in ["[data-cy='product-price']", ".price", ".money-discount"]:
                node = soup.select_one(selector)
                if node:
                    parsed = self._parse_price(node.get_text(" ", strip=True))
                    if parsed is not None:
                        return parsed

        if "a101.com.tr" in domain:
            for selector in [".price", "[class*='price']", "[data-testid='price']"]:
                node = soup.select_one(selector)
                if node:
                    parsed = self._parse_price(node.get_text(" ", strip=True))
                    if parsed is not None:
                        return parsed

        json_price_match = re.search(r'"price"\s*:\s*"?(\d+(?:[.,]\d+)?)"?', html, re.IGNORECASE)
        if json_price_match:
            return self._parse_price(json_price_match.group(1))

        price_match = PRICE_PATTERN.search(soup.get_text(" ", strip=True))
        if price_match:
            return self._parse_price(price_match.group(1))

        return None

    def _extract_stock(self, soup: BeautifulSoup) -> Optional[bool]:
        all_text = soup.get_text(" ", strip=True).lower()
        if any(marker in all_text for marker in OUT_OF_STOCK_MARKERS):
            return False
        if any(marker in all_text for marker in IN_STOCK_MARKERS):
            return True
        return None

    def _parse_price(self, value: str) -> Optional[float]:
        cleaned = (
            value.replace("TL", "")
            .replace("tl", "")
            .replace("₺", "")
            .replace(" ", "")
            .replace("\n", "")
            .replace("\r", "")
            .strip()
        )
        if not cleaned:
            return None

        cleaned = cleaned.replace(" ", "")

        if "," in cleaned and "." in cleaned:
            if cleaned.find(".") < cleaned.find(","):
                cleaned = cleaned.replace(".", "").replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", cleaned):
            # Yalnızca noktalı ve 3'erli gruplar: Türkçe binlik ayırıcı ("1.250" = 1250)
            cleaned = cleaned.replace(".", "")

        try:
            return float(cleaned)
        except ValueError:
            return None

    def find_alternative_offers(self, query: str, limit: int = 20, general_mode: bool = False) -> list[dict]:
        query = query.strip()
        if not query:
            return []

        effective_query = self._normalize_general_query(query) if general_mode else query

        self.last_search_debug = {}

        search_urls = [
            ("Akakce", f"https://www.akakce.com/arama/?q={quote_plus(effective_query)}"),
            ("Trendyol", f"https://www.trendyol.com/sr?q={quote_plus(effective_query)}"),
            ("CarrefourSA", f"https://www.carrefoursa.com/search?q={quote_plus(effective_query)}"),
            ("Cimri", f"https://www.cimri.com/arama?q={quote_plus(effective_query)}"),
            ("A101 Kapida", f"https://www.a101.com.tr/arama/?kelime={quote_plus(effective_query)}"),
            ("Migros", f"https://www.migros.com.tr/arama?q={quote_plus(effective_query)}"),
            ("Hepsiburada", f"https://www.hepsiburada.com/ara?q={quote_plus(effective_query)}"),
        ]

        offers: list[dict] = []
        link_only_offers: list[dict] = []

        for site_name, url in search_urls:
            site_debug: dict[str, object] = {
                "search_url": url,
                "status_code": None,
                "fetch_error": "",
                "links_scanned": 0,
                "title_filtered": 0,
                "token_filtered": 0,
                "price_filtered": 0,
                "url_filtered": 0,
                "accepted": 0,
                "returned": 0,
                "link_only": False,
            }
            try:
                soup, status_code, fetch_error = self._fetch_soup(url)
                site_debug["status_code"] = status_code
                site_debug["fetch_error"] = fetch_error
                site_offers: list[dict] = []
                if soup:
                    site_offers = self._collect_generic_offers(
                        site_name,
                        soup,
                        url,
                        effective_query,
                        site_debug,
                        general_mode,
                    )
                if site_offers:
                    offers.extend(site_offers)
                    site_debug["returned"] = len(site_offers)
                else:
                    link_only_offers.append(self._build_link_only_offer(site_name, effective_query, general_mode))
                    site_debug["link_only"] = True
            except Exception:
                link_only_offers.append(self._build_link_only_offer(site_name, effective_query, general_mode))
                site_debug["link_only"] = True
            finally:
                self.last_search_debug[site_name] = site_debug

        # Deduplicate ve sırala
        dedup: dict[str, dict] = {}
        for offer in offers:
            key = (offer.get("url", ""), offer.get("site", ""))
            if not key[0] or not offer.get("price"):
                continue
            if key not in dedup or offer["price"] < dedup[key]["price"]:
                dedup[key] = offer

        ranked = sorted(dedup.values(), key=lambda x: x.get("price", float("inf")))

        # Fiyatı çekilemeyen siteleri en sona ekle
        seen_sites = {o.get("site", "") for o in ranked}
        for offer in link_only_offers:
            if offer.get("site", "") not in seen_sites:
                ranked.append(offer)
                seen_sites.add(offer.get("site", ""))

        if general_mode:
            brand_offers = self._build_general_brand_link_offers(effective_query)
            existing_urls = {str(item.get("url", "")) for item in ranked}
            for offer in brand_offers:
                url = str(offer.get("url", ""))
                if url and url not in existing_urls:
                    ranked.append(offer)
                    existing_urls.add(url)

        return ranked[:limit]

    def _build_link_only_offer(self, site: str, query: str, general_mode: bool = False) -> dict:
        search_links = {
            "Akakce": f"https://www.akakce.com/arama/?q={quote_plus(query)}",
            "Trendyol": f"https://www.trendyol.com/sr?q={quote_plus(query)}",
            "CarrefourSA": f"https://www.carrefoursa.com/search?q={quote_plus(query)}",
            "Cimri": f"https://www.cimri.com/arama?q={quote_plus(query)}",
            "A101 Kapida": f"https://www.a101.com.tr/arama/?kelime={quote_plus(query)}",
            "Migros": f"https://www.migros.com.tr/arama?q={quote_plus(query)}",
            "Hepsiburada": f"https://www.hepsiburada.com/ara?q={quote_plus(query)}",
        }

        label = f"{site} arama sonucuna git"
        if general_mode:
            label = f"{site} genel arama sonucuna git"
        return {
            "site": site,
            "title": label,
            "price": None,
            "url": search_links.get(site, ""),
            "target_site": site,
            "link_only": True,
        }

    def _collect_generic_offers(
        self,
        site: str,
        soup: BeautifulSoup,
        search_url: str,
        query: str,
        debug: Optional[dict[str, object]] = None,
        general_mode: bool = False,
    ) -> list[dict]:
        offers: list[dict] = []
        query_tokens = self._build_query_tokens(query, general_mode)

        # Genel aramada daha esnek, normal aramada daha sıkı filtre kullan.
        ratio = 0.4 if general_mode else 0.6
        min_match = max(1, math.ceil(len(query_tokens) * ratio)) if query_tokens else 1

        for container in soup.select("a[href]"):
            try:
                href = container.get("href", "").strip()
                if not href or href.startswith("#") or "javascript:" in href.lower() or href.endswith(".jpg"):
                    continue

                full_url = urljoin(search_url, href) if not href.startswith("http") else href

                if not full_url.startswith("http"):
                    continue

                if full_url.rstrip("/") == search_url.rstrip("/"):
                    continue

                title = container.get_text(" ", strip=True)
                if not title or len(title) < 5 or len(title) > 300:
                    if debug is not None:
                        debug["title_filtered"] = int(debug.get("title_filtered", 0)) + 1
                    continue

                title_lower = title.lower()

                # Brand mismatch filter in brand-focused mode
                if self._is_brand_mismatch(query, title_lower, general_mode):
                    if debug is not None:
                        debug["token_filtered"] = int(debug.get("token_filtered", 0)) + 1
                    continue

                # Token filtresi
                is_prod = _is_product_url(full_url)
                if query_tokens:
                    match_count = sum(1 for token in query_tokens if token in title_lower)
                    if match_count < min_match:
                        if debug is not None:
                            debug["token_filtered"] = int(debug.get("token_filtered", 0)) + 1
                        continue

                if debug is not None:
                    debug["links_scanned"] = int(debug.get("links_scanned", 0)) + 1

                parent_text = ""
                if container.parent and container.parent.name != "body":
                    # Use raw text without separator to avoid spaces in prices (e.g. 65,95 -> 65 , 95)
                    parent_text = container.parent.get_text()[:400]
                    if container.parent.parent and container.parent.parent.name != "body":
                        parent_text += " " + container.parent.parent.get_text()[:400]

                combined_text = f"{title} {parent_text}"
                price = self._extract_price_from_free_text(combined_text)

                if not price or price <= 0 or price > 200000:
                    if debug is not None:
                        debug["price_filtered"] = int(debug.get("price_filtered", 0)) + 1
                    continue

                # Sadece arama sayfalarında query'yi kes; ürün sayfalarında koru
                if not is_prod and "?" in full_url:
                    full_url = full_url.split("?")[0]

                offers.append({
                    "site": site,
                    "title": title[:120],
                    "price": price,
                    "url": full_url,
                })

                if debug is not None:
                    debug["accepted"] = int(debug.get("accepted", 0)) + 1

                if len(offers) >= 15:
                    break
            except Exception:
                continue

        return offers

    def _build_query_tokens(self, query: str, general_mode: bool) -> list[str]:
        return build_query_tokens(query, general_mode)

    def _normalize_general_query(self, query: str) -> str:
        return normalize_general_query(query)

    def _is_brand_mismatch(self, query: str, title_lower: str, general_mode: bool) -> bool:
        return is_brand_mismatch(query, title_lower, general_mode)

    def _build_general_brand_link_offers(self, query: str) -> list[dict]:
        offers: list[dict] = []
        for brand in KNOWN_BRANDS:
            brand_query = f"{brand} {query}".strip()
            offers.append(
                {
                    "site": "Genel",
                    "title": f"{brand} urunlerini ara (Trendyol)",
                    "price": None,
                    "url": f"https://www.trendyol.com/sr?q={quote_plus(brand_query)}",
                    "target_site": "Trendyol",
                    "link_only": True,
                }
            )
        return offers

    def _fetch_soup(self, url: str) -> tuple[Optional[BeautifulSoup], Optional[int], str]:
        try:
            response = _http_get(url, timeout=20)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser"), response.status_code, ""
        except Exception as exc:
            status_code = None
            if hasattr(exc, "response") and getattr(exc, "response") is not None:
                status_code = getattr(exc, "response").status_code
            return None, status_code, str(exc)

    def get_last_search_debug_report(self) -> str:
        if not self.last_search_debug:
            return "Debug verisi yok. Once benzer urun aramasi calistir."

        lines = ["Benzer urun arama debug ozeti:"]
        for site, data in self.last_search_debug.items():
            lines.append(
                (
                    f"- {site}: status={data.get('status_code')} "
                    f"link_only={data.get('link_only')} returned={data.get('returned')} "
                    f"scanned={data.get('links_scanned')} title={data.get('title_filtered')} "
                    f"token={data.get('token_filtered')} price={data.get('price_filtered')} "
                    f"url={data.get('url_filtered')}"
                )
            )
            if data.get("fetch_error"):
                lines.append(f"  hata: {data.get('fetch_error')}")
        return "\n".join(lines)

    def _extract_price_from_free_text(self, text: str) -> Optional[float]:
        match = PRICE_PATTERN.search(text)
        if match:
            return self._parse_price(match.group(1))

        # Para birimi yoksa yalnızca ondalıklı ("65,95") sayıyı fiyat say: "stokta 200 adet",
        # "2 x 140 g" gibi sayılar fiyat değildir. Sonrasında birim harfi geliyorsa ("65,5 g") alma.
        generic_match = re.search(r"(?<![\d.,])(\d{1,6}[.,]\d{2})(?![\d.,]|\s*[A-Za-zÇĞİÖŞÜçğıöşü])", text)
        if generic_match:
            return self._parse_price(generic_match.group(1))

        return None