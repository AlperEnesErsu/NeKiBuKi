"""Arayüzün gösterdiği metinleri ve form doğrulamasını üreten saf fonksiyonlar (Tk yok)."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Product, ScrapeResult

COLOR_OK = "#34d399"      # stokta ve hedefin altında
COLOR_WARN = "#fbbf24"    # stokta ama hedefin üstünde
COLOR_BAD = "#f87171"     # stok yok / belirsiz


def product_row(product: Product) -> tuple[str, str, str, str, str]:
    """Ürün tablosundaki bir satırın hücreleri."""
    stock_label = "?" if product.last_stock_in is None else ("Var" if product.last_stock_in else "Yok")
    price_label = "-" if product.last_price is None else f"{product.last_price:.2f}"
    checked_label = product.last_checked_at.replace("T", " ")[:16] if product.last_checked_at else "-"
    return (product.name, f"{product.target_price:.2f}", price_label, stock_label, checked_label)


def describe_check(result: ScrapeResult, target_price: float | None) -> tuple[str, str]:
    """Kontrol sonucunun tek satırlık özeti ve rengi."""
    stock_text = "Belirsiz"
    if result.stock_in is True:
        stock_text = "Var"
    elif result.stock_in is False:
        stock_text = "Yok"

    below_target = False
    if result.price is None:
        price_text = "Fiyat bulunamadi"
        target_text = "Hedef durumu: Belirsiz"
    else:
        price_text = f"Fiyat: {result.price:.2f} TL"
        if target_price is None or target_price <= 0:
            target_text = "Hedef durumu: Hedef fiyat girilmedi"
        else:
            below_target = result.price <= target_price
            target_text = (
                f"Hedef alti: {'Evet' if below_target else 'Hayir'} "
                f"(Hedef {target_price:.2f} TL)"
            )

    if result.stock_in is True and below_target:
        color = COLOR_OK
    elif result.stock_in is True:
        color = COLOR_WARN
    else:
        color = COLOR_BAD
    return f"Stok: {stock_text} | {price_text} | {target_text}", color


@dataclass(frozen=True)
class ProductForm:
    name: str
    url: str
    target_price: float
    check_interval_hours: float


def parse_product_form(name: str, url: str, target: str, interval: str) -> ProductForm | str:
    """Geçerliyse `ProductForm`, değilse kullanıcıya gösterilecek hata metni."""
    name, url = name.strip(), url.strip()
    if not name or not url:
        return "Urun adi ve URL zorunludur."
    try:
        target_price = float(target.strip())
        check_interval = float(interval.strip())
    except ValueError:
        return "Hedef fiyat ve aralik sayi olmali."
    if check_interval <= 0:
        return "Kontrol araligi sifirdan buyuk olmali."
    return ProductForm(name, url, target_price, check_interval)
