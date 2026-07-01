from datetime import datetime
from tracker.models import Product, HistoryPoint, ScrapeResult

def test_product_creation_and_serialization():
    data = {
        "product_id": "test-uuid",
        "name": "Sek Quark",
        "url": "https://www.carrefoursa.com/sek-quark-sade-140-g-p-30162892",
        "target_price": 50.0,
        "check_interval_hours": 1.5,
        "notify_desktop": True,
        "notify_email": True,
        "email_to": "user@example.com",
        "last_price": 45.0,
        "last_stock_in": True,
        "last_checked_at": "2026-07-01T10:00:00",
        "last_status_message": "Fiyat: 45.0 TL"
    }

    product = Product.from_dict(data)
    assert product.product_id == "test-uuid"
    assert product.name == "Sek Quark"
    assert product.target_price == 50.0
    assert product.check_interval_hours == 1.5
    assert product.notify_desktop is True
    assert product.notify_email is True
    assert product.email_to == "user@example.com"
    assert product.last_price == 45.0
    assert product.last_stock_in is True
    assert product.last_checked_at == "2026-07-01T10:00:00"
    assert product.last_status_message == "Fiyat: 45.0 TL"

    serialized = product.to_dict()
    assert serialized == data


def test_history_point_creation_and_serialization():
    # Test creation now
    point = HistoryPoint.now("test-uuid", 45.0, True)
    assert point.product_id == "test-uuid"
    assert point.price == 45.0
    assert point.stock_in is True
    assert isinstance(point.checked_at, str)
    
    # Verify we can parse datetime from it
    dt = datetime.fromisoformat(point.checked_at)
    assert dt is not None

    # Test from_dict
    data = {
        "product_id": "test-uuid",
        "checked_at": "2026-07-01T10:00:00",
        "price": 45.0,
        "stock_in": True
    }
    point_from_dict = HistoryPoint.from_dict(data)
    assert point_from_dict.product_id == "test-uuid"
    assert point_from_dict.checked_at == "2026-07-01T10:00:00"
    assert point_from_dict.price == 45.0
    assert point_from_dict.stock_in is True

    assert point_from_dict.to_dict() == data
