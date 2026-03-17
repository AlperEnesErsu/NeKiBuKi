from __future__ import annotations

from typing import List, Optional

from .models import HistoryPoint, Product, ScrapeResult
from .notifier import Notifier
from .scraper import ProductScraper
from .storage import JsonStorage


class TrackerService:
    def __init__(self, storage: JsonStorage, scraper: ProductScraper, notifier: Notifier) -> None:
        self.storage = storage
        self.scraper = scraper
        self.notifier = notifier

    def list_products(self) -> List[Product]:
        return self.storage.list_products()

    def save_product(self, product: Product) -> None:
        self.storage.upsert_product(product)

    def delete_product(self, product_id: str) -> None:
        self.storage.delete_product(product_id)

    def get_history(self, product_id: str):
        return self.storage.get_history(product_id)

    def check_product(self, product: Product) -> ScrapeResult:
        previous_price = product.last_price
        previous_stock = product.last_stock_in
        result = self.scraper.scrape(product.url)

        point = HistoryPoint.now(product.product_id, result.price, result.stock_in)
        self.storage.append_history(point)

        product.last_price = result.price
        product.last_stock_in = result.stock_in
        product.last_checked_at = point.checked_at
        product.last_status_message = result.status_message
        self.storage.upsert_product(product)

        self._maybe_notify_price_drop(product, previous_price, result)
        self._maybe_notify_stock_back(product, previous_stock, result)

        return result

    def check_product_by_id(self, product_id: str) -> Optional[ScrapeResult]:
        product = self.storage.get_product(product_id)
        if not product:
            return None
        return self.check_product(product)

    def check_all_products(self) -> List[tuple[Product, ScrapeResult]]:
        output: List[tuple[Product, ScrapeResult]] = []
        for product in self.storage.list_products():
            result = self.check_product(product)
            output.append((product, result))
        return output

    def find_market_alternatives(self, query: str, limit: int = 10, general_mode: bool = False) -> List[dict]:
        return self.scraper.find_alternative_offers(query=query, limit=limit, general_mode=general_mode)

    def _maybe_notify_price_drop(self, product: Product, previous_price: Optional[float], result: ScrapeResult) -> None:
        if result.price is None:
            return
        if product.target_price <= 0:
            return

        crossed_target = (
            result.price <= product.target_price
            and (previous_price is None or previous_price > product.target_price)
        )
        if not crossed_target:
            return

        title = f"Hedef Fiyat! {product.name}"
        message = (
            f"{product.name} urunu hedef fiyatin altina dustu. "
            f"Guncel: {result.price} TL | Hedef: {product.target_price} TL"
        )
        self._dispatch_notification(product, title, message)

    def _maybe_notify_stock_back(self, product: Product, previous_stock: Optional[bool], result: ScrapeResult) -> None:
        if result.stock_in is not True:
            return
        if previous_stock is True:
            return

        title = f"Stokta! {product.name}"
        message = f"{product.name} urunu tekrar stokta gorunuyor: {product.url}"
        self._dispatch_notification(product, title, message)

    def _dispatch_notification(self, product: Product, title: str, message: str) -> None:
        if product.notify_desktop:
            self.notifier.send_desktop(title, message)

        if product.notify_email and product.email_to:
            self.notifier.send_email(product.email_to, title, message)
