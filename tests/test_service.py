from unittest.mock import MagicMock
from tracker.service import TrackerService
from tracker.models import Product, ScrapeResult, HistoryPoint
from tracker.storage import JsonStorage

def test_tracker_service_check_triggers_notifications(tmp_path):
    file_path = tmp_path / "products.json"
    storage = JsonStorage(file_path)
    
    # Mock Scraper & Notifier
    scraper = MagicMock()
    notifier = MagicMock()
    
    service = TrackerService(storage, scraper, notifier)

    # 1. Product setup
    product = Product(
        product_id="test-uuid",
        name="Sek Quark",
        url="https://www.carrefoursa.com/sek-quark-sade-140-g-p-30162892",
        target_price=50.0,
        notify_desktop=True,
        notify_email=True,
        email_to="user@example.com",
        last_price=55.0, # previous price was above target
        last_stock_in=True
    )
    storage.upsert_product(product)

    # 2. Mock scraper return value: price drops below target
    scraper.scrape.return_value = ScrapeResult(price=45.0, stock_in=True, status_message="Fiyat: 45.0 TL")

    # 3. Trigger check
    result = service.check_product_by_id("test-uuid")

    assert result.price == 45.0
    # Notifier should have been called for price drop
    assert notifier.send_desktop.call_count == 1
    assert notifier.send_email.call_count == 1
    
    desktop_args = notifier.send_desktop.call_args[0]
    assert "Hedef Fiyat" in desktop_args[0]
    assert "Sek Quark" in desktop_args[1]

    email_args = notifier.send_email.call_args[0]
    assert email_args[0] == "user@example.com"
    assert "Hedef Fiyat" in email_args[1]


def test_tracker_service_stock_trigger(tmp_path):
    file_path = tmp_path / "products.json"
    storage = JsonStorage(file_path)
    
    scraper = MagicMock()
    notifier = MagicMock()
    service = TrackerService(storage, scraper, notifier)

    # Product was out of stock
    product = Product(
        product_id="test-uuid",
        name="Sek Quark",
        url="https://www.carrefoursa.com/sek-quark-sade-140-g-p-30162892",
        target_price=50.0,
        notify_desktop=True,
        notify_email=False,
        last_price=45.0,
        last_stock_in=False
    )
    storage.upsert_product(product)

    # Product is now in stock
    scraper.scrape.return_value = ScrapeResult(price=45.0, stock_in=True, status_message="Stokta")

    service.check_product_by_id("test-uuid")

    # Notifier should have sent desktop alert for stock back
    assert notifier.send_desktop.call_count == 1
    desktop_args = notifier.send_desktop.call_args[0]
    assert "Stokta!" in desktop_args[0]
